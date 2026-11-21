from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import and_, update
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Slot, Usuario
from schemas import ConsultaOut, GerarSlotsIn, GerarSlotsOut, SlotOut
from security import exige_papel, usuario_atual
from slots_logic import filtrar_sobrepostos, gerar_slots
from tempo import agora

router = APIRouter(prefix="/api", tags=["Agenda"])

MAX_DIAS_CONSULTA = 400


def _limites(inicio: date, fim: date) -> tuple[datetime, datetime]:
    """[início do 1º dia, início do dia seguinte ao último)."""
    return datetime.combine(inicio, time.min), datetime.combine(fim + timedelta(days=1), time.min)


# ───────────── Calendário (médico e paciente usam o mesmo endpoint) ─────────────

@router.get("/medicos/{medico_id}/slots", response_model=list[SlotOut])
def listar_slots(
    medico_id: int,
    inicio: date,
    fim: date,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    """Horários do médico no período: livres e ocupados.

    O nome do paciente só é revelado ao próprio médico dono da agenda.
    """
    if fim < inicio or (fim - inicio).days > MAX_DIAS_CONSULTA:
        raise HTTPException(status_code=400, detail="Período inválido.")
    medico = db.get(Usuario, medico_id)
    if medico is None or medico.papel != "medico":
        raise HTTPException(status_code=404, detail="Médico não encontrado.")

    de, ate = _limites(inicio, fim)
    slots = (
        db.query(Slot)
        .options(joinedload(Slot.paciente))
        .filter(Slot.medico_id == medico_id, Slot.inicio >= de, Slot.inicio < ate)
        .order_by(Slot.inicio)
        .all()
    )
    dono = usuario.id == medico_id
    return [
        SlotOut(
            id=s.id,
            inicio=s.inicio,
            fim=s.fim,
            livre=s.paciente_id is None,
            minha=s.paciente_id == usuario.id,
            paciente_nome=s.paciente.nome if (dono and s.paciente) else None,
        )
        for s in slots
    ]


# ───────────── Médico: cadastrar / remover horários ─────────────

@router.post("/slots/gerar", response_model=GerarSlotsOut)
def gerar(
    dados: GerarSlotsIn,
    db: Session = Depends(get_db),
    medico: Usuario = Depends(exige_papel("medico")),
):
    """Cadastra os horários do médico em lote (ex.: o ano inteiro).

    Ex.: de 01/01 a 31/12, seg a sex, 08-12 e 14-18, consultas de 30 min.
    """
    try:
        novos = gerar_slots(
            dados.data_inicio,
            dados.data_fim,
            dados.dias_semana,
            [(f.inicio, f.fim) for f in dados.faixas],
            dados.duracao_min,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    agora_ = agora()
    futuros = [s for s in novos if s[0] > agora_]
    no_passado = len(novos) - len(futuros)

    de, ate = _limites(dados.data_inicio, dados.data_fim)
    existentes = (
        db.query(Slot.inicio, Slot.fim)
        .filter(Slot.medico_id == medico.id, Slot.inicio >= de, Slot.inicio < ate)
        .all()
    )
    aceitos, sobrepostos = filtrar_sobrepostos(futuros, [(i, f) for i, f in existentes])

    db.add_all([Slot(medico_id=medico.id, inicio=i, fim=f) for i, f in aceitos])
    db.commit()
    return GerarSlotsOut(criados=len(aceitos), ignorados=no_passado + sobrepostos)


@router.delete("/slots/{slot_id}", status_code=204)
def remover(
    slot_id: int,
    db: Session = Depends(get_db),
    medico: Usuario = Depends(exige_papel("medico")),
):
    """Remove um horário LIVRE do próprio médico."""
    apagados = (
        db.query(Slot)
        .filter(Slot.id == slot_id, Slot.medico_id == medico.id, Slot.paciente_id.is_(None))
        .delete(synchronize_session=False)
    )
    db.commit()
    if apagados == 0:
        slot = db.get(Slot, slot_id)
        if slot is None or slot.medico_id != medico.id:
            raise HTTPException(status_code=404, detail="Horário não encontrado.")
        raise HTTPException(
            status_code=409,
            detail="Há um paciente neste horário. Cancele a consulta antes de remover.",
        )
    return Response(status_code=204)


# ───────────── Paciente: marcar / cancelar ─────────────

@router.post("/slots/{slot_id}/marcar", response_model=SlotOut)
def marcar(
    slot_id: int,
    db: Session = Depends(get_db),
    paciente: Usuario = Depends(exige_papel("paciente")),
):
    """Marca a consulta.

    O UPDATE só acontece se o horário ainda estiver livre e no futuro; assim,
    se dois pacientes clicarem juntos, só um consegue.
    """
    resultado = db.execute(
        update(Slot)
        .where(Slot.id == slot_id, Slot.paciente_id.is_(None), Slot.inicio > agora())
        .values(paciente_id=paciente.id)
    )
    db.commit()

    if resultado.rowcount == 0:
        slot = db.get(Slot, slot_id)
        if slot is None:
            raise HTTPException(status_code=404, detail="Horário não encontrado.")
        if slot.paciente_id is not None:
            raise HTTPException(status_code=409, detail="Este horário acabou de ser ocupado.")
        raise HTTPException(status_code=400, detail="Este horário já passou.")

    slot = db.get(Slot, slot_id)
    return SlotOut(id=slot.id, inicio=slot.inicio, fim=slot.fim, livre=False, minha=True)


@router.post("/slots/{slot_id}/cancelar", status_code=204)
def cancelar(
    slot_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    """Cancela uma consulta futura e libera o horário.

    O paciente cancela a sua; o médico cancela qualquer uma da sua agenda.
    """
    if usuario.papel == "paciente":
        dono = Slot.paciente_id == usuario.id
    else:
        dono = and_(Slot.medico_id == usuario.id, Slot.paciente_id.isnot(None))

    resultado = db.execute(
        update(Slot)
        .where(Slot.id == slot_id, dono, Slot.inicio > agora())
        .values(paciente_id=None)
    )
    db.commit()
    if resultado.rowcount == 0:
        raise HTTPException(status_code=404, detail="Consulta não encontrada ou já realizada.")
    return Response(status_code=204)


# ───────────── Lista de consultas do usuário logado ─────────────

@router.get("/minhas-consultas", response_model=list[ConsultaOut])
def minhas_consultas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    """Paciente: consultas que marcou. Médico: consultas marcadas na sua agenda."""
    query = db.query(Slot).options(joinedload(Slot.medico), joinedload(Slot.paciente))
    if usuario.papel == "paciente":
        query = query.filter(Slot.paciente_id == usuario.id)
    else:
        query = query.filter(Slot.medico_id == usuario.id, Slot.paciente_id.isnot(None))

    agora_ = agora()
    return [
        ConsultaOut(
            id=s.id,
            inicio=s.inicio,
            fim=s.fim,
            medico_nome=s.medico.nome,
            especialidade=s.medico.especialidade,
            paciente_nome=s.paciente.nome,
            passada=s.inicio <= agora_,
        )
        for s in query.order_by(Slot.inicio).limit(500).all()
    ]
