"""Proteções contra abuso: movimentos por CSV, tamanho da descrição e teto de movimentações por conta."""

from datetime import date

import pytest
from fastapi import HTTPException

import main
from importar_csv import MAX_MOVIMENTOS_CSV, converter_linha, ler_extrato, transacoes_do_pdf
from limites import MAX_TRANSACOES_POR_CONTA, exigir_espaco_na_conta
from models import ExtratoPdf, MovimentoPdf

MENSAGEM_TETO = "Chegaste ao máximo de 20 000 movimentações nesta conta. Fala connosco se precisares de mais."


def csv_inventado(movimentos: int) -> bytes:
    """Um extrato CSV inventado com o número de movimentos pedido (saldos diferentes: nenhum é duplicado)."""
    linhas = ["Data;Descrição;Montante;Saldo"]
    linhas += [f"01-10-2026;CAFE INVENTADO;-1,20;{numero},00" for numero in range(movimentos)]
    return "\n".join(linhas).encode("utf-8")


def importar(cliente, conteudo, nome="extrato.csv", tipo="text/csv"):
    return cliente.post("/transacoes/importar", files={"ficheiro": (nome, conteudo, tipo)})


@pytest.fixture
def ia(monkeypatch):
    """Regista quantas transações foram à IA em cada chamada."""
    chamadas = []
    monkeypatch.setattr(
        main, "categorizar", lambda lista, user_id=None: chamadas.append(len(lista)) or ["outros"] * len(lista)
    )
    return chamadas


# --- Movimentos por CSV ---


def test_csv_com_o_maximo_de_movimentos_e_importado(cliente, ia, limite):
    resposta = importar(cliente, csv_inventado(MAX_MOVIMENTOS_CSV))

    assert resposta.status_code == 201
    assert resposta.json()["importadas"] == 2000
    assert ia == [2000]


def test_csv_com_movimentos_a_mais_e_recusado_sem_chamar_a_ia(cliente, ia, limite, base_dados):
    resposta = importar(cliente, csv_inventado(MAX_MOVIMENTOS_CSV + 1))

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Este extrato tem mais de 2000 movimentos. Divide-o em partes mais pequenas."
    assert ia == []
    assert limite.perguntas == 0
    assert base_dados.gravado == []


# --- Tamanho da descrição ---


def test_a_descricao_do_csv_e_cortada_a_200_caracteres():
    linha = {"Data": "01-10-2026", "Montante": "-1,20", "Descrição": "  " + "A" * 500, "Saldo": "100,00"}

    assert converter_linha(linha).descricao == "A" * 200


def test_a_descricao_do_pdf_e_cortada_a_200_caracteres():
    extrato = ExtratoPdf(movimentos=[MovimentoPdf(data=date(2026, 10, 1), descricao="B" * 500, valor=-1.2, saldo=None)])

    assert transacoes_do_pdf(extrato)[0].descricao == "B" * 200


def test_o_corte_nao_muda_o_hash_de_um_movimento_ja_importado():
    # O hash usa a descrição original: reimportar o mesmo extrato continua a dar duplicados.
    com_300 = ler_extrato("Data;Descrição;Montante;Saldo\n01-10-2026;" + "C" * 300 + ";-1,20;100,00")
    com_301 = ler_extrato("Data;Descrição;Montante;Saldo\n01-10-2026;" + "C" * 301 + ";-1,20;100,00")

    assert com_300[0].descricao == com_301[0].descricao
    assert com_300[0].hash_importacao != com_301[0].hash_importacao


# --- Teto de movimentações por conta ---


def test_o_teto_aceita_chegar_ao_maximo_e_recusa_passar():
    exigir_espaco_na_conta(MAX_TRANSACOES_POR_CONTA - 5, 5)

    with pytest.raises(HTTPException) as erro:
        exigir_espaco_na_conta(MAX_TRANSACOES_POR_CONTA - 5, 6)

    assert erro.value.status_code == 422
    assert erro.value.detail == MENSAGEM_TETO


def test_csv_que_passa_o_teto_e_recusado_sem_gastar_pedido(cliente, ia, limite, base_dados):
    base_dados.contagem = MAX_TRANSACOES_POR_CONTA - 2

    resposta = importar(cliente, csv_inventado(3))

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == MENSAGEM_TETO
    assert ia == []
    assert limite.perguntas == 0
    assert base_dados.gravado == []


def test_csv_que_cabe_ate_ao_teto_e_importado(cliente, ia, limite, base_dados):
    base_dados.contagem = MAX_TRANSACOES_POR_CONTA - 3

    resposta = importar(cliente, csv_inventado(3))

    assert resposta.status_code == 201
    assert resposta.json()["importadas"] == 3


def test_pdf_com_a_conta_no_teto_e_recusado_antes_de_ler(cliente, limite, base_dados, monkeypatch):
    base_dados.contagem = MAX_TRANSACOES_POR_CONTA
    lidos = []
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: lidos.append("paginas") or 1)
    monkeypatch.setattr(main, "ler_extrato_pdf", lambda pdf, user_id=None: lidos.append("ia"))

    resposta = importar(cliente, b"%PDF-1.4 extrato inventado", nome="extrato.pdf", tipo="application/pdf")

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == MENSAGEM_TETO
    # Ordem: plano, tamanho, páginas e só depois o teto. As páginas contam-se, a IA nunca é chamada.
    assert lidos == ["paginas"]
    assert limite.perguntas == 0
    assert limite.pdfs == 0


def test_pdf_com_movimentos_a_mais_para_o_teto_nao_grava_nem_categoriza(cliente, ia, limite, base_dados, monkeypatch):
    # Só depois de a IA ler o PDF se sabe quantos movimentos tem: o pedido da leitura fica gasto.
    base_dados.contagem = MAX_TRANSACOES_POR_CONTA - 1
    monkeypatch.setattr(main, "contar_paginas_pdf", lambda pdf: 1)
    movimentos = [
        MovimentoPdf(data=date(2026, 10, 1), descricao="CAFE", valor=-1.2, saldo=saldo) for saldo in (10.0, 8.8)
    ]
    monkeypatch.setattr(main, "ler_extrato_pdf", lambda pdf, user_id=None: ExtratoPdf(movimentos=movimentos))

    resposta = importar(cliente, b"%PDF-1.4 extrato inventado", nome="extrato.pdf", tipo="application/pdf")

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == MENSAGEM_TETO
    assert ia == []
    assert limite.perguntas == 1
    assert base_dados.gravado == []


def test_movimentacao_a_mao_com_a_conta_no_teto_e_recusada_sem_gastar_pedido(cliente, ia, limite, base_dados):
    base_dados.contagem = MAX_TRANSACOES_POR_CONTA

    resposta = cliente.post(
        "/transacoes",
        json={"data": "2026-11-08", "descricao": "Café", "valor": -1.2, "metodo_pagamento": "dinheiro"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == MENSAGEM_TETO
    assert ia == []
    assert limite.perguntas == 0
    assert base_dados.gravado == []


# --- Contagem das movimentações sem categoria ---


class ContagemFalsa:
    """Imita a tabela transacoes numa contagem: regista os filtros e devolve só o número."""

    def __init__(self, total):
        self.total = total
        self.chamadas: list[tuple] = []

    def __getattr__(self, nome):
        def guardar(*args, **opcoes):
            self.chamadas.append((nome, args, opcoes))
            return self

        return guardar

    def execute(self):
        total = self.total

        class Resposta:
            data = []
            count = total

        return Resposta


def test_a_contagem_sem_categoria_devolve_so_o_total_do_utilizador(cliente, monkeypatch):
    falsa = ContagemFalsa(42)
    monkeypatch.setattr(main, "supabase", falsa)

    resposta = cliente.get("/transacoes/sem-categoria/contagem")

    assert resposta.status_code == 200
    assert resposta.json() == {"total": 42}
    assert ("table", ("transacoes",), {}) in falsa.chamadas
    assert ("select", ("id",), {"count": "exact", "head": True}) in falsa.chamadas  # sem trazer linhas
    assert ("eq", ("user_id", "utilizador-teste"), {}) in falsa.chamadas
    assert ("is_", ("categoria", "null"), {}) in falsa.chamadas


def test_a_contagem_sem_categoria_sem_pendentes_da_zero(cliente, monkeypatch):
    monkeypatch.setattr(main, "supabase", ContagemFalsa(None))

    assert cliente.get("/transacoes/sem-categoria/contagem").json() == {"total": 0}


def test_csv_que_nao_e_utf8_da_422_e_nao_500(cliente, ia, limite):
    conteudo = "Data;Descrição;Montante;Saldo\n01-10-2026;CAFÉ;-1,20;10,00".encode("utf-16")

    resposta = importar(cliente, conteudo)

    assert resposta.status_code == 422
    assert "UTF-8" in resposta.json()["detail"]
    assert ia == []
    assert limite.perguntas == 0


def test_guardar_talao_com_a_conta_cheia_e_recusado(cliente, base_dados, monkeypatch):
    base_dados.contagem = MAX_TRANSACOES_POR_CONTA
    gravacoes = []
    monkeypatch.setattr(main, "gravar_compra", lambda user_id, nova, moeda=None: gravacoes.append(nova))

    resposta = cliente.post(
        "/compras",
        json={
            "loja": "LOJA INVENTADA",
            "data": "2026-10-01",
            "itens": [{"descricao": "PAO", "quantidade": 1, "preco": 1.0}],
            "total": 1.0,
            "categoria": "alimentação",
            "metodo_pagamento": "dinheiro",
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == MENSAGEM_TETO
    assert gravacoes == []


def test_guardar_talao_com_produtos_a_mais_e_recusado(cliente, monkeypatch):
    gravacoes = []
    monkeypatch.setattr(main, "gravar_compra", lambda user_id, nova, moeda=None: gravacoes.append(nova))
    itens = [{"descricao": "PAO", "quantidade": 1, "preco": 0.1}] * 201

    resposta = cliente.post(
        "/compras",
        json={
            "loja": "LOJA INVENTADA",
            "data": "2026-10-01",
            "itens": itens,
            "total": 20.1,
            "categoria": "alimentação",
            "metodo_pagamento": "dinheiro",
        },
    )

    assert resposta.status_code == 422
    assert gravacoes == []


def test_guardar_talao_com_descricao_enorme_e_recusado(cliente, monkeypatch):
    gravacoes = []
    monkeypatch.setattr(main, "gravar_compra", lambda user_id, nova, moeda=None: gravacoes.append(nova))

    resposta = cliente.post(
        "/compras",
        json={
            "loja": "LOJA INVENTADA",
            "data": "2026-10-01",
            "itens": [{"descricao": "X" * 201, "quantidade": 1, "preco": 1.0}],
            "total": 1.0,
            "categoria": "alimentação",
            "metodo_pagamento": "dinheiro",
        },
    )

    assert resposta.status_code == 422
    assert gravacoes == []
