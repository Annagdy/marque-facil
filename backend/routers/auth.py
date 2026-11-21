from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from schemas import CadastroIn, LoginIn, TokenOut, UsuarioOut
from security import criar_token, gerar_hash, usuario_atual, verificar_senha

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


def _resposta(usuario: Usuario) -> TokenOut:
    return TokenOut(
        access_token=criar_token(usuario),
        usuario=UsuarioOut.model_validate(usuario),
    )


@router.post("/cadastro", response_model=TokenOut, status_code=201)
def cadastro(dados: CadastroIn, db: Session = Depends(get_db)):
    """Cria conta de médico ou paciente e já devolve o token (login automático)."""
    email = dados.email.strip().lower()
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(status_code=409, detail="Já existe uma conta com este e-mail.")

    usuario = Usuario(
        nome=dados.nome.strip(),
        email=email,
        senha_hash=gerar_hash(dados.senha),
        papel=dados.papel,
        especialidade=dados.especialidade,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe uma conta com este e-mail.")
    db.refresh(usuario)
    return _resposta(usuario)


@router.post("/login", response_model=TokenOut)
def login(dados: LoginIn, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email.strip().lower()).first()
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    return _resposta(usuario)


@router.get("/eu", response_model=UsuarioOut)
def eu(usuario: Usuario = Depends(usuario_atual)):
    return usuario
