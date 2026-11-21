# Marque Fácil (versão simplificada)

Agendamento de consultas com três peças:

| Papel | O que faz |
|---|---|
| **Médico** | Cadastra seus horários no calendário (inclusive o ano inteiro de uma vez) e vê quem marcou |
| **Paciente** | Busca o médico por nome/especialidade e marca a consulta num horário livre |
| **Calendário** | Tela única usada pelos dois: mostra os horários do médico; o paciente marca, o médico gerencia |

Stack: **Vue 3 + Vite** (frontend) · **FastAPI + SQLAlchemy** (API) · **PostgreSQL** (SQLite em desenvolvimento).
Na produção é **1 imagem Docker / 1 container**: o FastAPI serve a API em `/api` e o frontend compilado.

---

## Rodar localmente

### Opção A — Docker (igual ao que vai para a nuvem)

```bash
docker compose up --build
```

Abra http://localhost:8080. O compose sobe a aplicação + um PostgreSQL e cria dados de exemplo (`SEED=1`).

Contas de exemplo (senha de todas: `senha123`):

| Papel | E-mail |
|---|---|
| Médico | `joao@marquefacil.test` (Cardiologia), `maria@marquefacil.test`, `pedro@marquefacil.test` |
| Paciente | `ana@marquefacil.test`, `bruno@marquefacil.test` |

Parar e apagar o banco local: `docker compose down -v`

### Opção B — sem Docker (dois terminais)

```bash
# 1) API  (Python 3.11+)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
SEED=1 uvicorn main:app --reload --port 8080            # Windows (PowerShell): $env:SEED=1; uvicorn main:app --reload --port 8080

# 2) Frontend  (Node 20+)
cd frontend
npm install
npm run dev                                             # http://localhost:5173  (o Vite encaminha /api para a porta 8080)
```

Sem `DATABASE_URL`, a API usa um arquivo SQLite (`backend/marquefacil.db`).

### Testes

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

- `tests/test_slots_logic.py`: regras de geração de horários.
- `tests/test_api.py`: fluxo completo pela API (cadastro, gerar horários, marcar, conflito, cancelar, permissões).

---

## Variáveis de ambiente

| Variável | Para quê | Padrão |
|---|---|---|
| `DATABASE_URL` | Banco. Ex.: `postgresql://usuario:senha@host:5432/marquefacil` | SQLite local |
| `SECRET_KEY` | Assina os tokens de login. **Obrigatória em produção** (`openssl rand -hex 32`) | chave de desenvolvimento (insegura) |
| `PORT` | Porta do servidor | `8080` |
| `SEED` | `1` = cria dados de exemplo se o banco estiver vazio | `0` |
| `TZ_CLINICA` | Fuso usado para decidir se um horário já passou | `America/Sao_Paulo` |
| `CORS_ORIGINS` | Só se o frontend ficar em outro endereço | `http://localhost:5173` |
| `TOKEN_EXPIRE_HORAS` | Validade do login | `8` |

Nenhuma senha ou endereço fica no código nem no repositório.

---

## API

Documentação interativa em `/docs` (Swagger). Tudo em `/api`:

| Método | Rota | Quem | O que faz |
|---|---|---|---|
| POST | `/auth/cadastro` | público | Cria médico ou paciente e já devolve o token |
| POST | `/auth/login` | público | Login por e-mail e senha |
| GET | `/especialidades` | logado | Especialidades existentes (filtro da busca) |
| GET | `/medicos?q=&especialidade=` | logado | Busca médicos (mostra nº de horários livres) |
| GET | `/medicos/{id}` | logado | Dados de um médico |
| GET | `/medicos/{id}/slots?inicio=&fim=` | logado | **Calendário**: horários livres/ocupados do período |
| POST | `/slots/gerar` | médico | Cadastra horários em lote (período + dias da semana + turnos + duração) |
| DELETE | `/slots/{id}` | médico | Remove um horário livre |
| POST | `/slots/{id}/marcar` | paciente | Marca a consulta (atômico: só um paciente consegue) |
| POST | `/slots/{id}/cancelar` | paciente / médico | Cancela e libera o horário |
| GET | `/minhas-consultas` | logado | Consultas do paciente / marcadas na agenda do médico |
| GET | `/health` | público | Health check (testa o banco) — usado pelo balanceador na nuvem |

## Modelo de dados

```
usuario (id, nome, email*, senha_hash, papel['medico'|'paciente'], especialidade)
slot    (id, medico_id→usuario, inicio, fim, paciente_id→usuario | NULL = livre)
        UNIQUE(medico_id, inicio)
```

`paciente_id` vazio = horário livre; preenchido = consulta marcada. Marcar é um `UPDATE ... WHERE paciente_id IS NULL`,
então dois pacientes clicando ao mesmo tempo nunca ficam com o mesmo horário.

## Estrutura

```
backend/
  main.py            app, startup (cria tabelas), health, serve o frontend
  config.py          variáveis de ambiente
  database.py        engine/sessão
  models.py          Usuario, Slot
  schemas.py         validação de entrada/saída
  security.py        senha (bcrypt), JWT, controle por papel
  slots_logic.py     geração de horários (função pura, testada)
  seed.py            dados de exemplo
  routers/           auth.py · medicos.py · slots.py
  tests/
frontend/src/
  pages/             Login · Cadastro · Medicos · Calendario · Consultas
  components/        NavBar
  api.js  auth.js  router.js
Dockerfile           build do Vue + API Python em uma imagem
compose.yaml         uso local (app + PostgreSQL)
```
