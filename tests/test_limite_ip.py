"""Limites por IP nas rotas públicas de entrada e registo (limite_ip.py).

O Supabase é imitado: as funções do auth.py que falariam com ele são trocadas por imitações que contam
as chamadas. Os IPs são de redes de documentação (203.0.113.0/24, 198.51.100.0/24, 2001:db8::/32).
"""

import base64
import hashlib
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

import limite_ip
import main

ORIGEM = "http://localhost:3000"
VERIFIER = "segredo-inventado-para-testes_0123456789.abcdefghijklmnopqrstuvw"
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode()
CODIGO = "11111111-2222-4333-8444-555555555555"


@dataclass(frozen=True)
class Rota:
    nome: str
    metodo: str
    caminho: str
    opcoes: dict
    por_ip: int
    por_48: int
    janela: int
    mensagem: str


ROTAS = [
    Rota(
        "login",
        "POST",
        "/login",
        {"json": {"email": "teste@exemplo.pt", "password": "palavra-inventada"}},
        limite_ip.LOGIN_POR_IP,
        limite_ip.LOGIN_POR_48,
        limite_ip.LOGIN_JANELA_SEGUNDOS,
        limite_ip.MENSAGEM_MUITAS_ENTRADAS,
    ),
    Rota(
        "registo",
        "POST",
        "/registo",
        {"json": {"email": "teste@exemplo.pt", "password": "palavra-inventada"}},
        limite_ip.REGISTO_POR_IP,
        limite_ip.REGISTO_POR_48,
        limite_ip.REGISTO_JANELA_SEGUNDOS,
        limite_ip.MENSAGEM_MUITOS_REGISTOS,
    ),
    Rota(
        "google_inicio",
        "GET",
        "/login/google",
        {"params": {"destino": f"{ORIGEM}/login/google", "code_challenge": CHALLENGE}},
        limite_ip.GOOGLE_INICIO_POR_IP,
        limite_ip.GOOGLE_INICIO_POR_48,
        limite_ip.GOOGLE_INICIO_JANELA_SEGUNDOS,
        limite_ip.MENSAGEM_MUITAS_ENTRADAS,
    ),
    Rota(
        "google_troca",
        "POST",
        "/login/google/troca",
        {"json": {"code": CODIGO, "code_verifier": VERIFIER}},
        limite_ip.GOOGLE_TROCA_POR_IP,
        limite_ip.GOOGLE_TROCA_POR_48,
        limite_ip.GOOGLE_TROCA_JANELA_SEGUNDOS,
        limite_ip.MENSAGEM_MUITAS_ENTRADAS,
    ),
]
POR_NOME = {rota.nome: rota for rota in ROTAS}


@pytest.fixture
def supabase_falso(monkeypatch):
    """Troca as funções do auth.py usadas pelo main.py: contam as chamadas e nunca saem para a rede."""
    chamadas: list[str] = []

    def login(email, password):
        chamadas.append("login")
        return "token-inventado"

    def registo(email, password):
        chamadas.append("registo")

    def inicio(destino, code_challenge):
        chamadas.append("google_inicio")
        return "https://exemplo.supabase.co/auth/v1/authorize?provider=google"

    def troca(codigo, code_verifier):
        chamadas.append("google_troca")
        return "token-inventado"

    monkeypatch.setattr(main, "fazer_login", login)
    monkeypatch.setattr(main, "fazer_registo", registo)
    monkeypatch.setattr(main, "url_login_google", inicio)
    monkeypatch.setattr(main, "trocar_codigo_google", troca)
    monkeypatch.setattr(main, "ORIGENS_FRONTEND", [ORIGEM])
    return chamadas


@pytest.fixture
def relogio(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(limite_ip, "_relogio", lambda: agora[0])
    return agora


@pytest.fixture
def api():
    return TestClient(main.app)


def pedir(api, rota: Rota, xff: str | None = None):
    cabecalhos = {"X-Forwarded-For": xff} if xff else {}
    return api.request(rota.metodo, rota.caminho, headers=cabecalhos, **rota.opcoes)


@pytest.mark.parametrize("rota", ROTAS, ids=lambda rota: rota.nome)
def test_429_no_pedido_a_seguir_ao_limite_sem_chamar_o_supabase(api, supabase_falso, relogio, rota):
    for i in range(rota.por_ip):
        assert pedir(api, rota, "203.0.113.7").status_code in (200, 201), i

    bloqueado = pedir(api, rota, "203.0.113.7")

    assert bloqueado.status_code == 429
    assert bloqueado.json() == {"detail": rota.mensagem}
    # O pedido recusado não chegou ao Supabase.
    assert supabase_falso.count(rota.nome) == rota.por_ip


@pytest.mark.parametrize("rota", ROTAS, ids=lambda rota: rota.nome)
def test_entrada_inventada_a_esquerda_do_x_forwarded_for_nao_escapa(api, supabase_falso, relogio, rota):
    for i in range(rota.por_ip):
        # O browser pode inventar as entradas da esquerda; só a da direita (a do proxy) conta.
        assert pedir(api, rota, f"198.51.100.{i}, 203.0.113.9").status_code in (200, 201)

    assert pedir(api, rota, "198.51.100.200, 203.0.113.9").status_code == 429
    # Outro IP verdadeiro continua a passar.
    assert pedir(api, rota, "203.0.113.10").status_code in (200, 201)


@pytest.mark.parametrize("rota", ROTAS, ids=lambda rota: rota.nome)
def test_ipv6_do_mesmo_64_contam_juntos(api, supabase_falso, relogio, rota):
    for i in range(rota.por_ip):
        assert pedir(api, rota, f"2001:db8:1:2::{i + 1:x}").status_code in (200, 201)

    assert pedir(api, rota, "2001:db8:1:2:abcd::99").status_code == 429
    # Outro /64 continua a passar.
    assert pedir(api, rota, "2001:db8:1:3::1").status_code in (200, 201)


@pytest.mark.parametrize("rota", ROTAS, ids=lambda rota: rota.nome)
def test_teto_por_48_no_ipv6(api, supabase_falso, relogio, rota):
    # Cada pedido vem de um /64 diferente do mesmo /48: nenhum chega ao limite por IP.
    for i in range(rota.por_48):
        assert pedir(api, rota, f"2001:db8:7:{i:x}::1").status_code in (200, 201), i

    bloqueado = pedir(api, rota, "2001:db8:7:ffff::1")
    assert bloqueado.status_code == 429
    assert bloqueado.json() == {"detail": rota.mensagem}
    # Outro /48 e os IPv4 não contam para este limite.
    assert pedir(api, rota, "2001:db8:8::1").status_code in (200, 201)
    assert pedir(api, rota, "203.0.113.50").status_code in (200, 201)


def test_contadores_separados_por_rota(api, supabase_falso, relogio):
    login = POR_NOME["login"]
    for _ in range(login.por_ip):
        pedir(api, login, "203.0.113.20")
    assert pedir(api, login, "203.0.113.20").status_code == 429

    # O mesmo IP continua a poder usar as outras rotas.
    for nome in ("registo", "google_inicio", "google_troca"):
        assert pedir(api, POR_NOME[nome], "203.0.113.20").status_code in (200, 201), nome


@pytest.mark.parametrize("rota", ROTAS, ids=lambda rota: rota.nome)
def test_a_janela_recomeca(api, supabase_falso, relogio, rota):
    for _ in range(rota.por_ip):
        pedir(api, rota, "203.0.113.30")
    assert pedir(api, rota, "203.0.113.30").status_code == 429

    relogio[0] += rota.janela - 1
    assert pedir(api, rota, "203.0.113.30").status_code == 429
    relogio[0] += 1
    assert pedir(api, rota, "203.0.113.30").status_code in (200, 201)


def test_corpo_invalido_tambem_conta(api, supabase_falso, relogio):
    # O limite corre antes de se ler o corpo: pedidos estragados não servem para martelar a rota.
    troca = POR_NOME["google_troca"]
    for _ in range(troca.por_ip):
        assert api.post(troca.caminho, json={"code": "x"}).status_code == 422

    assert pedir(api, troca).status_code == 429
    assert supabase_falso == []


def test_o_429_nao_poe_ips_nos_logs(api, supabase_falso, relogio, capsys):
    login = POR_NOME["login"]
    for _ in range(login.por_ip + 1):
        pedir(api, login, "198.51.100.77, 203.0.113.77")

    saida = capsys.readouterr()
    assert "203.0.113.77" not in saida.out + saida.err
    assert "198.51.100.77" not in saida.out + saida.err


def test_registo_recusado_nao_poe_o_email_nos_logs(api, relogio, monkeypatch, capsys):
    from supabase import AuthApiError

    def recusar(email, password):
        raise AuthApiError(f"User {email} already registered", 422, "user_already_exists")

    monkeypatch.setattr(main, "fazer_registo", recusar)

    resposta = api.post("/registo", json={"email": "pessoa.inventada@exemplo.pt", "password": "palavra-inventada"})

    assert resposta.status_code == 400
    saida = capsys.readouterr().out
    assert "pessoa.inventada@exemplo.pt" not in saida
    assert "user_already_exists" in saida


def test_pedido_recusado_pelo_ip_nao_conta_para_o_48(api, supabase_falso, relogio):
    # Um só telemóvel (um /64) a martelar não pode bloquear o /48 inteiro dos vizinhos.
    login = POR_NOME["login"]
    for _ in range(login.por_48 + 5):
        pedir(api, login, "2001:db8:9:1::1")

    assert pedir(api, login, "2001:db8:9:2::1").status_code == 200


def test_teto_cheio_esquece_o_ip_mais_antigo_em_vez_de_recusar(relogio):
    limite = limite_ip.LimitePorIP(2, 60, "cheio", teto_ips=3, esquecer_ao_encher=True)
    for i in range(3):
        relogio[0] += 1
        limite.registar(f"203.0.113.{i}")

    # Um IP novo entra na mesma (o mais antigo, .0, é esquecido).
    relogio[0] += 1
    limite.registar("203.0.113.99")
    assert "203.0.113.0" not in limite._pedidos
    assert len(limite._pedidos) == 3


def test_teto_cheio_sem_esquecer_continua_a_recusar(relogio):
    # A demo mantém o comportamento antigo: na dúvida fecha-se.
    limite = limite_ip.LimitePorIP(2, 60, "limite", teto_ips=1, mensagem_teto="teto")
    limite.registar("203.0.113.1")
    with pytest.raises(limite_ip.HTTPException) as erro:
        limite.registar("203.0.113.2")
    assert erro.value.detail == "teto"


def test_registo_com_erro_de_rede_da_503_sem_detalhes(api, relogio, monkeypatch, capsys):
    def falhar(email, password):
        raise ConnectionError(f"falhou para {email}")

    monkeypatch.setattr(main, "fazer_registo", falhar)

    resposta = api.post("/registo", json={"email": "pessoa.inventada@exemplo.pt", "password": "palavra-inventada"})

    assert resposta.status_code == 503
    assert "pessoa.inventada@exemplo.pt" not in capsys.readouterr().out
