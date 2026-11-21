import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import models  # noqa: F401  (registra as tabelas no Base)
from config import CORS_ORIGINS, SECRET_KEY, SECRET_KEY_PADRAO, SEED, STATIC_DIR
from database import Base, SessionLocal, engine
from routers import auth, medicos, slots
from seed import popular_banco

log = logging.getLogger("marquefacil")


def _criar_tabelas(tentativas: int = 30, espera: float = 2.0) -> None:
    """Cria as tabelas. Na nuvem o banco pode demorar a ficar pronto: tenta de novo."""
    for n in range(1, tentativas + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError as exc:
            log.warning("Banco indisponível (%d/%d): %s", n, tentativas, exc.__cause__ or exc)
            if n == tentativas:
                raise
            time.sleep(espera)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if SECRET_KEY == SECRET_KEY_PADRAO:
        log.warning("SECRET_KEY não definida: usando chave de desenvolvimento (inseguro).")
    _criar_tabelas()
    if SEED:
        with SessionLocal() as db:
            if popular_banco(db):
                log.info("Banco populado com dados de exemplo.")
    yield


app = FastAPI(title="Marque Fácil", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(medicos.router)
app.include_router(slots.router)


@app.get("/api/health", tags=["Infra"])
def health():
    """Usado pelo load balancer / health check da AWS e do Azure. Testa o banco também."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Banco indisponível.")
    return {"status": "ok"}


# ───────────── Frontend (build do Vue) servido pelo próprio FastAPI ─────────────
# Em produção a imagem Docker traz o build em ./static, então só há 1 container
# e 1 endereço: o navegador chama /api/... no mesmo domínio (sem CORS).
if STATIC_DIR.is_dir():
    _raiz = STATIC_DIR.resolve()

    if (_raiz / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_raiz / "assets"), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def frontend(caminho: str):
        if caminho == "api" or caminho.startswith("api/"):
            raise HTTPException(status_code=404, detail="Não encontrado.")
        arquivo = (_raiz / caminho).resolve()
        if caminho and arquivo.is_file() and arquivo.is_relative_to(_raiz):
            return FileResponse(arquivo)
        # Qualquer outra rota é do vue-router (SPA): devolve o index.html.
        return FileResponse(_raiz / "index.html")
