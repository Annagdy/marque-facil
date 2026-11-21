"""Dados de exemplo para demonstração (SEED=1).

Só roda se o banco estiver vazio. Senha de todos os usuários de exemplo: senha123
"""
from datetime import timedelta, time

from sqlalchemy.orm import Session

from models import Slot, Usuario
from security import gerar_hash
from slots_logic import gerar_slots
from tempo import agora

SENHA_DEMO = "senha123"

MEDICOS = [
    ("Dr. João Silva", "joao@marquefacil.test", "Cardiologia"),
    ("Dra. Maria Souza", "maria@marquefacil.test", "Ortopedia"),
    ("Dr. Pedro Lima", "pedro@marquefacil.test", "Pediatria"),
]
PACIENTES = [
    ("Ana Paciente", "ana@marquefacil.test"),
    ("Bruno Paciente", "bruno@marquefacil.test"),
]


def popular_banco(db: Session) -> bool:
    if db.query(Usuario).first():
        return False

    senha_hash = gerar_hash(SENHA_DEMO)
    medicos = [
        Usuario(nome=n, email=e, senha_hash=senha_hash, papel="medico", especialidade=esp)
        for n, e, esp in MEDICOS
    ]
    pacientes = [
        Usuario(nome=n, email=e, senha_hash=senha_hash, papel="paciente") for n, e in PACIENTES
    ]
    db.add_all(medicos + pacientes)
    db.flush()  # gera os ids

    hoje = agora().date()
    # Próximos 60 dias, de segunda a sexta, 08-12 e 14-17, consultas de 60 min.
    horarios = gerar_slots(
        hoje,
        hoje + timedelta(days=60),
        [0, 1, 2, 3, 4],
        [(time(8), time(12)), (time(14), time(17))],
        60,
    )
    limite = agora()
    for medico in medicos:
        db.add_all(
            Slot(medico_id=medico.id, inicio=i, fim=f) for i, f in horarios if i > limite
        )
    db.commit()
    return True
