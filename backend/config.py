"""Configuração lida de variáveis de ambiente.

Nada de senha ou endereço fixo no código: na nuvem, tudo isso é definido no
painel/CLI do serviço (App Runner, Container Apps etc.).
"""
import os
from pathlib import Path


def _database_url() -> str:
    # Sem DATABASE_URL usa SQLite local (bom para desenvolvimento).
    url = os.getenv("DATABASE_URL", "sqlite:///./marquefacil.db")
    # Alguns provedores entregam "postgres://", que o SQLAlchemy 2 não aceita.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _database_url()

# Em produção SEMPRE defina SECRET_KEY (ex.: openssl rand -hex 32).
SECRET_KEY_PADRAO = "dev-insecure-key-troque-em-producao-0123456789"
SECRET_KEY = os.getenv("SECRET_KEY") or SECRET_KEY_PADRAO
TOKEN_EXPIRE_HORAS = int(os.getenv("TOKEN_EXPIRE_HORAS", "8"))

# Os horários são guardados como "hora de parede" da clínica (sem fuso).
# Containers na AWS/Azure rodam em UTC, então o "agora" é calculado aqui.
TZ_CLINICA = os.getenv("TZ_CLINICA", "America/Sao_Paulo")

# Só necessário se o frontend for servido de outro endereço (ex.: vite dev).
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

# SEED=1 cria médicos/pacientes/horários de exemplo se o banco estiver vazio.
SEED = os.getenv("SEED", "0") == "1"

# Pasta com o build do Vue (copiada para dentro da imagem Docker).
STATIC_DIR = Path(os.getenv("STATIC_DIR", str(Path(__file__).parent / "static")))
