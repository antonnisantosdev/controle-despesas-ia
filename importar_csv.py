import csv
import hashlib
import io
from datetime import datetime

from models import ExtratoPdf, TransacaoImportada


class ErroImportacao(Exception):
    """Lançada quando o extrato tem linhas inválidas. Guarda a lista de erros encontrados."""

    def __init__(self, erros: list[str]):
        super().__init__(f"{len(erros)} linha(s) inválida(s)")
        self.erros = erros


class PdfIlegivel(Exception):
    """O PDF não se consegue abrir (estragado, ou protegido com palavra-passe)."""


class ExtratoGrandeDemais(Exception):
    """O CSV tem mais movimentos do que MAX_MOVIMENTOS_CSV."""


# Movimentos máximos de um CSV. Um ano de um extrato normal tem bem menos; acima disto,
# o ficheiro é recusado antes de chamar a IA (a categorização vai numa só chamada).
MAX_MOVIMENTOS_CSV = 2000

# Caracteres máximos da descrição de cada movimento (o mesmo teto da movimentação feita à mão).
# Uma descrição enorme só serviria para encher o prompt da IA e a base de dados.
MAX_CARACTERES_DESCRICAO = 200


# Teto de entradas na árvore de páginas ao contar. Um PDF feito de propósito com dezenas de milhares
# de páginas vazias cabe em poucos MB e faria o servidor gastar segundos de CPU e centenas de MB a contá-las.
MAX_ENTRADAS_ARVORE_PDF = 200


def contar_paginas_pdf(pdf: bytes) -> int:
    """Quantas páginas tem o PDF. Lê só a estrutura do ficheiro, sem chamar a IA.

    Se a árvore de páginas passar o teto, para de contar e devolve MAX_ENTRADAS_ARVORE_PDF + 1
    (quer dizer "mais do que o teto").
    """
    # Importado aqui dentro: só a importação de PDF precisa do pypdf.
    from pypdf import PdfReader, apply_configuration
    from pypdf.errors import LimitReachedError

    try:
        with apply_configuration(page_tree_maximum_entries=MAX_ENTRADAS_ARVORE_PDF):
            return len(PdfReader(io.BytesIO(pdf)).pages)
    except LimitReachedError:
        return MAX_ENTRADAS_ARVORE_PDF + 1
    # Um PDF estragado pode dar vários tipos de erro no pypdf: todos querem dizer "não se consegue ler".
    except Exception as erro:
        raise PdfIlegivel(str(erro)) from erro


def calcular_hash(linha: dict) -> str:
    texto = ";".join(f"{chave}={linha[chave]}" for chave in ["Data", "Montante", "Descrição", "Saldo"])
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cortar_descricao(descricao: str) -> str:
    """Tira os espaços das pontas e corta a descrição a MAX_CARACTERES_DESCRICAO."""
    return descricao.strip()[:MAX_CARACTERES_DESCRICAO]


def converter_linha(linha: dict) -> TransacaoImportada:
    # O hash usa a descrição original: o mesmo movimento importado antes deste corte continua a ser duplicado.
    return TransacaoImportada(
        data=datetime.strptime(linha["Data"], "%d-%m-%Y").date(),
        valor=float(linha["Montante"].replace(".", "").replace(",", ".")),
        descricao=cortar_descricao(linha["Descrição"]),
        hash_importacao=calcular_hash(linha),
    )


def ler_extrato(conteudo: str) -> list[TransacaoImportada]:
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=";")
    transacoes = []
    erros = []

    # A linha 1 do ficheiro é o cabeçalho, por isso os dados começam na linha 2.
    for numero, linha in enumerate(leitor, start=2):
        # Para logo de ler: um ficheiro grande demais não chega a ser todo convertido.
        if numero - 1 > MAX_MOVIMENTOS_CSV:
            raise ExtratoGrandeDemais()
        try:
            transacao = converter_linha(linha)
            transacoes.append(transacao)
        except (ValueError, KeyError) as e:
            erros.append(f"Linha {numero}: {e}")

    if erros:
        raise ErroImportacao(erros)
    return transacoes


def transacoes_do_pdf(extrato: ExtratoPdf) -> list[TransacaoImportada]:
    """Converte o que a IA leu do PDF nas mesmas transações que saem de um CSV."""
    transacoes = []
    for posicao, movimento in enumerate(extrato.movimentos):
        # Mesmo formato de uma linha do CSV: assim, o mesmo movimento em CSV e em PDF dá o mesmo hash.
        linha = {
            "Data": movimento.data.strftime("%d-%m-%Y"),
            "Montante": f"{movimento.valor:.2f}".replace(".", ","),
            "Descrição": movimento.descricao,
            # Sem saldo, dois cafés iguais no mesmo dia dariam o mesmo hash e um deles perdia-se.
            "Saldo": f"{movimento.saldo:.2f}".replace(".", ",") if movimento.saldo is not None else f"sem-saldo-{posicao}",
        }
        transacoes.append(
            TransacaoImportada(
                data=movimento.data,
                valor=movimento.valor,
                descricao=cortar_descricao(movimento.descricao),
                hash_importacao=calcular_hash(linha),
            )
        )
    return transacoes
