"""Pagamentos que se repetem todos os meses, sem IA (recorrentes.py). Todos os dados são inventados."""

from datetime import date

import pytest

import main
import recorrentes
from recorrentes import detetar_recorrentes, normalizar_descricao

HOJE = date(2026, 11, 9)


def despesa(data, descricao, valor, categoria="lazer"):
    return {"data": data, "descricao": descricao, "valor": valor, "categoria": categoria}


@pytest.mark.parametrize(
    ("original", "esperado"),
    [
        ("COMPRA 4312 NETFLIX.COM 05/10", "compra netflix com"),
        ("COMPRA 4312 NETFLIX.COM 05/11", "compra netflix com"),
        ("PAG. GINÁSIO FIT REF.123456789", "pag ginasio fit"),
        ("MB WAY P/ JOAO 912345678 ID00123", "mb way p joao"),
        ("CARTAO XXXX1234 SPOTIFY", "cartao spotify"),
    ],
)
def test_normaliza_tirando_o_que_muda_todos_os_meses(original, esperado):
    assert normalizar_descricao(original) == esperado


def test_tres_meses_seguidos_com_o_mesmo_valor_contam():
    transacoes = [
        despesa("2026-09-05", "COMPRA 4312 NETFLIX.COM 05/09", -12.99),
        despesa("2026-10-05", "COMPRA 4312 NETFLIX.COM 05/10", -12.99),
        despesa("2026-11-05", "COMPRA 4312 NETFLIX.COM 05/11", -12.99),
    ]

    [recorrente] = detetar_recorrentes(transacoes, HOJE)

    assert recorrente.valor_mensal == 12.99
    assert recorrente.meses_seguidos == 3
    assert recorrente.ultimo_pagamento == date(2026, 11, 5)
    assert recorrente.descricao == "COMPRA 4312 NETFLIX.COM 05/11"
    assert recorrente.categoria == "lazer"


def test_dois_meses_nao_chegam():
    transacoes = [despesa("2026-10-05", "SPOTIFY", -7.99), despesa("2026-11-05", "SPOTIFY", -7.99)]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_meses_com_um_buraco_no_meio_nao_sao_seguidos():
    transacoes = [
        despesa("2026-07-05", "SPOTIFY", -7.99),
        despesa("2026-08-05", "SPOTIFY", -7.99),
        despesa("2026-10-05", "SPOTIFY", -7.99),
        despesa("2026-11-05", "SPOTIFY", -7.99),
    ]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_valor_fora_dos_10_por_cento_parte_a_sequencia():
    transacoes = [
        despesa("2026-08-01", "GINASIO FIT", -30.00),
        despesa("2026-09-01", "GINASIO FIT", -30.00),
        despesa("2026-10-01", "GINASIO FIT", -45.00),  # 50% acima da mediana (30): não conta
        despesa("2026-11-01", "GINASIO FIT", -30.00),
    ]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_valor_dentro_dos_10_por_cento_conta():
    transacoes = [
        despesa("2026-09-20", "EDP COMERCIAL", -50.00, "casa"),
        despesa("2026-10-20", "EDP COMERCIAL", -54.00, "casa"),  # +8% em relação a setembro
        despesa("2026-11-02", "EDP COMERCIAL", -49.00, "casa"),  # -9% em relação a outubro
    ]

    [recorrente] = detetar_recorrentes(transacoes, HOJE)

    assert recorrente.valor_mensal == 49.00  # o valor do último pagamento
    assert recorrente.valor_anterior is None  # variações pequenas não são mudança de preço


def test_varias_compras_no_mesmo_mes_nao_sao_uma_assinatura():
    # Um supermercado: a mesma descrição, várias vezes por mês, com valores diferentes.
    transacoes = [
        despesa(f"2026-{mes:02d}-{dia:02d}", "CONTINENTE LISBOA", valor, "alimentação")
        for mes in (9, 10, 11)
        for dia, valor in ((3, -20.00), (17, -35.40))
    ]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_receitas_nao_contam():
    transacoes = [despesa(f"2026-{mes:02d}-25", "SALARIO EMPRESA XPTO", 1200.00, "rendimento") for mes in (9, 10, 11)]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_assinatura_cancelada_ha_meses_nao_aparece():
    transacoes = [despesa(f"2026-{mes:02d}-05", "DISNEY PLUS", -8.99) for mes in (3, 4, 5, 6)]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_ainda_conta_se_o_ultimo_pagamento_foi_no_mes_anterior():
    # Hoje é dia 9: a assinatura do dia 20 ainda não foi paga este mês.
    transacoes = [despesa(f"2026-{mes:02d}-20", "DISNEY PLUS", -8.99) for mes in (8, 9, 10)]

    assert len(detetar_recorrentes(transacoes, HOJE)) == 1


def test_atravessa_a_mudanca_de_ano():
    transacoes = [
        despesa("2026-11-10", "VODAFONE", -35.00, "telecomunicações"),
        despesa("2026-12-10", "VODAFONE", -35.00, "telecomunicações"),
        despesa("2027-01-10", "VODAFONE", -35.00, "telecomunicações"),
    ]

    assert len(detetar_recorrentes(transacoes, date(2027, 1, 15))) == 1


def test_descricoes_so_com_numeros_nao_se_juntam():
    # Sem letras, a descrição normalizada fica vazia: não há nada que diga que é o mesmo pagamento.
    transacoes = [despesa(f"2026-{mes:02d}-05", "12345 6789", -10.00) for mes in (9, 10, 11)]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_do_maior_para_o_menor():
    transacoes = [
        *(despesa(f"2026-{mes:02d}-05", "SPOTIFY", -7.99) for mes in (9, 10, 11)),
        *(despesa(f"2026-{mes:02d}-01", "RENDA CASA", -650.00, "casa") for mes in (9, 10, 11)),
    ]

    assert [r.valor_mensal for r in detetar_recorrentes(transacoes, HOJE)] == [650.00, 7.99]


# --- A rota GET /recorrentes ---


def test_a_rota_nao_gasta_pedidos_a_ia(cliente, limite, monkeypatch):
    lidos = []
    transacoes = [despesa(f"2026-{mes:02d}-05", "SPOTIFY", -7.99) for mes in (9, 10, 11)]
    monkeypatch.setattr(recorrentes, "ler_todas", lambda nova_consulta: lidos.append(1) or transacoes)
    monkeypatch.setattr(main, "hoje_do_utilizador", lambda user_id: HOJE)

    resposta = cliente.get("/recorrentes")

    assert resposta.status_code == 200
    assert resposta.json()[0]["valor_mensal"] == 7.99
    assert limite.perguntas == 0
    assert lidos == [1]


@pytest.mark.parametrize("plano", ["free", "essencial", "completo"])
def test_a_rota_e_de_todos_os_planos(cliente, limite, monkeypatch, plano):
    limite.plano = plano
    monkeypatch.setattr(recorrentes, "ler_todas", lambda nova_consulta: [])

    assert cliente.get("/recorrentes").status_code == 200


# --- Mudança de preço, duplicados e falsos positivos ---


def test_subida_de_preco_que_se_mantem_conta_e_mostra_o_valor_anterior():
    transacoes = [
        despesa("2026-08-05", "NETFLIX.COM", -10.99),
        despesa("2026-09-05", "NETFLIX.COM", -10.99),
        despesa("2026-10-05", "NETFLIX.COM", -12.99),  # +18%: o preço subiu
        despesa("2026-11-05", "NETFLIX.COM", -12.99),
    ]

    [recorrente] = detetar_recorrentes(transacoes, HOJE)

    assert recorrente.meses_seguidos == 4
    assert recorrente.valor_mensal == 12.99
    assert recorrente.valor_anterior == 10.99


def test_duas_mudancas_de_preco_partem_a_sequencia():
    # Sobe e volta a descer: não é uma mudança de preço que se mantém.
    transacoes = [
        despesa("2026-07-05", "GINASIO FIT", -30.00),
        despesa("2026-08-05", "GINASIO FIT", -30.00),
        despesa("2026-09-05", "GINASIO FIT", -45.00),
        despesa("2026-10-05", "GINASIO FIT", -30.00),
        despesa("2026-11-05", "GINASIO FIT", -30.00),
    ]

    # Recomeça em setembro: 45, 30, 30 (uma mudança) chega aos 3 meses.
    [recorrente] = detetar_recorrentes(transacoes, HOJE)
    assert recorrente.meses_seguidos == 3
    assert (recorrente.valor_anterior, recorrente.valor_mensal) == (45.00, 30.00)


def test_cobranca_repetida_no_mesmo_mes_conta_como_uma():
    transacoes = [
        despesa("2026-09-05", "SPOTIFY", -7.99),
        despesa("2026-10-05", "SPOTIFY", -7.99),
        despesa("2026-10-06", "SPOTIFY", -7.99),  # cobrada duas vezes em outubro
        despesa("2026-11-05", "SPOTIFY", -7.99),
    ]

    [recorrente] = detetar_recorrentes(transacoes, HOJE)

    assert recorrente.meses_seguidos == 3


def test_no_mes_repetido_conta_o_mais_recente():
    transacoes = [
        despesa("2026-09-05", "SPOTIFY", -7.99),
        despesa("2026-10-05", "SPOTIFY", -7.99),
        despesa("2026-11-01", "SPOTIFY", -7.99),
        despesa("2026-11-05", "SPOTIFY", -8.29),  # ±10% do outro: é o mesmo pagamento, fica o mais recente
    ]

    [recorrente] = detetar_recorrentes(transacoes, HOJE)

    assert recorrente.ultimo_pagamento == date(2026, 11, 5)
    assert recorrente.valor_mensal == 8.29


def test_mb_way_sem_nome_e_generico_e_nao_conta():
    # "MB WAY 912345678" e "MB WAY 913333333" ficam só "mb way": podiam ser pessoas diferentes.
    transacoes = [despesa(f"2026-{mes:02d}-05", f"MB WAY 91{mes}345678", -15.00, "outros") for mes in (9, 10, 11)]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_mb_way_com_nome_conta():
    transacoes = [despesa(f"2026-{mes:02d}-01", "MB WAY P/ SENHORIO SILVA", -450.00, "casa") for mes in (9, 10, 11)]

    assert len(detetar_recorrentes(transacoes, HOJE)) == 1


@pytest.mark.parametrize("categoria", ["levantamentos", "transferências"])
def test_levantamentos_e_transferencias_nao_contam(categoria):
    transacoes = [despesa(f"2026-{mes:02d}-01", "POUPANCA CONTA ORDEM", -100.00, categoria) for mes in (9, 10, 11)]

    assert detetar_recorrentes(transacoes, HOJE) == []


@pytest.mark.parametrize("descricao", ["LEVANTAMENTO ATM 1234", "TRANSFERENCIA SEPA 998877", "TRF 12345", "PAG 77"])
def test_descricoes_genericas_nao_contam(descricao):
    transacoes = [despesa(f"2026-{mes:02d}-01", descricao, -50.00, "outros") for mes in (9, 10, 11)]

    assert detetar_recorrentes(transacoes, HOJE) == []


def test_descricoes_iguais_depois_de_limpas_juntam_se():
    # A referência e a data mudam todos os meses; a descrição limpa é a mesma.
    transacoes = [
        despesa("2026-09-03", "DD VODAFONE PORTUGAL REF 4410923 03/09", -35.00, "telecomunicações"),
        despesa("2026-10-03", "DD VODAFONE PORTUGAL REF 4519833 03/10", -35.00, "telecomunicações"),
        despesa("2026-11-03", "DD VODAFONE PORTUGAL REF 4620011 03/11", -35.00, "telecomunicações"),
    ]

    [recorrente] = detetar_recorrentes(transacoes, HOJE)

    assert recorrente.meses_seguidos == 3
    assert recorrente.descricao == "DD VODAFONE PORTUGAL REF 4620011 03/11"


# --- Cache de 5 minutos ---


@pytest.fixture
def leituras(monkeypatch):
    """Conta as leituras à base de dados e deixa fixar o relógio da cache."""
    contador = {"leituras": 0, "agora": 1000.0}
    transacoes = [despesa(f"2026-{mes:02d}-05", "SPOTIFY", -7.99) for mes in (9, 10, 11)]

    def ler_todas(nova_consulta):
        contador["leituras"] += 1
        return transacoes

    monkeypatch.setattr(recorrentes, "ler_todas", ler_todas)
    monkeypatch.setattr(recorrentes, "_agora", lambda: contador["agora"])
    monkeypatch.setattr(main, "hoje_do_utilizador", lambda user_id: HOJE)
    return contador


def test_a_cache_evita_ler_outra_vez_durante_5_minutos(cliente, leituras):
    cliente.get("/recorrentes")
    leituras["agora"] += 299
    cliente.get("/recorrentes")

    assert leituras["leituras"] == 1


def test_a_cache_expira_ao_fim_de_5_minutos(cliente, leituras):
    cliente.get("/recorrentes")
    leituras["agora"] += 300
    cliente.get("/recorrentes")

    assert leituras["leituras"] == 2


def test_a_cache_e_de_cada_utilizador():
    recorrentes._CACHE["outra-pessoa"] = (0.0, HOJE, [])

    recorrentes.esquecer_recorrentes("utilizador-teste")

    assert "outra-pessoa" in recorrentes._CACHE
    recorrentes._CACHE.clear()


@pytest.mark.parametrize(
    ("metodo", "caminho", "corpo"),
    [
        ("post", "/transacoes", {"data": "2026-11-09", "descricao": "Café", "valor": -1.2, "metodo_pagamento": "dinheiro", "categoria": "restaurantes"}),
        ("patch", "/transacoes/1", {"categoria": "lazer"}),
    ],
)
def test_criar_ou_editar_movimentacoes_apaga_a_cache(cliente, leituras, base_dados, metodo, caminho, corpo):
    cliente.get("/recorrentes")
    # A base de dados a fingir devolve a linha alterada (como o Supabase quando o update encontra a linha).
    base_dados.update = lambda dados: base_dados.insert(
        {"data": "2026-11-05", "descricao": "SPOTIFY", "valor": -7.99, **dados}
    )

    getattr(cliente, metodo)(caminho, json=corpo)
    cliente.get("/recorrentes")

    assert leituras["leituras"] == 2


def test_importar_apaga_a_cache(cliente, leituras, monkeypatch):
    monkeypatch.setattr(main, "categorizar", lambda transacoes, user_id=None: ["outros"] * len(transacoes))
    cliente.get("/recorrentes")

    csv = "Data;Descrição;Montante;Saldo\n05-11-2026;SPOTIFY;-7,99;100,00\n".encode()
    resposta = cliente.post("/transacoes/importar", files={"ficheiro": ("extrato.csv", csv, "text/csv")})
    cliente.get("/recorrentes")

    assert resposta.status_code == 201
    assert leituras["leituras"] == 2


def test_a_cache_aguenta_pedidos_ao_mesmo_tempo(monkeypatch):
    import threading

    monkeypatch.setattr(recorrentes, "ler_todas", lambda nova_consulta: [])
    recorrentes._CACHE.clear()
    erros = []

    def trabalhar(i):
        try:
            for _ in range(200):
                recorrentes.recorrentes_do_utilizador(f"pessoa-{i % 5}", HOJE)
                recorrentes.esquecer_recorrentes(f"pessoa-{(i + 1) % 5}")
        except Exception as erro:  # um "dictionary changed size during iteration" apareceria aqui
            erros.append(erro)

    threads = [threading.Thread(target=trabalhar, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert erros == []
    recorrentes._CACHE.clear()
