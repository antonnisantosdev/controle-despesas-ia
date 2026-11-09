"""Custo de cada chamada à IA: é o que diz quanto custa servir cada utilizador."""

import pytest

from ia import custo_em_dolares


def test_um_milhao_de_tokens_custa_o_preco_da_tabela():
    assert custo_em_dolares("claude-haiku-5-5", 1_000_000, 0) == pytest.approx(0.10)
    assert custo_em_dolares("claude-haiku-5-5", 0, 1_000_000) == pytest.approx(0.50)


def test_soma_entrada_e_saida():
    # 2000 tokens de entrada e 500 de saída: 0,0002 + 0,00025 = 0,00045 dólares.
    assert custo_em_dolares("claude-haiku-5-5", 2000, 500) == pytest.approx(0.00045)


def test_modelo_sem_preco_devolve_none():
    assert custo_em_dolares("modelo-que-nao-existe", 1000, 1000) is None


@pytest.mark.parametrize(
    ("modelo", "entrada", "saida"),
    [("claude-haiku-5-5", 0.10, 0.50), ("claude-sonnet-5-5", 2.00, 10.00), ("claude-opus-5-5", 4.00, 20.00)],
)
def test_cada_modelo_tem_o_seu_preco(modelo, entrada, saida):
    assert custo_em_dolares(modelo, 1_000_000, 0) == pytest.approx(entrada)
    assert custo_em_dolares(modelo, 0, 1_000_000) == pytest.approx(saida)
