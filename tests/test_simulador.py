"""Simulador de poupança: as contas dos juros compostos."""

import pytest

from simulador import simular_poupanca


def test_sem_juros_o_valor_e_o_que_se_depositou():
    anos = simular_poupanca(mensal=50, anos=2, taxa_anual=0)

    assert [a.ano for a in anos] == [1, 2]
    assert anos[0].depositado == pytest.approx(600)  # 12 meses x 50 €
    assert anos[1].depositado == pytest.approx(1200)
    assert anos[1].valor == pytest.approx(1200)


def test_com_juros_o_valor_e_maior_do_que_o_depositado():
    anos = simular_poupanca(mensal=50, anos=10, taxa_anual=3)

    assert len(anos) == 10
    assert anos[-1].depositado == pytest.approx(6000)
    # Calculado à parte com a fórmula da renda: 50 x ((1 + 0,03/12)^120 - 1) / (0,03/12) = 6987,07 €.
    # O saldo ganha juros antes de entrar a poupança do mês, por isso o último depósito não chega a render.
    assert anos[-1].valor == pytest.approx(6987.07, abs=0.01)


def test_os_valores_vem_arredondados_ao_centimo():
    anos = simular_poupanca(mensal=33.33, anos=3, taxa_anual=2.5)

    for ano in anos:
        assert ano.valor == round(ano.valor, 2)
        assert ano.depositado == round(ano.depositado, 2)
