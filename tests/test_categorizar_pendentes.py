"""POST /transacoes/categorizar: o botão "Categorizar sem categoria" de Movimentações depende destas regras."""

import pytest

import main
from ia import ErroIA

# Transações inventadas, já gravadas sem categoria (ex.: CSV importado sem pedidos à IA).
PENDENTES = [
    {"id": 1, "data": "2026-10-01", "descricao": "CAFE CENTRAL", "valor": -1.2, "categoria": None, "metodo_pagamento": None},
    {"id": 2, "data": "2026-10-02", "descricao": "SUPERMERCADO X", "valor": -35.4, "categoria": None, "metodo_pagamento": None},
    {"id": 3, "data": "2026-09-28", "descricao": "ORDENADO", "valor": 900.0, "categoria": None, "metodo_pagamento": None},
]


class TransacoesFalsas:
    """Imita a tabela transacoes: o select devolve as pendentes e o update devolve a linha alterada."""

    def __init__(self, pendentes):
        self.pendentes = [dict(linha) for linha in pendentes]
        self.atualizadas: list[tuple[int, dict]] = []
        self.ordens: list[tuple] = []
        self.limites: list[int] = []
        self._update = None
        self._id = None

    def table(self, nome):
        self._update = None
        self._id = None
        return self

    def update(self, dados):
        self._update = dados
        return self

    def eq(self, campo, valor):
        if campo == "id":
            self._id = valor
        return self

    def order(self, campo, desc=False):
        self.ordens.append((campo, desc))
        return self

    def limit(self, quantas):
        self.limites.append(quantas)
        return self

    def __getattr__(self, nome):
        # select, is_...: só devolvem a própria consulta.
        return lambda *args, **opcoes: self

    def execute(self):
        if self._update is None:
            linhas = self.pendentes
        else:
            self.atualizadas.append((self._id, self._update))
            linha = next(p for p in self.pendentes if p["id"] == self._id)
            linhas = [linha | self._update]

        class Resposta:
            data = linhas

        return Resposta


@pytest.fixture
def transacoes(monkeypatch):
    falsa = TransacoesFalsas(PENDENTES)
    monkeypatch.setattr(main, "supabase", falsa)
    return falsa


def test_categoriza_o_lote_de_pendentes_numa_so_chamada_e_um_pedido(cliente, limite, transacoes, monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        main, "categorizar", lambda lista, user_id=None, local=None: chamadas.append(len(lista)) or ["outros"] * len(lista)
    )

    resposta = cliente.post("/transacoes/categorizar")

    assert resposta.status_code == 200
    assert chamadas == [3]  # as pendentes do lote, de vários meses, vão na mesma chamada
    assert limite.perguntas == 1
    assert [t["categoria"] for t in resposta.json()] == ["outros"] * 3
    assert [id_ for id_, _ in transacoes.atualizadas] == [1, 2, 3]


def test_vao_no_maximo_300_pendentes_as_mais_recentes_primeiro(cliente, limite, transacoes, monkeypatch):
    # Quem tiver mais de 300 carrega outra vez: cada clique é um lote e um pedido.
    monkeypatch.setattr(main, "categorizar", lambda lista, user_id=None, local=None: ["outros"] * len(lista))

    resposta = cliente.post("/transacoes/categorizar")

    assert resposta.status_code == 200
    assert main.MAX_PENDENTES_POR_PEDIDO == 300
    assert transacoes.limites == [300]
    assert transacoes.ordens == [("data", True), ("id", True)]
    assert limite.perguntas == 1


def test_sem_pendentes_nao_chama_a_ia_nem_gasta_pedido(cliente, limite, monkeypatch):
    # A BaseDadosFalsa do conftest devolve uma lista vazia no select.
    chamadas = []
    monkeypatch.setattr(main, "categorizar", lambda lista, user_id=None, local=None: chamadas.append(lista))

    resposta = cliente.post("/transacoes/categorizar")

    assert resposta.status_code == 200
    assert resposta.json() == []
    assert chamadas == []
    assert limite.perguntas == 0


def test_sem_pedidos_responde_429_sem_chamar_a_ia(cliente, limite, transacoes, monkeypatch):
    # O frontend mostra o AvisoLimite quando recebe este 429.
    limite.maximo = 0
    chamadas = []
    monkeypatch.setattr(main, "categorizar", lambda lista, user_id=None, local=None: chamadas.append(lista))

    resposta = cliente.post("/transacoes/categorizar")

    assert resposta.status_code == 429
    assert chamadas == []
    assert transacoes.atualizadas == []


def test_ia_em_baixo_responde_503_e_nao_grava_nada(cliente, limite, transacoes, monkeypatch):
    def ia_em_baixo(lista, user_id=None, local=None):
        raise ErroIA("IA indisponível (teste)")

    monkeypatch.setattr(main, "categorizar", ia_em_baixo)

    resposta = cliente.post("/transacoes/categorizar")

    assert resposta.status_code == 503
    assert resposta.json()["detail"] == "A categorização automática falhou. Tenta mais tarde."
    assert transacoes.atualizadas == []
