"""Regras puras de geração de horários (sem banco, sem FastAPI).

Fica separado para ser fácil de testar e de explicar.
dias_semana usa a convenção do Python: 0 = segunda ... 6 = domingo.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta

MAX_SLOTS = 10000


def gerar_slots(
    data_inicio: date,
    data_fim: date,
    dias_semana,
    faixas: list[tuple[time, time]],
    duracao_min: int,
) -> list[tuple[datetime, datetime]]:
    """Gera (inicio, fim) de cada consulta nos dias da semana escolhidos.

    Cada faixa (ex.: 08:00-12:00) é cortada em blocos de `duracao_min`;
    o último bloco só entra se couber inteiro na faixa.
    """
    if duracao_min <= 0:
        raise ValueError("A duração deve ser maior que zero.")

    duracao = timedelta(minutes=duracao_min)
    dias = set(dias_semana)
    resultado: list[tuple[datetime, datetime]] = []

    dia = data_inicio
    while dia <= data_fim:
        if dia.weekday() in dias:
            for hora_ini, hora_fim in faixas:
                atual = datetime.combine(dia, hora_ini)
                limite = datetime.combine(dia, hora_fim)
                while atual + duracao <= limite:
                    resultado.append((atual, atual + duracao))
                    atual += duracao
                    if len(resultado) > MAX_SLOTS:
                        raise ValueError(
                            f"Muitos horários de uma vez (máximo {MAX_SLOTS}). "
                            "Reduza o período ou aumente a duração."
                        )
        dia += timedelta(days=1)

    return resultado


def sobrepoe(a_ini: datetime, a_fim: datetime, b_ini: datetime, b_fim: datetime) -> bool:
    return a_ini < b_fim and b_ini < a_fim


def filtrar_sobrepostos(
    novos: list[tuple[datetime, datetime]],
    existentes: list[tuple[datetime, datetime]],
) -> tuple[list[tuple[datetime, datetime]], int]:
    """Remove horários novos que colidem com os já cadastrados (ou entre si).

    Retorna (aceitos, quantidade_ignorada).
    """
    por_dia: dict[date, list[tuple[datetime, datetime]]] = defaultdict(list)
    for ini, fim in existentes:
        por_dia[ini.date()].append((ini, fim))

    aceitos: list[tuple[datetime, datetime]] = []
    for ini, fim in sorted(novos):
        ocupados = por_dia[ini.date()]
        if any(sobrepoe(ini, fim, o_ini, o_fim) for o_ini, o_fim in ocupados):
            continue
        ocupados.append((ini, fim))
        aceitos.append((ini, fim))

    return aceitos, len(novos) - len(aceitos)
