"""Resumo anual (GET /relatorio, GET /relatorio/csv, POST /relatorio/resumo-ia). Dados inventados."""

import codecs
import csv
import io
import json
from datetime import date

import pytest

import consultas
import ia
import main
import relatorio
from models import ObjetivoRelatorio, ResumoAnualIA

HOJE = date(2026, 11, 10)


def mov(data: str, valor: float, categoria: str | None = "alimentação", descricao: str = "Supermercado Exemplo") -> dict:
    return {"data": data, "descricao": descricao, "valor": valor, "categoria": categoria}


# Ano de 2025 completo: salário todos os meses, renda todos os meses, e algumas compras.
LINHAS_2025 = (
    [mov(f"2025-{m:02d}-01", 1000.0, "rendimento", "Salario Empresa Exemplo") for m in range(1, 13)]
    + [mov(f"2025-{m:02d}-02", -500.0, "casa", "Renda Exemplo") for m in range(1, 13)]
    + [mov("2025-03-10", -100.0, "alimentação"), mov("2025-07-10", -300.0, "lazer", "Viagem Exemplo")]
)
# 2024: só em janeiro e dezembro (para a comparação de 2025).
LINHAS_2024 = [mov("2024-01-05", -200.0, "casa", "Renda Antiga"), mov("2024-12-05", -50.0, "lazer")]


def relatorio_de(ano: int, linhas: list[dict], hoje: date = HOJE, objetivos=None):
    return relatorio.montar_relatorio(ano, linhas, objetivos or [], hoje)


# --- Contas ---


def test_totais_do_ano_certos():
    r = relatorio_de(2025, LINHAS_2025 + LINHAS_2024)

    assert r.totais.entradas == 12000.0
    assert r.totais.saidas == 6400.0  # 12 x 500 + 100 + 300
    assert r.totais.saldo == 5600.0
    assert r.titulo == "Resumo anual das tuas finanças – 2025"
    assert r.ano_incompleto is False and r.meses_sem_dados == [] and r.ate_mes == "2025-12"


def test_mes_a_mes_tem_12_meses_num_ano_que_acabou():
    r = relatorio_de(2025, LINHAS_2025)

    assert [m.mes for m in r.meses] == [f"2025-{m:02d}" for m in range(1, 13)]
    julho = r.meses[6]
    assert (julho.entradas, julho.saidas, julho.saldo, julho.com_dados) == (1000.0, 800.0, 200.0, True)


def test_ano_corrente_vai_ate_ao_mes_atual_e_fica_incompleto():
    linhas = [mov("2026-02-03", -10.0), mov("2026-12-01", -999.0)]  # dezembro ainda não chegou: não conta
    r = relatorio_de(2026, linhas)

    assert len(r.meses) == 11 and r.ate_mes == "2026-11"
    assert r.ano_incompleto is True
    assert "2026-01" in r.meses_sem_dados and "2026-02" not in r.meses_sem_dados
    assert r.totais.saidas == 10.0


def test_ano_que_acabou_com_meses_sem_dados_fica_incompleto():
    r = relatorio_de(2024, LINHAS_2024)

    assert r.ano_incompleto is True
    assert len(r.meses_sem_dados) == 10


def test_percentagens_das_categorias():
    r = relatorio_de(2025, LINHAS_2025)

    por_categoria = {c.categoria: c for c in r.categorias}
    assert por_categoria["casa"].total == 6000.0
    assert por_categoria["casa"].percentagem == 93.8  # 6000 / 6400
    assert por_categoria["lazer"].percentagem == 4.7
    assert [c.categoria for c in r.categorias] == ["casa", "lazer", "alimentação"]  # da maior para a menor
    assert "rendimento" not in por_categoria  # as entradas não são gastos


def test_rendimento_mostra_se_como_entradas():
    # Uma saída com a categoria "rendimento" (ex.: devolução de salário) aparece com a etiqueta "Entradas".
    r = relatorio_de(2025, [mov("2025-05-01", -20.0, "rendimento")])

    assert r.categorias[0].categoria == "rendimento"
    assert r.categorias[0].etiqueta == "Entradas"
    assert relatorio.etiqueta(None) == "sem categoria"


def test_comparacao_so_com_dados_do_ano_anterior():
    sem_anterior = relatorio_de(2025, LINHAS_2025)
    com_anterior = relatorio_de(2025, LINHAS_2025 + LINHAS_2024)

    assert sem_anterior.comparacao is None
    comp = com_anterior.comparacao
    assert comp.ano == 2024 and comp.meses_com_dados == 2
    assert comp.totais.saidas == 250.0
    casa = next(c for c in comp.categorias if c.categoria == "casa")
    assert (casa.total, casa.total_anterior, casa.diferenca) == (6000.0, 200.0, 5800.0)


def test_comparacao_do_ano_corrente_usa_os_mesmos_meses():
    # Relatório de 2026 até novembro: o dezembro de 2025 fica de fora da comparação.
    so_dezembro = relatorio_de(2026, [mov("2026-03-01", -10.0), mov("2025-12-20", -80.0)])
    com_marco = relatorio_de(2026, [mov("2026-03-01", -10.0), mov("2025-12-20", -80.0), mov("2025-03-01", -30.0)])

    assert so_dezembro.comparacao is None
    assert com_marco.comparacao.meses_comparados[-1] == "11"
    assert com_marco.comparacao.totais.saidas == 30.0


def test_as_10_maiores_saidas():
    linhas = [mov(f"2025-01-{d:02d}", -float(d), "compras", f"Loja {d}") for d in range(1, 16)]
    linhas.append(mov("2025-01-20", 5000.0, "rendimento"))  # entrada: nunca entra nas maiores saídas
    r = relatorio_de(2025, linhas)

    assert len(r.maiores_saidas) == 10
    assert [s.valor for s in r.maiores_saidas] == [float(v) for v in range(15, 5, -1)]
    primeira = r.maiores_saidas[0]
    assert (primeira.data, primeira.descricao, primeira.categoria) == (date(2025, 1, 15), "Loja 15", "compras")


def test_pagamentos_que_se_repetem_somados_no_ano():
    linhas = [mov(f"2025-{m:02d}-08", -11.99, "lazer", f"COMPRA 4312 STREAMING EXEMPLO {m:02d}/25") for m in range(1, 13)]
    r = relatorio_de(2025, linhas)

    assert len(r.recorrentes) == 1
    streaming = r.recorrentes[0]
    assert streaming.pagamentos_no_ano == 12
    assert streaming.total_no_ano == 143.88
    assert streaming.valor_mensal == 11.99


def test_objetivos_vao_no_relatorio():
    objetivo = ObjetivoRelatorio(nome="Férias", valor_alvo=1000, valor_poupado=250, data_alvo=date(2027, 7, 1), percentagem=25.0)
    r = relatorio_de(2025, LINHAS_2025, objetivos=[objetivo])

    assert r.objetivos == [objetivo]


def test_aviso_e_nota_das_categorias_do_contador():
    r = relatorio_de(2025, LINHAS_2025)

    assert r.aviso.startswith("Resumo pessoal feito a partir dos extratos")
    assert "Não é um documento fiscal" in r.aviso
    assert r.nota_categorias == "Categorias da app, não correspondem às do e-fatura."


# --- Rotas ---


@pytest.fixture
def leituras(cliente, monkeypatch):
    """As leituras do relatório imitadas: guarda o user_id e os meses pedidos à base de dados."""
    pedidos = []

    def movimentos_entre(user_id, primeiro, ultimo):
        pedidos.append((user_id, primeiro, ultimo))
        return LINHAS_2025 + LINHAS_2024

    monkeypatch.setattr(relatorio, "movimentos_entre", movimentos_entre)
    monkeypatch.setattr(relatorio, "listar_objetivos", lambda user_id: pedidos.append((user_id, "objetivos")) or [])
    monkeypatch.setattr(main, "hoje_em_lisboa", lambda: HOJE)
    return pedidos


def test_rota_devolve_o_relatorio(cliente, leituras):
    resposta = cliente.get("/relatorio?ano=2025")

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["totais"] == {"entradas": 12000.0, "saidas": 6400.0, "saldo": 5600.0}
    assert len(dados["meses"]) == 12
    assert leituras[0] == ("utilizador-teste", "2024-01", "2025-12")


@pytest.mark.parametrize("ano", ["1999", "2027", "abc", ""])
def test_ano_invalido_da_422(cliente, leituras, ano):
    resposta = cliente.get(f"/relatorio?ano={ano}")

    assert resposta.status_code == 422
    assert leituras == []  # não chegou a ler nada


def test_user_id_vem_so_do_token(cliente, leituras):
    cliente.get("/relatorio?ano=2025&user_id=outra-pessoa")

    assert {pedido[0] for pedido in leituras} == {"utilizador-teste"}


class ConsultaQueGuardaFiltros:
    """Imita o Supabase do consultas.py: guarda os .eq() e devolve uma página de linhas e depois nada."""

    def __init__(self):
        self.filtros = []
        self.paginas = 0

    def table(self, nome):
        assert nome == "transacoes"
        return self

    def eq(self, coluna, valor):
        self.filtros.append((coluna, valor))
        return self

    def __getattr__(self, nome):
        return lambda *args, **opcoes: self

    def execute(self):
        self.paginas += 1
        return type("Resposta", (), {"data": LINHAS_2025 if self.paginas == 1 else []})


def test_a_consulta_filtra_pelo_user_id(cliente, monkeypatch):
    falsa = ConsultaQueGuardaFiltros()
    monkeypatch.setattr(consultas, "supabase", falsa)
    monkeypatch.setattr(relatorio, "listar_objetivos", lambda user_id: [])
    monkeypatch.setattr(main, "hoje_em_lisboa", lambda: HOJE)

    resposta = cliente.get("/relatorio?ano=2025")

    assert resposta.status_code == 200
    assert falsa.filtros and set(falsa.filtros) == {("user_id", "utilizador-teste")}


# --- CSV ---


def ler_csv(conteudo: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(conteudo.decode("utf-8-sig")), delimiter=";"))


def test_csv_para_o_excel_pt(cliente, leituras):
    resposta = cliente.get("/relatorio/csv?ano=2025")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/csv")
    assert resposta.headers["content-disposition"] == 'attachment; filename="relatorio-2025.csv"'
    assert resposta.content.startswith(codecs.BOM_UTF8)
    linhas = ler_csv(resposta.content)
    assert linhas[0] == ["Resumo anual das tuas finanças – 2025"]
    assert linhas[1] == [relatorio.AVISO]  # o aviso numa só célula, antes das tabelas
    assert ["Entradas", "12000,00"] in linhas  # vírgula decimal
    assert ["Saídas", "6400,00"] in linhas
    assert [relatorio.NOTA_CATEGORIAS] in linhas
    assert ["janeiro de 2025", "1000,00", "500,00", "500,00"] in linhas
    assert ";" in resposta.content.decode("utf-8-sig").splitlines()[5]
    # Nunca "rendimento" no relatório.
    assert "rendimento" not in resposta.content.decode("utf-8-sig").lower()


@pytest.mark.parametrize("perigoso", ["=HYPERLINK(\"http://exemplo.pt\")", "+351", "-2+3", "@SOMA(A1)", "\tX", "\rX"])
def test_csv_neutraliza_formulas(perigoso):
    r = relatorio_de(2025, [mov("2025-01-05", -50.0, "compras", perigoso)])

    linhas = ler_csv(relatorio.relatorio_em_csv(r))

    linha = next(l for l in linhas if l and l[0] == "2025-01-05")
    # Nenhuma célula de texto começa por um caractere de fórmula (o tab e o CR já saem com os espaços da descrição).
    assert not linha[1].startswith(relatorio.INICIOS_PERIGOSOS)
    assert linha[1] == "'" + perigoso or linha[1] == perigoso.strip()
    assert relatorio.texto_seguro(perigoso) == "'" + perigoso
    assert linha[2] == "50,00"
    # Os números gerados pela app não levam apóstrofo, mesmo negativos.
    assert relatorio._celula(-12.5) == "-12,50"


def test_saldo_negativo_no_csv_continua_numero():
    r = relatorio_de(2025, [mov("2025-01-05", -50.0)])

    assert ["Saldo", "-50,00"] in ler_csv(relatorio.relatorio_em_csv(r))


def test_csv_no_free_da_402(cliente, leituras, limite):
    limite.plano = "free"

    resposta = cliente.get("/relatorio/csv?ano=2025")

    # 402 e não 403: no frontend o 403 manda para /assinatura-expirada.
    assert resposta.status_code == 402
    assert "Essencial e Completo" in resposta.json()["detail"]
    assert leituras == []


def test_relatorio_json_e_de_todos_os_planos(cliente, leituras, limite):
    limite.plano = "free"

    assert cliente.get("/relatorio?ano=2025").status_code == 200


# --- Resumo do ano pela IA ---


@pytest.fixture
def ia_imitada(monkeypatch):
    chamadas = []

    def resumir_ano(dados, user_id=None, config=None):
        chamadas.append((dados, user_id, config))
        return ResumoAnualIA(resumo="Em 2025 entraram 12.000,00 €.")

    monkeypatch.setattr(main, "resumir_ano", resumir_ano)
    return chamadas


@pytest.mark.parametrize("plano", ["free", "essencial"])
def test_resumo_ia_so_no_completo(cliente, leituras, limite, ia_imitada, plano):
    limite.plano = plano

    resposta = cliente.post("/relatorio/resumo-ia?ano=2025")

    assert resposta.status_code == 402
    assert "Completo" in resposta.json()["detail"]
    assert limite.funcoes == [] and ia_imitada == []


def test_resumo_ia_conta_um_pedido(cliente, leituras, limite, ia_imitada, monkeypatch):
    limite.plano = "completo"
    monkeypatch.setattr(main, "plano_e_config_ia", lambda user_id: ("completo", "config-do-completo"))

    resposta = cliente.post("/relatorio/resumo-ia?ano=2025")

    assert resposta.status_code == 200
    assert resposta.json() == {"resumo": "Em 2025 entraram 12.000,00 €."}
    assert limite.funcoes == ["resumo_anual"]
    dados, user_id, config = ia_imitada[0]
    assert user_id == "utilizador-teste" and config == "config-do-completo"
    # Só números e categorias: nenhuma descrição de movimento vai para a IA.
    texto = json.dumps(dados, ensure_ascii=False)
    assert "Supermercado" not in texto and "Renda Exemplo" not in texto and "Salario" not in texto


def test_resumo_ia_sem_movimentos_nao_gasta_pedido(cliente, limite, ia_imitada, monkeypatch):
    limite.plano = "completo"
    monkeypatch.setattr(relatorio, "movimentos_entre", lambda *args: [])
    monkeypatch.setattr(relatorio, "listar_objetivos", lambda user_id: [])
    monkeypatch.setattr(main, "hoje_em_lisboa", lambda: HOJE)

    resposta = cliente.post("/relatorio/resumo-ia?ano=2025")

    assert resposta.status_code == 200
    assert limite.funcoes == [] and ia_imitada == []


def test_resumir_ano_com_ia_imitada(cliente_falso):
    falso = cliente_falso()

    resultado = ia.resumir_ano(relatorio.dados_para_ia(relatorio_de(2025, LINHAS_2025)), user_id="utilizador-teste")

    assert resultado.resumo == "ok"
    chamada = falso.chamadas[0]
    assert chamada["system"] == ia.INSTRUCOES_RESUMO_ANUAL
    assert chamada["output_format"] is ResumoAnualIA
    assert "Renda Exemplo" not in chamada["messages"][0]["content"]


# Regra do contador: o resumo do ano não fala de impostos nem dá recomendações.
PALAVRAS_DO_CONTADOR = [
    "IRS", "dedutível", "dedução", "benefício fiscal", "reembolso",
    "rendimento coletável", "imposto", "IVA", "e-fatura", "Finanças",
]  # fmt: skip


def test_instrucoes_do_resumo_anual_proibem_as_palavras_fiscais():
    instrucoes = ia.INSTRUCOES_RESUMO_ANUAL
    linhas = instrucoes.splitlines()
    proibicao = [linha for linha in linhas if linha.startswith("- Nunca uses estas palavras")]

    assert len(proibicao) == 1
    for palavra in PALAVRAS_DO_CONTADOR:
        assert palavra in ia.PALAVRAS_PROIBIDAS_RESUMO_ANUAL
        assert palavra in proibicao[0]
    # Fora da linha da proibição, as instruções nunca usam essas palavras.
    resto = "\n".join(linha for linha in linhas if linha not in proibicao).lower()
    for palavra in PALAVRAS_DO_CONTADOR:
        assert palavra.lower() not in resto
    # Só descreve, sem recomendações, e diz que os números dependem do que foi importado.
    assert "devias poupar" in instrucoes and "Não dês conselhos" in instrucoes
    assert "dependem dos movimentos" in instrucoes


def test_funcoes_do_relatorio_por_plano():
    from limites import plano_inclui

    assert [plano_inclui(p, "exportar_relatorio") for p in ("free", None, "essencial", "completo")] == [
        False, False, True, True,
    ]  # fmt: skip
    assert [plano_inclui(p, "resumo_anual_ia") for p in ("free", None, "essencial", "completo")] == [
        False, False, False, True,
    ]  # fmt: skip


def test_nome_de_objetivo_perigoso_tambem_e_neutralizado():
    objetivo = ObjetivoRelatorio(nome="=1+1", valor_alvo=100, valor_poupado=10, data_alvo=date(2027, 1, 1), percentagem=10.0)
    r = relatorio_de(2025, [], objetivos=[objetivo])

    assert ["'=1+1", "100,00", "10,00", "2027-01-01", "10,00"] in ler_csv(relatorio.relatorio_em_csv(r))


# --- Correções do dev-seguranca ---


def test_cada_descricao_normaliza_se_uma_so_vez(monkeypatch):
    import recorrentes

    chamadas = []
    original = recorrentes.normalizar_descricao

    def contar(descricao):
        chamadas.append(descricao)
        return original(descricao)

    monkeypatch.setattr(recorrentes, "normalizar_descricao", contar)
    # Nomes só com letras: os números saem na normalização ("Loja 1" e "Loja 2" seriam a mesma loja).
    nomes = [f"Loja Inventada {chr(97 + r)}{chr(97 + r)}" for r in range(26)] + ["Loja Extra um", "Loja Extra dois", "Loja Extra tres", "Loja Extra quatro"]
    linhas = [mov(f"2025-{m:02d}-05", -10.0, "compras", nome) for nome in nomes for m in range(1, 13)]

    r = relatorio_de(2025, linhas)

    assert len(r.recorrentes) == 30
    assert len(chamadas) == len(linhas)  # uma vez por linha, e não uma vez por linha e por recorrente


def test_desempenho_com_20000_linhas_e_200_recorrentes():
    import random
    import time

    aleatorio = random.Random(1)
    letras = "abcdefghijklmnopqrstuvwxyz"
    linhas = [
        mov(f"2026-{m:02d}-05", -10.0, "compras", f"Loja Inventada {letras[r % 26]}{letras[r // 26]} XXXX1234")
        for r in range(200)
        for m in range(1, 12)
    ]
    while len(linhas) < 20000:
        numero = aleatorio.randint(1, 99999)
        linhas.append(mov(f"2026-{aleatorio.randint(1, 11):02d}-10", -5.0, "compras", f"Compra loja ficticia {numero}"))

    inicio = time.perf_counter()
    r = relatorio_de(2026, linhas)
    duracao = time.perf_counter() - inicio

    # 200 lojas inventadas + "compra loja ficticia" (os números saem na normalização, por isso é uma só).
    assert len(r.recorrentes) == 201
    assert duracao < 2.0  # mede ~0,2 s; antes da correção eram vários segundos (cresce com os recorrentes)


def test_cabecalhos_sem_cache(cliente, leituras):
    json_ = cliente.get("/relatorio?ano=2025")
    csv_ = cliente.get("/relatorio/csv?ano=2025")

    assert json_.headers["cache-control"] == "no-store"
    assert csv_.headers["cache-control"] == "no-store"
    assert csv_.headers["x-content-type-options"] == "nosniff"


def test_quebra_de_linha_no_inicio_tambem_e_neutralizada():
    assert relatorio.texto_seguro("\n=1+1") == "'\n=1+1"


def test_nomes_compridos_no_csv_sao_cortados_e_sem_quebras():
    nome = "  =Objetivo\ncom   quebras " + "x" * 300
    objetivo = ObjetivoRelatorio(nome=nome, valor_alvo=100, valor_poupado=10, data_alvo=date(2027, 1, 1), percentagem=10.0)

    linhas = ler_csv(relatorio.relatorio_em_csv(relatorio_de(2025, [], objetivos=[objetivo])))

    linha = next(l for l in linhas if l and l[0].startswith("'=Objetivo"))
    assert "\n" not in linha[0] and len(linha[0]) == relatorio.MAX_CARACTERES_DESCRICAO + 1  # + o apóstrofo


def test_dados_para_ia_nao_levam_descricoes_nem_nomes_de_objetivos():
    marcador = "MARCADOR-INVENTADO-123"
    linhas = [mov(f"2025-{m:02d}-05", -40.0, "lazer", f"{marcador} Assinatura") for m in range(1, 13)]
    linhas.append(mov("2025-06-01", -900.0, "compras", f"{marcador} compra grande"))
    objetivo = ObjetivoRelatorio(nome=marcador, valor_alvo=100, valor_poupado=10, data_alvo=date(2027, 1, 1), percentagem=10.0)
    r = relatorio_de(2025, linhas, objetivos=[objetivo])
    assert r.recorrentes and r.maiores_saidas  # o marcador está no relatório...

    texto = json.dumps(relatorio.dados_para_ia(r), ensure_ascii=False)

    assert marcador.lower() not in texto.lower()  # ...mas nunca vai para a IA


def test_resumo_ia_no_limite_da_429_sem_chamar_a_ia(cliente, leituras, limite, ia_imitada):
    limite.plano = "completo"
    limite.maximo = 0

    resposta = cliente.post("/relatorio/resumo-ia?ano=2025")

    assert resposta.status_code == 429
    assert ia_imitada == []


@pytest.mark.parametrize(
    ("texto", "proibido"),
    [
        ("Podes declarar isto no IRS.", True),
        ("Os impostos subiram.", True),
        ("Sem iva.", True),
        ("Consulta o Portal das Financas.", True),
        ("Fala com a Autoridade Tributária.", True),
        ("Este é o resumo das tuas finanças em 2025.", False),
        ("Presta atenção: a conta ficou ativa.", False),
        ("Despesas dedutiveis.", True),
        ("Benefício Fiscal", True),
        ("O saldo foi positivo e a poupança ativa.", False),
        ("Entraram 1.234,56 € e saíram 1.000,00 €.", False),
    ],
)
def test_palavras_proibidas_sem_maiusculas_nem_acentos(texto, proibido):
    assert ia.tem_palavra_proibida(texto) is proibido


def test_resposta_da_ia_com_termo_fiscal_da_503(cliente, leituras, limite, monkeypatch):
    from types import SimpleNamespace

    limite.plano = "completo"
    monkeypatch.setattr(main, "plano_e_config_ia", lambda user_id: ("completo", ia.config_ia_do_plano("completo")))
    monkeypatch.setattr(ia, "_registar_chamada", lambda *args, **opcoes: None)

    class AnthropicFalso:
        def __init__(self):
            self.messages = self

        def parse(self, **argumentos):
            return SimpleNamespace(
                parsed_output=ResumoAnualIA(resumo="Guarda os talões para o IRS."), stop_reason="end_turn"
            )

    monkeypatch.setattr(ia.anthropic, "Anthropic", AnthropicFalso)

    resposta = cliente.post("/relatorio/resumo-ia?ano=2025")

    assert resposta.status_code == 503
    assert "IRS" not in resposta.text
    assert limite.funcoes == ["resumo_anual"]  # o pedido já tinha contado


@pytest.mark.parametrize(
    ("resumo", "estado"),
    [("Em 2025, as tuas finanças tiveram 12.000,00 € de entradas.", 200), ("Parte disto é dedutível.", 503)],
)
def test_as_tuas_financas_passa_mas_dedutivel_da_503(cliente, leituras, limite, monkeypatch, resumo, estado):
    from types import SimpleNamespace

    limite.plano = "completo"
    monkeypatch.setattr(main, "plano_e_config_ia", lambda user_id: ("completo", ia.config_ia_do_plano("completo")))
    monkeypatch.setattr(ia, "_registar_chamada", lambda *args, **opcoes: None)

    class AnthropicFalso:
        def __init__(self):
            self.messages = self

        def parse(self, **argumentos):
            return SimpleNamespace(parsed_output=ResumoAnualIA(resumo=resumo), stop_reason="end_turn")

    monkeypatch.setattr(ia.anthropic, "Anthropic", AnthropicFalso)

    resposta = cliente.post("/relatorio/resumo-ia?ano=2025")

    assert resposta.status_code == estado
    if estado == 200:
        assert resposta.json() == {"resumo": resumo}
