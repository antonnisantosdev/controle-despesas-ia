"""Planos: o limite diário de perguntas à IA depende do plano da assinatura."""

import pytest
from fastapi import HTTPException

import limites


@pytest.mark.parametrize(
    ("plano", "esperado"),
    [("free", 5), ("essencial", 30), ("completo", 100)],
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
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "free")
    monkeypatch.setattr(limites, "perguntas_de_hoje", lambda user_id: 3)

    resposta = cliente.get("/plano")

    assert resposta.status_code == 200
    assert resposta.json() == {"plano": "free", "limite": 5, "usadas_hoje": 3}
