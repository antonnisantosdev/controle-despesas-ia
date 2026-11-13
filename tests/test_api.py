"""As rotas da API, com a base de dados e a IA a fingir (nada é gravado nem pago)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from ia import ErroIA
from mensagens import Local, msg
from models import ExtratoPdf, MovimentoPdf, ResumoMes

EXTRATO = (Path(__file__).parent.parent / "dados_exemplo" / "extrato_exemplo.csv").read_bytes()


@pytest.fixture
def ia(monkeypatch):
    """Substitui as chamadas à IA e regista quantas vezes foram feitas."""
    chamadas = []

    def categorizar(transacoes, user_id=None, local=None):
        chamadas.append("categorizar")
        return ["outros"] * len(transacoes)

    def resumir_mes(dados, user_id=None, config=None, local=None):
        chamadas.append("resumir")
        return ResumoMes(resumo="Resumo de teste", alertas=[])

    monkeypatch.setattr(main, "categorizar", categorizar)
    monkeypatch.setattr(main, "resumir_mes", resumir_mes)
    return chamadas


def importar(cliente, conteudo, nome="extrato.csv"):
    return cliente.post("/transacoes/importar", files={"ficheiro": (nome, conteudo, "text/csv")})


def test_a_raiz_responde_200_sem_login():
    # O frontend usa o GET / para acordar a API antes de um POST ou PATCH (api.ts, acordarApi).
    resposta = TestClient(main.app).get("/")

    assert resposta.status_code == 200


def test_sem_login_responde_401():
    # Sem o fixture "cliente": aqui não há login fingido.
    resposta = TestClient(main.app).get("/transacoes")

    assert resposta.status_code == 401


def test_importa_um_csv_com_uma_so_chamada_a_ia(cliente, ia, limite, base_dados):
    resposta = importar(cliente, EXTRATO)

    assert resposta.status_code == 201
    assert resposta.json()["importadas"] == 11
    assert ia == ["categorizar"]  # 11 transações, uma só chamada
    assert limite.perguntas == 1
    # O dono vem sempre do token, nunca do ficheiro.
    assert {linha["user_id"] for linha in base_dados.gravado} == {"utilizador-teste"}


def test_csv_demasiado_grande_nao_gasta_perguntas(cliente, ia, limite):
    resposta = importar(cliente, b"a" * (main.TAMANHO_MAXIMO_CSV + 1))

    assert resposta.status_code == 422
    assert ia == []
    assert limite.perguntas == 0


def ia_em_baixo(transacoes, user_id=None, local=None):
    raise ErroIA("sem rede")


def test_se_a_ia_falhar_o_csv_grava_se_sem_categorias(cliente, monkeypatch, base_dados, limite):
    # Os dados do CSV já estão lidos: não se perdem por a IA não responder.
    monkeypatch.setattr(main, "categorizar", ia_em_baixo)

    resposta = importar(cliente, EXTRATO)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["importadas"] == 11
    assert corpo["aviso"] == (
        "Importámos as movimentações sem categorias porque a IA não respondeu. Podes categorizá-las mais tarde."
    )
    assert {linha["categoria"] for linha in base_dados.gravado} == {None}
    assert limite.perguntas == 1  # o pedido fica gasto: a chamada à IA foi feita


def test_se_a_ia_falhar_ao_categorizar_o_pdf_responde_503_e_nada_e_gravado(cliente, monkeypatch, base_dados):
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: 1)
    monkeypatch.setattr(
        main,
        "ler_extrato_pdf",
        lambda pdf, user_id=None, local=None: ExtratoPdf(
            movimentos=[MovimentoPdf(data="2026-10-01", descricao="CAFE", valor=-1.2, saldo=None)]
        ),
    )
    monkeypatch.setattr(main, "categorizar", ia_em_baixo)

    resposta = importar(cliente, b"%PDF-1.4 extrato inventado", nome="extrato.pdf")

    assert resposta.status_code == 503
    assert base_dados.gravado == []


def test_pdf_que_nao_e_um_extrato_responde_422(cliente, monkeypatch):
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: 1)
    monkeypatch.setattr(main, "ler_extrato_pdf", lambda pdf, user_id=None, local=None: ExtratoPdf(movimentos=[]))

    resposta = importar(cliente, b"%PDF-1.4 receita de bolo", nome="bolo.pdf")

    assert resposta.status_code == 422


def test_sem_perguntas_a_movimentacao_grava_se_sem_categoria(cliente, ia, limite):
    limite.maximo = 0

    resposta = cliente.post(
        "/transacoes",
        json={"data": "2026-11-08", "descricao": "Café", "valor": -1.2, "metodo_pagamento": "dinheiro"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["categoria"] is None
    assert ia == []


@pytest.mark.parametrize("metodo", ["pix", "boleto"])
def test_pix_e_boleto_sao_metodos_aceites_nas_contas_br(cliente, ia, limite, metodo, monkeypatch):
    limite.maximo = 0
    monkeypatch.setattr(main, "local_do_utilizador", lambda user_id: Local(pais="BR", moeda="BRL"))

    resposta = cliente.post(
        "/transacoes",
        json={"data": "2026-11-08", "descricao": "PIX ENVIADO FEIRA", "valor": -20.0, "metodo_pagamento": metodo},
    )

    assert resposta.status_code == 201
    assert resposta.json()["metodo_pagamento"] == metodo


@pytest.mark.parametrize(("pais", "metodo"), [("PT", "pix"), ("PT", "boleto"), ("BR", "mbway")])
def test_metodo_de_outro_pais_da_422_sem_gravar_nem_gastar_ia(cliente, ia, limite, base_dados, pais, metodo, monkeypatch):
    monkeypatch.setattr(main, "local_do_utilizador", lambda user_id: Local(pais=pais, moeda="EUR"))

    resposta = cliente.post(
        "/transacoes",
        json={"data": "2026-11-08", "descricao": "Teste", "valor": -20.0, "metodo_pagamento": metodo},
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == msg("metodo_de_outro_pais", pais)
    assert ia == []


def test_compra_com_metodo_de_outro_pais_da_422(cliente, limite):
    corpo = {
        "loja": "Loja",
        "data": "2026-11-08",
        "itens": [{"descricao": "Pão", "quantidade": 1, "preco": 1.0}],
        "total": 1.0,
        "categoria": "alimentação",
        "metodo_pagamento": "pix",
    }

    resposta = cliente.post("/compras", json=corpo)

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == msg("metodo_de_outro_pais", "PT")


def test_compras_extra_aceite_nas_escolhas_do_utilizador(cliente, ia, limite):
    resposta = cliente.post(
        "/transacoes",
        json={
            "data": "2026-11-08",
            "descricao": "Prenda",
            "valor": -40.0,
            "metodo_pagamento": "dinheiro",
            "categoria": "compras extra",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["categoria"] == "compras extra"
    assert ia == []


def test_a_ia_nunca_pode_devolver_compras_extra():
    from pydantic import ValidationError

    from ia import Categorizacao
    from models import Talao

    with pytest.raises(ValidationError):
        Categorizacao(indice=0, categoria="compras extra")
    with pytest.raises(ValidationError):
        Talao(loja="L", data=None, itens=[], total=1.0, categoria="compras extra")


@pytest.mark.parametrize(
    ("rota", "metodo_http", "corpo"),
    [
        ("/orcamentos/casa", "put", '{"limite": Infinity}'),
        ("/orcamentos/casa", "put", '{"limite": 1e15}'),
        ("/objetivos", "post", '{"nome": "X", "valor_alvo": Infinity, "data_alvo": "2030-01-01"}'),
        ("/objetivos", "post", '{"nome": "X", "valor_alvo": 1e15, "data_alvo": "2030-01-01"}'),
        ("/objetivos/1", "patch", '{"valor_poupado": Infinity}'),
        (
            "/compras",
            "post",
            '{"loja": "L", "data": "2026-11-08", "itens": [{"descricao": "P", "quantidade": 1e12, "preco": 1}],'
            ' "total": 1, "categoria": "alimentação", "metodo_pagamento": "dinheiro"}',
        ),
        (
            "/compras",
            "post",
            '{"loja": "L", "data": "2026-11-08", "itens": [{"descricao": "P", "quantidade": 1, "preco": 1}],'
            ' "total": Infinity, "categoria": "alimentação", "metodo_pagamento": "dinheiro"}',
        ),
    ],
)
def test_valores_enormes_ou_infinitos_dao_422_nas_outras_rotas(cliente, limite, rota, metodo_http, corpo):
    resposta = getattr(cliente, metodo_http)(rota, content=corpo, headers={"Content-Type": "application/json"})

    assert resposta.status_code == 422


@pytest.mark.parametrize("valor", ["-999999999999", "NaN", "Infinity"])
def test_valor_enorme_ou_invalido_da_422_e_nao_chega_a_base_de_dados(cliente, ia, limite, valor):
    # O corpo vai à mão: o json do Python escreve NaN e Infinity, como um pedido feito de propósito.
    corpo = '{"data": "2026-11-08", "descricao": "Erro", "valor": %s, "metodo_pagamento": "dinheiro"}' % valor
    resposta = cliente.post("/transacoes", content=corpo, headers={"Content-Type": "application/json"})

    assert resposta.status_code == 422
    assert ia == []


def test_o_resumo_repetido_nao_volta_a_chamar_a_ia(cliente, ia, limite, monkeypatch):
    dados = {"transacoes_no_mes": 3, "despesas": 100.0}
    monkeypatch.setattr(main, "recolher_dados", lambda user_id, mes: dict(dados))

    cliente.get("/resumo?mes=2026-10")
    cliente.get("/resumo?mes=2026-10")
    assert ia == ["resumir"]

    dados["despesas"] = 150.0  # entrou uma despesa nova: o resumo tem de ser refeito
    cliente.get("/resumo?mes=2026-10")
    assert ia == ["resumir", "resumir"]
    assert limite.perguntas == 2


def test_sem_pedidos_a_ia_o_resumo_mostra_o_aviso_do_limite(cliente, ia, limite, monkeypatch):
    limite.maximo = 0
    # Números diferentes dos outros testes, para o resumo não vir da memória (RESUMOS_EM_MEMORIA, resumo.py).
    monkeypatch.setattr(main, "recolher_dados", lambda user_id, mes: {"transacoes_no_mes": 1, "despesas": 7.77})

    resposta = cliente.get("/resumo?mes=2026-09")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "resumo": "Chegaste ao limite de pedidos à IA de hoje. O resumo volta depois da meia-noite.",
        "alertas": [],
    }
    assert ia == []
