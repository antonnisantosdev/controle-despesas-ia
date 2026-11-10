"""Ferramentas do chat: histórico por plano, vários meses, orçamentos e objetivos (dados inventados)."""

import json
from datetime import date, datetime, timezone

import pytest

import consultas
import ferramentas
import limites
from ferramentas import MAX_MESES_POR_CHAMADA, executar_ferramenta, meses_entre
from ia import PedidoInvalido
from models import GastoCategoria, LinhaOrcamento, Objetivo


@pytest.fixture
def dados(monkeypatch):
    """Hoje é 9 de novembro de 2026. As consultas devolvem dados inventados e guardam quem as pediu."""
    pedidos = []
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc))

    def gastos_do_mes(user_id, mes):
        pedidos.append(("mes", user_id, mes))
        return [GastoCategoria(categoria="lazer", total=12.5)]

    def gastos_de_varios_meses(user_id, meses):
        pedidos.append(("varios", user_id, meses))
        return {mes: [GastoCategoria(categoria="casa", total=100.0)] for mes in meses}

    def planeamento_do_mes(user_id, mes):
        pedidos.append(("orcamentos", user_id, mes))
        return [LinhaOrcamento(categoria="restaurantes", limite=50.0, gasto=42.0)]

    def listar_objetivos(user_id):
        pedidos.append(("objetivos", user_id))
        return [Objetivo(id=1, nome="Férias", valor_alvo=900.0, data_alvo=date(2027, 7, 1), valor_poupado=150.0)]

    monkeypatch.setattr(ferramentas, "gastos_do_mes", gastos_do_mes)
    monkeypatch.setattr(ferramentas, "gastos_de_varios_meses", gastos_de_varios_meses)
    monkeypatch.setattr(ferramentas, "planeamento_do_mes", planeamento_do_mes)
    monkeypatch.setattr(ferramentas, "listar_objetivos", listar_objetivos)
    return pedidos


def correr(nome, argumentos, plano):
    return json.loads(executar_ferramenta(nome, argumentos, "utilizador-teste", plano))


# --- Histórico em meses de calendário ---


@pytest.mark.parametrize(
    ("plano", "mes", "dentro"),
    [
        ("free", "2026-09", True),  # o mês atual e os 2 anteriores
        ("free", "2026-08", False),
        ("essencial", "2025-12", True),  # o mês atual e os 11 anteriores
        ("essencial", "2025-11", False),
        ("completo", "2019-01", True),  # sem limite
    ],
)
def test_cada_plano_ve_o_seu_historico(dados, plano, mes, dentro):
    resultado = correr("gastos_por_categoria", {"mes": mes}, plano)

    if dentro:
        assert resultado == [{"categoria": "lazer", "total": 12.5}]
    else:
        assert resultado["fora_do_historico"] is True
        assert dados == []  # nem se chega a ler a base de dados


def test_fora_do_historico_diz_desde_quando_e_sugere_mudar_de_plano(dados):
    resultado = correr("gastos_por_categoria", {"mes": "2026-01"}, "free")

    assert "plano Free" in resultado["mensagem"]
    assert "desde 2026-09" in resultado["mensagem"]
    assert "mudar para um plano" in resultado["mensagem"]


def test_um_plano_pago_que_terminou_ve_so_o_historico_do_free(dados):
    # O plano chega aqui já como "free" (plano_efetivo): é o que o main passa.
    assert correr("orcamentos_do_mes", {"mes": "2026-05"}, "free")["fora_do_historico"] is True


def test_plano_desconhecido_ve_so_o_historico_do_free(dados):
    assert correr("gastos_por_categoria", {"mes": "2026-08"}, None)["fora_do_historico"] is True


# --- Vários meses ---


def test_varios_meses_numa_so_consulta(dados):
    resultado = correr("gastos_de_varios_meses", {"mes_inicio": "2026-09", "mes_fim": "2026-11"}, "free")

    assert list(resultado["meses"]) == ["2026-09", "2026-10", "2026-11"]
    assert "aviso" not in resultado
    assert dados == [("varios", "utilizador-teste", ["2026-09", "2026-10", "2026-11"])]


def test_intervalo_que_comeca_antes_do_plano_e_cortado_com_aviso(dados):
    resultado = correr("gastos_de_varios_meses", {"mes_inicio": "2026-01", "mes_fim": "2026-10"}, "free")

    assert list(resultado["meses"]) == ["2026-09", "2026-10"]
    assert "desde 2026-09" in resultado["aviso"]


def test_intervalo_todo_fora_do_plano(dados):
    resultado = correr("gastos_de_varios_meses", {"mes_inicio": "2026-01", "mes_fim": "2026-03"}, "free")

    assert resultado["fora_do_historico"] is True
    assert dados == []


def test_no_maximo_12_meses_por_chamada(dados):
    assert MAX_MESES_POR_CHAMADA == 12
    assert len(correr("gastos_de_varios_meses", {"mes_inicio": "2025-12", "mes_fim": "2026-11"}, "completo")["meses"]) == 12

    with pytest.raises(PedidoInvalido, match="no máximo 12 meses"):
        correr("gastos_de_varios_meses", {"mes_inicio": "2025-01", "mes_fim": "2026-11"}, "completo")


def test_intervalo_ao_contrario_da_erro(dados):
    with pytest.raises(PedidoInvalido):
        correr("gastos_de_varios_meses", {"mes_inicio": "2026-11", "mes_fim": "2026-10"}, "completo")


@pytest.mark.parametrize("mes", ["2026-13", "outubro", "2026-1", None, 202610])
def test_mes_invalido_da_erro_para_a_ia_corrigir(dados, mes):
    with pytest.raises(PedidoInvalido, match="AAAA-MM"):
        correr("gastos_por_categoria", {"mes": mes}, "completo")


def test_meses_entre_atravessa_o_ano():
    assert meses_entre("2026-11", "2027-02") == ["2026-11", "2026-12", "2027-01", "2027-02"]


# --- Orçamentos e objetivos ---


def test_orcamentos_do_mes(dados):
    resultado = correr("orcamentos_do_mes", {"mes": "2026-11"}, "essencial")

    assert resultado == [{"categoria": "restaurantes", "limite": 50.0, "gasto": 42.0}]
    assert dados == [("orcamentos", "utilizador-teste", "2026-11")]


def test_objetivos_de_poupanca(dados):
    resultado = correr("objetivos_de_poupanca", {}, "free")

    assert resultado[0]["nome"] == "Férias"
    assert resultado[0]["data_alvo"] == "2027-07-01"
    assert dados == [("objetivos", "utilizador-teste")]


def test_a_ia_nao_escolhe_o_user_id(dados):
    # Mesmo que a IA mande um user_id nos argumentos, vale sempre o do token.
    correr("gastos_por_categoria", {"mes": "2026-11", "user_id": "outra-pessoa"}, "completo")

    assert dados == [("mes", "utilizador-teste", "2026-11")]


def test_ferramenta_desconhecida(dados):
    with pytest.raises(PedidoInvalido, match="desconhecida"):
        correr("apagar_tudo", {}, "completo")


# --- A consulta de vários meses ---


def test_gastos_de_varios_meses_separa_por_mes(monkeypatch):
    linhas = [
        {"data": "2026-10-03", "categoria": "casa", "valor": -400.0},
        {"data": "2026-10-20", "categoria": "casa", "valor": -50.0},
        {"data": "2026-11-02", "categoria": "lazer", "valor": -9.99},
        {"data": "2026-11-05", "categoria": "rendimento", "valor": 1200.0},  # não é gasto
    ]
    monkeypatch.setattr(consultas, "ler_todas", lambda nova_consulta: linhas)

    resultado = consultas.gastos_de_varios_meses("utilizador-teste", ["2026-09", "2026-10", "2026-11"])

    assert resultado["2026-09"] == []
    assert resultado["2026-10"] == [GastoCategoria(categoria="casa", total=450.0)]
    assert resultado["2026-11"] == [GastoCategoria(categoria="lazer", total=9.99)]


# --- Procurar movimentos (descrição e categoria) ---

MOVIMENTOS = [
    {"data": "2026-10-02", "descricao": "Combustível Posto da Estrada", "valor": -48.0, "categoria": "transporte"},
    {"data": "2026-10-09", "descricao": "Portagens Via Rapida", "valor": -6.2, "categoria": "transporte"},
    {"data": "2026-10-15", "descricao": "Supermercado Bom Preco", "valor": -62.4, "categoria": "alimentação"},
    {"data": "2026-11-03", "descricao": "MB WAY para Rita", "valor": -25.0, "categoria": "transferências"},
    {"data": "2026-11-07", "descricao": "MB WAY de Rita", "valor": 12.5, "categoria": "transferências"},
    {"data": "2026-11-08", "descricao": "Desconto 50% Loja", "valor": -10.0, "categoria": "compras"},
    {"data": "2026-11-08", "descricao": "Loja do Bairro", "valor": -4.0, "categoria": "compras"},
]


@pytest.fixture
def movimentos(monkeypatch):
    """Hoje é 9 de novembro de 2026. movimentos_entre devolve MOVIMENTOS e guarda quem os pediu."""
    pedidos = []
    monkeypatch.setattr(limites, "agora_utc", lambda: datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc))

    def movimentos_entre(user_id, primeiro, ultimo, categoria=None, tipo="todos"):
        # A base de dados filtraria categoria e tipo; aqui devolve tudo e o filtro em Python faz o resto.
        pedidos.append((user_id, primeiro, ultimo))
        return [linha for linha in MOVIMENTOS if primeiro <= linha["data"][:7] <= ultimo]

    monkeypatch.setattr(ferramentas, "movimentos_entre", movimentos_entre)
    return pedidos


def procurar(plano="completo", **argumentos):
    return correr("procurar_movimentos", {"mes_inicio": "2026-09", "mes_fim": "2026-11", **argumentos}, plano)


def test_procura_sem_acentos_nem_maiusculas(movimentos):
    resultado = procurar(termos=["COMBUSTIVEL"])

    assert resultado["n_movimentos"] == 1
    assert resultado["amostra"][0]["descricao"] == "Combustível Posto da Estrada"
    assert resultado["total_saidas"] == 48.0


def test_basta_um_dos_termos_coincidir(movimentos):
    resultado = procurar(termos=["gasolina", "combustível", "portagens"])

    assert resultado["n_movimentos"] == 2
    assert resultado["total_saidas"] == 54.2


def test_tipo_separa_saidas_e_entradas(movimentos):
    todos = procurar(termos=["rita"])
    saidas = procurar(termos=["rita"], tipo="saidas")
    entradas = procurar(termos=["rita"], tipo="entradas")

    assert (todos["n_movimentos"], todos["total_saidas"], todos["total_entradas"]) == (2, 25.0, 12.5)
    assert (saidas["n_movimentos"], saidas["total_saidas"], saidas["total_entradas"]) == (1, 25.0, 0)
    assert (entradas["n_movimentos"], entradas["total_saidas"], entradas["total_entradas"]) == (1, 0, 12.5)


def test_procura_por_categoria_e_por_categoria_com_termos(movimentos):
    assert procurar(categoria="transporte")["n_movimentos"] == 2
    # Com categoria e termos, têm de coincidir os dois.
    assert procurar(categoria="transporte", termos=["portagens"])["n_movimentos"] == 1
    assert procurar(categoria="alimentação", termos=["portagens"])["n_movimentos"] == 0


def test_percentagem_e_sublinhado_sao_texto(movimentos):
    # Na base de dados (ILIKE) seriam curingas; aqui são letras como as outras.
    assert procurar(termos=["50%"])["n_movimentos"] == 1
    assert procurar(termos=["%%"])["n_movimentos"] == 0
    assert procurar(termos=["__"])["n_movimentos"] == 0


def test_amostra_tem_no_maximo_10_os_maiores_primeiro_e_descricao_cortada(monkeypatch, movimentos):
    linhas = [
        {"data": "2026-11-01", "descricao": f"Gasolina {i} " + "x" * 80, "valor": -float(i), "categoria": "transporte"}
        for i in range(1, 16)
    ]
    monkeypatch.setattr(ferramentas, "movimentos_entre", lambda user_id, primeiro, ultimo, categoria=None, tipo="todos": linhas)

    resultado = procurar(termos=["gasolina"])

    assert resultado["n_movimentos"] == 15
    assert resultado["restantes"] == 5
    assert [linha["valor"] for linha in resultado["amostra"]] == [-float(i) for i in range(15, 5, -1)]
    assert all(len(linha["descricao"]) == 60 for linha in resultado["amostra"])
    assert resultado["total_saidas"] == 120.0


@pytest.mark.parametrize(
    ("argumentos", "erro"),
    [
        ({"termos": ["aa", "bb", "cc", "dd", "ee", "ff"]}, "no máximo 5"),
        ({"termos": [""]}, "entre 2 e 40"),
        ({"termos": ["  "]}, "entre 2 e 40"),
        ({"termos": ["x" * 41]}, "entre 2 e 40"),
        ({"termos": "gasolina"}, "lista"),
        ({"categoria": "carros"}, "categoria inválida"),
        ({"termos": ["rita"], "tipo": "tudo"}, "tipo inválido"),
        ({}, "pelo menos termos ou categoria"),
        ({"termos": []}, "pelo menos termos ou categoria"),
        ({"termos": ["rita"], "mes_inicio": "2025-01", "mes_fim": "2026-11"}, "no máximo 12 meses"),
        ({"termos": ["rita"], "mes_inicio": "2026-11", "mes_fim": "2026-10"}, "anterior a mes_fim"),
        ({"termos": ["rita"], "mes_inicio": "2026-13"}, "AAAA-MM"),
    ],
)
def test_pedidos_mal_feitos_voltam_para_a_ia(movimentos, argumentos, erro):
    with pytest.raises(PedidoInvalido, match=erro):
        procurar(**argumentos)
    assert movimentos == []  # nem se chega a ler a base de dados


def test_procura_fora_do_historico_do_free(movimentos):
    resultado = procurar("free", termos=["rita"], mes_inicio="2026-01", mes_fim="2026-06")

    assert resultado["fora_do_historico"] is True
    assert movimentos == []


def test_procura_cortada_pelo_historico_do_free_avisa(movimentos):
    resultado = procurar("free", termos=["rita"], mes_inicio="2026-05", mes_fim="2026-11")

    assert "desde 2026-09" in resultado["aviso"]
    assert resultado["n_movimentos"] == 2
    assert movimentos == [("utilizador-teste", "2026-09", "2026-11")]


def test_a_ia_nao_escolhe_o_user_id_na_procura(movimentos):
    # additionalProperties: false diz à IA que não pode; mesmo que mande, vale o do token.
    procurar(termos=["rita"], user_id="outra-pessoa")

    assert movimentos == [("utilizador-teste", "2026-09", "2026-11")]


def test_procurar_movimentos_esta_na_lista_com_o_esquema_fechado():
    ferramenta = next(f for f in ferramentas.FERRAMENTAS if f["name"] == "procurar_movimentos")
    esquema = ferramenta["input_schema"]

    assert esquema["additionalProperties"] is False
    assert "user_id" not in esquema["properties"]
    assert esquema["properties"]["categoria"]["enum"] == ferramentas.CATEGORIAS
    assert esquema["properties"]["termos"]["maxItems"] == 5


def test_movimentos_entre_le_so_as_transacoes_do_utilizador(monkeypatch):
    filtros = []

    class Consulta:
        def __getattr__(self, nome):
            def metodo(*args):
                filtros.append((nome, *args))
                return self

            return metodo

    monkeypatch.setattr(consultas, "supabase", Consulta())
    monkeypatch.setattr(consultas, "ler_todas", lambda nova_consulta: nova_consulta() and [])

    consultas.movimentos_entre("utilizador-teste", "2026-09", "2026-11")

    assert ("select", "data, descricao, valor, categoria") in filtros
    assert ("eq", "user_id", "utilizador-teste") in filtros
    assert ("gte", "data", "2026-09-01") in filtros
    assert ("lt", "data", "2026-12-01") in filtros


def test_movimentos_entre_filtra_categoria_e_tipo_na_base_de_dados(monkeypatch):
    filtros = []

    class Consulta:
        def __getattr__(self, nome):
            def metodo(*args):
                filtros.append((nome, *args))
                return self

            return metodo

    monkeypatch.setattr(consultas, "supabase", Consulta())
    monkeypatch.setattr(consultas, "ler_todas", lambda nova_consulta: nova_consulta() and [])

    consultas.movimentos_entre("utilizador-teste", "2026-11", "2026-11", "transporte", "saidas")
    assert ("eq", "categoria", "transporte") in filtros
    assert ("lt", "valor", 0) in filtros

    filtros.clear()
    consultas.movimentos_entre("utilizador-teste", "2026-11", "2026-11", None, "entradas")
    assert ("gt", "valor", 0) in filtros
    assert not any(f[0] == "eq" and f[1] == "categoria" for f in filtros)


def test_termo_tem_de_comecar_uma_palavra():
    linhas = [
        {"data": "2026-11-03", "descricao": "MB WAY para Rita", "valor": -25.0, "categoria": "outros"},
        {"data": "2026-11-04", "descricao": "Bar Margarita", "valor": -9.0, "categoria": "restaurantes"},
        {"data": "2026-11-05", "descricao": "Pizzeria do Bazar", "valor": -12.0, "categoria": "restaurantes"},
        {"data": "2026-11-06", "descricao": "Combustível Posto", "valor": -48.0, "categoria": "transporte"},
    ]
    assert consultas.resumir_movimentos(linhas, ["rita"], None, "todos")["n_movimentos"] == 1
    assert consultas.resumir_movimentos(linhas, ["Ze"], None, "todos")["n_movimentos"] == 0
    assert consultas.resumir_movimentos(linhas, ["combust"], None, "todos")["n_movimentos"] == 1
