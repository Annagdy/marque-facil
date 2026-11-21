"""Testes da lógica pura de horários (não precisam de FastAPI nem de banco)."""
from datetime import date, datetime, time

import pytest

from slots_logic import MAX_SLOTS, filtrar_sobrepostos, gerar_slots

SEG_A_SEX = [0, 1, 2, 3, 4]


def test_uma_faixa_corta_em_blocos():
    # 2026-11-23 é uma segunda-feira
    slots = gerar_slots(date(2026, 11, 23), date(2026, 11, 23), SEG_A_SEX, [(time(8), time(10))], 30)
    assert [(i.strftime("%H:%M"), f.strftime("%H:%M")) for i, f in slots] == [
        ("08:00", "08:30"),
        ("08:30", "09:00"),
        ("09:00", "09:30"),
        ("09:30", "10:00"),
    ]


def test_ultimo_bloco_so_entra_se_couber():
    slots = gerar_slots(date(2026, 11, 23), date(2026, 11, 23), SEG_A_SEX, [(time(8), time(9, 45))], 30)
    assert len(slots) == 3  # 08:00, 08:30, 09:00 (09:30-10:00 passaria do fim)


def test_duas_faixas_com_almoco():
    slots = gerar_slots(
        date(2026, 11, 23), date(2026, 11, 23), SEG_A_SEX, [(time(8), time(12)), (time(14), time(18))], 60
    )
    horas = [i.hour for i, _ in slots]
    assert horas == [8, 9, 10, 11, 14, 15, 16, 17]


def test_so_gera_nos_dias_da_semana_escolhidos():
    # 23/11 (seg) a 29/11 (dom), apenas terça e quinta
    slots = gerar_slots(date(2026, 11, 23), date(2026, 11, 29), [1, 3], [(time(8), time(9))], 60)
    assert [i.date() for i, _ in slots] == [date(2026, 11, 24), date(2026, 11, 26)]


def test_ano_inteiro_seg_a_sex():
    slots = gerar_slots(date(2027, 1, 1), date(2027, 12, 31), SEG_A_SEX, [(time(8), time(12))], 60)
    assert len(slots) == 261 * 4  # 2027 tem 261 dias úteis (seg-sex)


def test_duracao_invalida():
    with pytest.raises(ValueError):
        gerar_slots(date(2026, 11, 23), date(2026, 11, 23), SEG_A_SEX, [(time(8), time(9))], 0)


def test_limite_de_horarios():
    with pytest.raises(ValueError):
        gerar_slots(date(2026, 1, 1), date(2026, 12, 31), [0, 1, 2, 3, 4, 5, 6], [(time(0, 0), time(23, 59))], 5)
    assert MAX_SLOTS == 10000


def _dt(h, m=0, dia=23):
    return datetime(2026, 11, dia, h, m)


def test_filtra_sobreposicao_com_existentes():
    existentes = [(_dt(9), _dt(10))]
    novos = [(_dt(8), _dt(9)), (_dt(9), _dt(10)), (_dt(9, 30), _dt(10, 30)), (_dt(10), _dt(11))]
    aceitos, ignorados = filtrar_sobrepostos(novos, existentes)
    # 08-09 encosta mas não sobrepõe; 10-11 idem. 09-10 e 09:30-10:30 colidem.
    assert aceitos == [(_dt(8), _dt(9)), (_dt(10), _dt(11))]
    assert ignorados == 2


def test_filtra_sobreposicao_entre_novos():
    # faixas 08-12 e 10-14 geram horários que se sobrepõem entre si
    novos = gerar_slots(date(2026, 11, 23), date(2026, 11, 23), SEG_A_SEX, [(time(8), time(12)), (time(10), time(14))], 60)
    aceitos, ignorados = filtrar_sobrepostos(novos, [])
    assert [i.hour for i, _ in aceitos] == [8, 9, 10, 11, 12, 13]
    assert ignorados == 2


def test_dias_diferentes_nao_colidem():
    aceitos, ignorados = filtrar_sobrepostos([(_dt(9, dia=24), _dt(10, dia=24))], [(_dt(9), _dt(10))])
    assert len(aceitos) == 1 and ignorados == 0
