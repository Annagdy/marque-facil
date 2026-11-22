#!/usr/bin/env python3
"""Teste de carga do Marque Fácil (só biblioteca padrão do Python 3.9+).

Cenários:
  health   GET /api/health                       (rede + balanceador + banco, sem login)
  login    POST /api/auth/login                  (custo de CPU: bcrypt)
  leitura  GET /api/medicos e /medicos/{id}/slots (consulta ao banco, com token)
  reserva  N pacientes disputam o MESMO horário  (correção sob concorrência)

Exemplos:
  python loadtest.py --url https://meu-app.exemplo.com --scenario health  -c 1,10,50,100 -d 30
  python loadtest.py --url https://meu-app.exemplo.com --scenario leitura -c 10,50 -d 30 --rotulo aws-ecs --csv resultados.csv
  python loadtest.py --url https://meu-app.exemplo.com --scenario reserva -c 20 --rodadas 5

Requer o banco com SEED=1 (usa joao@marquefacil.test / senha123 como médico de referência).
"""
import argparse
import csv
import http.client
import json
import os
import statistics
import sys
import threading
import time
import uuid
from datetime import date, timedelta
from urllib.parse import urlparse

SENHA = "senha123"
MEDICO_EMAIL = "joao@marquefacil.test"
PACIENTE_EMAIL = "ana@marquefacil.test"


class Cliente:
    """Uma conexão HTTP persistente (keep-alive) por thread, como um navegador faria."""

    def __init__(self, url, timeout=30):
        u = urlparse(url)
        self.https = u.scheme == "https"
        self.host = u.hostname
        self.port = u.port or (443 if self.https else 80)
        self.base = u.path.rstrip("/")
        self.timeout = timeout
        self.conn = None
        self.token = None

    def _abrir(self):
        cls = http.client.HTTPSConnection if self.https else http.client.HTTPConnection
        self.conn = cls(self.host, self.port, timeout=self.timeout)

    def req(self, metodo, caminho, corpo=None):
        """Devolve (status, json_ou_None, segundos). status 0 = falha de rede/timeout."""
        headers = {"Accept": "application/json"}
        dados = None
        if corpo is not None:
            dados = json.dumps(corpo).encode()
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        t0 = time.perf_counter()
        for tentativa in (1, 2):
            try:
                if self.conn is None:
                    self._abrir()
                self.conn.request(metodo, self.base + caminho, body=dados, headers=headers)
                r = self.conn.getresponse()
                raw = r.read()
                dt = time.perf_counter() - t0
                try:
                    return r.status, json.loads(raw) if raw else None, dt
                except ValueError:
                    return r.status, None, dt
            except (OSError, http.client.HTTPException):
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
                if tentativa == 2:
                    return 0, None, time.perf_counter() - t0
        return 0, None, time.perf_counter() - t0

    def login(self, email, senha=SENHA):
        st, js, _ = self.req("POST", "/api/auth/login", {"email": email, "senha": senha})
        if st != 200:
            raise SystemExit(f"Login falhou para {email} (HTTP {st}). O banco tem SEED=1?")
        self.token = js["access_token"]
        return js["usuario"]


def pct(valores, p):
    if not valores:
        return float("nan")
    v = sorted(valores)
    k = min(len(v) - 1, max(0, round(p / 100 * (len(v) - 1))))
    return v[k]


def resumo(rotulo, cenario, conc, duracao, amostras, extra=""):
    """amostras = lista de (status, segundos). Sucesso = 2xx."""
    total = len(amostras)
    ok = [dt for st, dt in amostras if 200 <= st < 300]
    erros = total - len(ok)
    return {
        "rotulo": rotulo, "cenario": cenario, "concorrencia": conc,
        "duracao_s": round(duracao, 1), "requisicoes": total, "erros": erros,
        "taxa_erro_pct": round(100 * erros / total, 2) if total else 0,
        "req_por_s": round(len(ok) / duracao, 1) if duracao else 0,
        "p50_ms": round(pct(ok, 50) * 1000, 1), "p95_ms": round(pct(ok, 95) * 1000, 1),
        "p99_ms": round(pct(ok, 99) * 1000, 1),
        "max_ms": round(max(ok) * 1000, 1) if ok else float("nan"),
        "media_ms": round(statistics.fmean(ok) * 1000, 1) if ok else float("nan"),
        "extra": extra,
    }


def rodar_carga(url, cenario, conc, duracao, aquecimento):
    """conc threads executando o cenário em laço por `duracao` segundos (após `aquecimento`)."""
    amostras = []
    trava = threading.Lock()
    inicio_medida = time.perf_counter() + aquecimento
    fim = inicio_medida + duracao
    prontos = threading.Barrier(conc + 1)
    ctx = preparar(url, cenario)

    def trabalhador(i):
        c = Cliente(url)
        passo = preparar_thread(c, cenario, ctx, i)
        local = []
        prontos.wait()
        while True:
            agora = time.perf_counter()
            if agora >= fim:
                break
            for st, dt in passo():
                if agora >= inicio_medida:
                    local.append((st, dt))
        with trava:
            amostras.extend(local)

    ths = [threading.Thread(target=trabalhador, args=(i,), daemon=True) for i in range(conc)]
    for t in ths:
        t.start()
    prontos.wait()
    for t in ths:
        t.join()
    return amostras


def preparar(url, cenario):
    """Dados compartilhados entre as threads (ex.: id do médico de referência)."""
    c = Cliente(url)
    c.login(PACIENTE_EMAIL)
    st, js, _ = c.req("GET", "/api/medicos")
    if st != 200 or not js:
        raise SystemExit(f"GET /api/medicos falhou (HTTP {st}). Banco sem dados?")
    return {"medico_id": js[0]["id"]}


def preparar_thread(c, cenario, ctx, i):
    hoje = date.today()
    qs = f"?inicio={hoje.isoformat()}&fim={(hoje + timedelta(days=30)).isoformat()}"
    if cenario == "health":
        return lambda: [c.req("GET", "/api/health")[::2]]
    if cenario == "login":
        # login completo a cada requisição: mede o custo do bcrypt
        return lambda: [c.req("POST", "/api/auth/login", {"email": PACIENTE_EMAIL, "senha": SENHA})[::2]]
    if cenario == "leitura":
        c.login(PACIENTE_EMAIL)  # fora da medição: só uma vez por usuário virtual
        def passo():
            a = c.req("GET", "/api/medicos")
            b = c.req("GET", f"/api/medicos/{ctx['medico_id']}/slots{qs}")
            return [a[::2], b[::2]]
        return passo
    raise SystemExit(f"Cenário desconhecido: {cenario}")


def cenario_reserva(url, conc, rodadas, rotulo):
    """conc pacientes tentam marcar o mesmo horário no mesmo instante. Esperado: 1x 200 e (conc-1)x 409."""
    run = uuid.uuid4().hex[:8]
    print(f"Cadastrando {conc} pacientes de teste (bcrypt: pode levar alguns segundos)...")
    clientes = []
    for i in range(conc):
        c = Cliente(url)
        st, js, _ = c.req("POST", "/api/auth/cadastro", {
            "nome": f"Carga {run} {i}", "email": f"carga-{run}-{i}@marquefacil.test",
            "senha": SENHA, "papel": "paciente"})
        if st != 201:
            raise SystemExit(f"Cadastro falhou (HTTP {st})")
        c.token = js["access_token"]
        clientes.append(c)

    adm = clientes[0]
    st, med, _ = adm.req("GET", "/api/medicos")
    hoje = date.today()
    st, slots, _ = adm.req("GET", f"/api/medicos/{med[0]['id']}/slots?inicio={hoje.isoformat()}&fim={(hoje + timedelta(days=60)).isoformat()}")
    livres = [s["id"] for s in slots if s["livre"]]
    if len(livres) < rodadas:
        raise SystemExit(f"Só há {len(livres)} horários livres; reduza --rodadas ou rode o seed de novo.")

    linhas = []
    for r, slot_id in enumerate(livres[:rodadas], 1):
        barreira = threading.Barrier(conc)
        resultados = [None] * conc

        def disputar(i):
            barreira.wait()
            resultados[i] = clientes[i].req("POST", f"/api/slots/{slot_id}/marcar")

        ths = [threading.Thread(target=disputar, args=(i,)) for i in range(conc)]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        ganhadores = [i for i, x in enumerate(resultados) if x[0] == 200]
        conflitos = sum(1 for x in resultados if x[0] == 409)
        outros = conc - len(ganhadores) - conflitos
        lat = [x[2] * 1000 for x in resultados]
        certo = len(ganhadores) == 1 and outros == 0
        print(f"  rodada {r}: ganhadores={len(ganhadores)} conflitos(409)={conflitos} outros={outros} "
              f"p50={statistics.median(lat):.0f}ms max={max(lat):.0f}ms  {'OK' if certo else 'FALHA'}")
        linhas.append({
            "rotulo": rotulo, "cenario": "reserva", "concorrencia": conc, "duracao_s": "",
            "requisicoes": conc, "erros": outros, "taxa_erro_pct": round(100 * outros / conc, 2),
            "req_por_s": "", "p50_ms": round(statistics.median(lat), 1), "p95_ms": round(pct(lat, 95), 1),
            "p99_ms": round(pct(lat, 99), 1), "max_ms": round(max(lat), 1), "media_ms": round(statistics.fmean(lat), 1),
            "extra": f"rodada={r};ganhadores={len(ganhadores)};409={conflitos}",
        })
        for i in ganhadores:  # devolve o horário para o banco ficar como estava
            clientes[i].req("POST", f"/api/slots/{slot_id}/cancelar")
    return linhas


CAMPOS = ["data_hora", "rotulo", "cenario", "concorrencia", "duracao_s", "requisicoes", "erros",
          "taxa_erro_pct", "req_por_s", "p50_ms", "p95_ms", "p99_ms", "max_ms", "media_ms", "extra"]


def imprimir(linhas):
    cab = ["cenario", "concorrencia", "requisicoes", "erros", "req_por_s", "p50_ms", "p95_ms", "p99_ms", "max_ms"]
    print("\n" + " | ".join(f"{h:>12}" for h in cab))
    for l in linhas:
        print(" | ".join(f"{str(l[h]):>12}" for h in cab))


def salvar_csv(caminho, linhas):
    novo = not os.path.exists(caminho)
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        agora = time.strftime("%Y-%m-%d %H:%M:%S")
        for l in linhas:
            w.writerow({"data_hora": agora, **l})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", required=True, help="Endereço base, ex.: https://meu-app.exemplo.com")
    p.add_argument("--scenario", "-s", required=True, choices=["health", "login", "leitura", "reserva"])
    p.add_argument("--concurrency", "-c", default="10", help="Usuários simultâneos; lista separada por vírgula (ex.: 1,10,50)")
    p.add_argument("--duration", "-d", type=float, default=30, help="Segundos medidos por nível (padrão 30)")
    p.add_argument("--warmup", type=float, default=5, help="Segundos de aquecimento descartados (padrão 5)")
    p.add_argument("--rodadas", type=int, default=5, help="Só no cenário reserva: quantos horários disputar")
    p.add_argument("--rotulo", default="", help="Nome da implantação (ex.: aws-ecs, azure-aca); vai para o CSV")
    p.add_argument("--csv", help="Arquivo CSV onde acrescentar os resultados")
    a = p.parse_args()

    niveis = [int(x) for x in a.concurrency.split(",") if x.strip()]
    linhas = []
    if a.scenario == "reserva":
        for n in niveis:
            linhas += cenario_reserva(a.url, n, a.rodadas, a.rotulo)
    else:
        for n in niveis:
            print(f"{a.scenario}: {n} usuários simultâneos por {a.duration:.0f}s (+{a.warmup:.0f}s de aquecimento)...")
            am = rodar_carga(a.url, a.scenario, n, a.duration, a.warmup)
            linhas.append(resumo(a.rotulo, a.scenario, n, a.duration, am))
    imprimir(linhas)
    if a.csv:
        salvar_csv(a.csv, linhas)
        print(f"\nResultados acrescentados em {a.csv}")


if __name__ == "__main__":
    sys.exit(main())
