"""Avaliação da categorização: quantas transações a IA acerta num conjunto com as respostas certas.

Usa a IA verdadeira (a chave do .env), por isso custa dinheiro. Com o Haiku, menos de 1 cêntimo por execução.

Correr a partir da raiz do projeto:
    python avaliacao/avaliar_categorizacao.py                        (casos_categorizacao.csv)
    python avaliacao/avaliar_categorizacao.py casos_novos.csv        (outro conjunto de casos)
    python avaliacao/avaliar_categorizacao.py --guardar "nota"       (junta o resultado a resultados.md)
    python avaliacao/avaliar_categorizacao.py casos_br.csv --pais BR (bancos brasileiros: moeda BRL e prompt BR)
"""

import csv
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

PASTA = Path(__file__).parent
# O script está na pasta avaliacao/, mas os ficheiros da API estão na raiz do projeto.
sys.path.insert(0, str(PASTA.parent))
# As chamadas feitas pela avaliação ficam marcadas na tabela chamadas_ia (não são de utilizadores).
os.environ["IA_ORIGEM"] = "avaliacao"

from typing import get_args  # noqa: E402

from ia import categorizar  # noqa: E402
from mensagens import Local  # noqa: E402
from models import Categoria, TransacaoCriar  # noqa: E402

# --pais BR: conta do Brasil em reais (o prompt da categorização escolhe-se pela moeda da conta).
LOCAIS = {"PT": Local("PT", "EUR"), "BR": Local("BR", "BRL")}

CATEGORIAS = set(get_args(Categoria))


def ler_casos(nome: str) -> list[dict]:
    """Lê os casos e confirma que estão bem escritos. Um caso mal escrito estragava a percentagem."""
    with open(PASTA / nome, encoding="utf-8") as ficheiro:
        # Guarda o número de cada linha no ficheiro, para os avisos apontarem para a linha certa.
        numeradas = [(n, linha) for n, linha in enumerate(ficheiro, start=1) if linha.strip() and not linha.startswith("#")]
    numeros = [n for n, _ in numeradas][1:]  # a primeira é o cabeçalho
    linhas = [linha for _, linha in numeradas]

    casos, problemas = [], []
    for numero, caso in zip(numeros, csv.DictReader(linhas, delimiter=";")):
        # Espaços a mais à volta do ";" não contam.
        caso = {chave.strip(): (valor or "").strip() for chave, valor in caso.items()}
        if caso["categoria"] not in CATEGORIAS:
            problemas.append(f"Linha {numero} ({caso['descricao']}): a categoria \"{caso['categoria']}\" não existe")
        try:
            # Formato português: "-1.234,56" -> -1234.56
            caso["valor"] = float(caso["valor"].replace(".", "").replace(",", "."))
        except ValueError:
            problemas.append(f"Linha {numero} ({caso['descricao']}): o valor \"{caso['valor']}\" não é um número")
        casos.append(caso)

    if problemas:
        print("Corrige estes casos antes de avaliar:")
        for problema in problemas:
            print("  " + problema)
        print("\nCategorias permitidas:", ", ".join(sorted(CATEGORIAS)))
        sys.exit(1)
    return casos


def main():
    argumentos = sys.argv[1:]
    pais = "PT"
    if "--pais" in argumentos:
        posicao = argumentos.index("--pais")
        pais = argumentos[posicao + 1].upper() if posicao + 1 < len(argumentos) else ""
        if pais not in LOCAIS:
            print("Usa --pais PT ou --pais BR.")
            sys.exit(1)
        del argumentos[posicao : posicao + 2]
    argumentos = [a for a in argumentos if a != "--guardar"]
    # Uma opção desconhecida (ex. "--pais=BR" ou um 2.º --pais) parava na nota e gastava pedidos com o país errado.
    desconhecidas = [a for a in argumentos if a.startswith("--")]
    if desconhecidas:
        print(f"Opção desconhecida: {desconhecidas[0]}. Usa --pais PT ou --pais BR (uma vez) e --guardar.")
        sys.exit(1)
    # O conjunto de casos é o argumento que acaba em .csv; o resto é uma nota para o resultados.md.
    conjunto = next((a for a in argumentos if a.endswith(".csv")), "casos_categorizacao.csv")
    nota = " ".join(a for a in argumentos if not a.endswith(".csv"))
    casos = ler_casos(conjunto)
    transacoes = [
        TransacaoCriar(data=date.today(), descricao=caso["descricao"], valor=caso["valor"]) for caso in casos
    ]

    # Exatamente a mesma função que a API usa ao importar um extrato: é ela que se está a avaliar.
    respostas = categorizar(transacoes, local=LOCAIS[pais])

    erros = [
        (caso["descricao"], caso["categoria"], resposta)
        for caso, resposta in zip(casos, respostas)
        if resposta != caso["categoria"]
    ]
    acertos = len(casos) - len(erros)
    percentagem = 100 * acertos / len(casos)
    modelo = os.getenv("CLAUDE_MODELO", "claude-haiku-5-5")

    print(f"Modelo: {modelo} | Conjunto: {conjunto} | País: {pais}")
    print(f"Acertou {acertos} de {len(casos)}: {percentagem:.1f}%\n")

    if erros:
        print("Erros (descrição: certa -> resposta da IA):")
        for descricao, certa, resposta in erros:
            print(f"  {descricao}: {certa} -> {resposta}")
        # Que categorias certas a IA mais falha? Ajuda a saber que regra acrescentar ao prompt.
        por_categoria = Counter(certa for _, certa, _ in erros)
        print("\nErros por categoria certa:", dict(por_categoria.most_common()))

    if "--guardar" in sys.argv:
        resultados = PASTA / "resultados.md"
        if not resultados.exists():
            resultados.write_text(
                "# Resultados da avaliação da categorização\n\n"
                "| Data | Modelo | Conjunto | Casos | Acertos | Percentagem | Nota |\n"
                "|---|---|---|---|---|---|---|\n",
                encoding="utf-8",
            )
        with open(resultados, "a", encoding="utf-8") as ficheiro:
            ficheiro.write(
                f"| {date.today()} | {modelo} | {conjunto} | {len(casos)} | {acertos} | {percentagem:.1f}% | {nota} |\n"
            )
        print(f"\nGuardado em {resultados}")


if __name__ == "__main__":
    main()
