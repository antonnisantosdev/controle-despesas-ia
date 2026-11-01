import csv
import io
from datetime import datetime

from models import TransacaoCriar


class ErroImportacao(Exception):
    """Lançada quando o extrato tem linhas inválidas. Guarda a lista de erros encontrados."""

    def __init__(self, erros: list[str]):
        super().__init__(f"{len(erros)} linha(s) inválida(s)")
        self.erros = erros


def converter_linha(linha: dict) -> TransacaoCriar:
    """Converte uma linha do CSV do banco numa TransacaoCriar."""
    return TransacaoCriar(
        data=datetime.strptime(linha["Data"], "%d-%m-%Y").date(),
        valor=float(linha["Montante"].replace(".", "").replace(",", ".")),
        descricao=linha["Descrição"].strip(),
    )


def ler_extrato(conteudo: str) -> list[TransacaoCriar]:
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=";")
    transacoes = []
    erros = []

    # A linha 1 do ficheiro é o cabeçalho, por isso os dados começam na linha 2.
    for numero, linha in enumerate(leitor, start=2):
        try:
            transacao = converter_linha(linha)
            transacoes.append(transacao)
        except Exception as e:
            erros.append(f"Linha {numero}: {e}")

    if erros:
        raise ErroImportacao(erros)
    return transacoes
