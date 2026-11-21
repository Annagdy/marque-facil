from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class Usuario(Base):
    """Médico ou paciente (campo `papel`)."""

    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False, unique=True, index=True)
    senha_hash = Column(String(100), nullable=False)
    papel = Column(String(10), nullable=False)  # "medico" | "paciente"
    especialidade = Column(String(80))  # só para médicos


class Slot(Base):
    """Um horário na agenda de um médico.

    paciente_id vazio  -> horário livre
    paciente_id preenchido -> consulta marcada

    Uma única tabela representa "horário disponível" e "consulta marcada",
    então marcar é um UPDATE atômico (impede dois pacientes no mesmo horário).
    """

    __tablename__ = "slot"
    __table_args__ = (UniqueConstraint("medico_id", "inicio", name="uq_slot_medico_inicio"),)

    id = Column(Integer, primary_key=True)
    medico_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    inicio = Column(DateTime, nullable=False, index=True)
    fim = Column(DateTime, nullable=False)
    paciente_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True)

    medico = relationship("Usuario", foreign_keys=[medico_id])
    paciente = relationship("Usuario", foreign_keys=[paciente_id])
