"""Leitura de extratos: CSV linha a linha, e a conversão do que a IA leu de um PDF."""

from datetime import date
from pathlib import Path

import pytest

from importar_csv import ErroImportacao, calcular_hash, ler_extrato, transacoes_do_pdf
from models import ExtratoPdf, MovimentoPdf

DADOS = Path(__file__).parent.parent / "dados_exemplo"


def ler(nome: str) -> str:
    return (DADOS / nome).read_text(encoding="utf-8-sig")


def test_le_um_extrato_valido():
    transacoes = ler_extrato(ler("extrato_exemplo.csv"))

    assert len(transacoes) == 11
    primeira = transacoes[0]
    assert primeira.data == date(2026, 10, 1)
    assert primeira.valor == 1200.0  # "1200,00" no formato português
    assert primeira.descricao == "TRF SALARIO EMPRESA FICTICIA LDA"


def test_junta_todos_os_erros_antes_de_falhar():
    with pytest.raises(ErroImportacao) as erro:
        ler_extrato(ler("extrato_com_erros.csv"))

    # O utilizador vê todas as linhas erradas de uma vez, com o número da linha.
    assert len(erro.value.erros) == 2
    assert erro.value.erros[0].startswith("Linha 3:")


def test_a_mesma_linha_da_sempre_o_mesmo_hash():
    linha = {"Data": "01-10-2026", "Montante": "-1,20", "Descrição": "CAFE", "Saldo": "100,00"}

    assert calcular_hash(linha) == calcular_hash(dict(linha))
    assert calcular_hash(linha) != calcular_hash(linha | {"Saldo": "98,80"})


def test_o_mesmo_movimento_em_pdf_e_em_csv_da_o_mesmo_hash():
    do_csv = ler_extrato(ler("extrato_exemplo.csv"))[0]
    salario = MovimentoPdf(
        data=date(2026, 10, 1), descricao="TRF SALARIO EMPRESA FICTICIA LDA", valor=1200.0, saldo=1850.40
    )

    assert transacoes_do_pdf(ExtratoPdf(movimentos=[salario]))[0].hash_importacao == do_csv.hash_importacao


def test_dois_movimentos_iguais_sem_saldo_nao_se_juntam():
    cafe = MovimentoPdf(data=date(2026, 10, 5), descricao="CAFE CENTRAL", valor=-1.2, saldo=None)

    transacoes = transacoes_do_pdf(ExtratoPdf(movimentos=[cafe, cafe]))

    assert transacoes[0].hash_importacao != transacoes[1].hash_importacao
