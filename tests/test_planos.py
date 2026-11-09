"""Planos: o limite diário de perguntas à IA depende do plano da assinatura."""

from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import limites
import main


@pytest.mark.parametrize(
    ("plano", "esperado"),
    [("free", 5), ("essencial", 20), ("completo", 50)],
)
def test_cada_plano_tem_o_seu_limite(plano, esperado):
    assert limites.limite_do_plano(plano) == esperado


class UsoIaFalso:
    """Imita a tabela uso_ia: responde com quantas perguntas já se fizeram hoje."""

    def __init__(self, feitas_hoje):
        self.count = feitas_hoje
        self.inseridas = 0

    def table(self, nome):
        return self

    def insert(self, dados):
        self.inseridas += 1
        return self

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        return self


def test_o_free_bloqueia_a_sexta_pergunta(monkeypatch):
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "free")
    monkeypatch.setattr(limites, "supabase", UsoIaFalso(feitas_hoje=5))

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste")
    assert erro.value.status_code == 429


def test_o_aviso_do_limite_fala_em_pedidos_a_ia_e_diz_o_limite(monkeypatch):
    # O frontend e o texto aprovado usam "pedidos à IA" (não "perguntas").
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "essencial")
    monkeypatch.setattr(limites, "supabase", UsoIaFalso(feitas_hoje=20))

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste")
    assert erro.value.detail == (
        "Chegaste ao limite de hoje. Já usaste os 20 pedidos à IA do teu plano. O contador volta a zero à meia-noite."
    )


def test_o_completo_ainda_deixa_perguntar_com_as_mesmas_perguntas(monkeypatch):
    uso = UsoIaFalso(feitas_hoje=5)
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "completo")
    monkeypatch.setattr(limites, "supabase", uso)

    limites.registar_pergunta("utilizador-teste")
    assert uso.inseridas == 1  # a pergunta ficou contada


@pytest.mark.parametrize("plano", [None, "Completo", "premium"])
def test_plano_desconhecido_nao_deixa_usar_a_ia(plano):
    # Na dúvida, fecha: um erro na coluna plano nunca pode gastar créditos da IA.
    assert limites.limite_do_plano(plano) == 0


def test_a_rota_plano_mostra_o_limite_e_as_perguntas_de_hoje(cliente, monkeypatch):
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: ("free", None))
    monkeypatch.setattr(limites, "perguntas_de_hoje", lambda user_id: 3)

    resposta = cliente.get("/plano")

    assert resposta.status_code == 200
    assert resposta.json() == {"plano": "free", "limite": 5, "usadas_hoje": 3, "ativo_ate": None}


def test_a_rota_plano_mostra_ate_quando_dura_um_plano_pago(cliente, monkeypatch):
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: ("essencial", date(2026, 12, 31)))
    monkeypatch.setattr(limites, "perguntas_de_hoje", lambda user_id: 0)

    resposta = cliente.get("/plano")

    assert resposta.status_code == 200
    assert resposta.json()["ativo_ate"] == "2026-12-31"


def test_o_free_nunca_mostra_data_de_fim(monkeypatch):
    # Mesmo que a coluna ativo_ate tenha uma data perdida, o Free não acaba.
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: ("free", date(2026, 1, 1)))
    monkeypatch.setattr(limites, "perguntas_de_hoje", lambda user_id: 0)

    assert limites.estado_do_plano("utilizador-teste").ativo_ate is None


class AssinaturasFalsas:
    """Imita a tabela assinaturas: devolve as linhas que lhe dermos."""

    def __init__(self, linhas):
        self.data = linhas

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        return self


@pytest.mark.parametrize(
    ("linhas", "esperado"),
    [
        ([{"plano": "completo", "ativo_ate": "2026-12-31"}], ("completo", date(2026, 12, 31))),
        ([{"plano": "free", "ativo_ate": None}], ("free", None)),
        ([], (None, None)),  # sem linha na tabela
    ],
)
def test_a_assinatura_le_o_plano_e_a_data(monkeypatch, linhas, esperado):
    monkeypatch.setattr(limites, "supabase", AssinaturasFalsas(linhas))
    assert limites.assinatura_do_utilizador("utilizador-teste") == esperado


def test_a_rota_planos_lista_os_planos_por_ordem_sem_login():
    # Sem dependency_overrides nem token: a rota é pública.
    resposta = TestClient(main.app).get("/planos")

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"plano": "free", "limite_diario": 5},
        {"plano": "essencial", "limite_diario": 20},
        {"plano": "completo", "limite_diario": 50},
    ]


def test_a_rota_planos_segue_os_limites_de_limites_py(monkeypatch):
    # Os números vêm só de LIMITES_POR_PLANO: mudar lá muda a página de preços.
    monkeypatch.setattr(limites, "LIMITES_POR_PLANO", {"free": 1, "completo": 2})

    resposta = TestClient(main.app).get("/planos")

    assert resposta.json() == [{"plano": "free", "limite_diario": 1}, {"plano": "completo", "limite_diario": 2}]
