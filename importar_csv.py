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


def calcular_hash(linha: dict) -> str:
    texto = ";".join(f"{chave}={linha[chave]}" for chave in ["Data", "Montante", "Descrição", "Saldo"])
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def converter_linha(linha: dict) -> TransacaoImportada:
    return TransacaoImportada(
        data=datetime.strptime(linha["Data"], "%d-%m-%Y").date(),
        valor=float(linha["Montante"].replace(".", "").replace(",", ".")),
        descricao=linha["Descrição"].strip(),
        hash_importacao=calcular_hash(linha),
    )


def ler_extrato(conteudo: str) -> list[TransacaoImportada]:
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=";")
    transacoes = []
    erros = []

    # A linha 1 do ficheiro é o cabeçalho, por isso os dados começam na linha 2.
    for numero, linha in enumerate(leitor, start=2):
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
                descricao=movimento.descricao.strip(),
                hash_importacao=calcular_hash(linha),
            )
        )
    return transacoes
