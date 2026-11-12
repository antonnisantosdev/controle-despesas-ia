"""Planos: o limite de pedidos à IA (por mês no Free, por dia nos pagos) e as funções só dos planos pagos."""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

import limites
import main
from models import ExtratoPdf, ItemTalao, MovimentoPdf, Talao

UTC = timezone.utc
EXTRATO = (Path(__file__).parent.parent / "dados_exemplo" / "extrato_exemplo.csv").read_bytes()


@pytest.mark.parametrize(
    ("plano", "limite", "periodo"),
    [("free", 30, "mes"), ("essencial", 20, "dia"), ("completo", 50, "dia")],
)
def test_cada_plano_tem_o_seu_limite_e_periodo(plano, limite, periodo):
    assert limites.limite_do_plano(plano) == limite
    assert limites.periodo_do_plano(plano) == periodo


@pytest.mark.parametrize("plano", [None, "Completo", "premium"])
def test_plano_desconhecido_nao_deixa_usar_a_ia(plano):
    # Na dúvida, fecha: um erro na coluna plano nunca pode gastar créditos da IA.
    assert limites.limite_do_plano(plano) == 0


# --- Contagem na tabela uso_ia ---


class UsoIaFalso:
    """Imita a tabela uso_ia: guarda a hora (UTC) de cada pedido e conta os que são >= ao filtro gte.

    com_funcao=True imita o Supabase com a migração 015 (função registar_pedido_ia);
    com_funcao=False imita o Supabase antes dela: o rpc falha como o PostgREST quando a função não existe.
    com_016=True imita a versão da 016 (com p_funcao); com_016=False só aceita os 3 parâmetros da 015
    e não tem a coluna funcao.
    """

    def __init__(self, pedidos: list[datetime], com_funcao: bool = True, com_016: bool = True):
        self.pedidos = list(pedidos)
        self.com_funcao = com_funcao
        self.com_016 = com_funcao and com_016
        self.funcoes: list[str | None] = []  # a funcao de cada pedido inserido (None = sem a coluna)
        self.inseridas = 0
        self.inseridas_na_tabela = 0  # pelo caminho antigo (insert direto)
        self.chamadas_rpc: list[tuple[str, dict]] = []
        self.contagens_a_parte = 0  # SELECT COUNT feitos pelo caminho antigo
        self.desde: datetime | None = None
        self.count = 0
        self.data = None

    def table(self, nome):
        return self

    def gte(self, campo, valor):
        self.contagens_a_parte += 1
        self.desde = datetime.fromisoformat(valor)
        return self

    def insert(self, dados):
        if "funcao" in dados and not self.com_016:
            raise APIError({"code": "PGRST204", "message": "Could not find the 'funcao' column of 'uso_ia'"})
        self.inseridas += 1
        self.inseridas_na_tabela += 1
        self.funcoes.append(dados.get("funcao"))
        return self

    def rpc(self, nome, parametros):
        self.chamadas_rpc.append((nome, parametros))
        if not self.com_funcao or ("p_funcao" in parametros and not self.com_016):
            raise APIError({"code": "PGRST202", "message": f"Could not find the function public.{nome}"})
        # O mesmo que a função SQL: conta desde p_desde e só regista se estiver abaixo do limite.
        self.desde = datetime.fromisoformat(parametros["p_desde"])
        pedidos = sum(1 for pedido in self.pedidos if pedido >= self.desde)
        self.data = pedidos < parametros["p_limite"]
        if self.data:
            self.inseridas += 1
            self.funcoes.append(parametros.get("p_funcao"))
        return self

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        if self.desde is not None:
            self.count = sum(1 for pedido in self.pedidos if pedido >= self.desde)
        return self


@pytest.fixture(
    params=[(True, True), (True, False), (False, False)], ids=["com_016", "so_com_015", "sem_015"]
)
def preparar(request, monkeypatch):
    """Fixa o plano, os pedidos já feitos e a hora atual (UTC).

    Cada teste que a usa corre três vezes: com a função da 016, só com a da 015, e sem nenhuma (caminho antigo).
    """

    def _preparar(plano, pedidos, agora):
        com_funcao, com_016 = request.param
        uso = UsoIaFalso(pedidos, com_funcao=com_funcao, com_016=com_016)
        monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: plano)
        monkeypatch.setattr(limites, "supabase", uso)
        monkeypatch.setattr(limites, "agora_utc", lambda: agora)
        return uso

    return _preparar


AGORA = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)  # inverno: Lisboa = UTC


def test_o_free_conta_os_pedidos_do_mes_inteiro_e_bloqueia_o_31(preparar):
    # 30 pedidos espalhados por novembro, nenhum hoje: o limite do Free é do mês, não do dia.
    pedidos = [datetime(2026, 11, 1 + i % 19, 10, 0, tzinfo=UTC) for i in range(30)]
    uso = preparar("free", pedidos, AGORA)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste", "chat")
    assert erro.value.status_code == 429
    assert erro.value.detail == (
        "Chegaste ao limite deste mês. Já usaste os 30 pedidos à IA deste mês. O contador volta a zero no dia 1."
    )
    assert uso.inseridas == 0


def test_o_free_ainda_faz_o_30_pedido(preparar):
    uso = preparar("free", [datetime(2026, 11, 2, 10, 0, tzinfo=UTC)] * 29, AGORA)

    limites.registar_pergunta("utilizador-teste", "chat")
    assert uso.inseridas == 1


def test_os_pedidos_do_mes_passado_nao_contam_no_free(preparar):
    uso = preparar("free", [datetime(2026, 10, 31, 10, 0, tzinfo=UTC)] * 30, AGORA)

    limites.registar_pergunta("utilizador-teste", "chat")
    assert uso.inseridas == 1


@pytest.mark.parametrize(("plano", "limite"), [("essencial", 20), ("completo", 50)])
def test_os_pagos_bloqueiam_quando_acabam_os_pedidos_de_hoje(preparar, plano, limite):
    preparar(plano, [datetime(2026, 11, 20, 9, 0, tzinfo=UTC)] * limite, AGORA)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste", "chat")
    assert erro.value.status_code == 429
    assert erro.value.detail == (
        f"Chegaste ao limite de hoje. Já usaste os {limite} pedidos à IA do teu plano. "
        "O contador volta a zero à meia-noite."
    )


@pytest.mark.parametrize(("plano", "limite"), [("essencial", 20), ("completo", 50)])
def test_os_pedidos_de_ontem_nao_contam_nos_pagos(preparar, plano, limite):
    uso = preparar(plano, [datetime(2026, 11, 19, 23, 0, tzinfo=UTC)] * limite, AGORA)

    limites.registar_pergunta("utilizador-teste", "chat")
    assert uso.inseridas == 1


def test_perto_da_meia_noite_de_lisboa_o_dia_dos_contadores_ainda_e_o_de_sao_paulo(preparar):
    # 23:30 UTC de 15 de julho: em Lisboa já é dia 16 (00:30), em São Paulo ainda é 15 (20:30).
    # Os contadores começam na meia-noite mais antiga (03:00 UTC de 15, a de São Paulo): os pedidos
    # das 22:30 UTC ainda contam, mesmo numa conta PT. É o preço de mudar de país não dar pedidos a mais.
    agora = datetime(2026, 7, 15, 23, 30, tzinfo=UTC)
    uso = preparar("essencial", [datetime(2026, 7, 15, 22, 30, tzinfo=UTC)] * 20, agora)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste", "chat")
    assert erro.value.status_code == 429
    assert uso.inseridas == 0
    assert uso.desde == datetime(2026, 7, 15, 3, 0, tzinfo=UTC)


def test_os_pedidos_de_antes_da_meia_noite_de_sao_paulo_ja_nao_contam(preparar):
    # Os mesmos 23:30 UTC: os pedidos das 02:00 UTC de 15 (antes das duas meias-noites) são de ontem.
    agora = datetime(2026, 7, 15, 23, 30, tzinfo=UTC)
    uso = preparar("essencial", [datetime(2026, 7, 15, 2, 0, tzinfo=UTC)] * 20, agora)

    limites.registar_pergunta("utilizador-teste", "chat")
    assert uso.inseridas == 1


def test_no_verao_um_pedido_depois_da_meia_noite_de_lisboa_conta_para_hoje(preparar):
    agora = datetime(2026, 7, 15, 23, 30, tzinfo=UTC)
    preparar("essencial", [datetime(2026, 7, 15, 23, 5, tzinfo=UTC)] * 20, agora)

    with pytest.raises(HTTPException):
        limites.registar_pergunta("utilizador-teste", "chat")


def test_o_mes_so_vira_quando_e_dia_1_em_lisboa_e_em_sao_paulo(preparar):
    # 23:30 UTC de 31 de julho: em Lisboa já é 1 de agosto, em São Paulo ainda é julho.
    # Os 30 pedidos de julho continuam a contar até às 03:00 UTC de 1 de agosto.
    agora = datetime(2026, 7, 31, 23, 30, tzinfo=UTC)
    uso = preparar("free", [datetime(2026, 7, 31, 22, 0, tzinfo=UTC)] * 30, agora)

    with pytest.raises(HTTPException):
        limites.registar_pergunta("utilizador-teste", "chat")
    assert uso.inseridas == 0
    assert uso.desde == datetime(2026, 7, 1, 3, 0, tzinfo=UTC)


def test_o_mes_vira_quando_ja_e_dia_1_nos_dois_fusos(preparar):
    # 03:00 UTC de 1 de agosto: já é dia 1 em Lisboa e em São Paulo. Os pedidos de julho deixam de contar.
    agora = datetime(2026, 8, 1, 3, 0, tzinfo=UTC)
    uso = preparar("free", [datetime(2026, 7, 31, 22, 0, tzinfo=UTC)] * 30, agora)

    limites.registar_pergunta("utilizador-teste", "chat")
    assert uso.inseridas == 1
    assert uso.desde == datetime(2026, 7, 31, 23, 0, tzinfo=UTC)


# --- Função registar_pedido_ia (migração 015) e caminho antigo ---


def preparar_uso(monkeypatch, uso, plano="essencial"):
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: plano)
    monkeypatch.setattr(limites, "supabase", uso)
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)
    return uso


def test_com_a_funcao_conta_e_regista_numa_so_chamada_a_base_de_dados(monkeypatch):
    uso = preparar_uso(monkeypatch, UsoIaFalso([], com_funcao=True))

    limites.registar_pergunta("utilizador-teste", "chat")

    # Um só pedido ao Supabase, com o utilizador, o início do dia de Lisboa e o limite do plano.
    assert uso.chamadas_rpc == [
        (
            "registar_pedido_ia",
            {
                "p_user_id": "utilizador-teste",
                "p_desde": "2026-11-20T00:00:00+00:00",
                "p_limite": 20,
                "p_funcao": "chat",
            },
        )
    ]
    assert uso.inseridas == 1
    assert uso.inseridas_na_tabela == 0
    assert uso.funcoes == ["chat"]


def test_so_com_a_015_usa_a_funcao_antiga_sem_p_funcao(monkeypatch):
    # Antes de o CEO correr a 016: a versão com p_funcao não existe, mas a da 015 sim.
    # O pedido conta na mesma, de forma atómica, só fica sem a funcao.
    uso = preparar_uso(monkeypatch, UsoIaFalso([], com_funcao=True, com_016=False))

    limites.registar_pergunta("utilizador-teste", "chat")

    assert [parametros.get("p_funcao") for _, parametros in uso.chamadas_rpc] == ["chat", None]
    assert "p_funcao" not in uso.chamadas_rpc[1][1]
    assert uso.inseridas == 1
    assert uso.inseridas_na_tabela == 0  # não caiu no caminho antigo


def test_so_com_a_015_no_limite_responde_429(monkeypatch):
    uso = preparar_uso(monkeypatch, UsoIaFalso([AGORA] * 20, com_funcao=True, com_016=False))

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste", "chat")

    assert erro.value.status_code == 429
    assert uso.inseridas == 0


def test_com_a_funcao_no_limite_responde_429_sem_usar_o_caminho_antigo(monkeypatch):
    uso = preparar_uso(monkeypatch, UsoIaFalso([AGORA] * 20, com_funcao=True))

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste", "chat")

    assert erro.value.status_code == 429
    assert uso.inseridas == 0
    assert uso.contagens_a_parte == 0  # não houve contagem à parte (o caminho antigo)


def test_sem_a_funcao_usa_o_caminho_antigo(monkeypatch):
    # Antes de o CEO correr a 015, o PostgREST responde PGRST202 e a API conta e insere como antes.
    uso = preparar_uso(monkeypatch, UsoIaFalso([], com_funcao=False))

    limites.registar_pergunta("utilizador-teste", "chat")

    # Tentou a versão da 016 e a da 015, e só então o caminho antigo, sem a coluna funcao.
    assert len(uso.chamadas_rpc) == 2
    assert uso.inseridas_na_tabela == 1
    assert uso.funcoes == [None]


def test_o_caminho_antigo_grava_a_funcao_quando_a_coluna_existe(monkeypatch):
    # Caso raro (coluna da 016 criada mas sem nenhuma função): a funcao não se perde.
    uso = preparar_uso(monkeypatch, UsoIaFalso([], com_funcao=False))
    uso.com_016 = True

    limites.registar_pergunta("utilizador-teste", "importar_pdf")

    assert uso.funcoes == ["importar_pdf"]


@pytest.mark.parametrize("codigo", ["PGRST202", "42883"])
def test_os_dois_codigos_de_funcao_em_falta_dao_none(monkeypatch, codigo):
    class SemFuncao:
        def rpc(self, nome, parametros):
            raise APIError({"code": codigo, "message": "a função não existe"})

    monkeypatch.setattr(limites, "supabase", SemFuncao())

    assert limites.registar_pedido_atomico("utilizador-teste", AGORA, 20, "chat") is None


def test_outros_erros_da_funcao_nao_caem_no_caminho_antigo(monkeypatch):
    # Ex.: sem permissão (42501). Isto é um erro a sério: não se pode contornar o limite com o caminho antigo.
    class SemPermissao:
        def rpc(self, nome, parametros):
            raise APIError({"code": "42501", "message": "permission denied for function registar_pedido_ia"})

        def table(self, nome):
            raise AssertionError("não devia usar o caminho antigo")

    monkeypatch.setattr(limites, "supabase", SemPermissao())
    monkeypatch.setattr(limites, "plano_do_utilizador", lambda user_id: "essencial")

    with pytest.raises(APIError):
        limites.registar_pergunta("utilizador-teste", "chat")


@pytest.mark.parametrize("dados", [None, [], [True], "true"])
def test_uma_resposta_estranha_da_funcao_conta_como_limite(monkeypatch, dados):
    # Na dúvida, fecha: só um true verdadeiro deixa gastar créditos da IA.
    class RespostaEstranha:
        data = None

        def rpc(self, nome, parametros):
            return self

        def execute(self):
            self.data = dados
            return self

    monkeypatch.setattr(limites, "supabase", RespostaEstranha())

    assert limites.registar_pedido_atomico("utilizador-teste", AGORA, 20, "chat") is False


def test_plano_desconhecido_com_a_funcao_tambem_da_429(monkeypatch):
    uso = preparar_uso(monkeypatch, UsoIaFalso([], com_funcao=True), plano=None)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste", "chat")

    assert erro.value.status_code == 429
    assert uso.chamadas_rpc[0][1]["p_limite"] == 0
    assert uso.inseridas == 0


CASOS_INICIO = [
    # (período, agora em UTC, início esperado em UTC)
    ("dia", datetime(2026, 1, 10, 0, 30, tzinfo=UTC), datetime(2026, 1, 10, 0, 0, tzinfo=UTC)),  # inverno
    ("dia", datetime(2026, 7, 15, 22, 59, tzinfo=UTC), datetime(2026, 7, 14, 23, 0, tzinfo=UTC)),  # 23:59 em Lisboa
    ("dia", datetime(2026, 7, 15, 23, 0, tzinfo=UTC), datetime(2026, 7, 15, 23, 0, tzinfo=UTC)),  # meia-noite certa
    ("dia", datetime(2026, 3, 29, 12, 0, tzinfo=UTC), datetime(2026, 3, 29, 0, 0, tzinfo=UTC)),  # dia da mudança para o verão
    ("dia", datetime(2026, 10, 25, 12, 0, tzinfo=UTC), datetime(2026, 10, 24, 23, 0, tzinfo=UTC)),  # dia da mudança para o inverno
    ("mes", datetime(2026, 11, 20, 15, 0, tzinfo=UTC), datetime(2026, 11, 1, 0, 0, tzinfo=UTC)),
    ("mes", datetime(2026, 8, 1, 0, 30, tzinfo=UTC), datetime(2026, 7, 31, 23, 0, tzinfo=UTC)),  # 01:30 de 1 de agosto
    ("mes", datetime(2026, 12, 31, 23, 59, tzinfo=UTC), datetime(2026, 12, 1, 0, 0, tzinfo=UTC)),
]


@pytest.mark.parametrize(("periodo", "agora", "esperado"), CASOS_INICIO)
def test_inicio_do_periodo_em_hora_de_lisboa(periodo, agora, esperado):
    assert limites.inicio_do_periodo(periodo, agora) == esperado


# --- Funções só dos planos pagos ---


@pytest.mark.parametrize("funcao", ["importar_pdf", "ler_talao"])
def test_pdf_e_taloes_sao_so_dos_planos_pagos(funcao):
    assert not limites.plano_inclui("free", funcao)
    assert not limites.plano_inclui(None, funcao)
    assert limites.plano_inclui("essencial", funcao)
    assert limites.plano_inclui("completo", funcao)


def test_o_resto_e_de_todos_os_planos():
    assert limites.plano_inclui("free", "chat")


def importar_pdf(cliente):
    return cliente.post(
        "/transacoes/importar", files={"ficheiro": ("extrato.pdf", b"%PDF-1.4 extrato inventado", "application/pdf")}
    )


# Uma "fotografia" inventada: começa como um JPEG verdadeiro (FF D8 FF) e tem mais de 1 KB.
JPEG_INVENTADO = b"\xff\xd8\xff\xe0" + b"x" * 2048


def ler_talao(cliente, imagem=JPEG_INVENTADO, tipo="image/jpeg"):
    return cliente.post("/compras/ler", files={"foto": ("talao.jpg", imagem, tipo)})


def test_o_free_nao_importa_pdf_e_nao_gasta_pedido(cliente, limite, monkeypatch):
    limite.plano = "free"
    paginas_contadas = []
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: paginas_contadas.append(pdf) or 1)

    resposta = importar_pdf(cliente)

    # 402 e não 403: o 403 faz o frontend mandar para "O teu plano terminou".
    assert resposta.status_code == 402
    assert resposta.json()["detail"] == (
        "A importação de extratos em PDF está disponível nos planos Essencial e Completo. "
        "No Free, podes importar o extrato em CSV."
    )
    assert limite.perguntas == 0
    assert paginas_contadas == []


def test_ler_pdf_enviado_tambem_recusa_o_free(limite, monkeypatch):
    # Segunda proteção: mesmo chamada fora da rota, a função não conta páginas nem gasta pedidos no Free.
    limite.plano = "free"
    paginas_contadas = []
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: paginas_contadas.append(pdf) or 1)

    with pytest.raises(HTTPException) as erro:
        main.ler_pdf_enviado(b"%PDF-1.4 extrato inventado", "utilizador-teste")

    assert erro.value.status_code == 402
    assert limite.perguntas == 0
    assert paginas_contadas == []


def importar_csv(cliente):
    return cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.csv", EXTRATO, "text/csv")})


def test_o_free_com_pedidos_importa_csv_categorizado_e_gasta_um(cliente, limite, monkeypatch):
    limite.plano = "free"
    monkeypatch.setattr(main, "categorizar", lambda transacoes, user_id=None, local=None: ["outros"] * len(transacoes))

    resposta = importar_csv(cliente)

    assert resposta.status_code == 201
    assert limite.perguntas == 1
    corpo = resposta.json()
    assert corpo["aviso"] is None
    assert {transacao["categoria"] for transacao in corpo["transacoes"]} == {"outros"}


def test_sem_pedidos_o_csv_importa_na_mesma_sem_categorias(cliente, limite, monkeypatch):
    # Os dados são do utilizador: sem pedidos à IA, importam-se na mesma, sem categoria.
    limite.plano = "free"
    limite.maximo = 0
    chamadas = []
    monkeypatch.setattr(main, "categorizar", lambda transacoes, user_id=None, local=None: chamadas.append(transacoes))

    resposta = importar_csv(cliente)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["importadas"] == 11
    assert corpo["aviso"] == (
        "Importámos as movimentações sem categorias porque chegaste ao limite de pedidos à IA. "
        "Podes categorizá-las mais tarde."
    )
    # Categoria vazia (NULL): é assim que o POST /transacoes/categorizar as encontra.
    assert {transacao["categoria"] for transacao in corpo["transacoes"]} == {None}
    assert chamadas == []
    assert limite.perguntas == 0


def test_o_free_nao_le_taloes_e_nao_gasta_pedido(cliente, limite, monkeypatch):
    limite.plano = "free"
    chamadas = []
    monkeypatch.setattr(main, "ler_talao", lambda *args, **opcoes: chamadas.append(args))

    resposta = ler_talao(cliente)

    assert resposta.status_code == 402
    assert resposta.json()["detail"] == "A leitura de talões está disponível nos planos Essencial e Completo."
    assert limite.perguntas == 0
    assert chamadas == []


@pytest.mark.parametrize("plano", ["essencial", "completo"])
def test_os_pagos_leem_taloes(cliente, limite, monkeypatch, plano):
    limite.plano = plano
    talao = Talao(
        loja="Loja Inventada", data=None, itens=[ItemTalao(descricao="Pão", quantidade=1, preco=0.5)], total=0.5,
        categoria="alimentação",
    )
    monkeypatch.setattr(main, "ler_talao", lambda *args, **opcoes: talao)

    resposta = ler_talao(cliente)

    assert resposta.status_code == 200
    assert limite.perguntas == 1


@pytest.mark.parametrize(
    ("imagem", "esperado"),
    [
        (b"\xff\xd8\xff\xe0resto", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\nresto", "image/png"),
        (b"RIFF\x10\x00\x00\x00WEBPresto", "image/webp"),
        (b"RIFF\x10\x00\x00\x00WAVEresto", None),  # RIFF, mas é som
        (b"%PDF-1.4 resto", None),
        (b"x" * 2048, None),
    ],
)
def test_o_formato_da_imagem_ve_se_pelos_primeiros_bytes(imagem, esperado):
    assert main.eh_imagem_suportada(imagem) == esperado


def test_a_ia_recebe_o_tipo_dos_bytes_e_nao_o_do_browser(cliente, limite, monkeypatch):
    # O browser diz JPEG, mas os bytes são de um PNG: a IA tem de receber "image/png".
    tipos = []
    talao = Talao(
        loja="Loja Inventada", data=None, itens=[ItemTalao(descricao="Pão", quantidade=1, preco=0.5)], total=0.5,
        categoria="alimentação",
    )
    monkeypatch.setattr(main, "ler_talao", lambda imagem, tipo, **opcoes: tipos.append(tipo) or talao)

    resposta = ler_talao(cliente, imagem=b"\x89PNG\r\n\x1a\n" + b"x" * 2048, tipo="image/jpeg")

    assert resposta.status_code == 200
    assert tipos == ["image/png"]


def test_talao_com_bytes_que_nao_sao_imagem_responde_422_sem_gastar_pedido(cliente, limite, monkeypatch):
    # O content_type diz JPEG, mas o ficheiro não é: recusa-se antes de gastar o pedido.
    chamadas = []
    monkeypatch.setattr(main, "ler_talao", lambda *args, **opcoes: chamadas.append(args))

    resposta = ler_talao(cliente, imagem=b"x" * 2048)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Formato de imagem não suportado. Usa JPEG, PNG ou WebP."
    assert limite.perguntas == 0
    assert chamadas == []


def test_o_free_recebe_402_antes_de_validar_os_bytes(cliente, limite):
    limite.plano = "free"

    assert ler_talao(cliente, imagem=b"x" * 2048).status_code == 402


def test_os_pagos_importam_pdf(cliente, limite, monkeypatch):
    limite.plano = "completo"
    paginas_contadas = []
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: paginas_contadas.append(pdf) or 1)
    monkeypatch.setattr(
        main,
        "ler_extrato_pdf",
        lambda pdf, user_id=None, local=None: ExtratoPdf(
            movimentos=[MovimentoPdf(data="2026-10-01", descricao="CAFE", valor=-1.2, saldo=None)]
        ),
    )
    monkeypatch.setattr(main, "categorizar", lambda transacoes, user_id=None, local=None: ["outros"] * len(transacoes))

    resposta = importar_pdf(cliente)

    assert resposta.status_code == 201
    # O plano verifica-se na rota e na função, mas o pedido e as páginas contam uma só vez.
    assert limite.perguntas == 1
    assert len(paginas_contadas) == 1


def test_o_resumo_do_free_sem_pedidos_fala_do_mes(cliente, limite, monkeypatch):
    limite.plano = "free"
    limite.maximo = 0
    monkeypatch.setattr(main, "recolher_dados", lambda user_id, mes: {"transacoes_no_mes": 1, "despesas": 3.33})

    resposta = cliente.get("/resumo?mes=2026-08")

    assert resposta.json()["resumo"] == "Chegaste ao limite de pedidos à IA deste mês. O resumo volta no dia 1."


# --- GET /plano e GET /planos ---


@pytest.fixture
def assinatura(monkeypatch):
    """Fixa a linha da assinaturas, os pedidos e os PDF já feitos, e a hora (20 de novembro de 2026)."""

    def _assinatura(plano, ativo_ate, pedidos=0, pdfs=0):
        pdfs_contados = []
        monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: limites.Assinatura(plano, ativo_ate))
        por_periodo = pedidos if isinstance(pedidos, dict) else {"dia": pedidos, "mes": pedidos}
        monkeypatch.setattr(limites, "pedidos_no_periodo", lambda user_id, periodo: por_periodo[periodo])
        monkeypatch.setattr(limites, "pdfs_no_mes", lambda user_id: pdfs_contados.append(user_id) or pdfs)
        monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)
        return pdfs_contados

    return _assinatura


def test_a_rota_plano_mostra_o_limite_o_periodo_e_os_pedidos_usados(cliente, assinatura):
    pdfs_contados = assinatura("free", None, pedidos={"mes": 3, "dia": 99})

    resposta = cliente.get("/plano")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "plano": "free",
        "limite": 30,
        "periodo": "mes",
        "usadas": 3,
        "usadas_hoje": 3,  # nome antigo, mesmo número
        "ativo_ate": None,
        "plano_terminado": None,
        "terminou_em": None,
        "pdf_usados": 0,
        "pdf_limite": 0,  # o Free não importa PDF
        "memoria_mensagens": 0,  # o chat do Free não guarda mensagens anteriores
        "meses_historico": 3,  # o mês atual e os 2 anteriores
        # Perfil da conta (sql/020): o de sempre, para as contas que já existiam.
        "pais": "PT",
        "paises_bancos": ["PT"],
        "moeda": "EUR",
        # Questionário de boas-vindas (sql/021): sem a coluna lida, ninguém o tem por fazer.
        "boas_vindas_pendente": False,
        "brasil_disponivel": True,  # nos testes o Brasil está aberto (conftest.py)
    }
    assert pdfs_contados == []  # no Free nem se contam os PDF


def test_a_rota_plano_conta_por_dia_nos_pagos(cliente, assinatura):
    assinatura("essencial", date(2026, 12, 31), pedidos={"dia": 7, "mes": 99}, pdfs=4)

    resposta = cliente.get("/plano")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["periodo"], corpo["usadas"], corpo["limite"]) == ("dia", 7, 20)
    assert corpo["ativo_ate"] == "2026-12-31"
    assert (corpo["pdf_usados"], corpo["pdf_limite"]) == (4, 15)
    assert corpo["plano_terminado"] is None


def test_um_plano_pago_que_terminou_aparece_como_free(cliente, assinatura):
    # O Completo acabou a 19 de novembro; hoje é dia 20. A base de dados não muda: só a leitura.
    pdfs_contados = assinatura("completo", date(2026, 11, 19), pedidos={"mes": 12, "dia": 2})

    corpo = cliente.get("/plano").json()

    assert corpo["plano"] == "free"
    assert (corpo["limite"], corpo["periodo"], corpo["usadas"]) == (30, "mes", 12)
    assert corpo["ativo_ate"] is None
    assert corpo["plano_terminado"] == "completo"
    assert corpo["terminou_em"] == "2026-11-19"
    assert corpo["pdf_limite"] == 0
    assert pdfs_contados == []


def test_no_ultimo_dia_o_plano_pago_ainda_vale(cliente, assinatura):
    assinatura("essencial", date(2026, 11, 20))

    corpo = cliente.get("/plano").json()

    assert (corpo["plano"], corpo["plano_terminado"], corpo["ativo_ate"]) == ("essencial", None, "2026-11-20")


def test_plano_pago_sem_data_vale_como_free_sem_aviso_de_terminado(cliente, assinatura):
    assinatura("essencial", None)

    corpo = cliente.get("/plano").json()

    assert corpo["plano"] == "free"
    assert corpo["plano_terminado"] is None  # sem data não há "terminou a ..." para mostrar


def test_um_plano_pago_que_terminou_conta_os_pedidos_do_mes_e_nao_tem_pdf(monkeypatch):
    # O Free conta todos os pedidos do mês, incluindo os feitos ainda no plano pago (aceite pelo CEO).
    uso = UsoIaFalso([datetime(2026, 11, 5, 10, 0, tzinfo=UTC)] * 30)
    monkeypatch.setattr(limites, "supabase", uso)
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: limites.Assinatura("essencial", date(2026, 11, 19)))
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)

    with pytest.raises(HTTPException) as erro:
        limites.registar_pergunta("utilizador-teste", "chat")
    assert erro.value.status_code == 429
    assert "deste mês" in erro.value.detail

    with pytest.raises(HTTPException) as erro:
        limites.exigir_funcao("utilizador-teste", "importar_pdf")
    assert erro.value.status_code == 402


def test_o_free_nunca_mostra_data_de_fim(monkeypatch):
    # Mesmo que a coluna ativo_ate tenha uma data perdida, o Free não acaba.
    monkeypatch.setattr(limites, "assinatura_do_utilizador", lambda user_id: limites.Assinatura("free", date(2026, 1, 1)))
    monkeypatch.setattr(limites, "pedidos_no_periodo", lambda user_id, periodo: 0)

    assert limites.estado_do_plano("utilizador-teste").ativo_ate is None


class AssinaturasFalsas:
    """Imita a tabela assinaturas: devolve as linhas que lhe dermos."""

    def __init__(self, linhas):
        self.data = linhas

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        return self


@pytest.mark.parametrize(
    ("linhas", "esperado"),
    [
        ([{"plano": "completo", "ativo_ate": "2026-12-31"}], ("completo", date(2026, 12, 31))),
        ([{"plano": "free", "ativo_ate": None}], ("free", None)),
        ([], (None, None)),  # sem linha na tabela
    ],
)
def test_a_assinatura_le_o_plano_e_a_data(monkeypatch, linhas, esperado):
    monkeypatch.setattr(limites, "supabase", AssinaturasFalsas(linhas))
    conta = limites.assinatura_do_utilizador("utilizador-teste")
    assert (conta.plano, conta.ativo_ate) == esperado


def test_a_rota_planos_lista_os_planos_por_ordem_sem_login():
    # Sem dependency_overrides nem token: a rota é pública.
    resposta = TestClient(main.app).get("/planos")

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"plano": "free", "limite_diario": 30, "periodo": "mes", "limite_pdf": 0, "memoria_mensagens": 0, "meses_historico": 3},
        {"plano": "essencial", "limite_diario": 20, "periodo": "dia", "limite_pdf": 15, "memoria_mensagens": 4, "meses_historico": 12},
        {"plano": "completo", "limite_diario": 50, "periodo": "dia", "limite_pdf": 30, "memoria_mensagens": 10, "meses_historico": None},
    ]


def test_a_rota_planos_segue_os_limites_de_limites_py(monkeypatch):
    # Os números vêm só de LIMITES_POR_PLANO: mudar lá muda a página de preços.
    monkeypatch.setattr(limites, "LIMITES_POR_PLANO", {"free": (1, "mes"), "completo": (2, "dia")})
    monkeypatch.setattr(limites, "LIMITES_PDF_POR_PLANO", {"completo": 3})

    resposta = TestClient(main.app).get("/planos")

    assert resposta.json() == [
        {"plano": "free", "limite_diario": 1, "periodo": "mes", "limite_pdf": 0, "memoria_mensagens": 0, "meses_historico": 3},
        {"plano": "completo", "limite_diario": 2, "periodo": "dia", "limite_pdf": 3, "memoria_mensagens": 10, "meses_historico": None},
    ]
