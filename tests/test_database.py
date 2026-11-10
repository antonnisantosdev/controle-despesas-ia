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


# --- Ligações mortas ao Supabase (a API acordou no Render) ---

import httpx  # noqa: E402

import database  # noqa: E402
from database import TransporteQueRepete  # noqa: E402


def cliente_que_falha(erros):
    """Um cliente httpx cujas primeiras tentativas dão os erros da lista; depois responde 200."""
    tentativas = []

    def responder(pedido):
        tentativas.append(pedido.method)
        if len(tentativas) <= len(erros):
            raise erros[len(tentativas) - 1]
        return httpx.Response(200, json=[{"id": 1}])

    cliente = httpx.Client(transport=TransporteQueRepete(httpx.MockTransport(responder)))
    return cliente, tentativas


@pytest.mark.parametrize(
    "erro",
    [httpx.ReadError("Resource temporarily unavailable"), httpx.RemoteProtocolError("ligação fechada"),
     httpx.ConnectError("ligação recusada")],
)
def test_leitura_repete_uma_vez_se_a_ligacao_morreu(erro):
    cliente, tentativas = cliente_que_falha([erro])
    resposta = cliente.get("https://exemplo.supabase.co/rest/v1/orcamentos")
    assert resposta.status_code == 200
    assert tentativas == ["GET", "GET"]


def test_leitura_so_repete_uma_vez():
    cliente, tentativas = cliente_que_falha([httpx.ReadError("x"), httpx.ReadError("x")])
    with pytest.raises(httpx.ReadError):
        cliente.get("https://exemplo.supabase.co/rest/v1/orcamentos")
    assert tentativas == ["GET", "GET"]


@pytest.mark.parametrize("metodo", ["POST", "PATCH", "PUT", "DELETE"])
def test_escritas_nunca_se_repetem(metodo):
    cliente, tentativas = cliente_que_falha([httpx.ReadError("x")])
    with pytest.raises(httpx.ReadError):
        cliente.request(metodo, "https://exemplo.supabase.co/rest/v1/orcamentos", json={"limite": 100})
    assert tentativas == [metodo]


def test_outros_erros_nao_se_repetem():
    cliente, tentativas = cliente_que_falha([httpx.ReadTimeout("demorou")])
    with pytest.raises(httpx.ReadTimeout):
        cliente.get("https://exemplo.supabase.co/rest/v1/orcamentos")
    assert tentativas == ["GET"]


def test_cliente_partilhado_usa_o_transporte_que_repete():
    # A base de dados e o auth do cliente partilhado passam pelo transporte que repete.
    assert isinstance(database.supabase.postgrest.session._transport, TransporteQueRepete)
    assert isinstance(database.supabase.auth._http_client._transport, TransporteQueRepete)


def test_select_do_postgrest_repete_depois_de_read_error(monkeypatch):
    """Ponta a ponta: um select verdadeiro do postgrest sobrevive a uma ligação morta."""
    cliente, tentativas = cliente_que_falha([httpx.ReadError("Resource temporarily unavailable")])
    sessao = database.supabase.postgrest.session
    monkeypatch.setattr(sessao, "_transport", cliente._transport)
    resposta = database.supabase.table("orcamentos").select("*").execute()
    assert resposta.data == [{"id": 1}]
    assert tentativas == ["GET", "GET"]
