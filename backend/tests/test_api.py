"""Testes de ponta a ponta da API (SQLite temporário).

Precisam de: pip install -r requirements-dev.txt   |   rodar: pytest  (dentro de backend/)
"""
import os
import tempfile
from datetime import timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("httpx")

# Precisa ser definido ANTES de importar a aplicação.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/teste.db"
os.environ["SECRET_KEY"] = "chave-de-teste-" + "x" * 40
os.environ["SEED"] = "0"
os.environ["STATIC_DIR"] = os.path.join(_tmp, "sem-frontend")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from tempo import agora  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:  # `with` dispara o lifespan (cria as tabelas)
        yield c


def _cadastrar(client, nome, email, papel, especialidade=None):
    r = client.post(
        "/api/auth/cadastro",
        json={"nome": nome, "email": email, "senha": "segredo1", "papel": papel, "especialidade": especialidade},
    )
    assert r.status_code == 201, r.text
    dados = r.json()
    return dados["usuario"], {"Authorization": f"Bearer {dados['access_token']}"}


def _gerar_amanha(client, headers, duracao=60, faixas=None):
    amanha = (agora() + timedelta(days=1)).date()
    return client.post(
        "/api/slots/gerar",
        headers=headers,
        json={
            "data_inicio": amanha.isoformat(),
            "data_fim": amanha.isoformat(),
            "dias_semana": [0, 1, 2, 3, 4, 5, 6],
            "faixas": faixas or [{"inicio": "08:00", "fim": "10:00"}],
            "duracao_min": duracao,
        },
    ), amanha


def _slots(client, headers, medico_id, dia):
    r = client.get(
        f"/api/medicos/{medico_id}/slots",
        headers=headers,
        params={"inicio": dia.isoformat(), "fim": dia.isoformat()},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_cadastro_validacoes(client):
    r = client.post(
        "/api/auth/cadastro",
        json={"nome": "Sem Esp", "email": "sem@x.com", "senha": "segredo1", "papel": "medico"},
    )
    assert r.status_code == 422  # médico precisa de especialidade

    _cadastrar(client, "Dr. Dup", "dup@x.com", "medico", "Clínica")
    r = client.post(
        "/api/auth/cadastro",
        json={"nome": "Outro", "email": "DUP@x.com", "senha": "segredo1", "papel": "paciente"},
    )
    assert r.status_code == 409


def test_login_e_rotas_protegidas(client):
    _cadastrar(client, "Paciente Login", "login@x.com", "paciente")
    ok = client.post("/api/auth/login", json={"email": "login@x.com", "senha": "segredo1"})
    assert ok.status_code == 200 and ok.json()["usuario"]["papel"] == "paciente"
    ruim = client.post("/api/auth/login", json={"email": "login@x.com", "senha": "errada"})
    assert ruim.status_code == 401
    assert client.get("/api/medicos").status_code == 401


def test_fluxo_completo_medico_cadastra_e_paciente_marca(client):
    medico, h_med = _cadastrar(client, "Dra. Fluxo", "fluxo@x.com", "medico", "Dermatologia")
    paciente, h_pac = _cadastrar(client, "Paciente Fluxo", "pfluxo@x.com", "paciente")

    r, dia = _gerar_amanha(client, h_med)
    assert r.status_code == 200 and r.json() == {"criados": 2, "ignorados": 0}

    # paciente busca o médico pela especialidade
    medicos = client.get("/api/medicos", headers=h_pac, params={"especialidade": "Dermatologia"}).json()
    assert [m["nome"] for m in medicos] == ["Dra. Fluxo"] and medicos[0]["horarios_livres"] == 2

    slots = _slots(client, h_pac, medico["id"], dia)
    assert [s["livre"] for s in slots] == [True, True]

    # paciente marca o primeiro horário
    r = client.post(f"/api/slots/{slots[0]['id']}/marcar", headers=h_pac)
    assert r.status_code == 200 and r.json()["minha"] is True

    # o médico vê o nome do paciente; outro paciente não vê
    visto_pelo_medico = _slots(client, h_med, medico["id"], dia)
    assert visto_pelo_medico[0]["paciente_nome"] == "Paciente Fluxo"
    _, h_outro = _cadastrar(client, "Outro Paciente", "outro@x.com", "paciente")
    visto_por_outro = _slots(client, h_outro, medico["id"], dia)
    assert visto_por_outro[0]["livre"] is False and visto_por_outro[0]["paciente_nome"] is None

    # listas de consultas
    assert len(client.get("/api/minhas-consultas", headers=h_pac).json()) == 1
    do_medico = client.get("/api/minhas-consultas", headers=h_med).json()
    assert do_medico[0]["paciente_nome"] == "Paciente Fluxo"


def test_nao_permite_marcar_horario_ocupado(client):
    medico, h_med = _cadastrar(client, "Dr. Corrida", "corrida@x.com", "medico", "Neurologia")
    _, h_a = _cadastrar(client, "Paciente A", "a@x.com", "paciente")
    _, h_b = _cadastrar(client, "Paciente B", "b@x.com", "paciente")
    _, dia = _gerar_amanha(client, h_med)
    slot_id = _slots(client, h_a, medico["id"], dia)[0]["id"]

    assert client.post(f"/api/slots/{slot_id}/marcar", headers=h_a).status_code == 200
    assert client.post(f"/api/slots/{slot_id}/marcar", headers=h_b).status_code == 409


def test_cancelar_libera_o_horario(client):
    medico, h_med = _cadastrar(client, "Dr. Cancela", "cancela@x.com", "medico", "Urologia")
    _, h_pac = _cadastrar(client, "Paciente Cancela", "pcancela@x.com", "paciente")
    _, h_b = _cadastrar(client, "Paciente Depois", "depois@x.com", "paciente")
    _, dia = _gerar_amanha(client, h_med)
    slot_id = _slots(client, h_pac, medico["id"], dia)[0]["id"]

    client.post(f"/api/slots/{slot_id}/marcar", headers=h_pac)
    assert client.post(f"/api/slots/{slot_id}/cancelar", headers=h_b).status_code == 404  # não é dele
    assert client.post(f"/api/slots/{slot_id}/cancelar", headers=h_pac).status_code == 204
    assert client.post(f"/api/slots/{slot_id}/marcar", headers=h_b).status_code == 200  # livre de novo


def test_permissoes_por_papel(client):
    medico, h_med = _cadastrar(client, "Dr. Perm", "perm@x.com", "medico", "Oftalmologia")
    _, h_pac = _cadastrar(client, "Paciente Perm", "pperm@x.com", "paciente")
    _, h_med2 = _cadastrar(client, "Dr. Outro", "outromed@x.com", "medico", "Oftalmologia")
    _, dia = _gerar_amanha(client, h_med)
    slot_id = _slots(client, h_pac, medico["id"], dia)[0]["id"]

    r, _ = _gerar_amanha(client, h_pac)
    assert r.status_code == 403  # paciente não cadastra horários
    assert client.post(f"/api/slots/{slot_id}/marcar", headers=h_med).status_code == 403  # médico não marca
    assert client.delete(f"/api/slots/{slot_id}", headers=h_pac).status_code == 403
    assert client.delete(f"/api/slots/{slot_id}", headers=h_med2).status_code == 404  # agenda de outro médico


def test_medico_remove_livre_mas_nao_ocupado(client):
    medico, h_med = _cadastrar(client, "Dr. Remove", "remove@x.com", "medico", "Endocrinologia")
    _, h_pac = _cadastrar(client, "Paciente Remove", "premove@x.com", "paciente")
    _, dia = _gerar_amanha(client, h_med)
    s1, s2 = [s["id"] for s in _slots(client, h_med, medico["id"], dia)]

    client.post(f"/api/slots/{s1}/marcar", headers=h_pac)
    assert client.delete(f"/api/slots/{s1}", headers=h_med).status_code == 409
    assert client.delete(f"/api/slots/{s2}", headers=h_med).status_code == 204
    assert len(_slots(client, h_med, medico["id"], dia)) == 1


def test_gerar_duas_vezes_nao_duplica(client):
    _, h_med = _cadastrar(client, "Dr. Repete", "repete@x.com", "medico", "Geriatria")
    r1, _ = _gerar_amanha(client, h_med)
    r2, _ = _gerar_amanha(client, h_med)
    assert r1.json()["criados"] == 2
    assert r2.json() == {"criados": 0, "ignorados": 2}


def test_validacao_do_periodo(client):
    _, h_med = _cadastrar(client, "Dr. Periodo", "periodo@x.com", "medico", "Psiquiatria")
    hoje = agora().date()
    corpo = {
        "data_inicio": hoje.isoformat(),
        "data_fim": (hoje - timedelta(days=1)).isoformat(),
        "dias_semana": [0],
        "faixas": [{"inicio": "08:00", "fim": "09:00"}],
        "duracao_min": 30,
    }
    assert client.post("/api/slots/gerar", headers=h_med, json=corpo).status_code == 422
    corpo["data_fim"] = hoje.isoformat()
    corpo["faixas"] = [{"inicio": "10:00", "fim": "09:00"}]
    assert client.post("/api/slots/gerar", headers=h_med, json=corpo).status_code == 422
