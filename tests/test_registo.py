"""Registo público e a regra de quando uma assinatura dá acesso."""

from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from supabase import AuthApiError

import auth
import limites
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


class AssinaturaFalsa:
    """Imita a tabela assinaturas com uma só linha."""

    def __init__(self, linha):
        self.data = [linha]

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        return self


def test_hoje_em_lisboa_ja_e_amanha_as_23_30_utc_de_verao(monkeypatch):
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 7, 31, 23, 30, tzinfo=timezone.utc))
    assert limites.hoje_em_lisboa() == date(2026, 8, 1)


def test_a_assinatura_acaba_a_meia_noite_de_lisboa(monkeypatch):
    # 23:30 UTC de 31 de julho já é 1 de agosto em Lisboa: um plano até 31 de julho já acabou,
    # mesmo que no servidor (UTC) ainda seja dia 31.
    monkeypatch.setattr(auth, "supabase", AssinaturaFalsa({"plano": "essencial", "ativo_ate": "2026-07-31"}))
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 7, 31, 23, 30, tzinfo=timezone.utc))

    with pytest.raises(HTTPException) as erro:
        auth.verificar_assinatura("utilizador-teste")
    assert erro.value.status_code == 403


def test_a_assinatura_ainda_vale_no_ultimo_dia_em_lisboa(monkeypatch):
    monkeypatch.setattr(auth, "supabase", AssinaturaFalsa({"plano": "essencial", "ativo_ate": "2026-07-31"}))
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 7, 31, 22, 30, tzinfo=timezone.utc))

    auth.verificar_assinatura("utilizador-teste")  # 23:30 de 31 em Lisboa: ainda dá acesso


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


def test_login_avisa_quando_o_email_nao_esta_confirmado(cliente, monkeypatch):
    def falha(email, password):
        raise AuthApiError("Email not confirmed", 400, "email_not_confirmed")

    monkeypatch.setattr(main, "fazer_login", falha)

    resposta = cliente.post("/login", json={"email": "nova@exemplo.com", "password": "uma-boa-palavra"})
    assert resposta.status_code == 401
    assert "confirmaste o email" in resposta.json()["detail"]
