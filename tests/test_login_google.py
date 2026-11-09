"""Login com o Google: a API só monta o endereço do Supabase se o destino for o nosso frontend."""

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

import main

ORIGENS = ["http://localhost:3000", "https://app-exemplo.vercel.app"]


@pytest.fixture
def cliente_publico(monkeypatch):
    """Um cliente sem login: a rota do Google é pública."""
    monkeypatch.setattr(main, "ORIGENS_FRONTEND", ORIGENS)
    return TestClient(main.app)


@pytest.mark.parametrize("origem", ORIGENS)
def test_destino_valido_devolve_o_url_do_supabase(cliente_publico, origem):
    destino = f"{origem}/login/google"

    resposta = cliente_publico.get("/login/google", params={"destino": destino})

    assert resposta.status_code == 200
    url = urlparse(resposta.json()["url"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == "https://exemplo.supabase.co/auth/v1/authorize"
    parametros = parse_qs(url.query)
    assert parametros["provider"] == ["google"]
    assert parametros["redirect_to"] == [destino]


def test_o_destino_vai_codificado_no_url(cliente_publico):
    resposta = cliente_publico.get("/login/google", params={"destino": "http://localhost:3000/login/google"})

    assert "redirect_to=http%3A%2F%2Flocalhost%3A3000%2Flogin%2Fgoogle" in resposta.json()["url"]


def test_aceita_origens_com_espacos_depois_da_virgula(monkeypatch):
    # FRONTEND_URL="http://localhost:3000, https://app-exemplo.vercel.app" também tem de funcionar.
    monkeypatch.setattr(main, "ORIGENS_FRONTEND", ["http://localhost:3000", " https://app-exemplo.vercel.app"])

    resposta = TestClient(main.app).get("/login/google", params={"destino": "https://app-exemplo.vercel.app/login/google"})
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
    resposta = cliente_publico.get("/login/google", params={"destino": destino})

    assert resposta.status_code == 400
    assert "url" not in resposta.json()


def test_sem_destino_responde_400(cliente_publico):
    assert cliente_publico.get("/login/google").status_code == 400
