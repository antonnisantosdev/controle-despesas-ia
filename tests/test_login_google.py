"""Login com o Google (PKCE): a API só monta o endereço do Supabase se o destino for o nosso frontend
e troca o código pelo token só com o segredo certo (o Supabase é imitado)."""

import base64
import hashlib
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from supabase import AuthApiError, AuthRetryableError

import auth
import main

ORIGENS = ["http://localhost:3000", "https://app-exemplo.vercel.app"]

# Um segredo PKCE inventado (64 caracteres) e o seu code_challenge, calculado como no browser.
VERIFIER = "segredo-inventado-para-testes_0123456789.abcdefghijklmnopqrstuvw"
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode()
CODIGO = "11111111-2222-4333-8444-555555555555"  # o Supabase devolve um UUID


@pytest.fixture
def cliente_publico(monkeypatch):
    """Um cliente sem login: a rota do Google é pública."""
    monkeypatch.setattr(main, "ORIGENS_FRONTEND", ORIGENS)
    return TestClient(main.app)


@pytest.mark.parametrize("origem", ORIGENS)
def test_destino_valido_devolve_o_url_do_supabase(cliente_publico, origem):
    destino = f"{origem}/login/google"

    resposta = cliente_publico.get("/login/google", params={"destino": destino, "code_challenge": CHALLENGE})

    assert resposta.status_code == 200
    url = urlparse(resposta.json()["url"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == "https://exemplo.supabase.co/auth/v1/authorize"
    parametros = parse_qs(url.query)
    assert parametros["provider"] == ["google"]
    assert parametros["redirect_to"] == [destino]
    assert parametros["code_challenge"] == [CHALLENGE]
    assert parametros["code_challenge_method"] == ["s256"]


def test_o_destino_vai_codificado_no_url(cliente_publico):
    resposta = cliente_publico.get("/login/google", params={"destino": "http://localhost:3000/login/google", "code_challenge": CHALLENGE})

    assert "redirect_to=http%3A%2F%2Flocalhost%3A3000%2Flogin%2Fgoogle" in resposta.json()["url"]


def test_aceita_origens_com_espacos_depois_da_virgula(monkeypatch):
    # FRONTEND_URL="http://localhost:3000, https://app-exemplo.vercel.app" também tem de funcionar.
    monkeypatch.setattr(main, "ORIGENS_FRONTEND", ["http://localhost:3000", " https://app-exemplo.vercel.app"])

    resposta = TestClient(main.app).get("/login/google", params={"destino": "https://app-exemplo.vercel.app/login/google", "code_challenge": CHALLENGE})
    assert resposta.status_code == 200


@pytest.mark.parametrize(
    "destino",
    [
        "https://site-malicioso.com/login/google",  # outro domínio
        "https://app-exemplo.vercel.app.site-malicioso.com/login/google",  # o nosso nome como subdomínio de outro
        "http://app-exemplo.vercel.app/login/google",  # http em vez de https
        "https://app-exemplo.vercel.app/dashboard",  # outro caminho
        "https://app-exemplo.vercel.app/login/google/extra",  # caminho mais comprido
        "https://app-exemplo.vercel.app/login/google?x=1",  # com parâmetros
        "https://app-exemplo.vercel.app",  # só a origem
        "/login/google",  # sem origem
        "",  # vazio
    ],
)
def test_destino_invalido_responde_400(cliente_publico, destino):
    resposta = cliente_publico.get("/login/google", params={"destino": destino, "code_challenge": CHALLENGE})

    assert resposta.status_code == 400
    assert "url" not in resposta.json()


def test_sem_destino_responde_400(cliente_publico):
    assert cliente_publico.get("/login/google", params={"code_challenge": CHALLENGE}).status_code == 400


# --- PKCE: o code_challenge no início ---


def test_o_challenge_tem_43_caracteres_como_o_do_browser():
    assert len(CHALLENGE) == 43
    assert len(VERIFIER) == 64


@pytest.mark.parametrize(
    "challenge",
    [
        None,  # sem challenge: sem PKCE não há login
        "",
        CHALLENGE[:-1],  # 42 caracteres
        CHALLENGE + "A",  # 44
        CHALLENGE[:-1] + "=",  # base64 com enchimento
        CHALLENGE[:-1] + "+",  # base64 normal, não base64url
        CHALLENGE[:-1] + "/",
        CHALLENGE[:-1] + "&",  # tentaria juntar parâmetros ao URL
    ],
)
def test_challenge_invalido_responde_400(cliente_publico, challenge):
    parametros = {"destino": "http://localhost:3000/login/google"}
    if challenge is not None:
        parametros["code_challenge"] = challenge

    resposta = cliente_publico.get("/login/google", params=parametros)

    assert resposta.status_code == 400
    assert "url" not in resposta.json()


def test_o_destino_continua_a_ser_validado_antes_do_challenge(cliente_publico):
    resposta = cliente_publico.get(
        "/login/google", params={"destino": "https://site-malicioso.com/login/google", "code_challenge": CHALLENGE}
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Destino do login inválido"


# --- PKCE: a troca do código pelo token ---


class SupabaseAuthFalso:
    """Imita create_client(...).auth.exchange_code_for_session: guarda o que recebeu e responde como o Supabase.

    Só aceita o CODIGO com o segredo cujo SHA-256 é o CHALLENGE (como o Supabase faz).
    """

    def __init__(self, erro=None, sem_sessao=False):
        self.erro = erro
        self.sem_sessao = sem_sessao
        self.recebido: list[dict] = []
        self.opcoes = []
        self.auth = self

    def __call__(self, url, chave, options=None):
        self.opcoes.append(options)
        return self

    def exchange_code_for_session(self, parametros):
        self.recebido.append(parametros)
        if self.erro:
            raise self.erro
        if self.sem_sessao:
            return SimpleNamespace(session=None, user=None)
        desafio = base64.urlsafe_b64encode(hashlib.sha256(parametros["code_verifier"].encode()).digest()).rstrip(b"=")
        if parametros["auth_code"] != CODIGO or desafio.decode() != CHALLENGE:
            raise AuthApiError("invalid flow state, no valid flow state found", 404, "flow_state_not_found")
        sessao = SimpleNamespace(access_token="token-inventado", refresh_token="refresh-inventado")
        return SimpleNamespace(session=sessao, user=None)


@pytest.fixture
def supabase_auth(monkeypatch):
    def _criar(**opcoes):
        falso = SupabaseAuthFalso(**opcoes)
        monkeypatch.setattr(auth, "create_client", falso)
        return falso

    return _criar


def trocar(cliente, code=CODIGO, code_verifier=VERIFIER):
    return cliente.post("/login/google/troca", json={"code": code, "code_verifier": code_verifier})


def test_troca_devolve_o_token_como_o_login_com_email(cliente_publico, supabase_auth):
    falso = supabase_auth()

    resposta = trocar(cliente_publico)

    assert resposta.status_code == 200
    assert resposta.json() == {"access_token": "token-inventado", "token_type": "bearer"}  # sem refresh_token
    assert falso.recebido == [{"auth_code": CODIGO, "code_verifier": VERIFIER}]


def test_troca_com_o_segredo_errado_responde_401_generico(cliente_publico, supabase_auth):
    supabase_auth()

    resposta = trocar(cliente_publico, code_verifier="outro-segredo-inventado-com-mais-de-quarenta-e-tres-letras")

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Não foi possível entrar com o Google. Tenta outra vez."}
    assert "flow" not in resposta.text  # os detalhes do Supabase não chegam ao utilizador


def test_troca_com_codigo_ja_usado_responde_401(cliente_publico, supabase_auth):
    supabase_auth(erro=AuthApiError("invalid flow state", 404, "flow_state_not_found"))

    assert trocar(cliente_publico).status_code == 401


def test_troca_com_supabase_em_baixo_responde_503_generico(cliente_publico, supabase_auth):
    supabase_auth(erro=AuthRetryableError("ligação recusada", 0))

    resposta = trocar(cliente_publico)

    assert resposta.status_code == 503
    assert resposta.json() == {"detail": "Não foi possível entrar com o Google. Tenta outra vez."}


def test_troca_sem_sessao_na_resposta_nao_entra(cliente_publico, supabase_auth):
    supabase_auth(sem_sessao=True)

    resposta = trocar(cliente_publico)

    assert resposta.status_code == 503
    assert "access_token" not in resposta.json()


@pytest.mark.parametrize(
    ("code", "code_verifier"),
    [
        ("", VERIFIER),  # sem código
        (CODIGO, ""),  # sem segredo
        (CODIGO, "a" * 42),  # segredo curto demais
        (CODIGO, "a" * 129),  # segredo comprido demais
        (CODIGO, "a" * 42 + "/"),  # caractere fora do RFC 7636
        ("x" * 257, VERIFIER),  # código comprido demais
        ("codigo com espacos", VERIFIER),
        ("codigo&grant_type=password", VERIFIER),
    ],
)
def test_troca_com_dados_invalidos_responde_422_sem_falar_com_o_supabase(
    cliente_publico, supabase_auth, code, code_verifier
):
    falso = supabase_auth()

    resposta = trocar(cliente_publico, code, code_verifier)

    assert resposta.status_code == 422
    assert falso.recebido == []


def test_troca_sem_corpo_responde_422(cliente_publico, supabase_auth):
    falso = supabase_auth()

    assert cliente_publico.post("/login/google/troca").status_code == 422
    assert cliente_publico.post("/login/google/troca", json={"code": CODIGO}).status_code == 422
    assert falso.recebido == []


# --- Clientes de login sem sessão guardada nem renovação automática ---


def test_a_troca_usa_um_cliente_sem_sessao(cliente_publico, supabase_auth):
    falso = supabase_auth()

    trocar(cliente_publico)

    assert len(falso.opcoes) == 1
    assert falso.opcoes[0].auto_refresh_token is False
    assert falso.opcoes[0].persist_session is False


def test_o_login_com_email_usa_um_cliente_sem_sessao(monkeypatch):
    opcoes = []

    class ClienteLogin:
        auth = SimpleNamespace(
            sign_in_with_password=lambda dados: SimpleNamespace(session=SimpleNamespace(access_token="token-inventado"))
        )

    def criar(url, chave, options=None):
        opcoes.append(options)
        return ClienteLogin()

    monkeypatch.setattr(auth, "create_client", criar)

    assert auth.fazer_login("teste@exemplo.pt", "palavra-inventada") == "token-inventado"
    assert opcoes[0].auto_refresh_token is False
    assert opcoes[0].persist_session is False


def test_o_cliente_verdadeiro_fica_sem_sessao_nem_renovacao():
    # Sem imitação: confirma que o SDK instalado recebe mesmo as opções (não fala com a rede ao criar).
    cliente = auth.cliente_sem_sessao()

    assert cliente.options.auto_refresh_token is False
    assert cliente.options.persist_session is False


# --- Revisão: respostas genéricas, formatos aceites e logs sem segredos ---


def test_troca_com_dados_invalidos_nao_repete_o_que_foi_enviado(cliente_publico, supabase_auth):
    supabase_auth()

    resposta = trocar(cliente_publico, "codigo com espacos", "segredo-curto")

    assert resposta.status_code == 422
    assert resposta.json() == {"detail": "Não foi possível entrar com o Google. Tenta outra vez."}
    assert "segredo-curto" not in resposta.text
    assert "codigo com espacos" not in resposta.text
    assert "A-Za-z" not in resposta.text  # nem os formatos aceites


def test_as_outras_rotas_mantem_o_422_normal(cliente):
    # O /login e o /registo também têm 422 genérico (test_limite_email.py): usa-se uma rota sem segredos.
    resposta = cliente.get("/transacoes", params={"mes": "não é mês"})

    assert resposta.status_code == 422
    assert isinstance(resposta.json()["detail"], list)  # o 422 do FastAPI, com a lista dos campos


@pytest.mark.parametrize(
    ("code", "code_verifier"),
    [
        (CODIGO, "a" * 43),  # o mínimo do RFC 7636
        (CODIGO, "a" * 128),  # o máximo
        (CODIGO, "segredo.com.pontos~e~tis_e-hifens-0123456789abcdef"),  # . e ~ são permitidos
        ("c" * 256, VERIFIER),  # código no teto
    ],
)
def test_formatos_no_limite_sao_aceites_e_chegam_ao_supabase(cliente_publico, supabase_auth, code, code_verifier):
    falso = supabase_auth()

    resposta = trocar(cliente_publico, code, code_verifier)

    assert resposta.status_code != 422
    assert falso.recebido == [{"auth_code": code, "code_verifier": code_verifier}]


def test_erro_que_nao_e_do_supabase_responde_503_e_nunca_500(cliente_publico, supabase_auth):
    supabase_auth(erro=httpx.ConnectError("ligação recusada"))

    resposta = trocar(cliente_publico)

    assert resposta.status_code == 503
    assert resposta.json() == {"detail": "Não foi possível entrar com o Google. Tenta outra vez."}


@pytest.mark.parametrize(
    ("erro", "estado"),
    [
        (AuthApiError("invalid flow state", 404, "flow_state_not_found"), 401),
        (AuthRetryableError("ligação recusada", 0), 503),
        (httpx.ConnectError("ligação recusada"), 503),
    ],
)
def test_os_logs_nao_mostram_o_codigo_nem_o_segredo(cliente_publico, supabase_auth, capsys, erro, estado):
    supabase_auth(erro=erro)

    assert trocar(cliente_publico).status_code == estado

    logs = capsys.readouterr().out
    assert "AVISO: troca do código do Google" in logs
    assert CODIGO not in logs
    assert VERIFIER not in logs
