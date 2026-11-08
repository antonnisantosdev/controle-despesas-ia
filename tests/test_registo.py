"""Registo público e a regra de quando uma assinatura dá acesso."""

from datetime import date

import pytest
from supabase import AuthApiError

import main
from auth import assinatura_ativa

HOJE = date(2026, 11, 8)


@pytest.mark.parametrize(
    ("plano", "ativo_ate", "esperado"),
    [
        ("free", None, True),  # o Free não tem data de fim
        ("essencial", date(2026, 12, 31), True),
        ("completo", HOJE, True),  # o último dia ainda conta
        ("essencial", date(2026, 11, 7), False),  # acabou ontem
        ("essencial", None, False),  # plano pago sem data: na dúvida, fecha
        (None, None, False),
    ],
)
def test_quando_a_assinatura_da_acesso(plano, ativo_ate, esperado):
    assert assinatura_ativa(plano, ativo_ate, HOJE) is esperado


def test_registo_cria_a_conta(cliente, monkeypatch):
    contas = []
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: contas.append(email))

    resposta = cliente.post("/registo", json={"email": "nova@exemplo.com", "password": "uma-boa-palavra"})

    assert resposta.status_code == 201
    assert contas == ["nova@exemplo.com"]


@pytest.mark.parametrize(
    "corpo",
    [
        {"email": "isto-nao-e-email", "password": "uma-boa-palavra"},
        {"email": "nova@exemplo.com", "password": "curta"},
    ],
)
def test_registo_recusa_dados_invalidos(cliente, monkeypatch, corpo):
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: pytest.fail("não devia chegar ao Supabase"))

    assert cliente.post("/registo", json=corpo).status_code == 422


def test_registo_com_erro_do_supabase_responde_400(cliente, monkeypatch):
    def falha(email, password):
        raise AuthApiError("Password should contain letters and digits", 422, "weak_password")

    monkeypatch.setattr(main, "fazer_registo", falha)

    resposta = cliente.post("/registo", json={"email": "nova@exemplo.com", "password": "12345678"})
    assert resposta.status_code == 400
