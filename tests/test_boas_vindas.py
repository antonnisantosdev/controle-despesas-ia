"""Questionário de boas-vindas (sql/021): quem o vê, o que se grava e o que acontece antes da migração.

Contas novas veem-no (boas_vindas_em NULL); contas antigas e a demo não. O PUT grava o perfil (sql/020),
o motivo e os objetivos (só opções fechadas) e marca a conta. Supabase imitado; dados inventados.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from postgrest.exceptions import APIError

import boas_vindas
import limite_ip
import limites
import main
import perfil
from auth import obter_utilizador_atual
from limites import Assinatura
from mensagens import msg

ID_DEMO = "00000000-0000-4000-8000-00000000d3e0"
AGORA = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)
RESPONDIDO = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)

CONTA_NOVA = Assinatura("free", None, com_perfil=True, com_boas_vindas=True)
CONTA_ANTIGA = Assinatura("free", None, com_perfil=True, boas_vindas_em=RESPONDIDO, com_boas_vindas=True)
CONTA_SEM_021 = Assinatura("free", None, com_perfil=True, com_boas_vindas=False)
CONTA_BR_NOVA = Assinatura("free", None, pais="BR", paises_bancos=("BR",), moeda="BRL", com_perfil=True, com_boas_vindas=True)

TODOS_OS_OBJETIVOS = ["importar", "categorias", "orcamento", "chat", "resumo", "reserva", "taloes"]


class TabelasFalsas:
    """Imita as tabelas boas_vindas e assinaturas: guarda cada operação (tabela, ação, dados, filtros)."""

    def __init__(self, linhas=None, erro=None):
        self.linhas = linhas or []
        self.erro = erro
        self.operacoes: list[dict] = []
        self._atual: dict = {}

    def table(self, nome):
        self._atual = {"tabela": nome, "filtros": []}
        return self

    def _acao(self, acao, dados=None, **opcoes):
        self._atual.update(acao=acao, dados=dados, opcoes=opcoes)
        return self

    def upsert(self, dados, **opcoes):
        return self._acao("upsert", dados, **opcoes)

    def update(self, dados):
        return self._acao("update", dados)

    def delete(self):
        return self._acao("delete")

    def select(self, colunas):
        return self._acao("select", colunas)

    def eq(self, coluna, valor):
        self._atual["filtros"].append(("eq", coluna, valor))
        return self

    def is_(self, coluna, valor):
        self._atual["filtros"].append(("is", coluna, valor))
        return self

    def execute(self):
        if self.erro:
            raise self.erro
        self.operacoes.append(self._atual)
        return SimpleNamespace(data=self.linhas if self._atual["acao"] == "select" else [])


class PerfilRpc:
    """Imita supabase.rpc("atualizar_perfil_conta"): devolve as respostas dadas, por ordem (a última repete-se)."""

    def __init__(self, *respostas):
        self.respostas = list(respostas) or ["ok"]
        self.chamadas: list[dict] = []

    def rpc(self, nome, parametros):
        self.chamadas.append(parametros)
        return self

    def execute(self):
        resposta = self.respostas.pop(0) if len(self.respostas) > 1 else self.respostas[0]
        return SimpleNamespace(data=resposta)


@pytest.fixture
def preparar(monkeypatch):
    """Fixa a conta lida, a função do perfil e as tabelas. Devolve (tabelas, rpc)."""

    def _preparar(conta=CONTA_NOVA, respostas_rpc=("ok",), linhas=None, erro=None):
        monkeypatch.setattr(boas_vindas, "assinatura_do_utilizador", lambda user_id: conta)
        monkeypatch.setattr(perfil, "assinatura_do_utilizador", lambda user_id: conta)
        monkeypatch.setattr(boas_vindas, "agora_utc", lambda: AGORA)
        tabelas = TabelasFalsas(linhas, erro)
        rpc = PerfilRpc(*respostas_rpc)
        monkeypatch.setattr(boas_vindas, "supabase", tabelas)
        monkeypatch.setattr(perfil, "supabase", rpc)
        return tabelas, rpc

    return _preparar


def responder(cliente, **campos):
    corpo = {"pais": "PT", "paises_bancos": ["PT"], **campos}
    return cliente.put("/conta/boas-vindas", json=corpo)


# --- Quem vê o questionário (GET /plano) ---


@pytest.fixture
def plano_com(monkeypatch):
    def _fixar(conta):
        monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: conta)
        monkeypatch.setattr(limites, "pedidos_no_periodo", lambda user_id, periodo: 0)
        monkeypatch.setattr(limites, "pdfs_no_mes", lambda user_id: 0)

    return _fixar


@pytest.mark.parametrize(
    ("conta", "pendente"),
    [
        (CONTA_NOVA, True),  # conta nova: o gatilho da 013 deixa boas_vindas_em a NULL
        (CONTA_ANTIGA, False),  # contas que já existiam: a 021 marca-as
        (CONTA_SEM_021, False),  # antes da 021: ninguém vê o questionário
        (Assinatura(), False),  # sem linha em assinaturas
    ],
)
def test_o_plano_diz_quem_tem_o_questionario_por_fazer(cliente, plano_com, conta, pendente):
    plano_com(conta)

    assert cliente.get("/plano").json()["boas_vindas_pendente"] is pendente


def test_a_demo_nunca_ve_o_questionario(cliente, plano_com, monkeypatch):
    monkeypatch.setenv("DEMO_USER_ID", ID_DEMO)
    main.app.dependency_overrides[obter_utilizador_atual] = lambda: ID_DEMO
    plano_com(CONTA_NOVA)  # mesmo que a marca da 021 faltasse

    assert cliente.get("/plano").json()["boas_vindas_pendente"] is False


class AssinaturasFalsas:
    """Imita a tabela assinaturas. sem: as colunas que ainda não existem (o select com elas falha)."""

    def __init__(self, linha, sem=()):
        self.linha = linha
        self.sem = sem
        self.selects: list[str] = []

    def table(self, nome):
        return self

    def select(self, colunas):
        self.selects.append(colunas)
        return self

    def eq(self, *args):
        return self

    def execute(self):
        if any(coluna in self.selects[-1] for coluna in self.sem):
            raise APIError({"code": "42703", "message": "column does not exist"})
        return SimpleNamespace(data=[self.linha])


LINHA = {"plano": "free", "ativo_ate": None, "pais": "BR", "paises_bancos": ["BR"], "moeda": "BRL"}


@pytest.mark.parametrize(
    ("boas_vindas_em", "pendente"),
    [(None, True), ("2026-11-12T10:00:00+00:00", False), ("2026-11-12T10:00:00Z", False), ("lixo", False)],
)
def test_a_assinatura_le_a_marca_do_questionario(monkeypatch, boas_vindas_em, pendente):
    monkeypatch.setattr(limites, "supabase", AssinaturasFalsas(LINHA | {"boas_vindas_em": boas_vindas_em}))

    conta = limites.assinatura_do_utilizador("utilizador-teste")

    assert conta.com_boas_vindas is True
    assert conta.boas_vindas_pendente is pendente
    assert (conta.pais, conta.moeda) == ("BR", "BRL")


def test_sem_a_021_le_o_perfil_e_ninguem_ve_o_questionario(monkeypatch, capsys):
    falsa = AssinaturasFalsas(LINHA, sem=("boas_vindas_em",))
    monkeypatch.setattr(limites, "supabase", falsa)

    conta = limites.assinatura_do_utilizador("utilizador-teste")

    assert len(falsa.selects) == 2
    assert (conta.com_perfil, conta.com_boas_vindas, conta.boas_vindas_pendente) == (True, False, False)
    assert (conta.pais, conta.moeda) == ("BR", "BRL")
    assert "sql/021" in capsys.readouterr().out


# --- PUT /conta/boas-vindas ---


def test_conta_nova_grava_o_perfil_as_respostas_e_a_marca(cliente, preparar):
    tabelas, rpc = preparar()

    resposta = responder(
        cliente, pais="BR", paises_bancos=["PT", "BR"], moeda="EUR", motivo="supermercado", objetivos=["chat", "resumo"]
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "pais": "BR",
        "paises_bancos": ["PT", "BR"],
        "moeda": "EUR",
        "motivo": "supermercado",
        "objetivos": ["chat", "resumo"],
        "aviso": None,
    }
    assert rpc.chamadas == [
        {
            "p_user_id": "utilizador-teste",
            "p_pais": "BR",
            "p_paises_bancos": ["PT", "BR"],
            "p_moeda": "EUR",
            "p_so_se_padrao": False,
        }
    ]
    upsert, marca = tabelas.operacoes
    assert upsert["tabela"] == "boas_vindas" and upsert["acao"] == "upsert"
    assert upsert["dados"] == {
        "user_id": "utilizador-teste",
        "motivo": "supermercado",
        "objetivos": ["chat", "resumo"],
        "atualizado_em": AGORA.isoformat(),
    }
    assert upsert["opcoes"] == {"on_conflict": "user_id"}
    # A marca só se escreve da 1.ª vez (nas definições fica a data de quando o questionário foi feito).
    assert marca["tabela"] == "assinaturas" and marca["dados"] == {"boas_vindas_em": AGORA.isoformat()}
    assert marca["filtros"] == [("eq", "user_id", "utilizador-teste"), ("is", "boas_vindas_em", "null")]


def test_saltar_as_opcionais_grava_null(cliente, preparar):
    tabelas, _ = preparar()

    resposta = responder(cliente, objetivos=[])

    assert resposta.status_code == 200
    assert (resposta.json()["motivo"], resposta.json()["objetivos"]) == (None, None)
    assert (tabelas.operacoes[0]["dados"]["motivo"], tabelas.operacoes[0]["dados"]["objetivos"]) == (None, None)


def test_com_um_so_pais_a_moeda_e_a_desse_pais(cliente, preparar):
    _, rpc = preparar()

    resposta = responder(cliente, pais="BR", paises_bancos=["BR"])

    assert resposta.json()["moeda"] == "BRL"
    assert rpc.chamadas[0]["p_moeda"] == "BRL"


def test_conta_br_aceita_a_lista_toda_de_objetivos(cliente, preparar):
    # O frontend esconde "importar" e "taloes" no Brasil; a API aceita-os (as definições mostram o que houver).
    preparar(CONTA_BR_NOVA)

    resposta = responder(cliente, pais="BR", paises_bancos=["BR"], objetivos=TODOS_OS_OBJETIVOS)

    assert resposta.status_code == 200
    assert resposta.json()["objetivos"] == TODOS_OS_OBJETIVOS


def test_moeda_com_dados_grava_o_resto_e_devolve_o_aviso(cliente, preparar):
    tabelas, rpc = preparar(respostas_rpc=("tem_dados", "ok"))

    resposta = responder(cliente, pais="BR", paises_bancos=["PT", "BR"], moeda="BRL", motivo="poupar")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["pais"], corpo["paises_bancos"], corpo["moeda"]) == ("BR", ["PT", "BR"], "EUR")
    assert corpo["aviso"] == msg("perfil_moeda_com_dados", "PT")
    assert [c["p_moeda"] for c in rpc.chamadas] == ["BRL", "EUR"]
    assert len(tabelas.operacoes) == 2  # as respostas e a marca gravam-se na mesma


def test_moeda_com_dados_e_bancos_que_nao_servem_ficam_os_bancos_de_antes(cliente, preparar):
    _, rpc = preparar(respostas_rpc=("tem_dados", "ok"))

    resposta = responder(cliente, pais="BR", paises_bancos=["BR"])

    corpo = resposta.json()
    assert (corpo["pais"], corpo["paises_bancos"], corpo["moeda"]) == ("BR", ["PT"], "EUR")
    assert rpc.chamadas[1]["p_paises_bancos"] == ["PT"]


def test_antes_da_021_responde_503_sem_gravar_nada(cliente, preparar):
    tabelas, rpc = preparar(CONTA_SEM_021)

    resposta = responder(cliente, motivo="outro")

    assert resposta.status_code == 503
    assert resposta.json() == {"detail": msg("boas_vindas_indisponivel", "PT")}
    assert rpc.chamadas == [] and tabelas.operacoes == []


def test_tabela_em_falta_ou_erro_da_503_no_pais_da_conta(cliente, preparar):
    preparar(CONTA_BR_NOVA, erro=APIError({"code": "PGRST205", "message": "Could not find the table"}))

    resposta = responder(cliente, pais="BR", paises_bancos=["BR"])

    assert resposta.status_code == 503
    assert resposta.json() == {"detail": msg("boas_vindas_indisponivel", "BR")}


def test_erro_a_ler_a_assinatura_da_503(cliente, preparar, monkeypatch):
    tabelas, rpc = preparar()

    def falhar(user_id):
        raise APIError({"code": "57014", "message": "timeout"})

    monkeypatch.setattr(boas_vindas, "assinatura_do_utilizador", falhar)

    assert responder(cliente).status_code == 503
    assert rpc.chamadas == [] and tabelas.operacoes == []


CORPOS_INVALIDOS = [
    {"pais": "ES", "paises_bancos": ["PT"]},
    {"paises_bancos": ["PT"]},  # sem país
    {"pais": "PT"},  # sem bancos
    {"pais": "PT", "paises_bancos": []},
    {"pais": "PT", "paises_bancos": ["PT"], "moeda": "BRL"},  # moeda que não é dos bancos
    {"pais": "PT", "paises_bancos": ["PT"], "motivo": "porque sim"},  # sem texto livre
    {"pais": "PT", "paises_bancos": ["PT"], "motivo": ["poupar"]},
    {"pais": "PT", "paises_bancos": ["PT"], "objetivos": ["voar"]},
    {"pais": "PT", "paises_bancos": ["PT"], "objetivos": ["chat", "chat"]},
    {"pais": "PT", "paises_bancos": ["PT"], "objetivos": "chat"},
    {"pais": "PT", "paises_bancos": ["PT"], "objetivos": [*TODOS_OS_OBJETIVOS, "chat"]},
]


@pytest.mark.parametrize("corpo", CORPOS_INVALIDOS)
def test_valores_invalidos_dao_422_sem_tocar_na_base_de_dados(cliente, preparar, corpo):
    tabelas, rpc = preparar()

    resposta = cliente.put("/conta/boas-vindas", json=corpo)

    assert resposta.status_code == 422
    assert rpc.chamadas == [] and tabelas.operacoes == []


def test_o_user_id_vem_so_do_token(cliente, preparar):
    tabelas, rpc = preparar()

    responder(cliente, user_id="outra-conta")

    assert rpc.chamadas[0]["p_user_id"] == "utilizador-teste"
    assert tabelas.operacoes[0]["dados"]["user_id"] == "utilizador-teste"


@pytest.fixture
def relogio(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(limite_ip, "_relogio", lambda: agora[0])
    return agora


def test_partilha_o_limite_de_10_por_hora_com_o_perfil(cliente, preparar, relogio):
    preparar()
    for _ in range(5):
        assert cliente.put("/conta/perfil", json={"pais": "PT"}).status_code == 200
    for _ in range(4):
        assert responder(cliente).status_code == 200
    assert cliente.delete("/conta/boas-vindas").status_code == 204

    a_mais = responder(cliente, pais="BR", paises_bancos=["BR"])

    assert a_mais.status_code == 429
    assert a_mais.json() == {"detail": msg("perfil_muitas_mudancas", "BR")}


# --- GET e DELETE /conta/boas-vindas (definições) ---


def test_ler_as_respostas_para_as_definicoes(cliente, preparar):
    preparar(CONTA_BR_NOVA, linhas=[{"motivo": "folhas", "objetivos": ["chat", "estranho", "chat", "reserva"]}])

    resposta = cliente.get("/conta/boas-vindas")

    assert resposta.status_code == 200
    # Valores fora da lista (não deviam existir: há CHECK) e repetidos não se devolvem.
    assert resposta.json() == {
        "pais": "BR",
        "paises_bancos": ["BR"],
        "moeda": "BRL",
        "motivo": "folhas",
        "objetivos": ["chat", "reserva"],
        "aviso": None,
    }


def test_sem_respostas_devolve_null(cliente, preparar):
    preparar(CONTA_ANTIGA, linhas=[])

    corpo = cliente.get("/conta/boas-vindas").json()

    assert (corpo["motivo"], corpo["objetivos"]) == (None, None)


def test_apagar_as_respostas_apaga_so_a_linha_desta_conta(cliente, preparar):
    tabelas, rpc = preparar(CONTA_ANTIGA)

    resposta = cliente.delete("/conta/boas-vindas")

    assert resposta.status_code == 204
    assert tabelas.operacoes == [
        {"tabela": "boas_vindas", "acao": "delete", "dados": None, "opcoes": {}, "filtros": [("eq", "user_id", "utilizador-teste")]}
    ]
    assert rpc.chamadas == []  # o perfil e a marca ficam


@pytest.mark.parametrize("metodo", ["GET", "DELETE"])
def test_ler_e_apagar_antes_da_021_dao_503(cliente, preparar, metodo):
    tabelas, _ = preparar(CONTA_SEM_021)

    assert cliente.request(metodo, "/conta/boas-vindas").status_code == 503
    assert tabelas.operacoes == []


def test_as_listas_sao_as_mesmas_no_modelo_e_no_modulo():
    from typing import get_args

    from models import MotivoBoasVindas, ObjetivoBoasVindas

    assert get_args(MotivoBoasVindas) == boas_vindas.MOTIVOS
    assert get_args(ObjetivoBoasVindas) == boas_vindas.OBJETIVOS
    assert list(boas_vindas.OBJETIVOS) == TODOS_OS_OBJETIVOS


def test_as_listas_sao_as_mesmas_na_sql_021():
    from pathlib import Path

    sql = (Path(__file__).parent.parent / "sql" / "021_boas_vindas.sql").read_text(encoding="utf-8")
    for valor in (*boas_vindas.MOTIVOS, *boas_vindas.OBJETIVOS):
        assert f"'{valor}'" in sql, valor

