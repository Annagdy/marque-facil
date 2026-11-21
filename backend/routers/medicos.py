from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Slot, Usuario
from schemas import MedicoOut
from security import usuario_atual
from tempo import agora

router = APIRouter(prefix="/api", tags=["Médicos"])


def _livres_por_medico(db: Session) -> dict[int, int]:
    linhas = (
        db.query(Slot.medico_id, func.count(Slot.id))
        .filter(Slot.paciente_id.is_(None), Slot.inicio >= agora())
        .group_by(Slot.medico_id)
        .all()
    )
    return {medico_id: total for medico_id, total in linhas}


@router.get("/especialidades", response_model=list[str])
def listar_especialidades(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    linhas = (
        db.query(Usuario.especialidade)
        .filter(Usuario.papel == "medico", Usuario.especialidade.isnot(None))
        .distinct()
        .order_by(Usuario.especialidade)
        .all()
    )
    return [esp for (esp,) in linhas]


@router.get("/medicos", response_model=list[MedicoOut])
def listar_medicos(
    especialidade: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    """Busca médicos por especialidade e/ou parte do nome."""
    query = db.query(Usuario).filter(Usuario.papel == "medico")
    if especialidade:
        query = query.filter(Usuario.especialidade == especialidade)
    if q:
        query = query.filter(Usuario.nome.ilike(f"%{q.strip()}%"))

    livres = _livres_por_medico(db)
    return [
        MedicoOut(
            id=m.id,
            nome=m.nome,
            especialidade=m.especialidade,
            horarios_livres=livres.get(m.id, 0),
        )
        for m in query.order_by(Usuario.nome).all()
    ]


@router.get("/medicos/{medico_id}", response_model=MedicoOut)
def buscar_medico(
    medico_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    medico = db.get(Usuario, medico_id)
    if medico is None or medico.papel != "medico":
        raise HTTPException(status_code=404, detail="Médico não encontrado.")
    return MedicoOut(
        id=medico.id,
        nome=medico.nome,
        especialidade=medico.especialidade,
        horarios_livres=_livres_por_medico(db).get(medico.id, 0),
    )
