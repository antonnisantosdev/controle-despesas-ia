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


# --- Prompt caching (chat do Completo) ---


def test_escrita_e_leitura_da_cache_tem_preco_proprio():
    # Haiku 5.5: escrever na cache 0,125 e ler da cache 0,01 dólares por milhão de tokens.
    assert custo_em_dolares("claude-haiku-5-5", 0, 0, cache_escrita=1_000_000) == pytest.approx(0.125)
    assert custo_em_dolares("claude-haiku-5-5", 0, 0, cache_leitura=1_000_000) == pytest.approx(0.01)


def test_custo_com_cache_soma_tudo():
    # 200 de entrada, 300 de saída, 1000 escritos e 5000 lidos da cache:
    # 0,00002 + 0,00015 + 0,000125 + 0,00005 = 0,000345 dólares.
    assert custo_em_dolares("claude-haiku-5-5", 200, 300, cache_escrita=1000, cache_leitura=5000) == pytest.approx(0.000345)


def test_sem_cache_o_custo_fica_igual_ao_de_antes():
    assert custo_em_dolares("claude-haiku-5-5", 2000, 500) == custo_em_dolares("claude-haiku-5-5", 2000, 500, 0, 0)
