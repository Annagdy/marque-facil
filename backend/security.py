from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from config import SECRET_KEY, TOKEN_EXPIRE_HORAS
from database import get_db
from models import Usuario

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode()[:72], bcrypt.gensalt()).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode()[:72], senha_hash.encode())
    except ValueError:
        return False


def criar_token(usuario: Usuario) -> str:
    expira = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HORAS)
    payload = {"sub": str(usuario.id), "papel": usuario.papel, "exp": expira}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def usuario_atual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Dependência: exige token válido e devolve o usuário logado."""
    erro = HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre novamente.")
    if cred is None:
        raise erro
    try:
        payload = jwt.decode(cred.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise erro
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise erro
    return usuario


def exige_papel(papel: str):
    """Dependência: além de logado, o usuário precisa ter o papel indicado."""

    def _verifica(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.papel != papel:
            raise HTTPException(status_code=403, detail=f"Ação permitida apenas para {papel}.")
        return usuario

    return _verifica
