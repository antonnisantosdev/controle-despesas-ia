"""Lista de espera do Brasil (POST /lista-espera): pública, só com consentimento, sem revelar quem já se inscreveu
e sem pôr o email nos logs. O Supabase é imitado. Emails inventados."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import lista_espera
import main

EMAIL = "pessoa.inventada@exemplo.com"


@pytest.fixture
def api():
    return TestClient(main.app)


class Inscritos(list):
    """As inscrições que chegaram à base de dados: (email, pais, origem); os países dos cartões ficam em cartoes."""

    def __init__(self):
        super().__init__()
        self.cartoes: list[list[str]] = []

    def __call__(self, email, pais, paises_cartoes, origem):
        self.append((email, pais, origem))
        self.cartoes.append(paises_cartoes)


@pytest.fixture
def inscritos(monkeypatch):
    """Troca a gravação pela imitação Inscritos."""
    lista = Inscritos()
    monkeypatch.setattr(main, "inscrever", lista)
    return lista


def inscrever(api, **campos):
    corpo = {"email": EMAIL, "pais": "BR", "paises_cartoes": ["BR"], "consentimento": True, **campos}
    return api.post("/lista-espera", json=corpo)


def test_inscricao_com_consentimento_responde_201(api, inscritos):
    resposta = inscrever(api)

    assert resposta.status_code == 201
    assert resposta.json() == {"mensagem": main.MENSAGEM_LISTA_ESPERA_OK}
    assert inscritos == [(EMAIL, "BR", None)]


def test_o_email_fica_em_minusculas_e_sem_espacos(api, inscritos):
    assert inscrever(api, email="  Pessoa.Inventada@Exemplo.COM ").status_code == 201
    assert inscritos == [(EMAIL, "BR", None)]


def test_o_segundo_pedido_do_mesmo_email_responde_igual(api, inscritos):
    primeira = inscrever(api)
    segunda = inscrever(api)

    # A mesma resposta: a rota não serve para descobrir quem já está na lista.
    assert (primeira.status_code, primeira.json()) == (segunda.status_code, segunda.json())


@pytest.mark.parametrize(
    ("origem", "esperada"),
    [("instagram", "instagram"), (" TikTok ", "tiktok"), ("facebook", "outro"), ("", None), (None, None)],
)
def test_a_origem_entra_na_lista_fechada(api, inscritos, origem, esperada):
    assert inscrever(api, origem=origem).status_code == 201
    assert inscritos[0][2] == esperada


@pytest.mark.parametrize("pais", ["BR", "PT", "outro"])
def test_os_tres_paises_sao_aceites(api, inscritos, pais):
    assert inscrever(api, pais=pais).status_code == 201
    assert inscritos == [(EMAIL, pais, None)]


@pytest.mark.parametrize("cartoes", [["BR"], ["PT"], ["outro"], ["BR", "PT"], ["PT", "BR", "outro"]])
def test_paises_dos_cartoes_chegam_a_base_de_dados(api, inscritos, cartoes):
    assert inscrever(api, paises_cartoes=cartoes).status_code == 201
    assert inscritos.cartoes == [cartoes]


@pytest.mark.parametrize(
    "campos",
    [
        {"consentimento": False},
        {"consentimento": 1},  # só o booleano true conta como consentimento
        {"consentimento": "true"},
        {"consentimento": None},
        {"pais": "br"},
        {"pais": "ES"},
        {"paises_cartoes": []},  # pelo menos um
        {"paises_cartoes": ["BR", "BR"]},  # sem repetidos
        {"paises_cartoes": ["BR", "PT", "outro", "BR"]},  # no máximo 3
        {"paises_cartoes": ["ES"]},
        {"paises_cartoes": ["br"]},
        {"paises_cartoes": "BR"},  # tem de ser uma lista
        {"paises_cartoes": [None]},
        {"paises_cartoes": None},
        {"email": "isto-nao-e-email"},
        {"email": ("a" * 64) + "@" + ("b" * 63 + ".") * 3 + "com"},  # mais de 254 caracteres
    ],
)
def test_dados_invalidos_respondem_422_generico_sem_gravar(api, inscritos, campos):
    resposta = inscrever(api, **campos)

    assert resposta.status_code == 422
    assert resposta.json() == {"detail": main.MENSAGEM_LISTA_ESPERA_INVALIDA}
    assert inscritos == []


def test_sem_paises_dos_cartoes_no_corpo_responde_422(api, inscritos):
    resposta = api.post("/lista-espera", json={"email": EMAIL, "pais": "BR", "consentimento": True})

    assert resposta.status_code == 422
    assert inscritos == []


def test_sem_consentimento_no_corpo_responde_422(api, inscritos):
    resposta = api.post("/lista-espera", json={"email": EMAIL, "pais": "BR", "paises_cartoes": ["BR"]})

    assert resposta.status_code == 422
    assert inscritos == []


def test_o_422_nao_repete_o_email(api, inscritos):
    resposta = inscrever(api, consentimento=False)

    assert EMAIL not in resposta.text


def test_falha_do_supabase_responde_503_sem_o_email_nos_logs(api, monkeypatch, capsys):
    def falhar(email, pais, paises_cartoes, origem):
        raise ConnectionError(f"falhou para {email}")

    monkeypatch.setattr(main, "inscrever", falhar)

    resposta = inscrever(api)

    assert resposta.status_code == 503
    assert resposta.json() == {"detail": main.MENSAGEM_LISTA_ESPERA_FALHOU}
    saida = capsys.readouterr()
    assert EMAIL not in saida.out + saida.err
    assert "ConnectionError" in saida.out


def test_a_rota_e_publica_e_ignora_o_token(api, inscritos):
    # Como o /registo: não lê token nenhum (nem o da demo), por isso um token qualquer não muda nada.
    resposta = api.post(
        "/lista-espera",
        json={"email": EMAIL, "pais": "BR", "paises_cartoes": ["BR"], "consentimento": True},
        headers={"Authorization": "Bearer token-inventado"},
    )

    assert resposta.status_code == 201


# --- A gravação (lista_espera.inscrever) ---


class TabelaFalsa:
    """Imita supabase.table(...).upsert(...).execute() e guarda o que recebeu."""

    def __init__(self):
        self.tabela = None
        self.linha = None
        self.opcoes = None

    def table(self, nome):
        self.tabela = nome
        return self

    def upsert(self, linha, **opcoes):
        self.linha = linha
        self.opcoes = opcoes
        return self

    def execute(self):
        return self


def test_inscrever_grava_sem_mudar_quem_ja_estava(monkeypatch):
    falsa = TabelaFalsa()
    monkeypatch.setattr(lista_espera, "supabase", falsa)
    monkeypatch.setattr(lista_espera, "agora_utc", lambda: datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc))

    lista_espera.inscrever(EMAIL, "PT", ["BR", "PT"], "youtube")

    assert falsa.tabela == "lista_espera"
    assert falsa.linha == {
        "email": EMAIL,
        "pais": "PT",
        "paises_cartoes": ["BR", "PT"],
        "origem": "youtube",
        "consentimento_em": "2026-11-11T12:00:00+00:00",
        "consentimento_versao": lista_espera.VERSAO_CONSENTIMENTO,
    }
    # ON CONFLICT (email) DO NOTHING: o segundo pedido não dá erro nem muda a data do consentimento.
    assert falsa.opcoes["on_conflict"] == "email"
    assert falsa.opcoes["ignore_duplicates"] is True
