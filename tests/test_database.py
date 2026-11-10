"""Leitura por páginas: o Supabase só devolve 1000 linhas por pedido."""

import pytest

from database import ler_todas


class ConsultaFalsa:
    """Imita uma consulta com `total` linhas, que devolve no máximo `maximo` linhas por pedido."""

    pedidos = 0

    def __init__(self, total, maximo):
        self.total, self.maximo = total, maximo
        self.inicio = None

    def range(self, inicio, fim):
        # Na biblioteca verdadeira, um segundo range na mesma consulta estraga o pedido.
        assert self.inicio is None, "range chamado duas vezes na mesma consulta"
        self.inicio, self.fim = inicio, fim
        return self

    def execute(self):
        ConsultaFalsa.pedidos += 1
        assert ConsultaFalsa.pedidos < 100, "ciclo infinito"
        ultima = min(self.fim, self.inicio + self.maximo - 1, self.total - 1)

        class Resposta:
            data = [{"id": i} for i in range(self.inicio, ultima + 1)]

        return Resposta


@pytest.mark.parametrize(
    "total, maximo",
    # (2500, 500): um Supabase que devolve menos linhas por pedido do que TAMANHO_PAGINA não perde nenhuma.
    [(0, 1000), (999, 1000), (1000, 1000), (2500, 1000), (2500, 500)],
)
def test_le_todas_as_linhas_sem_repetir(total, maximo):
    ConsultaFalsa.pedidos = 0

    linhas = ler_todas(lambda: ConsultaFalsa(total, maximo))

    ids = [linha["id"] for linha in linhas]
    assert len(ids) == total
    assert len(set(ids)) == total


@pytest.mark.parametrize(
    ("total", "pedidos"),
    [
        (0, 1),  # vazia: um pedido
        (999, 2),  # 999 e depois a página vazia que diz que acabou
        (1000, 2),  # 1000 e a página vazia
        (2500, 4),  # 1000 + 1000 + 500 e a página vazia
    ],
)
def test_para_so_na_pagina_vazia(total, pedidos):
    ConsultaFalsa.pedidos = 0

    ler_todas(lambda: ConsultaFalsa(total, 1000))

    assert ConsultaFalsa.pedidos == pedidos
