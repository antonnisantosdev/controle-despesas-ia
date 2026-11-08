"""Contas do plano de poupança: são feitas em Python, e a IA só as explica."""

from datetime import date

from objetivos import meses_ate

HOJE = date(2026, 11, 8)


def test_meses_ate_conta_o_mes_atual():
    # De 8 de novembro a julho do ano seguinte: nov, dez, jan, fev, mar, abr, mai, jun, jul.
    assert meses_ate(date(2027, 7, 1), hoje=HOJE) == 9
    # O dia do mês não conta: no fim de novembro faltam os mesmos 9 meses.
    assert meses_ate(date(2027, 7, 1), hoje=date(2026, 11, 30)) == 9


def test_prazo_ja_passou_da_zero():
    # Sem meses para poupar: quem chama a função sabe que o prazo terminou.
    assert meses_ate(date(2026, 10, 1), hoje=HOJE) == 0


def test_prazo_no_mesmo_mes_da_um():
    # Ainda há o mês atual para juntar o dinheiro. Também vale para um prazo que é hoje.
    assert meses_ate(date(2026, 11, 30), hoje=HOJE) == 1
    assert meses_ate(HOJE, hoje=HOJE) == 1


def test_viragem_de_ano():
    # Dezembro e janeiro: a diferença de anos (+12) e de meses (1 - 12 = -11) tem de dar 2.
    assert meses_ate(date(2027, 1, 15), hoje=date(2026, 12, 20)) == 2
