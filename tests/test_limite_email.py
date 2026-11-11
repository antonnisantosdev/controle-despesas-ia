"""Limite de tentativas falhadas por conta no POST /login (limite_ip.LimiteDeFalhasPorEmail).

- por (email, rede): LOGIN_FALHAS_POR_EMAIL_E_REDE em 15 min (rede = /48 no IPv6, o próprio IPv4);
- por email: LOGIN_FALHAS_POR_EMAIL_DIA num dia.

O Supabase é imitado: fazer_login aceita só a palavra-passe certa. Os pedidos da mesma "rede" vêm de /64
diferentes do mesmo /48, para o limite por IP (/64) não entrar em jogo. IPs de documentação (2001:db8::/32),
emails e palavras-passe inventados.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from supabase import AuthApiError

import limite_ip
import main

EMAIL = "pessoa.inventada@exemplo.pt"
CERTA = "palavra-certa-inventada"
ERRADA = "palavra-errada-inventada"
POR_PAR = limite_ip.LOGIN_FALHAS_POR_EMAIL_E_REDE
POR_PAR_DIA = limite_ip.LOGIN_FALHAS_POR_EMAIL_E_REDE_DIA
POR_DIA = limite_ip.LOGIN_FALHAS_POR_EMAIL_DIA
MENSAGEM = limite_ip.MENSAGEM_MUITAS_FALHAS_NA_CONTA


@pytest.fixture(autouse=True)
def limites_ligados(monkeypatch):
    monkeypatch.setattr(limite_ip, "LIMITES_PUBLICOS_LIGADOS", True)


@pytest.fixture
def chamadas(monkeypatch):
    """Imita o login do Supabase: conta as chamadas; só a palavra-passe CERTA entra."""
    feitas: list[str] = []

    def login(email, password):
        feitas.append(email)
        if password != CERTA:
            raise AuthApiError("Invalid login credentials", 400, "invalid_credentials")
        return "token-inventado"

    monkeypatch.setattr(main, "fazer_login", login)
    return feitas


@pytest.fixture
def relogio(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(limite_ip, "_relogio", lambda: agora[0])
    return agora


@pytest.fixture
def api():
    return TestClient(main.app)


_contador = [0]


@pytest.fixture(autouse=True)
def contador_a_zero():
    _contador[0] = 0


def ip_da_rede(rede: int) -> str:
    """Um IP novo (um /64 que ainda não foi usado) dentro do /48 número `rede`."""
    _contador[0] += 1
    return f"2001:db8:{rede:x}:{_contador[0]:x}::1"


def entrar(api, email=EMAIL, password=ERRADA, rede=1, cliente=None):
    cliente = cliente or api
    return cliente.post(
        "/login", json={"email": email, "password": password}, headers={"X-Forwarded-For": ip_da_rede(rede)}
    )


def test_rede_do_ip():
    assert limite_ip.rede_do_ip("203.0.113.5") == "203.0.113.5"
    assert limite_ip.rede_do_ip("::ffff:203.0.113.5") == "203.0.113.5"
    assert limite_ip.rede_do_ip("2001:db8:1:2::9") == "2001:db8:1::/48"


def test_falhas_da_mesma_rede_acumulam_e_bloqueiam(api, chamadas, relogio):
    for i in range(POR_PAR):
        assert entrar(api).status_code == 401, i

    bloqueado = entrar(api)

    assert bloqueado.status_code == 429
    assert bloqueado.json() == {"detail": MENSAGEM}
    # O pedido bloqueado não chegou ao Supabase.
    assert len(chamadas) == POR_PAR


def test_mensagem_igual_exista_ou_nao_a_conta(api, chamadas, relogio):
    # O Supabase responde igual (invalid_credentials) a uma conta que não existe: a API também.
    for _ in range(POR_PAR):
        entrar(api, email="nao.existe@exemplo.pt")
        entrar(api)
    assert entrar(api, email="nao.existe@exemplo.pt").json() == entrar(api).json() == {"detail": MENSAGEM}


def test_bloqueio_vale_tambem_para_a_palavra_passe_certa(api, chamadas, relogio):
    for _ in range(POR_PAR):
        entrar(api)

    assert entrar(api, password=CERTA).status_code == 429


def test_outra_rede_continua_a_entrar(api, chamadas, relogio):
    for _ in range(POR_PAR):
        entrar(api, rede=1)
    assert entrar(api, rede=1).status_code == 429

    assert entrar(api, rede=2).status_code == 401
    assert entrar(api, rede=2, password=CERTA).status_code == 200


def test_login_certo_nao_conta(api, chamadas, relogio):
    for _ in range(POR_PAR + 5):
        assert entrar(api, password=CERTA).status_code == 200
    # Ainda há espaço para as falhas todas.
    for _ in range(POR_PAR):
        assert entrar(api).status_code == 401


def test_email_por_confirmar_nao_conta(api, monkeypatch, relogio):
    def por_confirmar(email, password):
        raise AuthApiError("Email not confirmed", 400, "email_not_confirmed")

    monkeypatch.setattr(main, "fazer_login", por_confirmar)
    for _ in range(POR_PAR + 2):
        assert entrar(api).status_code == 401


def test_supabase_em_baixo_nao_conta(api, chamadas, monkeypatch, relogio):
    def em_baixo(email, password):
        raise ConnectionError("sem rede (inventado)")

    monkeypatch.setattr(main, "fazer_login", em_baixo)
    sem_excecoes = TestClient(main.app, raise_server_exceptions=False)
    for _ in range(POR_PAR + 2):
        assert entrar(api, cliente=sem_excecoes).status_code == 500

    # As tentativas com o Supabase em baixo foram devolvidas.
    assert limite_ip.LIMITE_LOGIN_POR_EMAIL.curto._pedidos == {}
    assert limite_ip.LIMITE_LOGIN_POR_EMAIL.dia._pedidos == {}


def test_maiusculas_e_espacos_contam_como_o_mesmo_email(api, chamadas, relogio):
    formas = [EMAIL, EMAIL.upper(), f"  {EMAIL}  ", "Pessoa.Inventada@Exemplo.PT "]
    for i in range(POR_PAR):
        assert entrar(api, email=formas[i % len(formas)]).status_code == 401

    assert entrar(api, email=EMAIL.title()).status_code == 429


def test_outro_email_nao_e_afetado(api, chamadas, relogio):
    for _ in range(POR_PAR):
        entrar(api)
    assert entrar(api).status_code == 429

    assert entrar(api, email="outra.pessoa@exemplo.pt").status_code == 401
    assert entrar(api, email="outra.pessoa@exemplo.pt", password=CERTA).status_code == 200


def test_janela_curta_acaba(api, chamadas, relogio):
    for _ in range(POR_PAR):
        entrar(api)
    assert entrar(api).status_code == 429

    relogio[0] += limite_ip.LOGIN_FALHAS_POR_EMAIL_E_REDE_JANELA_SEGUNDOS
    assert entrar(api).status_code == 401


def test_limite_do_dia_por_email_apanha_ataques_de_muitas_redes(api, chamadas, relogio):
    # Cada rede fica abaixo do limite por (email, rede), mas o email chega ao limite do dia.
    for i in range(POR_DIA):
        assert entrar(api, rede=100 + i // (POR_PAR - 1)).status_code == 401, i

    bloqueado = entrar(api, rede=9999)
    assert bloqueado.status_code == 429
    assert bloqueado.json() == {"detail": MENSAGEM}
    assert len(chamadas) == POR_DIA

    # No dia seguinte volta a entrar.
    relogio[0] += limite_ip.DIA
    assert entrar(api, rede=9999, password=CERTA).status_code == 200


def test_bloqueio_do_dia_nao_gasta_o_limite_da_rede(relogio):
    # Se o limite do dia recusar, a reserva do par é devolvida (nada fica meio contado).
    limite = limite_ip.LimiteDeFalhasPorEmail(5, 900, 5, 1, MENSAGEM)
    limite.reservar(EMAIL, "203.0.113.1")
    with pytest.raises(Exception):
        limite.reservar(EMAIL, "203.0.113.2")
    assert limite.curto._pedidos == {limite_ip.chave_do_email(EMAIL, "203.0.113.1"): (1000.0, 1)}
    assert limite.par_dia._pedidos == {limite_ip.chave_do_email(EMAIL, "203.0.113.1"): (1000.0, 1)}


def test_limites_desligados_nao_contam_falhas(api, chamadas, relogio, monkeypatch):
    monkeypatch.setattr(limite_ip, "LIMITES_PUBLICOS_LIGADOS", False)
    for _ in range(POR_PAR + 5):
        assert entrar(api).status_code == 401


def test_pedidos_ao_mesmo_tempo_nao_passam_todos(monkeypatch):
    """Muitos pedidos simultâneos da mesma rede: só POR_PAR chegam ao Supabase, porque a tentativa
    se conta antes do login (sem a reserva, passavam todos antes de o primeiro falhar)."""
    pedidos = POR_PAR * 2
    chamadas: list[str] = []
    cadeado = threading.Lock()

    def login_lento(email, password):
        with cadeado:
            chamadas.append(email)
        time.sleep(0.3)
        raise AuthApiError("Invalid login credentials", 400, "invalid_credentials")

    monkeypatch.setattr(main, "fazer_login", login_lento)
    ips = [f"2001:db8:77:{i + 1:x}::1" for i in range(pedidos)]

    def pedir(ip):
        with TestClient(main.app) as cliente:
            resposta = cliente.post(
                "/login", json={"email": EMAIL, "password": ERRADA}, headers={"X-Forwarded-For": ip}
            )
        return resposta.status_code

    with ThreadPoolExecutor(max_workers=pedidos) as executor:
        estados = list(executor.map(pedir, ips))

    assert len(chamadas) == POR_PAR
    assert sorted(estados) == [401] * POR_PAR + [429] * POR_PAR


def test_memoria_guarda_so_o_hash_do_email(api, chamadas, relogio):
    entrar(api, email=f" {EMAIL.upper()} ")

    limite = limite_ip.LIMITE_LOGIN_POR_EMAIL
    assert list(limite.dia._pedidos) == [limite_ip.chave_do_email(EMAIL)]
    assert list(limite.curto._pedidos) == [limite_ip.chave_do_email(EMAIL, "2001:db8:1::/48")]
    chaves = list(limite.curto._pedidos) + list(limite.dia._pedidos)
    assert all(EMAIL not in chave and len(chave) == 64 for chave in chaves)


def test_email_nao_aparece_nos_logs(api, chamadas, relogio, capsys):
    for _ in range(POR_PAR + 1):
        entrar(api)

    assert EMAIL not in capsys.readouterr().out


@pytest.mark.parametrize(
    "corpo",
    [
        {"email": "a" * 245 + "@exemplo.pt", "password": ERRADA},
        {"email": EMAIL, "password": "p" * 257},
    ],
    ids=["email 256", "password 257"],
)
def test_credenciais_compridas_dao_422_sem_chegar_ao_supabase(api, chamadas, corpo):
    assert api.post("/login", json=corpo).status_code == 422
    assert chamadas == []


def test_credenciais_no_limite_do_tamanho_passam(api, chamadas):
    corpo = {"email": "a" * 243 + "@exemplo.pt", "password": "p" * 256}
    assert len(corpo["email"]) == 254
    assert api.post("/login", json=corpo).status_code == 401


@pytest.mark.parametrize(
    "caminho, mensagem",
    [("/login", main.MENSAGEM_LOGIN_INVALIDO), ("/registo", main.MENSAGEM_REGISTO_INVALIDO)],
)
def test_422_do_login_e_do_registo_nao_devolve_o_que_foi_enviado(api, chamadas, caminho, mensagem):
    password = "segredo-inventado-" + "x" * 282
    assert len(password) == 300

    resposta = api.post(caminho, json={"email": EMAIL, "password": password})

    assert resposta.status_code == 422
    assert resposta.json() == {"detail": mensagem}
    assert password not in resposta.text
    assert "segredo-inventado" not in resposta.text
    assert EMAIL not in resposta.text


@pytest.mark.parametrize("caminho", ["/login", "/registo"])
def test_422_generico_tambem_com_corpo_estragado(api, chamadas, caminho):
    resposta = api.post(caminho, json={"password": "segredo-inventado-sem-email"})

    assert resposta.status_code == 422
    assert "segredo-inventado-sem-email" not in resposta.text


def test_limite_do_dia_por_rede(api, chamadas, relogio):
    # Respeitando a janela curta, a mesma rede chega às falhas do dia e fica bloqueada até ao dia seguinte.
    feitas = 0
    while feitas < POR_PAR_DIA:
        for _ in range(min(POR_PAR, POR_PAR_DIA - feitas)):
            assert entrar(api).status_code == 401
            feitas += 1
        relogio[0] += limite_ip.LOGIN_FALHAS_POR_EMAIL_E_REDE_JANELA_SEGUNDOS

    bloqueado = entrar(api)
    assert bloqueado.status_code == 429
    assert bloqueado.json() == {"detail": MENSAGEM}
    # Outra rede continua a entrar; a mesma rede volta no dia seguinte.
    assert entrar(api, rede=2, password=CERTA).status_code == 200
    relogio[0] += limite_ip.DIA
    assert entrar(api, password=CERTA).status_code == 200


def test_limite_por_email_so_se_atinge_com_cinco_redes(api, chamadas, relogio):
    redes = POR_DIA // POR_PAR_DIA
    assert redes == 5
    for rede in range(redes):
        for _ in range(POR_PAR_DIA // POR_PAR):
            for _ in range(POR_PAR):
                assert entrar(api, rede=500 + rede).status_code == 401
            relogio[0] += limite_ip.LOGIN_FALHAS_POR_EMAIL_E_REDE_JANELA_SEGUNDOS
        # Cada rede fica bloqueada ao fim das suas falhas do dia.
        assert entrar(api, rede=500 + rede).status_code == 429
    assert len(chamadas) == POR_DIA
    # O email chegou ao limite do dia: uma rede nova também é recusada.
    assert entrar(api, rede=999).status_code == 429


@pytest.mark.parametrize(
    "codigo, estado",
    [("over_request_rate_limit", 429), ("unexpected_failure", 500), (None, 503)],
)
def test_outros_erros_do_supabase_nao_contam_como_falha(api, monkeypatch, relogio, codigo, estado):
    def erro_do_supabase(email, password):
        raise AuthApiError("erro do Supabase (inventado)", estado, codigo)

    monkeypatch.setattr(main, "fazer_login", erro_do_supabase)
    for _ in range(POR_PAR + 2):
        resposta = entrar(api)
        # A resposta ao utilizador fica igual à de antes.
        assert resposta.status_code == 401
        assert resposta.json() == {"detail": "Email ou palavra-passe errados"}
    limite = limite_ip.LIMITE_LOGIN_POR_EMAIL
    assert limite.curto._pedidos == limite.par_dia._pedidos == limite.dia._pedidos == {}
