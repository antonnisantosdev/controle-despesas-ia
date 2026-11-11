"""Origem do registo (o canal do utm_source): lista fechada, gravada na assinatura só se estiver vazia,
no registo com email e no primeiro login com o Google. Nunca faz falhar o registo. O Supabase é imitado."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import auth
import main
from models import NovaConta, normalizar_origem

ID_NOVO = "00000000-0000-4000-8000-000000000001"
EMAIL = "nova@exemplo.com"
VERIFIER = "segredo-inventado-para-testes_0123456789.abcdefghijklmnopqrstuvw"
CODIGO = "11111111-2222-4333-8444-555555555555"


class AssinaturasFalsas:
    """Imita supabase.table("assinaturas").update(...).eq(...).is_(...).execute() e guarda cada passo."""

    def __init__(self, erro: Exception | None = None):
        self.erro = erro
        self.passos: list[tuple] = []

    def table(self, nome):
        self.passos.append(("table", nome))
        return self

    def update(self, dados):
        self.passos.append(("update", dados))
        return self

    def eq(self, coluna, valor):
        self.passos.append(("eq", coluna, valor))
        return self

    def is_(self, coluna, valor):
        self.passos.append(("is_", coluna, valor))
        return self

    def execute(self):
        if self.erro:
            raise self.erro
        return SimpleNamespace(data=[])


@pytest.fixture
def assinaturas(monkeypatch):
    def _criar(erro=None):
        falsa = AssinaturasFalsas(erro)
        monkeypatch.setattr(auth, "supabase", falsa)
        return falsa

    return _criar


@pytest.fixture
def api():
    return TestClient(main.app)


def update_esperado(origem, user_id=ID_NOVO):
    return [
        ("table", "assinaturas"),
        ("update", {"origem": origem}),
        ("eq", "user_id", user_id),
        ("is_", "origem", "null"),  # só se ainda estiver vazia
    ]


# --- Lista fechada ---


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("instagram", "instagram"),
        ("youtube", "youtube"),
        ("tiktok", "tiktok"),
        ("linkedin", "linkedin"),
        (" LinkedIn ", "linkedin"),
        ("outro", "outro"),
        ("facebook", "outro"),
        ("x" * 5000, "outro"),
        ("<script>", "outro"),
        (123, "outro"),
        (["instagram"], "outro"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalizar_origem(valor, esperado):
    assert normalizar_origem(valor) == esperado


def test_nova_conta_sem_origem_continua_valida():
    assert NovaConta(email=EMAIL, password="uma-boa-palavra").origem is None


# --- Registo com email ---


def test_registo_guarda_a_origem_da_conta_nova(api, monkeypatch, assinaturas):
    falsa = assinaturas()
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: ID_NOVO)

    resposta = api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "origem": "instagram"})

    assert resposta.status_code == 201
    assert falsa.passos == update_esperado("instagram")


def test_registo_com_origem_desconhecida_guarda_outro_e_nao_da_422(api, monkeypatch, assinaturas):
    falsa = assinaturas()
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: ID_NOVO)

    resposta = api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "origem": "y" * 1000})

    assert resposta.status_code == 201
    assert falsa.passos == update_esperado("outro")


def test_registo_sem_origem_nao_mexe_na_assinatura(api, monkeypatch, assinaturas):
    falsa = assinaturas()
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: ID_NOVO)

    assert api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra"}).status_code == 201
    assert falsa.passos == []


def test_registo_sem_id_do_supabase_nao_mexe_na_assinatura(api, monkeypatch, assinaturas):
    falsa = assinaturas()
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: None)

    resposta = api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "origem": "youtube"})

    assert resposta.status_code == 201
    assert falsa.passos == []


def test_registo_nao_falha_se_a_origem_nao_gravar(api, monkeypatch, assinaturas, capsys):
    # Ex.: a migração 019 ainda não foi corrida (coluna origem inexistente).
    assinaturas(erro=RuntimeError(f"coluna origem não existe ({ID_NOVO}, {EMAIL})"))
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: ID_NOVO)

    resposta = api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "origem": "tiktok"})

    assert resposta.status_code == 201
    saida = capsys.readouterr().out
    assert "AVISO: origem do registo não gravada (RuntimeError)." in saida
    assert EMAIL not in saida
    assert ID_NOVO not in saida


def test_fazer_registo_devolve_o_id_da_conta(monkeypatch):
    class ClienteFalso:
        def __init__(self):
            self.auth = self

        def sign_up(self, dados):
            criada = datetime.now(timezone.utc) - timedelta(seconds=2)
            return SimpleNamespace(user=SimpleNamespace(id=ID_NOVO, created_at=criada), session=None)

    monkeypatch.setattr(auth, "create_client", lambda url, chave: ClienteFalso())

    assert auth.fazer_registo(EMAIL, "uma-boa-palavra") == ID_NOVO


@pytest.mark.parametrize("criada_em", [datetime.now(timezone.utc) - timedelta(days=3), None, "ontem"])
def test_fazer_registo_de_conta_antiga_nao_devolve_o_id(monkeypatch, criada_em):
    # Ex.: segundo registo com o email de uma conta criada há dias e ainda por confirmar.
    class ClienteFalso:
        def __init__(self):
            self.auth = self

        def sign_up(self, dados):
            return SimpleNamespace(user=SimpleNamespace(id=ID_NOVO, created_at=criada_em), session=None)

    monkeypatch.setattr(auth, "create_client", lambda url, chave: ClienteFalso())

    assert auth.fazer_registo(EMAIL, "uma-boa-palavra") is None


def test_fazer_registo_sem_utilizador_na_resposta_devolve_none(monkeypatch):
    class ClienteFalso:
        def __init__(self):
            self.auth = self

        def sign_up(self, dados):
            return SimpleNamespace(user=None, session=None)

    monkeypatch.setattr(auth, "create_client", lambda url, chave: ClienteFalso())

    assert auth.fazer_registo(EMAIL, "uma-boa-palavra") is None


# --- Login com o Google ---


def trocar(api, **campos):
    return api.post("/login/google/troca", json={"code": CODIGO, "code_verifier": VERIFIER, **campos})


def test_primeiro_login_google_guarda_a_origem(api, monkeypatch, assinaturas):
    falsa = assinaturas()
    sessao = auth.SessaoGoogle("token-inventado", ID_NOVO, conta_nova=True)
    monkeypatch.setattr(main, "trocar_codigo_google", lambda codigo, verifier: sessao)

    resposta = trocar(api, origem="linkedin")

    assert resposta.status_code == 200
    assert resposta.json() == {"access_token": "token-inventado", "token_type": "bearer"}
    assert falsa.passos == update_esperado("linkedin")


def test_login_google_de_conta_antiga_nao_guarda_a_origem(api, monkeypatch, assinaturas):
    falsa = assinaturas()
    sessao = auth.SessaoGoogle("token-inventado", ID_NOVO, conta_nova=False)
    monkeypatch.setattr(main, "trocar_codigo_google", lambda codigo, verifier: sessao)

    assert trocar(api, origem="linkedin").status_code == 200
    assert falsa.passos == []


def test_login_google_nao_falha_se_a_origem_nao_gravar(api, monkeypatch, assinaturas):
    assinaturas(erro=RuntimeError("em baixo"))
    sessao = auth.SessaoGoogle("token-inventado", ID_NOVO, conta_nova=True)
    monkeypatch.setattr(main, "trocar_codigo_google", lambda codigo, verifier: sessao)

    assert trocar(api, origem="instagram").status_code == 200


AGORA = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("criada_em", "nova"),
    [
        (AGORA - timedelta(seconds=5), True),
        (AGORA - timedelta(minutes=9), True),
        (AGORA - timedelta(minutes=11), False),
        (AGORA - timedelta(days=30), False),
        (AGORA + timedelta(minutes=1), False),  # no futuro: não se confia
        ("2026-11-11T11:58:00Z", True),  # texto ISO, como pode vir do Supabase
        ("2026-11-11T11:58:00", True),  # sem fuso: UTC
        ("ontem", False),
        (None, False),
    ],
)
def test_conta_acabada_de_criar(criada_em, nova):
    assert auth._conta_acabada_de_criar(criada_em, AGORA) is nova


def test_trocar_codigo_google_devolve_o_id_e_se_a_conta_e_nova(monkeypatch):
    utilizador = SimpleNamespace(id=ID_NOVO, created_at=datetime.now(timezone.utc) - timedelta(seconds=3))

    class ClienteFalso:
        def __init__(self):
            self.auth = self

        def exchange_code_for_session(self, parametros):
            return SimpleNamespace(session=SimpleNamespace(access_token="token-inventado"), user=utilizador)

    monkeypatch.setattr(auth, "cliente_sem_sessao", ClienteFalso)

    assert auth.trocar_codigo_google(CODIGO, VERIFIER) == auth.SessaoGoogle("token-inventado", ID_NOVO, True)
