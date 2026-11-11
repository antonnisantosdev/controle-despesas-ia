"""Brasil, Fase 1 (sql/020): país onde vive, países dos cartões e contas, moeda principal e fuso por país.

Contas PT continuam como sempre (EUR). O "hoje" mostrado e as datas são os do país onde a pessoa vive;
os contadores dos limites começam no início de dia/mês mais antigo entre Lisboa e São Paulo (mudar de país
não dá pedidos a mais); o ativo_ate dos planos pagos conta sempre em Lisboa.
A moeda de cada movimento é sempre a principal da conta, nunca a do pedido. Supabase imitado; dados inventados.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from pydantic import ValidationError

import auth
import compras
import ferramentas
import ia
import limite_ip
import limites
import main
import perfil
from limites import FUSO_LISBOA, FUSO_SAO_PAULO, Assinatura, CONFIG_IA_POR_PLANO
from models import NovaCompra, NovaConta, PerfilConta, TrocaGoogle
from conftest import BaseDadosFalsa
from perfil import Perfil

UTC = timezone.utc
ID_NOVO = "00000000-0000-4000-8000-000000000001"
EMAIL = "nova@exemplo.com"
VERIFIER = "segredo-inventado-para-testes_0123456789.abcdefghijklmnopqrstuvw"
CODIGO = "11111111-2222-4333-8444-555555555555"
CONTA_BR = Assinatura("essencial", date(2099, 12, 31), pais="BR", paises_bancos=("BR",), moeda="BRL", com_perfil=True)
CONTA_PT = Assinatura("essencial", date(2099, 12, 31), com_perfil=True)


# --- Fuso por país ---


def test_cada_pais_tem_o_seu_fuso():
    assert limites.fuso_do_pais("PT") is FUSO_LISBOA
    assert limites.fuso_do_pais("BR") is FUSO_SAO_PAULO
    # Desconhecido ou vazio: Lisboa, como até aqui.
    assert limites.fuso_do_pais(None) is FUSO_LISBOA
    assert limites.fuso_do_pais("US") is FUSO_LISBOA


@pytest.mark.parametrize(
    ("agora", "periodo", "esperado"),
    [
        # 02:59 UTC de 20 de novembro = 23:59 de 19 em São Paulo (UTC-3, sem hora de verão): ainda é dia 19.
        (datetime(2026, 11, 20, 2, 59, tzinfo=UTC), "dia", datetime(2026, 11, 19, 3, 0, tzinfo=UTC)),
        # 03:00 UTC = meia-noite em São Paulo: o dia 20 começa aqui.
        (datetime(2026, 11, 20, 3, 0, tzinfo=UTC), "dia", datetime(2026, 11, 20, 3, 0, tzinfo=UTC)),
        # 1 de dezembro às 02:30 UTC ainda é 30 de novembro em São Paulo: o mês é novembro.
        (datetime(2026, 12, 1, 2, 30, tzinfo=UTC), "mes", datetime(2026, 11, 1, 3, 0, tzinfo=UTC)),
        (datetime(2026, 12, 1, 3, 0, tzinfo=UTC), "mes", datetime(2026, 12, 1, 3, 0, tzinfo=UTC)),
    ],
)
def test_inicio_do_periodo_em_sao_paulo_a_volta_da_meia_noite(agora, periodo, esperado):
    assert limites.inicio_do_periodo(periodo, agora, FUSO_SAO_PAULO) == esperado


def test_inicio_do_periodo_sem_fuso_continua_em_lisboa():
    agora = datetime(2026, 12, 1, 2, 30, tzinfo=UTC)
    assert limites.inicio_do_periodo("mes", agora) == datetime(2026, 12, 1, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("conta", "esperado"),
    [(CONTA_BR, date(2026, 11, 30)), (CONTA_PT, date(2026, 12, 1))],
)
def test_hoje_do_utilizador_e_o_do_pais_onde_vive(monkeypatch, conta, esperado):
    # 1 de dezembro à 01:00 UTC: em Lisboa já é dia 1, em São Paulo ainda é 30 de novembro.
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 12, 1, 1, 0, tzinfo=UTC))
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: conta)

    assert limites.hoje_do_utilizador("utilizador-teste") == esperado


def test_o_plano_pago_acaba_a_meia_noite_de_lisboa_mesmo_numa_conta_br(monkeypatch):
    # 23:30 UTC de 31 de julho: em São Paulo ainda é dia 31 (20:30), mas o ativo_ate conta em Lisboa (já é 1).
    conta = Assinatura("essencial", date(2026, 7, 31), pais="BR", paises_bancos=("BR",), moeda="BRL", com_perfil=True)
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: conta)
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 7, 31, 23, 30, tzinfo=UTC))

    assert limites.plano_do_utilizador("utilizador-teste") == "free"
    # O "hoje" mostrado continua a ser o do país onde vive.
    assert limites.hoje_do_utilizador("utilizador-teste") == date(2026, 7, 31)


# --- Contadores de pedidos à IA numa conta BR ---


class RpcFalso:
    """Imita supabase.rpc(...): guarda os parâmetros e devolve a resposta dada."""

    def __init__(self, resposta):
        self.resposta = resposta
        self.chamadas: list[tuple[str, dict]] = []

    def rpc(self, nome, parametros):
        self.chamadas.append((nome, parametros))
        return self

    def execute(self):
        return SimpleNamespace(data=self.resposta)


def test_o_dia_dos_pedidos_numa_conta_br_comeca_a_meia_noite_de_sao_paulo(monkeypatch):
    # 02:30 UTC de 20 de novembro: em São Paulo ainda é dia 19 (23:30). Os pedidos de dia 19 ainda contam.
    falso = RpcFalso(True)
    monkeypatch.setattr(limites, "supabase", falso)
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: CONTA_BR)
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 11, 20, 2, 30, tzinfo=UTC))

    limites.registar_pergunta("utilizador-teste", "chat")

    assert falso.chamadas[0][1]["p_desde"] == "2026-11-19T03:00:00+00:00"


def test_o_mes_do_free_numa_conta_br_e_o_de_sao_paulo(monkeypatch):
    falso = RpcFalso(True)
    conta = Assinatura("free", None, pais="BR", paises_bancos=("BR",), moeda="BRL", com_perfil=True)
    monkeypatch.setattr(limites, "supabase", falso)
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: conta)
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 12, 1, 2, 30, tzinfo=UTC))

    limites.registar_pergunta("utilizador-teste", "chat")

    assert falso.chamadas[0][1]["p_desde"] == "2026-11-01T03:00:00+00:00"


def test_o_pdf_numa_conta_br_conta_o_dia_e_o_mes_de_sao_paulo(monkeypatch):
    falso = RpcFalso("ok")
    monkeypatch.setattr(limites, "supabase", falso)
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: CONTA_BR)
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 12, 1, 2, 30, tzinfo=UTC))

    limites.registar_pdf("utilizador-teste")

    parametros = falso.chamadas[0][1]
    assert parametros["p_desde_pedidos"] == "2026-11-30T03:00:00+00:00"
    assert parametros["p_desde_pdf"] == "2026-11-01T03:00:00+00:00"


def test_uma_conta_pt_perto_da_meia_noite_conta_desde_a_meia_noite_de_sao_paulo(monkeypatch):
    # 02:30 UTC de 20 de novembro: em Lisboa já é dia 20, em São Paulo ainda é 19 (23:30).
    # O dia dos contadores é o mais antigo (o de São Paulo), mesmo numa conta PT; o "hoje" mostrado é o de Lisboa.
    falso = RpcFalso(True)
    monkeypatch.setattr(limites, "supabase", falso)
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: CONTA_PT)
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 11, 20, 2, 30, tzinfo=UTC))

    limites.registar_pergunta("utilizador-teste", "chat")

    assert falso.chamadas[0][1]["p_desde"] == "2026-11-19T03:00:00+00:00"
    assert limites.hoje_do_utilizador("utilizador-teste") == date(2026, 11, 20)


@pytest.mark.parametrize(
    "agora",
    [
        datetime(2026, 11, 20, 2, 30, tzinfo=UTC),  # inverno: já é dia 20 em Lisboa, ainda 19 em São Paulo
        datetime(2026, 7, 31, 23, 30, tzinfo=UTC),  # verão: já é 1 de agosto em Lisboa, ainda julho em São Paulo
        datetime(2026, 11, 20, 15, 0, tzinfo=UTC),  # a meio do dia nos dois fusos
    ],
)
def test_mudar_de_pais_nao_da_pedidos_a_mais(monkeypatch, agora):
    # A mesma conta, no mesmo instante, como PT e depois como BR: os contadores começam no mesmo sítio
    # (pedidos, PDF do mês e o mês do Free). Se mudassem, mudar de país abria uma janela nova.
    monkeypatch.setattr(limites, "agora_utc", lambda: agora)
    inicios = []
    free_pt = Assinatura("free", None, com_perfil=True)
    free_br = Assinatura("free", None, pais="BR", paises_bancos=("BR",), moeda="BRL", com_perfil=True)
    for conta in (CONTA_PT, CONTA_BR, free_pt, free_br):
        monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id, conta=conta: conta)
        falso_pdf, falso_pedido = RpcFalso("ok"), RpcFalso(True)
        monkeypatch.setattr(limites, "supabase", falso_pdf)
        limites.registar_pdf("utilizador-teste")
        monkeypatch.setattr(limites, "supabase", falso_pedido)
        limites.registar_pergunta("utilizador-teste", "chat")
        pdf = falso_pdf.chamadas[0][1]
        inicios.append((pdf["p_desde_pedidos"], pdf["p_desde_pdf"], falso_pedido.chamadas[0][1]["p_desde"]))

    assert inicios[0] == inicios[1]  # Essencial: PT e BR iguais
    assert inicios[2] == inicios[3]  # Free: PT e BR iguais


def test_o_plano_de_uma_conta_br_mostra_o_perfil_e_os_contadores(cliente, monkeypatch):
    contados = []
    conta = Assinatura("essencial", date(2099, 1, 1), pais="BR", paises_bancos=("PT", "BR"), moeda="EUR", com_perfil=True)
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: conta)
    monkeypatch.setattr(limites, "pedidos_no_periodo", lambda user_id, periodo: contados.append(periodo) or 2)
    monkeypatch.setattr(limites, "pdfs_no_mes", lambda user_id: contados.append("pdf") or 1)

    corpo = cliente.get("/plano").json()

    assert contados == ["dia", "pdf"]
    assert (corpo["pais"], corpo["paises_bancos"], corpo["moeda"]) == ("BR", ["PT", "BR"], "EUR")
    assert (corpo["usadas"], corpo["pdf_usados"]) == (2, 1)


# --- Ler a assinatura (com e sem a sql/020) ---


class AssinaturasFalsas:
    """Imita a tabela assinaturas. sem_020: o select com as colunas novas falha como no PostgREST."""

    def __init__(self, linhas, sem_020=False):
        self.linhas = linhas
        self.sem_020 = sem_020
        self.selects: list[str] = []

    def table(self, nome):
        return self

    def select(self, colunas):
        self.selects.append(colunas)
        return self

    def eq(self, *args):
        return self

    def execute(self):
        if self.sem_020 and "moeda" in self.selects[-1]:
            raise APIError({"code": "42703", "message": "column assinaturas.pais does not exist"})
        return SimpleNamespace(data=self.linhas)


def test_a_assinatura_le_o_perfil(monkeypatch):
    linha = {"plano": "free", "ativo_ate": None, "pais": "BR", "paises_bancos": ["PT", "BR"], "moeda": "BRL"}
    monkeypatch.setattr(limites, "supabase", AssinaturasFalsas([linha]))

    conta = limites.assinatura_do_utilizador("utilizador-teste")

    assert (conta.pais, conta.paises_bancos, conta.moeda, conta.com_perfil) == ("BR", ("PT", "BR"), "BRL", True)
    assert conta.fuso is FUSO_SAO_PAULO
    assert limites.moeda_da_conta("utilizador-teste") == "BRL"


def test_sem_a_020_a_conta_fica_pt_eur_e_a_moeda_nao_se_envia(monkeypatch, capsys):
    falsa = AssinaturasFalsas([{"plano": "essencial", "ativo_ate": "2026-12-31"}], sem_020=True)
    monkeypatch.setattr(limites, "supabase", falsa)

    conta = limites.assinatura_do_utilizador("utilizador-teste")

    assert falsa.selects == ["plano, ativo_ate, pais, paises_bancos, moeda", "plano, ativo_ate"]
    assert (conta.plano, conta.ativo_ate) == ("essencial", date(2026, 12, 31))
    assert (conta.pais, conta.paises_bancos, conta.moeda, conta.com_perfil) == ("PT", ("PT",), "EUR", False)
    assert limites.moeda_da_conta("utilizador-teste") is None
    assert "sql/020" in capsys.readouterr().out


def test_outros_erros_ao_ler_a_assinatura_nao_sao_escondidos(monkeypatch):
    class SemPermissao(AssinaturasFalsas):
        def execute(self):
            raise APIError({"code": "42501", "message": "permission denied"})

    monkeypatch.setattr(limites, "supabase", SemPermissao([]))

    with pytest.raises(APIError):
        limites.assinatura_do_utilizador("utilizador-teste")


def test_valores_estranhos_na_base_de_dados_passam_aos_de_sempre(monkeypatch):
    linha = {"plano": "free", "ativo_ate": None, "pais": "US", "paises_bancos": ["XX"], "moeda": "USD"}
    monkeypatch.setattr(limites, "supabase", AssinaturasFalsas([linha]))

    conta = limites.assinatura_do_utilizador("utilizador-teste")

    assert (conta.pais, conta.paises_bancos, conta.moeda) == ("PT", ("PT",), "EUR")


# --- Regras do perfil (sem base de dados) ---


@pytest.mark.parametrize(
    ("pais", "bancos", "moeda", "esperado"),
    [
        (None, None, None, None),  # nada no pedido: fica o DEFAULT da base de dados
        ("BR", None, None, Perfil("BR", ("BR",), "BRL")),  # sem bancos: os do país onde vive
        ("PT", None, None, Perfil("PT", ("PT",), "EUR")),
        ("PT", ["BR"], None, Perfil("PT", ("BR",), "BRL")),  # vive em PT com contas só no BR: BRL
        ("BR", ["PT", "BR"], None, Perfil("BR", ("PT", "BR"), "BRL")),  # dois países sem moeda: a do país onde vive
        ("PT", ["PT", "BR"], None, Perfil("PT", ("PT", "BR"), "EUR")),
        ("BR", ["PT", "BR"], "EUR", Perfil("BR", ("PT", "BR"), "EUR")),  # dois países: a escolhida
        (None, ["BR"], None, Perfil("PT", ("BR",), "BRL")),
    ],
)
def test_perfil_inicial(pais, bancos, moeda, esperado):
    assert perfil.perfil_inicial(pais, bancos, moeda) == esperado


@pytest.mark.parametrize(
    ("pais", "bancos", "moeda"),
    [("PT", ["PT"], "BRL"), ("BR", ["BR"], "EUR"), (None, None, "BRL")],
)
def test_perfil_inicial_com_moeda_de_outro_pais_e_recusado(pais, bancos, moeda):
    with pytest.raises(perfil.PerfilInvalido):
        perfil.perfil_inicial(pais, bancos, moeda)


ATUAL_PT = Perfil("PT", ("PT",), "EUR")


@pytest.mark.parametrize(
    ("pais", "bancos", "moeda", "esperado"),
    [
        ("BR", None, None, Perfil("BR", ("PT",), "EUR")),  # mudar só o país não mexe na moeda
        (None, ["PT", "BR"], None, Perfil("PT", ("PT", "BR"), "EUR")),  # juntar BR mantém EUR
        (None, ["PT", "BR"], "BRL", Perfil("PT", ("PT", "BR"), "BRL")),
        (None, ["BR"], None, Perfil("PT", ("BR",), "BRL")),  # tirar PT dos bancos pede BRL
        (None, None, None, ATUAL_PT),
    ],
)
def test_perfil_atualizado(pais, bancos, moeda, esperado):
    assert perfil.perfil_atualizado(ATUAL_PT, pais, bancos, moeda) == esperado


def test_perfil_atualizado_com_moeda_que_nao_e_dos_bancos_e_recusado():
    with pytest.raises(perfil.PerfilInvalido):
        perfil.perfil_atualizado(ATUAL_PT, None, None, "BRL")


# --- Modelos do registo e do Google ---


def test_nova_conta_sem_perfil_continua_valida():
    conta = NovaConta(email=EMAIL, password="uma-boa-palavra")
    assert conta.perfil_pedido() is None


def test_nova_conta_com_perfil_resolve_a_moeda():
    conta = NovaConta(email=EMAIL, password="uma-boa-palavra", pais="BR", paises_bancos=["PT", "BR"])
    assert conta.perfil_pedido() == Perfil("BR", ("PT", "BR"), "BRL")


CAMPOS_INVALIDOS = [
    {"pais": "US"},
    {"pais": "br"},  # só os códigos exatos
    {"paises_bancos": []},
    {"paises_bancos": ["PT", "BR", "PT"]},
    {"paises_bancos": ["PT", "PT"]},
    {"paises_bancos": ["PT", None]},
    {"paises_bancos": "PT"},
    {"moeda": "USD"},
]


@pytest.mark.parametrize("campos", [*CAMPOS_INVALIDOS, {"paises_bancos": ["PT"], "moeda": "BRL"}])
def test_perfil_invalido_no_registo_e_no_google_da_422(campos):
    with pytest.raises(ValidationError):
        NovaConta(email=EMAIL, password="uma-boa-palavra", **campos)
    with pytest.raises(ValidationError):
        TrocaGoogle(code=CODIGO, code_verifier=VERIFIER, **campos)


@pytest.mark.parametrize("campos", CAMPOS_INVALIDOS)
def test_perfil_invalido_nas_definicoes_da_422(campos):
    # A coerência da moeda com os bancos vê-se na rota (precisa do perfil atual): ver mais abaixo.
    with pytest.raises(ValidationError):
        PerfilConta(**campos)


# --- Gravar o perfil no registo e no 1.º login com o Google ---


class PerfilRpcFalso(RpcFalso):
    """Imita o rpc atualizar_perfil_conta; erro imita o PostgREST a recusar."""

    def __init__(self, resposta="ok", erro=None):
        super().__init__(resposta)
        self.erro = erro

    def execute(self):
        if self.erro:
            raise self.erro
        return super().execute()


@pytest.fixture
def rpc_perfil(monkeypatch):
    def _criar(resposta="ok", erro=None):
        falso = PerfilRpcFalso(resposta, erro)
        monkeypatch.setattr(perfil, "supabase", falso)
        return falso

    return _criar


@pytest.fixture
def api():
    return TestClient(main.app)


def parametros(pais, bancos, moeda, user_id=ID_NOVO, so_se_padrao=True):
    """Os parâmetros do rpc. so_se_padrao: True no registo e no Google (por omissão aqui), False nas definições."""
    return (
        "atualizar_perfil_conta",
        {
            "p_user_id": user_id,
            "p_pais": pais,
            "p_paises_bancos": bancos,
            "p_moeda": moeda,
            "p_so_se_padrao": so_se_padrao,
        },
    )


def test_registo_grava_o_perfil_da_conta_nova(api, monkeypatch, rpc_perfil):
    falso = rpc_perfil()
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: ID_NOVO)

    resposta = api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "pais": "BR"})

    assert resposta.status_code == 201
    assert falso.chamadas == [parametros("BR", ["BR"], "BRL")]


def test_registo_sem_perfil_nao_chama_a_funcao(api, monkeypatch, rpc_perfil):
    falso = rpc_perfil()
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: ID_NOVO)

    assert api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra"}).status_code == 201
    assert falso.chamadas == []


def test_registo_de_conta_que_nao_e_nova_nao_grava_o_perfil(api, monkeypatch, rpc_perfil):
    # fazer_registo devolve None quando a conta não acabou de ser criada (ver auth.fazer_registo).
    falso = rpc_perfil()
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: None)

    assert api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "pais": "BR"}).status_code == 201
    assert falso.chamadas == []


def test_registo_com_perfil_incoerente_da_422_generico(api, monkeypatch, rpc_perfil):
    falso = rpc_perfil()
    registos = []
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: registos.append(email))

    resposta = api.post(
        "/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "paises_bancos": ["PT"], "moeda": "BRL"}
    )

    assert resposta.status_code == 422
    assert resposta.json() == {"detail": main.MENSAGEM_REGISTO_INVALIDO}
    assert registos == [] and falso.chamadas == []


@pytest.mark.parametrize(
    "erro",
    [
        APIError({"code": "PGRST202", "message": "Could not find the function"}),  # sql/020 por correr
        RuntimeError("em baixo"),
    ],
)
def test_registo_nao_falha_se_o_perfil_nao_gravar(api, monkeypatch, rpc_perfil, capsys, erro):
    rpc_perfil(erro=erro)
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: ID_NOVO)

    resposta = api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "pais": "BR"})

    assert resposta.status_code == 201
    saida = capsys.readouterr().out
    assert "AVISO" in saida and EMAIL not in saida and ID_NOVO not in saida


def test_registo_de_conta_que_ja_nao_tem_o_perfil_padrao_so_deixa_aviso(api, monkeypatch, rpc_perfil, capsys):
    # A base de dados recusa (a conta já mudou de perfil ou já tem dados): o registo não falha nem muda nada.
    falso = rpc_perfil("nao_padrao")
    monkeypatch.setattr(main, "fazer_registo", lambda email, password: ID_NOVO)

    resposta = api.post("/registo", json={"email": EMAIL, "password": "uma-boa-palavra", "pais": "BR"})

    assert resposta.status_code == 201
    assert falso.chamadas == [parametros("BR", ["BR"], "BRL")]
    saida = capsys.readouterr().out
    assert "AVISO" in saida and "perfil padrão" in saida
    assert EMAIL not in saida and ID_NOVO not in saida


def test_mudar_o_perfil_nas_definicoes_nao_exige_o_perfil_padrao(cliente, conta, rpc_perfil):
    conta(CONTA_BR)
    falso = rpc_perfil("ok")

    assert cliente.put("/conta/perfil", json={"pais": "PT"}).status_code == 200
    assert falso.chamadas[0][1]["p_so_se_padrao"] is False


def test_nao_padrao_nas_definicoes_e_inesperado_e_da_503(cliente, conta, rpc_perfil):
    conta()
    rpc_perfil("nao_padrao")

    resposta = cliente.put("/conta/perfil", json={"pais": "BR"})

    assert resposta.status_code == 503
    assert resposta.json() == {"detail": perfil.MENSAGEM_PERFIL_INDISPONIVEL}


def trocar(api, **campos):
    return api.post("/login/google/troca", json={"code": CODIGO, "code_verifier": VERIFIER, **campos})


def test_primeiro_login_google_grava_o_perfil(api, monkeypatch, rpc_perfil):
    falso = rpc_perfil()
    monkeypatch.setattr(auth, "supabase", SimpleNamespace())  # a origem não vem: não se toca na tabela
    sessao = auth.SessaoGoogle("token-inventado", ID_NOVO, conta_nova=True)
    monkeypatch.setattr(main, "trocar_codigo_google", lambda codigo, verifier: sessao)

    resposta = trocar(api, pais="PT", paises_bancos=["PT", "BR"], moeda="BRL")

    assert resposta.status_code == 200
    assert falso.chamadas == [parametros("PT", ["PT", "BR"], "BRL")]


def test_login_google_de_conta_antiga_nao_grava_o_perfil(api, monkeypatch, rpc_perfil):
    falso = rpc_perfil()
    sessao = auth.SessaoGoogle("token-inventado", ID_NOVO, conta_nova=False)
    monkeypatch.setattr(main, "trocar_codigo_google", lambda codigo, verifier: sessao)

    assert trocar(api, pais="BR").status_code == 200
    assert falso.chamadas == []


# --- PUT /conta/perfil ---


@pytest.fixture
def conta(monkeypatch):
    """Fixa a assinatura que o perfil.py lê (por omissão uma conta PT com a sql/020 corrida)."""

    def _fixar(assinatura=CONTA_PT):
        monkeypatch.setattr(perfil, "assinatura_do_utilizador", lambda user_id: assinatura)

    return _fixar


def test_mudar_o_pais_com_dados_e_livre(cliente, conta, rpc_perfil):
    conta()
    falso = rpc_perfil("ok")

    resposta = cliente.put("/conta/perfil", json={"pais": "BR"})

    assert resposta.status_code == 200
    assert resposta.json() == {"pais": "BR", "paises_bancos": ["PT"], "moeda": "EUR"}
    assert falso.chamadas == [parametros("BR", ["PT"], "EUR", user_id="utilizador-teste", so_se_padrao=False)]


def test_juntar_bancos_do_brasil_mantem_a_moeda(cliente, conta, rpc_perfil):
    conta()
    falso = rpc_perfil("ok")

    resposta = cliente.put("/conta/perfil", json={"paises_bancos": ["PT", "BR"]})

    assert resposta.json() == {"pais": "PT", "paises_bancos": ["PT", "BR"], "moeda": "EUR"}
    assert falso.chamadas[0][1]["p_moeda"] == "EUR"


@pytest.mark.parametrize("corpo", [{"paises_bancos": ["PT", "BR"], "moeda": "BRL"}, {"paises_bancos": ["BR"]}])
def test_mudar_a_moeda_com_dados_da_409(cliente, conta, rpc_perfil, corpo):
    conta()
    falso = rpc_perfil("tem_dados")

    resposta = cliente.put("/conta/perfil", json=corpo)

    assert resposta.status_code == 409
    assert resposta.json() == {"detail": perfil.MENSAGEM_MOEDA_COM_DADOS}
    assert falso.chamadas[0][1]["p_moeda"] == "BRL"


def test_mudar_a_moeda_sem_dados_passa(cliente, conta, rpc_perfil):
    conta()
    rpc_perfil("ok")

    resposta = cliente.put("/conta/perfil", json={"pais": "BR", "paises_bancos": ["BR"]})

    assert resposta.status_code == 200
    assert resposta.json() == {"pais": "BR", "paises_bancos": ["BR"], "moeda": "BRL"}


def test_moeda_que_nao_e_dos_bancos_da_422_sem_chamar_a_base_de_dados(cliente, conta, rpc_perfil):
    conta()
    falso = rpc_perfil("ok")

    resposta = cliente.put("/conta/perfil", json={"moeda": "BRL"})

    assert resposta.status_code == 422
    assert resposta.json() == {"detail": perfil.MENSAGEM_MOEDA_INCOERENTE}
    assert falso.chamadas == []


def test_antes_da_020_o_perfil_responde_503(cliente, conta, rpc_perfil):
    conta(Assinatura("free", None, com_perfil=False))
    falso = rpc_perfil("ok")

    resposta = cliente.put("/conta/perfil", json={"pais": "BR"})

    assert resposta.status_code == 503
    assert resposta.json() == {"detail": perfil.MENSAGEM_PERFIL_INDISPONIVEL}
    assert falso.chamadas == []


@pytest.mark.parametrize(
    ("resposta_rpc", "erro"),
    [
        (None, APIError({"code": "PGRST202", "message": "Could not find the function"})),
        (None, APIError({"code": "23514", "message": "violates check constraint"})),
        (None, APIError({"code": "42501", "message": "permission denied"})),
        ("talvez", None),
        ("sem_conta", None),
    ],
)
def test_respostas_inesperadas_da_funcao_dao_503(cliente, conta, rpc_perfil, resposta_rpc, erro):
    conta()
    rpc_perfil(resposta_rpc, erro)

    resposta = cliente.put("/conta/perfil", json={"pais": "BR"})

    assert resposta.status_code == 503


@pytest.mark.parametrize("codigo", ["42501", "57014"])
def test_erro_a_ler_a_assinatura_no_perfil_da_503(cliente, monkeypatch, rpc_perfil, codigo):
    def falhar(user_id):
        raise APIError({"code": codigo, "message": "falhou"})

    monkeypatch.setattr(perfil, "assinatura_do_utilizador", falhar)
    falso = rpc_perfil("ok")

    resposta = cliente.put("/conta/perfil", json={"pais": "BR"})

    assert resposta.status_code == 503
    assert resposta.json() == {"detail": perfil.MENSAGEM_PERFIL_INDISPONIVEL}
    assert falso.chamadas == []


def test_o_user_id_do_perfil_vem_so_do_token(cliente, conta, rpc_perfil):
    conta()
    falso = rpc_perfil("ok")

    cliente.put("/conta/perfil", json={"pais": "BR", "user_id": "outro-utilizador", "p_user_id": "outro"})

    assert falso.chamadas[0][1]["p_user_id"] == "utilizador-teste"


# --- Limite do PUT /conta/perfil: 10 por hora por conta ---


@pytest.fixture
def relogio(monkeypatch):
    """Fixa o relógio dos limites em memória (segundos); o teste avança-o mudando relogio[0]."""
    agora = [1000.0]
    monkeypatch.setattr(limite_ip, "_relogio", lambda: agora[0])
    return agora


def test_o_11_pedido_numa_hora_da_429_sem_tocar_na_base_de_dados(cliente, monkeypatch, rpc_perfil, relogio):
    leituras = []
    monkeypatch.setattr(perfil, "assinatura_do_utilizador", lambda user_id: leituras.append(user_id) or CONTA_PT)
    falso = rpc_perfil("ok")

    respostas = [cliente.put("/conta/perfil", json={"pais": "BR"}).status_code for _ in range(10)]
    a_mais = cliente.put("/conta/perfil", json={"pais": "BR"})

    assert respostas == [200] * 10
    assert a_mais.status_code == 429
    assert a_mais.json() == {"detail": limite_ip.MENSAGEM_MUITAS_MUDANCAS_DE_PERFIL}
    assert len(leituras) == 10 and len(falso.chamadas) == 10


def test_passada_uma_hora_o_perfil_volta_a_mudar(cliente, conta, rpc_perfil, relogio):
    conta()
    rpc_perfil("ok")
    for _ in range(10):
        cliente.put("/conta/perfil", json={"pais": "BR"})
    assert cliente.put("/conta/perfil", json={"pais": "BR"}).status_code == 429

    relogio[0] += limite_ip.PERFIL_JANELA_SEGUNDOS

    assert cliente.put("/conta/perfil", json={"pais": "BR"}).status_code == 200


def test_o_limite_do_perfil_e_de_cada_conta(cliente, conta, rpc_perfil, relogio):
    conta()
    falso = rpc_perfil("ok")
    for _ in range(10):
        cliente.put("/conta/perfil", json={"pais": "BR"})
    assert cliente.put("/conta/perfil", json={"pais": "BR"}).status_code == 429

    main.app.dependency_overrides[auth.obter_utilizador_atual] = lambda: "outra-conta-teste"

    assert cliente.put("/conta/perfil", json={"pais": "BR"}).status_code == 200
    assert falso.chamadas[-1][1]["p_user_id"] == "outra-conta-teste"


def test_o_user_id_do_corpo_nao_muda_o_contador(cliente, conta, rpc_perfil, relogio):
    # Mandar outro user_id no corpo não abre um contador novo: o limite é pelo user_id do token.
    conta()
    rpc_perfil("ok")
    for numero in range(10):
        cliente.put("/conta/perfil", json={"pais": "BR", "user_id": f"outro-{numero}"})

    assert cliente.put("/conta/perfil", json={"pais": "BR", "user_id": "mais-outro"}).status_code == 429


def test_corpos_invalidos_nao_contam_no_limite(cliente, conta, rpc_perfil, relogio):
    # O Pydantic recusa-os antes da rota (sem tocar na base de dados): não gastam pedidos.
    conta()
    rpc_perfil("ok")

    invalidos = [cliente.put("/conta/perfil", json={"pais": "US"}).status_code for _ in range(15)]

    assert invalidos == [422] * 15
    assert cliente.put("/conta/perfil", json={"pais": "BR"}).status_code == 200


def test_os_409_e_os_422_da_moeda_contam_no_limite(cliente, conta, rpc_perfil, relogio):
    # Cada um já leu a base de dados (a assinatura, e no 409 a função): contam.
    conta()
    rpc_perfil("tem_dados")
    for _ in range(5):
        assert cliente.put("/conta/perfil", json={"paises_bancos": ["BR"]}).status_code == 409
    for _ in range(5):
        assert cliente.put("/conta/perfil", json={"moeda": "BRL"}).status_code == 422

    assert cliente.put("/conta/perfil", json={"pais": "BR"}).status_code == 429


def test_com_o_interruptor_desligado_nao_ha_limite_do_perfil(cliente, conta, rpc_perfil, monkeypatch, relogio):
    monkeypatch.setattr(limite_ip, "LIMITE_PERFIL_LIGADO", False)
    conta()
    rpc_perfil("ok")

    respostas = [cliente.put("/conta/perfil", json={"pais": "BR"}).status_code for _ in range(15)]

    assert respostas == [200] * 15


# --- Moeda dos movimentos: sempre a da conta, nunca a do pedido ---


def test_nova_movimentacao_grava_a_moeda_da_conta_e_ignora_a_do_pedido(cliente, base_dados, monkeypatch):
    monkeypatch.setattr(main, "moeda_da_conta", lambda user_id: "BRL")
    corpo = {
        "data": "2026-11-10",
        "descricao": "Café inventado",
        "valor": -2.5,
        "metodo_pagamento": "dinheiro",
        "categoria": "restaurantes",
        "moeda": "EUR",
    }

    resposta = cliente.post("/transacoes", json=corpo)

    assert resposta.status_code == 201
    assert [linha["moeda"] for linha in base_dados.gravado] == ["BRL"]


def test_sem_a_020_a_movimentacao_vai_sem_moeda(cliente, base_dados, monkeypatch):
    monkeypatch.setattr(main, "moeda_da_conta", lambda user_id: None)
    corpo = {"data": "2026-11-10", "descricao": "Café", "valor": -2.5, "metodo_pagamento": "dinheiro", "categoria": "lazer"}

    assert cliente.post("/transacoes", json=corpo).status_code == 201
    assert "moeda" not in base_dados.gravado[0]


def test_importar_csv_grava_a_moeda_da_conta_em_cada_linha(cliente, base_dados, limite, monkeypatch):
    monkeypatch.setattr(main, "moeda_da_conta", lambda user_id: "BRL")
    monkeypatch.setattr(main, "categorizar", lambda novas, user_id=None: ["outros"] * len(novas))
    csv = "Data;Descrição;Montante;Saldo\n01-11-2026;MERCADO INVENTADO;-10,00;90,00\n02-11-2026;SALARIO INVENTADO;1000,00;1090,00\n"

    resposta = cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.csv", csv.encode(), "text/csv")})

    assert resposta.status_code == 201, resposta.text
    assert {linha["moeda"] for linha in base_dados.gravado} == {"BRL"}
    assert len(base_dados.gravado) == 2


def _nova_compra():
    return NovaCompra(
        loja="LOJA INVENTADA",
        data=date(2026, 11, 1),
        itens=[{"descricao": "PAO", "quantidade": 1, "preco": 1.0}],
        total=1.0,
        categoria="alimentação",
        metodo_pagamento="dinheiro",
    )


def test_o_talao_grava_a_moeda_na_transacao_e_na_compra(monkeypatch):
    falsa = BaseDadosFalsa()
    monkeypatch.setattr(compras, "supabase", falsa)

    compras.gravar_compra("utilizador-teste", _nova_compra(), "BRL")

    transacao, compra = falsa.gravado[0], falsa.gravado[1]
    assert transacao["moeda"] == "BRL" and compra["moeda"] == "BRL"
    assert "moeda" not in falsa.gravado[2]  # os produtos não têm moeda (vão com a compra)


def test_o_talao_sem_a_020_vai_sem_moeda(monkeypatch):
    falsa = BaseDadosFalsa()
    monkeypatch.setattr(compras, "supabase", falsa)

    compras.gravar_compra("utilizador-teste", _nova_compra())

    assert all("moeda" not in linha for linha in falsa.gravado)


def test_a_rota_de_compras_passa_a_moeda_da_conta(cliente, monkeypatch):
    recebidas = []
    monkeypatch.setattr(main, "moeda_da_conta", lambda user_id: "BRL")

    def gravar(user_id, nova, moeda=None):
        recebidas.append(moeda)
        return compras.Compra(id=1, transacao_id=1, loja=nova.loja, data=nova.data, total=nova.total, itens=[])

    monkeypatch.setattr(main, "gravar_compra", gravar)
    corpo = _nova_compra().model_dump(mode="json") | {"moeda": "EUR"}

    assert cliente.post("/compras", json=corpo).status_code == 201
    assert recebidas == ["BRL"]


# --- O "hoje" do utilizador nas rotas, no chat e nas ferramentas ---


def test_os_alertas_de_orcamento_usam_o_mes_do_pais_onde_vive(cliente, monkeypatch):
    # 1 de dezembro à 01:00 UTC: numa conta BR ainda é novembro.
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 12, 1, 1, 0, tzinfo=UTC))
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: CONTA_BR)
    monkeypatch.setattr(main, "hoje_do_utilizador", limites.hoje_do_utilizador)
    meses = []
    monkeypatch.setattr(main, "planeamento_do_mes", lambda user_id, mes: meses.append(mes) or [])

    resposta = cliente.get("/orcamentos/alertas")

    assert resposta.json()["mes"] == "2026-11"
    assert meses == ["2026-11"]


def test_as_instrucoes_do_chat_levam_o_dia_dado():
    texto = ia.instrucoes_do_chat(CONFIG_IA_POR_PLANO["free"], date(2026, 11, 30))
    assert texto.endswith("Hoje é 2026-11-30.")


def test_as_ferramentas_usam_o_dia_dado_para_o_historico(monkeypatch):
    # Free: o mês atual e os 2 anteriores. Em Lisboa já é 1 de dezembro (vê desde outubro);
    # na conta BR ainda é 30 de novembro (vê desde setembro).
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 12, 1, 1, 0, tzinfo=UTC))
    monkeypatch.setattr(ferramentas, "gastos_do_mes", lambda user_id, mes: [])

    em_lisboa = json.loads(ferramentas.executar_ferramenta("gastos_por_categoria", {"mes": "2026-09"}, "u", "free"))
    no_brasil = json.loads(
        ferramentas.executar_ferramenta("gastos_por_categoria", {"mes": "2026-09"}, "u", "free", date(2026, 11, 30))
    )

    assert em_lisboa["fora_do_historico"] is True
    assert no_brasil == []


def test_sem_assinatura_nao_ha_pedidos_e_o_fuso_e_lisboa(monkeypatch):
    # Sem linha na tabela: plano None (0 pedidos), fuso de Lisboa. O 403 vem antes, no auth.
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: Assinatura())
    monkeypatch.setattr(limites, "supabase", RpcFalso(False))
    # 1 de dezembro à 01:00 UTC: em Lisboa já é dia 1 (em São Paulo ainda seria 30 de novembro).
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 12, 1, 1, 0, tzinfo=UTC))

    assert limites.plano_do_utilizador("x") is None
    assert Assinatura().fuso is FUSO_LISBOA
    assert limites.hoje_do_utilizador("x") == date(2026, 12, 1)
    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("x", "chat")
    assert erro.value.status_code == 429


# --- sql/020 (não há Postgres nos testes: confirma-se o texto da migração) ---


SQL_020 = (Path(__file__).parent.parent / "sql" / "020_pais_moeda.sql").read_text(encoding="utf-8")
ASSINATURA_NOVA = "public.atualizar_perfil_conta(uuid, text, text[], text, boolean)"


def _codigo_sql(texto: str) -> str:
    """O SQL sem as linhas de comentário (as consultas de verificação no fim ficam de fora)."""
    return "\n".join(linha for linha in texto.splitlines() if not linha.lstrip().startswith("--"))


def test_a_020_recusa_arrays_2d_e_indices_que_nao_comecam_em_1():
    codigo = _codigo_sql(SQL_020)
    check = codigo[codigo.index("ADD CONSTRAINT assinaturas_paises_bancos_validos") :]
    check = check[: check.index(");")]
    assert "array_ndims(paises_bancos) = 1" in check
    assert "array_lower(paises_bancos, 1) = 1" in check


def test_a_020_troca_a_funcao_do_perfil_pela_versao_so_se_padrao():
    codigo = _codigo_sql(SQL_020)
    # A versão antiga apaga-se antes de criar a nova (senão ficavam as duas).
    apagar = codigo.index("DROP FUNCTION IF EXISTS public.atualizar_perfil_conta(uuid, text, text[], text);")
    assert apagar < codigo.index("CREATE OR REPLACE FUNCTION public.atualizar_perfil_conta(")
    assert "p_so_se_padrao boolean DEFAULT false" in codigo
    assert "RETURN 'nao_padrao';" in codigo
    # Só a API (service_role) a pode chamar, já com a assinatura nova.
    assert f"REVOKE EXECUTE ON FUNCTION {ASSINATURA_NOVA} FROM PUBLIC, anon, authenticated;" in codigo
    assert f"GRANT EXECUTE ON FUNCTION {ASSINATURA_NOVA} TO service_role;" in codigo
    assert "public.atualizar_perfil_conta(uuid, text, text[], text) FROM" not in codigo
    funcao = codigo[codigo.index("CREATE OR REPLACE FUNCTION public.atualizar_perfil_conta(") :]
    funcao = funcao[: funcao.index("$$;")]
    assert "SECURITY INVOKER" in funcao and "SET search_path = ''" in funcao
    assert "SECURITY DEFINER" not in funcao
