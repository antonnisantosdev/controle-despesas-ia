import csv
import io
from datetime import datetime

from models import TransacaoCriar


def converter_linha(linha: dict) -> TransacaoCriar:

    return TransacaoCriar(
        data=datetime.strptime(linha["Data"], "%d-%m-%Y").date(),
        valor=float(linha["Montante"].replace(".", "").replace(",", ".")),
       descricao = linha["Descrição"].strip()
    )


def ler_extrato(conteudo: str) -> list[TransacaoCriar]:
    """Lê o texto completo de um extrato CSV e devolve a lista de transações."""
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=";")
    return [converter_linha(linha) for linha in leitor]
