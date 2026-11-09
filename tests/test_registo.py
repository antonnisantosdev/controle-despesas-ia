"""Registo público e a regra de qual plano vale hoje (um plano pago que termina passa a Free)."""

from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from supabase import AuthApiError

import auth
import limites
import main
from limites import plano_efetivo

HOJE = date(2026, 11, 8)


@pytest.mark.parametrize(
    ("plano", "ativo_ate", "esperado"),
    [
        ("free", None, "free"),  # o Free não tem data de fim
        ("free", date(2026, 1, 1), "free"),  # uma data perdida na coluna não muda nada
        ("essencial", date(2026, 12, 31), "essencial"),
        ("completo", HOJE, "completo"),  # o último dia ainda conta
        ("essencial", date(2026, 11, 7), "free"),  # acabou ontem: passa a Free
        ("completo", date(2026, 11, 7), "free"),
        ("essencial", None, "free"),  # plano pago sem data: na dúvida, Free (sem IA paga a mais)
        (None, None, None),  # sem linha: não há plano (a API responde 403)
    ],
)
def test_qual_plano_vale_hoje(plano, ativo_ate, esperado):
    assert plano_efetivo(plano, ativo_ate, HOJE) == esperado


class AssinaturaFalsa:
    """Imita a tabela assinaturas com as linhas que lhe dermos."""

    def __init__(self, linhas):
        self.data = linhas

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        return self


def test_hoje_em_lisboa_ja_e_amanha_as_23_30_utc_de_verao(monkeypatch):
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 7, 31, 23, 30, tzinfo=timezone.utc))
    assert limites.hoje_em_lisboa() == date(2026, 8, 1)


def test_sem_linha_na_tabela_assinaturas_responde_403(monkeypatch):
    monkeypatch.setattr(auth, "supabase", AssinaturaFalsa([]))

    with pytest.raises(HTTPException) as erro:
        auth.verificar_assinatura("utilizador-teste")
    assert erro.value.status_code == 403
    assert erro.value.detail == "Sem assinatura ativa"


def test_um_plano_pago_que_terminou_ja_nao_bloqueia(monkeypatch):
    monkeypatch.setattr(auth, "supabase", AssinaturaFalsa([{"user_id": "utilizador-teste"}]))

    auth.verificar_assinatura("utilizador-teste")  # não pode lançar 403


def test_o_plano_pago_passa_a_free_a_meia_noite_de_lisboa(monkeypatch):
    # 23:30 UTC de 31 de julho já é 1 de agosto em Lisboa: um plano até 31 de julho já acabou,
    # mesmo que no servidor (UTC) ainda seja dia 31.
    monkeypatch.setattr(limites, "supabase", AssinaturaFalsa([{"plano": "essencial", "ativo_ate": "2026-07-31"}]))
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 7, 31, 23, 30, tzinfo=timezone.utc))

    assert limites.plano_do_utilizador("utilizador-teste") == "free"


def test_o_plano_pago_ainda_vale_no_ultimo_dia_em_lisboa(monkeypatch):
    monkeypatch.setattr(limites, "supabase", AssinaturaFalsa([{"plano": "essencial", "ativo_ate": "2026-07-31"}]))
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 7, 31, 22, 30, tzinfo=timezone.utc))

    assert limites.plano_do_utilizador("utilizador-teste") == "essencial"  # 23:30 de 31 em Lisboa


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
