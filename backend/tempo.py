from datetime import datetime
from zoneinfo import ZoneInfo

from config import TZ_CLINICA


def agora() -> datetime:
    """Data/hora atual no fuso da clínica, sem tzinfo (igual ao que está no banco)."""
    return datetime.now(ZoneInfo(TZ_CLINICA)).replace(tzinfo=None)
