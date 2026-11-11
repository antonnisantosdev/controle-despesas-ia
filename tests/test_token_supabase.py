"""Validação local dos tokens do Supabase com o JWKS (token_supabase.py e obter_utilizador_atual em auth.py).

Sem rede: as chaves (ECC P-256 e RSA) são geradas aqui com o cryptography, e o "pedido" do JWKS
é uma função que devolve o que o teste quiser. Ids e emails inventados.
"""

import hashlib
import hmac
import json
import threading
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi.testclient import TestClient
from supabase import AuthApiError

import auth
import database
import main
import token_supabase
from token_supabase import CacheJWKS, TokenInvalido, ler_token_supabase

SUPABASE_URL = "https://exemplo.supabase.co"
EMISSOR = f"{SUPABASE_URL}/auth/v1"
USER_ID = "0b1c2d3e-4f50-4617-8899-aabbccddeeff"

CHAVE_EC = ec.generate_private_key(ec.SECP256R1())
CHAVE_RSA = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OUTRA_EC = ec.generate_private_key(ec.SECP256R1())


def jwk(chave_privada, kid: str, alg: str) -> dict:
    publica = chave_privada.public_key()
    algoritmo = jwt.algorithms.ECAlgorithm if alg == "ES256" else jwt.algorithms.RSAAlgorithm
    dados = algoritmo.to_jwk(publica, as_dict=True)
    return {**dados, "kid": kid, "alg": alg, "use": "sig"}


JWK_EC = jwk(CHAVE_EC, "kid-ec", "ES256")
JWK_RSA = jwk(CHAVE_RSA, "kid-rsa", "RS256")
JWK_OUTRA = jwk(OUTRA_EC, "kid-novo", "ES256")


def corpo(**mudancas) -> dict:
    agora = int(time.time())
    dados = {
        "sub": USER_ID,
        "aud": "authenticated",
        "iss": EMISSOR,
        "role": "authenticated",
        "iat": agora,
        "exp": agora + 3600,
        "email": "pessoa.inventada@exemplo.pt",
    }
    dados.update(mudancas)
    return {chave: valor for chave, valor in dados.items() if valor is not None}


def token(chave=CHAVE_EC, kid="kid-ec", alg="ES256", **mudancas) -> str:
    return jwt.encode(corpo(**mudancas), chave, algorithm=alg, headers={"kid": kid})


def b64(dados: bytes) -> str:
    return jwt.utils.base64url_encode(dados).decode()


class Pedidos:
    """Imita o pedido do JWKS: devolve as respostas por ordem (a última repete-se) e conta os pedidos."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.feitos = 0

    def __call__(self, url):
        assert url == f"{EMISSOR}/.well-known/jwks.json"
        resposta = self.respostas[min(self.feitos, len(self.respostas) - 1)]
        self.feitos += 1
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


@pytest.fixture
def relogio(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(token_supabase, "_relogio", lambda: agora[0])
    return agora


def cache(*respostas) -> tuple[CacheJWKS, Pedidos]:
    pedidos = Pedidos(*respostas)
    return CacheJWKS(token_supabase.url_jwks(SUPABASE_URL), pedir=pedidos), pedidos


def ler(t: str, chaves: CacheJWKS):
    return ler_token_supabase(t, chaves, EMISSOR)


# --- token_supabase.ler_token_supabase ---


def test_token_es256_valido_devolve_o_id(relogio):
    chaves, _ = cache({"keys": [JWK_EC, JWK_RSA]})
    assert ler(token(), chaves) == USER_ID


def test_token_rs256_valido_devolve_o_id(relogio):
    chaves, _ = cache({"keys": [JWK_EC, JWK_RSA]})
    assert ler(token(CHAVE_RSA, "kid-rsa", "RS256"), chaves) == USER_ID


@pytest.mark.parametrize(
    "mudancas",
    [
        {"exp": int(time.time()) - 3600, "iat": int(time.time()) - 7200},
        {"aud": "anon"},
        {"aud": None},
        {"iss": "https://outro.supabase.co/auth/v1"},
        {"iss": None},
        {"exp": None},
        {"sub": None},
        {"sub": "nao-e-um-uuid"},
        {"role": "service_role"},
        {"role": None},
    ],
    ids=[
        "expirado", "aud errado", "sem aud", "iss errado", "sem iss", "sem exp", "sem sub",
        "sub nao uuid", "role service", "sem role",
    ],
)
def test_token_da_nossa_chave_mas_estragado_e_recusado(relogio, mudancas):
    chaves, _ = cache({"keys": [JWK_EC]})
    with pytest.raises(TokenInvalido):
        ler(token(**mudancas), chaves)


def test_assinatura_de_outra_chave_com_o_nosso_kid_e_recusada(relogio):
    chaves, _ = cache({"keys": [JWK_EC]})
    with pytest.raises(TokenInvalido):
        ler(token(OUTRA_EC, "kid-ec"), chaves)


def test_alg_none_e_recusado_sem_pedir_o_jwks(relogio):
    chaves, pedidos = cache({"keys": [JWK_EC]})
    sem_assinatura = f"{b64(json.dumps({'alg': 'none', 'kid': 'kid-ec'}).encode())}.{b64(json.dumps(corpo()).encode())}."
    with pytest.raises(TokenInvalido):
        ler(sem_assinatura, chaves)
    assert pedidos.feitos == 0


def test_hs256_com_a_chave_publica_nunca_e_aceite(relogio):
    # Confusão de algoritmos: assinar HS256 usando a chave pública (que é pública) como segredo.
    chaves, _ = cache({"keys": [JWK_EC]})
    publica_pem = CHAVE_EC.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    cabecalho = b64(json.dumps({"alg": "HS256", "kid": "kid-ec", "typ": "JWT"}).encode())
    dados = b64(json.dumps(corpo()).encode())
    assinatura = b64(hmac.new(publica_pem, f"{cabecalho}.{dados}".encode(), hashlib.sha256).digest())
    # Não se valida aqui: segue para o Supabase (get_user), que o recusa.
    assert ler(f"{cabecalho}.{dados}.{assinatura}", chaves) is None


def test_alg_do_token_diferente_do_da_chave_e_recusado(relogio):
    # kid da chave RSA, mas o token diz ES256 (assinado com uma chave EC).
    chaves, _ = cache({"keys": [JWK_EC, JWK_RSA]})
    with pytest.raises(TokenInvalido):
        ler(token(CHAVE_EC, "kid-rsa", "ES256"), chaves)


def test_lixo_e_token_sem_kid_seguem_para_o_supabase(relogio):
    chaves, _ = cache({"keys": [JWK_EC]})
    assert ler("isto-nao-e-um-token", chaves) is None
    sem_kid = jwt.encode(corpo(), CHAVE_EC, algorithm="ES256")
    assert ler(sem_kid, chaves) is None


def test_chave_simetrica_no_jwks_e_ignorada(relogio):
    segredo = "segredo-inventado-com-mais-de-32-caracteres"
    oct_jwk = {"kty": "oct", "kid": "kid-oct", "alg": "HS256", "k": b64(segredo.encode())}
    chaves, _ = cache({"keys": [oct_jwk]})
    assert ler(jwt.encode(corpo(), segredo, algorithm="HS256", headers={"kid": "kid-oct"}), chaves) is None


# --- CacheJWKS ---


def test_jwks_fica_em_cache_10_minutos(relogio):
    chaves, pedidos = cache({"keys": [JWK_EC]})
    for _ in range(5):
        assert ler(token(), chaves) == USER_ID
    assert pedidos.feitos == 1

    relogio[0] += token_supabase.VALIDADE_CACHE_SEGUNDOS
    assert ler(token(), chaves) == USER_ID
    assert pedidos.feitos == 2


def test_kid_desconhecido_refresca_o_jwks(relogio):
    # O Supabase rodou a chave: o kid novo só aparece no segundo pedido do JWKS.
    chaves, pedidos = cache({"keys": [JWK_EC]}, {"keys": [JWK_EC, JWK_OUTRA]})
    assert ler(token(), chaves) == USER_ID

    relogio[0] += token_supabase.INTERVALO_MINIMO_ENTRE_PEDIDOS
    assert ler(token(OUTRA_EC, "kid-novo"), chaves) == USER_ID
    assert pedidos.feitos == 2


def test_kids_inventados_nao_obrigam_a_pedir_o_jwks_em_cada_pedido(relogio):
    chaves, pedidos = cache({"keys": [JWK_EC]})
    assert ler(token(), chaves) == USER_ID
    for i in range(20):
        assert ler(token(OUTRA_EC, f"kid-inventado-{i}"), chaves) is None
    # Dentro do intervalo mínimo, nenhum pedido a mais.
    assert pedidos.feitos == 1


def test_jwks_em_baixo_segue_para_o_supabase_e_espera_antes_de_tentar(relogio, capsys):
    chaves, pedidos = cache(ConnectionError("sem rede (inventado)"), {"keys": [JWK_EC]})
    assert ler(token(), chaves) is None
    assert ler(token(), chaves) is None
    assert pedidos.feitos == 1
    assert "ConnectionError" in capsys.readouterr().out

    relogio[0] += token_supabase.ESPERA_DEPOIS_DE_FALHA
    assert ler(token(), chaves) == USER_ID


def test_jwks_vazio_segue_para_o_supabase(relogio):
    # Projeto ainda com o segredo HS256: o JWKS não tem chaves assimétricas.
    chaves, _ = cache({"keys": []})
    assert ler(token(), chaves) is None


# --- obter_utilizador_atual e DELETE /conta (auth.py e main.py) ---


class AuthFalso:
    def __init__(self, contas: dict[str, str]):
        self.contas = contas
        self.pedidos: list[str] = []

    def get_user(self, t):
        self.pedidos.append(t)
        if t not in self.contas:
            raise AuthApiError("invalid JWT", 401, "bad_jwt")
        return SimpleNamespace(user=SimpleNamespace(id=self.contas[t]))


class SupabaseFalso:
    """Só o que o auth.py usa: get_user e a tabela assinaturas."""

    def __init__(self, contas=None, com_assinatura=(USER_ID,)):
        self.auth = AuthFalso(contas or {})
        self.com_assinatura = set(com_assinatura)
        self._id = None

    def table(self, nome):
        assert nome == "assinaturas"
        return self

    def select(self, *args):
        return self

    def eq(self, coluna, valor):
        self._id = valor
        return self

    def execute(self):
        return SimpleNamespace(data=[{"user_id": self._id}] if self._id in self.com_assinatura else [])


@pytest.fixture
def api():
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def com_jwks(monkeypatch, *respostas) -> Pedidos:
    pedidos = Pedidos(*respostas)
    monkeypatch.setattr(auth.CHAVES_SUPABASE, "pedir", pedidos)
    return pedidos


def cabecalho(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def test_api_aceita_token_valido_sem_pedir_ao_supabase(api, monkeypatch):
    falso = SupabaseFalso()
    monkeypatch.setattr(auth, "supabase", falso)
    com_jwks(monkeypatch, {"keys": [JWK_EC]})

    resposta = api.get("/eu", headers=cabecalho(token()))

    assert resposta.status_code == 200
    assert resposta.json() == {"user_id": USER_ID}
    assert falso.auth.pedidos == []


@pytest.mark.parametrize("mudancas", [{"exp": int(time.time()) - 60}, {"aud": "anon"}, {"iss": "https://x/auth/v1"}])
def test_api_recusa_token_estragado_com_401_sem_pedir_ao_supabase(api, monkeypatch, mudancas):
    falso = SupabaseFalso()
    monkeypatch.setattr(auth, "supabase", falso)
    com_jwks(monkeypatch, {"keys": [JWK_EC]})

    resposta = api.get("/eu", headers=cabecalho(token(**mudancas)))

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Token inválido"}
    assert falso.auth.pedidos == []


def test_api_com_jwks_em_baixo_usa_o_get_user(api, monkeypatch):
    t = token()
    falso = SupabaseFalso(contas={t: USER_ID})
    monkeypatch.setattr(auth, "supabase", falso)
    com_jwks(monkeypatch, ConnectionError("sem rede (inventado)"))

    resposta = api.get("/eu", headers=cabecalho(t))

    assert resposta.status_code == 200
    assert falso.auth.pedidos == [t]


def test_conta_apagada_com_token_ainda_valido_leva_403(api, monkeypatch):
    # A assinatura apaga-se com a conta (ON DELETE CASCADE): o token ainda é válido, mas a conta já não entra.
    monkeypatch.setattr(auth, "supabase", SupabaseFalso(com_assinatura=()))
    com_jwks(monkeypatch, {"keys": [JWK_EC]})

    assert api.get("/eu", headers=cabecalho(token())).status_code == 403


def test_apagar_conta_confirma_sempre_no_supabase(api, monkeypatch):
    t = token()
    falso = SupabaseFalso(contas={t: USER_ID})
    monkeypatch.setattr(auth, "supabase", falso)
    com_jwks(monkeypatch, {"keys": [JWK_EC]})
    apagados: list[str] = []
    monkeypatch.setattr(main, "apagar_utilizador", apagados.append)

    resposta = api.request("DELETE", "/conta", json={"confirmacao": "APAGAR"}, headers=cabecalho(t))

    assert resposta.status_code == 204
    assert falso.auth.pedidos == [t]
    assert apagados == [USER_ID]


def test_apagar_conta_com_sessao_terminada_no_supabase_da_401(api, monkeypatch):
    # O token ainda é válido pela assinatura, mas o Supabase já não o aceita (sessão terminada, conta bloqueada).
    monkeypatch.setattr(auth, "supabase", SupabaseFalso(contas={}))
    com_jwks(monkeypatch, {"keys": [JWK_EC]})
    apagados: list[str] = []
    monkeypatch.setattr(main, "apagar_utilizador", apagados.append)

    resposta = api.request("DELETE", "/conta", json={"confirmacao": "APAGAR"}, headers=cabecalho(token()))

    assert resposta.status_code == 401
    assert apagados == []


def test_apagar_conta_pelo_get_user_nao_pergunta_duas_vezes(api, monkeypatch):
    t = token()
    falso = SupabaseFalso(contas={t: USER_ID})
    monkeypatch.setattr(auth, "supabase", falso)
    com_jwks(monkeypatch, {"keys": []})
    monkeypatch.setattr(main, "apagar_utilizador", lambda user_id: None)

    resposta = api.request("DELETE", "/conta", json={"confirmacao": "APAGAR"}, headers=cabecalho(t))

    assert resposta.status_code == 204
    assert falso.auth.pedidos == [t]



# --- Casos pedidos pelo dev-seguranca ---


def test_emissor_e_jwks_vem_do_supabase_url_do_env():
    # Com um domínio próprio no Supabase, o SUPABASE_URL tem de ser esse domínio (ver emissor_esperado).
    url = database.SUPABASE_URL.rstrip("/")
    assert auth.EMISSOR_SUPABASE == f"{url}/auth/v1"
    assert auth.CHAVES_SUPABASE.url == f"{url}/auth/v1/.well-known/jwks.json"
    assert token_supabase.emissor_esperado("https://exemplo.supabase.co/") == EMISSOR


@pytest.mark.parametrize(
    "mudancas",
    [{"iat": int(time.time()) + 3600}, {"nbf": int(time.time()) + 3600}],
    ids=["iat no futuro", "nbf no futuro"],
)
def test_token_ainda_nao_valido_e_recusado(relogio, mudancas):
    chaves, _ = cache({"keys": [JWK_EC]})
    with pytest.raises(TokenInvalido):
        ler(token(**mudancas), chaves)


def test_chave_de_cifra_no_jwks_e_ignorada(relogio, capsys):
    chaves, _ = cache({"keys": [{**JWK_EC, "use": "enc"}]})
    assert ler(token(), chaves) is None


@pytest.mark.parametrize("jwks", [["nao", "e", "um", "dict"], "texto", None, {"keys": "nao-e-lista"}])
def test_jwks_com_forma_estranha_segue_para_o_supabase(relogio, jwks):
    chaves, _ = cache(jwks)
    assert ler(token(), chaves) is None


def test_aviso_uma_vez_se_o_jwks_tem_chaves_e_nenhuma_serve(relogio, capsys):
    chaves, _ = cache({"keys": [{**JWK_EC, "use": "enc"}]})
    ler(token(), chaves)
    relogio[0] += token_supabase.VALIDADE_CACHE_SEGUNDOS
    ler(token(), chaves)

    saida = capsys.readouterr().out
    assert saida.count("nenhuma serve") == 1
    # Sem dados das chaves no log.
    assert JWK_EC["x"] not in saida and "kid-ec" not in saida


def test_jwks_vazio_nao_avisa(relogio, capsys):
    chaves, _ = cache({"keys": []})
    ler(token(), chaves)
    assert "nenhuma serve" not in capsys.readouterr().out


def test_pedido_do_jwks_nao_prende_os_outros_pedidos(relogio):
    # Enquanto um pedido vai buscar o JWKS (lento), outro não espera: segue para o get_user (None).
    a_pedir = threading.Event()
    soltar = threading.Event()

    def pedir_lento(url):
        a_pedir.set()
        assert soltar.wait(5)
        return {"keys": [JWK_EC]}

    chaves = CacheJWKS(token_supabase.url_jwks(SUPABASE_URL), pedir=pedir_lento)
    resultado: list = []
    primeiro = threading.Thread(target=lambda: resultado.append(ler(token(), chaves)))
    primeiro.start()
    assert a_pedir.wait(5)

    inicio = time.monotonic()
    assert ler(token(), chaves) is None
    assert time.monotonic() - inicio < 1

    soltar.set()
    primeiro.join(5)
    assert resultado == [USER_ID]
    assert ler(token(), chaves) == USER_ID


@pytest.mark.parametrize("demo_ligada", [False, True], ids=["demo desligada", "demo ligada"])
def test_conta_de_demo_com_token_validado_pelo_jwks_leva_423(api, monkeypatch, demo_ligada):
    # Quem entra na conta de demo com email e palavra-passe recebe um token do Supabase: as regras da demo mantêm-se.
    monkeypatch.setenv("DEMO_USER_ID", USER_ID)
    if demo_ligada:
        monkeypatch.setenv("DEMO_TOKEN_SEGREDO", "segredo-da-demo-inventado-com-mais-de-32-caracteres")
        monkeypatch.setenv("DEMO_EMAIL", "demo.inventada@exemplo.pt")
    falso = SupabaseFalso()
    monkeypatch.setattr(auth, "supabase", falso)
    com_jwks(monkeypatch, {"keys": [JWK_EC]})

    assert api.post("/transacoes/categorizar", headers=cabecalho(token())).status_code == 423
    assert api.request("DELETE", "/conta", json={"confirmacao": "APAGAR"}, headers=cabecalho(token())).status_code == 423
    assert api.get("/eu", headers=cabecalho(token())).status_code == 200
    assert falso.auth.pedidos == []


def test_confirmado_com_get_user_de_outra_conta_da_401(api, monkeypatch):
    t = token()
    falso = SupabaseFalso(contas={t: "99999999-8888-4777-8666-555555555555"})
    monkeypatch.setattr(auth, "supabase", falso)
    com_jwks(monkeypatch, {"keys": [JWK_EC]})
    apagados: list[str] = []
    monkeypatch.setattr(main, "apagar_utilizador", apagados.append)

    resposta = api.request("DELETE", "/conta", json={"confirmacao": "APAGAR"}, headers=cabecalho(t))

    assert resposta.status_code == 401
    assert apagados == []
