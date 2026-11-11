"""Limite de extratos PDF por mês (Essencial 15, Completo 30) e a ordem das verificações antes de chamar a IA."""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from postgrest.exceptions import APIError

import limites
import main
from importar_csv import PdfIlegivel
from limites import MAX_PAGINAS_PDF, MAX_TRANSACOES_POR_CONTA
from models import ExtratoPdf, MovimentoPdf

UTC = timezone.utc
AGORA = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)

MENSAGEM_15 = (
    "Chegaste ao limite de 15 extratos PDF este mês. O contador volta a zero no dia 1. "
    "Até lá, podes importar o extrato em CSV."
)


@pytest.fixture
def ia(monkeypatch):
    """Substitui a IA e o contador de páginas; regista por que ordem foram chamados."""
    chamadas = []

    def ler_extrato_pdf(pdf, user_id=None):
        chamadas.append("ia")
        return ExtratoPdf(movimentos=[MovimentoPdf(data="2026-10-01", descricao="CAFE", valor=-1.2, saldo=None)])

    monkeypatch.setattr(main, "ler_extrato_pdf", ler_extrato_pdf)
    monkeypatch.setattr(main, "categorizar", lambda transacoes, user_id=None: ["outros"] * len(transacoes))
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: chamadas.append("paginas") or 1)
    return chamadas


def importar_pdf(cliente, conteudo=b"%PDF-1.4 extrato inventado"):
    return cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.pdf", conteudo, "application/pdf")})


# --- Limites de cada plano ---


def test_limites_de_pdf_de_cada_plano():
    assert limites.limite_pdf_do_plano("essencial") == 15
    assert limites.limite_pdf_do_plano("completo") == 30
    assert limites.limite_pdf_do_plano("free") == 0
    assert limites.limite_pdf_do_plano(None) == 0


def test_os_limites_de_pedidos_nao_mudaram():
    assert limites.LIMITES_POR_PLANO == {"free": (30, "mes"), "essencial": (20, "dia"), "completo": (50, "dia")}


@pytest.mark.parametrize(("plano", "limite"), [("essencial", 15), ("completo", 30)])
def test_exigir_limite_pdf_deixa_ate_ao_limite_e_recusa_a_partir_dele(monkeypatch, plano, limite):
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: plano)

    monkeypatch.setattr(limites, "pdfs_no_mes", lambda user_id: limite - 1)
    limites.exigir_limite_pdf("utilizador-teste")  # ainda pode

    monkeypatch.setattr(limites, "pdfs_no_mes", lambda user_id: limite)
    with pytest.raises(HTTPException) as erro:
        limites.exigir_limite_pdf("utilizador-teste")
    assert erro.value.status_code == 429
    assert erro.value.detail == (
        f"Chegaste ao limite de {limite} extratos PDF este mês. O contador volta a zero no dia 1. "
        "Até lá, podes importar o extrato em CSV."
    )


# --- Na rota: a ordem das verificações ---


def test_pdf_aceite_conta_um_pdf_e_gasta_um_pedido(cliente, ia, limite):
    resposta = importar_pdf(cliente)

    assert resposta.status_code == 201
    assert limite.funcoes == ["importar_pdf"]  # um só pedido, registado como PDF
    assert limite.pdfs == 1
    assert ia == ["paginas", "ia"]


def test_no_limite_de_pdf_responde_429_sem_gastar_pedido_nem_chamar_a_ia(cliente, ia, limite):
    limite.funcoes = ["importar_pdf"] * 15  # 15 PDF já este mês

    resposta = importar_pdf(cliente)

    assert resposta.status_code == 429
    assert resposta.json()["detail"] == MENSAGEM_15
    assert limite.pdfs == 15  # o recusado não conta
    assert ia == ["paginas"]  # contou as páginas (vem antes), mas não chamou a IA


def test_o_free_recebe_402_antes_do_limite_de_pdf(cliente, ia, limite):
    limite.plano = "free"
    limite.maximo_pdf = 0

    resposta = importar_pdf(cliente)

    assert resposta.status_code == 402
    assert limite.pdfs == 0
    assert ia == []


def test_pdf_grande_demais_nao_conta(cliente, ia, limite):
    limite.maximo_pdf = 0  # mesmo no limite de PDF, o tamanho vem primeiro

    resposta = importar_pdf(cliente, b"%PDF" + b"0" * main.TAMANHO_MAXIMO_PDF)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "PDF demasiado grande. Máx. 10 MB."
    assert limite.perguntas == 0
    assert ia == []


def test_pdf_com_paginas_a_mais_nao_conta(cliente, ia, limite, monkeypatch):
    limite.maximo_pdf = 0  # as páginas vêm antes do limite de PDF
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: MAX_PAGINAS_PDF + 1)

    resposta = importar_pdf(cliente)

    assert resposta.status_code == 400
    assert limite.perguntas == 0


def test_pdf_ilegivel_nao_conta(cliente, ia, limite, monkeypatch):
    def estragado(pdf):
        raise PdfIlegivel("EOF marker not found")

    monkeypatch.setattr(main, "contar_paginas_pdf", estragado)

    resposta = importar_pdf(cliente)

    assert resposta.status_code == 422
    assert limite.perguntas == 0
    assert limite.pdfs == 0


def test_conta_cheia_vem_antes_do_limite_de_pdf(cliente, ia, limite, base_dados):
    base_dados.contagem = MAX_TRANSACOES_POR_CONTA
    limite.maximo_pdf = 0

    resposta = importar_pdf(cliente)

    # 422 do teto e não 429 do PDF: o teto vem antes.
    assert resposta.status_code == 422
    assert limite.perguntas == 0
    assert ia == ["paginas"]


def test_sem_pedidos_a_ia_o_pdf_nao_conta(cliente, ia, limite):
    limite.maximo = 0

    resposta = importar_pdf(cliente)

    assert resposta.status_code == 429
    assert limite.pdfs == 0
    assert ia == ["paginas"]


# --- Que funcao fica registada em cada rota ---


def test_o_csv_e_a_movimentacao_nova_registam_a_sua_funcao(cliente, ia, limite):
    csv = "Data;Descrição;Montante;Saldo\n01-10-2026;CAFE INVENTADO;-1,20;10,00".encode()
    resposta_csv = cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.csv", csv, "text/csv")})
    resposta_nova = cliente.post(
        "/transacoes",
        json={"data": "2026-11-08", "descricao": "Café", "valor": -1.2, "metodo_pagamento": "dinheiro"},
    )

    assert (resposta_csv.status_code, resposta_nova.status_code) == (201, 201)

    assert limite.funcoes == ["importar_csv", "categorizar"]
    assert limite.pdfs == 0  # um CSV nunca conta como PDF


# --- Contagem dos PDF do mês (pdfs_no_mes) ---


class TabelasFalsas:
    """Imita uso_ia e chamadas_ia numa contagem. sem_coluna imita o Supabase antes da sql/016."""

    def __init__(self, uso_ia=0, chamadas_ia=0, sem_coluna=False, chamadas_em_baixo=False):
        self.contagens = {"uso_ia": uso_ia, "chamadas_ia": chamadas_ia}
        self.sem_coluna = sem_coluna
        self.chamadas_em_baixo = chamadas_em_baixo
        self.filtros: dict[str, list] = {}
        self.tabela = ""

    def table(self, nome):
        self.tabela = nome
        self.filtros[nome] = []
        return self

    def eq(self, campo, valor):
        self.filtros[self.tabela].append((campo, valor))
        return self

    def gte(self, campo, valor):
        self.filtros[self.tabela].append((campo, valor))
        return self

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        if self.tabela == "uso_ia" and self.sem_coluna:
            raise APIError({"code": "42703", "message": "column uso_ia.funcao does not exist"})
        if self.tabela == "chamadas_ia" and self.chamadas_em_baixo:
            raise APIError({"code": "42703", "message": "column chamadas_ia.user_id does not exist"})
        self.count = self.contagens[self.tabela]
        return self


def test_conta_os_pdf_pela_coluna_funcao_desde_o_dia_1_de_lisboa(monkeypatch):
    tabelas = TabelasFalsas(uso_ia=4)
    monkeypatch.setattr(limites, "supabase", tabelas)
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)

    assert limites.pdfs_no_mes("utilizador-teste") == 4
    assert tabelas.filtros["uso_ia"] == [
        ("user_id", "utilizador-teste"),
        ("funcao", "importar_pdf"),
        ("criado_em", "2026-11-01T00:00:00+00:00"),
    ]
    assert "chamadas_ia" not in tabelas.filtros


def test_sem_a_016_conta_os_pdf_pelas_chamadas_a_ia(monkeypatch):
    tabelas = TabelasFalsas(uso_ia=99, chamadas_ia=3, sem_coluna=True)
    monkeypatch.setattr(limites, "supabase", tabelas)
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)

    assert limites.pdfs_no_mes("utilizador-teste") == 3
    assert ("funcao", "extrato_pdf") in tabelas.filtros["chamadas_ia"]
    assert ("user_id", "utilizador-teste") in tabelas.filtros["chamadas_ia"]


def test_se_nada_der_para_contar_o_pdf_e_recusado(monkeypatch):
    # Falha fechado: sem saber quantos PDF já foram lidos, não se deixa ler mais nenhum.
    monkeypatch.setattr(limites, "supabase", TabelasFalsas(sem_coluna=True, chamadas_em_baixo=True))
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)

    with pytest.raises(HTTPException) as erro:
        limites.pdfs_no_mes("utilizador-teste")
    assert erro.value.status_code == 503


def test_outros_erros_na_contagem_nao_sao_escondidos(monkeypatch):
    class SemPermissao(TabelasFalsas):
        def execute(self):
            raise APIError({"code": "42501", "message": "permission denied"})

    monkeypatch.setattr(limites, "supabase", SemPermissao())

    with pytest.raises(APIError):
        limites.pdfs_no_mes("utilizador-teste")


# --- Registo atómico do PDF (registar_pdf e a função registar_pdf_ia da sql/017) ---


class RpcFalso:
    """Imita supabase.rpc("registar_pdf_ia", ...): guarda os parâmetros e devolve a resposta dada.

    erro imita o PostgREST a recusar a chamada (ex.: PGRST202 antes da sql/017).
    """

    def __init__(self, resposta="ok", erro=None):
        self.resposta = resposta
        self.erro = erro
        self.chamadas: list[tuple[str, dict]] = []

    def rpc(self, nome, parametros):
        self.chamadas.append((nome, parametros))
        return self

    def execute(self):
        if self.erro:
            raise APIError(self.erro)
        self.data = self.resposta
        return self


@pytest.fixture
def rpc(monkeypatch):
    def _criar(resposta="ok", erro=None, plano="essencial"):
        falso = RpcFalso(resposta, erro)
        monkeypatch.setattr(limites, "supabase", falso)
        monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)
        monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: plano)
        return falso

    return _criar


@pytest.mark.parametrize(
    ("plano", "pedidos", "desde_pedidos", "pdf"),
    [
        ("essencial", 20, "2026-11-20T00:00:00+00:00", 15),  # pedidos por dia de Lisboa
        ("completo", 50, "2026-11-20T00:00:00+00:00", 30),
    ],
)
def test_registar_pdf_manda_os_dois_limites_numa_so_chamada(rpc, plano, pedidos, desde_pedidos, pdf):
    falso = rpc("ok", plano=plano)

    limites.registar_pdf("utilizador-teste")  # 'ok': não responde nada

    assert falso.chamadas == [
        (
            "registar_pdf_ia",
            {
                "p_user_id": "utilizador-teste",
                "p_desde_pedidos": desde_pedidos,
                "p_limite_pedidos": pedidos,
                "p_desde_pdf": "2026-11-01T00:00:00+00:00",  # os PDF contam desde o dia 1 de Lisboa
                "p_limite_pdf": pdf,
            },
        )
    ]


def test_registar_pdf_sem_pdf_no_mes_responde_429_com_a_mensagem_do_pdf(rpc):
    rpc("pdf")

    with pytest.raises(HTTPException) as erro:
        limites.registar_pdf("utilizador-teste")
    assert erro.value.status_code == 429
    assert erro.value.detail == MENSAGEM_15


def test_registar_pdf_sem_pedidos_responde_429_com_a_mensagem_dos_pedidos(rpc):
    rpc("pedidos")

    with pytest.raises(HTTPException) as erro:
        limites.registar_pdf("utilizador-teste")
    assert erro.value.status_code == 429
    assert erro.value.detail == limites.mensagem_do_limite(20, "dia")


@pytest.mark.parametrize("resposta", [None, "", "talvez", True])
def test_registar_pdf_com_resposta_inesperada_falha_fechado(rpc, resposta):
    rpc(resposta)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pdf("utilizador-teste")
    assert erro.value.status_code == 503


@pytest.mark.parametrize("codigo", ["PGRST202", "42883"])
def test_sem_a_017_usa_o_caminho_antigo_e_avisa(rpc, monkeypatch, capsys, codigo):
    rpc(erro={"code": codigo, "message": "Could not find the function public.registar_pdf_ia"})
    ordem = []
    monkeypatch.setattr(limites, "exigir_limite_pdf", lambda user_id: ordem.append("limite_pdf"))
    monkeypatch.setattr(limites, "registar_pergunta", lambda user_id, funcao: ordem.append(funcao))

    limites.registar_pdf("utilizador-teste")

    assert ordem == ["limite_pdf", "importar_pdf"]  # a mesma ordem de antes: PDF primeiro, depois o pedido
    assert "AVISO: função registar_pdf_ia não encontrada" in capsys.readouterr().out


def test_sem_a_017_e_sem_pdf_no_mes_nao_gasta_pedido(rpc, monkeypatch):
    rpc(erro={"code": "PGRST202", "message": "Could not find the function"})
    pedidos = []

    def sem_pdf(user_id):
        raise HTTPException(status_code=429, detail=MENSAGEM_15)

    monkeypatch.setattr(limites, "exigir_limite_pdf", sem_pdf)
    monkeypatch.setattr(limites, "registar_pergunta", lambda user_id, funcao: pedidos.append(funcao))

    with pytest.raises(HTTPException) as erro:
        limites.registar_pdf("utilizador-teste")
    assert erro.value.status_code == 429
    assert pedidos == []


def test_outros_erros_da_017_nao_sao_escondidos(rpc):
    rpc(erro={"code": "42501", "message": "permission denied for function registar_pdf_ia"})

    with pytest.raises(APIError):
        limites.registar_pdf("utilizador-teste")


def test_a_rota_usa_o_registo_atomico_e_nao_os_dois_passos(cliente, ia, limite, monkeypatch):
    # Na rota, o PDF conta-se só pela registar_pdf (o caminho em dois passos fica dentro dela).
    chamadas = []
    monkeypatch.setattr(main, "registar_pdf", lambda user_id: chamadas.append(user_id))

    resposta = importar_pdf(cliente)

    assert resposta.status_code == 201
    assert chamadas == ["utilizador-teste"]
    assert limite.funcoes == []  # nada passou pela registar_pergunta


# --- Revisão: a rota quando a registar_pdf recusa, planos sem PDF e viragem do dia/mês em Lisboa ---


@pytest.mark.parametrize(
    ("estado", "mensagem"),
    [
        (429, MENSAGEM_15),  # sem PDF no mês
        (429, limites.mensagem_do_limite(20, "dia")),  # sem pedidos à IA
        (503, "Não foi possível importar o PDF agora. Tenta outra vez daqui a pouco."),  # resposta inesperada
    ],
)
def test_pdf_recusado_pela_registar_pdf_nao_chama_a_ia_nem_grava(cliente, ia, limite, base_dados, monkeypatch, estado, mensagem):
    def recusar(user_id):
        raise HTTPException(status_code=estado, detail=mensagem)

    monkeypatch.setattr(main, "registar_pdf", recusar)

    resposta = importar_pdf(cliente)

    assert resposta.status_code == estado
    assert resposta.json()["detail"] == mensagem
    assert ia == ["paginas"]  # a IA não foi chamada
    assert base_dados.gravado == []  # nenhuma movimentação gravada
    assert limite.funcoes == []  # nenhum pedido contado


@pytest.mark.parametrize(
    ("plano", "limite_pedidos", "desde_pedidos"),
    [
        ("free", 30, "2026-11-01T00:00:00+00:00"),  # o Free conta os pedidos por mês
        (None, 0, "2026-11-20T00:00:00+00:00"),  # sem plano: 0 pedidos (período "dia", como em limites.py)
        ("plano-inventado", 0, "2026-11-20T00:00:00+00:00"),
    ],
)
def test_planos_sem_pdf_mandam_limite_de_pdf_zero(rpc, plano, limite_pedidos, desde_pedidos):
    falso = rpc("pdf", plano=plano)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pdf("utilizador-teste")
    assert erro.value.status_code == 429

    parametros = falso.chamadas[0][1]
    assert parametros["p_limite_pdf"] == 0
    assert parametros["p_limite_pedidos"] == limite_pedidos
    assert parametros["p_desde_pedidos"] == desde_pedidos
    assert parametros["p_desde_pdf"] == "2026-11-01T00:00:00+00:00"


@pytest.mark.parametrize(
    ("agora", "desde_dia", "desde_mes"),
    [
        # Inverno (Lisboa = UTC): 23h30 UTC do último dia do mês ainda é esse dia em Lisboa.
        (datetime(2026, 11, 30, 23, 30, tzinfo=UTC), "2026-11-30T00:00:00+00:00", "2026-11-01T00:00:00+00:00"),
        # Verão: 23h30 UTC de 31 de agosto já é 1 de setembro em Lisboa, mas em São Paulo ainda é dia 31
        # (20h30). Conta o início mais antigo: o dia e o mês de São Paulo (mudar de país não dá pedidos a mais).
        (datetime(2026, 8, 31, 23, 30, tzinfo=UTC), "2026-08-31T03:00:00+00:00", "2026-08-01T03:00:00+00:00"),
        # Verão, a meio do mês: a meia-noite de Lisboa é às 23h00 UTC do dia anterior.
        (datetime(2026, 7, 15, 12, 0, tzinfo=UTC), "2026-07-14T23:00:00+00:00", "2026-06-30T23:00:00+00:00"),
        # Passagem de ano no inverno.
        (datetime(2026, 12, 31, 23, 30, tzinfo=UTC), "2026-12-31T00:00:00+00:00", "2026-12-01T00:00:00+00:00"),
    ],
)
def test_os_inicios_sao_os_mais_antigos_entre_lisboa_e_sao_paulo(rpc, monkeypatch, agora, desde_dia, desde_mes):
    falso = rpc("ok", plano="essencial")
    monkeypatch.setattr(limites, "agora_utc", lambda: agora)

    limites.registar_pdf("utilizador-teste")

    parametros = falso.chamadas[0][1]
    assert parametros["p_desde_pedidos"] == desde_dia
    assert parametros["p_desde_pdf"] == desde_mes
