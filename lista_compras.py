"""Fazer as minhas compras: os mercados, a limpeza do que a IA devolve e o cálculo do plano.

A IA (ia.fazer_compras) procura os preços nos sites oficiais dos mercados e devolve uma lista de achados.
Tudo o que vem dela é tratado como dado (pode estar errado ou ter sido "plantado" numa página):
- só passam os mercados escolhidos pela pessoa;
- os links só passam se forem https e do site desse mercado (domínio ou subdomínio); senão ficam vazios;
- os preços têm de ser números finitos entre 0 e PRECO_MAXIMO, e as embalagens entre 1 e MAX_EMBALAGENS;
- o preço total de cada achado e o plano (o mais barato de cada produto, o total por mercado e o orçamento)
  calculam-se aqui, em Python, nunca pela IA.

Sem base de dados nem IA: tudo testável sozinho (tests/test_fazer_compras.py).
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import quote_plus, urlsplit, urlunsplit


@dataclass(frozen=True)
class Mercado:
    nome: str
    # Sites oficiais: só estes podem ser pesquisados, e só links destes passam.
    dominios: tuple[str, ...]


# Os mercados que a pessoa pode escolher (só Portugal, por agora). A chave é a que vem do frontend.
MERCADOS: dict[str, Mercado] = {
    "pingo_doce": Mercado("Pingo Doce", ("pingodoce.pt",)),
    "continente": Mercado("Continente", ("continente.pt",)),
    "auchan": Mercado("Auchan", ("auchan.pt",)),
    "lidl": Mercado("Lidl", ("lidl.pt",)),
    "intermarche": Mercado("Intermarché", ("intermarche.pt",)),
    "minipreco": Mercado("Minipreço", ("minipreco.pt",)),
}

# Tetos do que a IA devolve. Um preço de supermercado nunca chega perto disto: acima, é um erro de leitura.
PRECO_MAXIMO = 10_000
MAX_EMBALAGENS = 100
# Tamanho dos textos que vêm da IA (o resto corta-se) e número máximo de achados aceites.
MAX_CARACTERES_PEDIDO = 200
MAX_CARACTERES_PRODUTO = 200
MAX_CARACTERES_NOTA = 300
MAX_CARACTERES_LINK = 500
MAX_ITENS = 150

ENDERECO_MAPA = "https://www.google.com/maps/search/?api=1&query="


def mapa_url(nome_mercado: str) -> str:
    """O link do Google Maps para procurar o mercado (construído aqui, nunca vem da IA)."""
    return ENDERECO_MAPA + quote_plus(nome_mercado)


def _sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(letra for letra in decomposto if not unicodedata.combining(letra)).casefold()


def _chave_do_texto(texto: str) -> str:
    """Para comparar nomes: sem acentos, sem maiúsculas, só letras e números ("Pingo-Doce" = "pingo doce")."""
    return "".join(letra for letra in _sem_acentos(texto) if letra.isalnum())


def mercado_do_nome(nome: object, escolhidos: list[str]) -> str | None:
    """A chave do mercado escolhido a que o nome devolvido pela IA corresponde, ou None.

    Aceita o nome ("Pingo Doce", "pingo doce", "Intermarche") ou a própria chave ("pingo_doce").
    Um mercado que a pessoa não escolheu nunca passa.
    """
    if not isinstance(nome, str):
        return None
    procurado = _chave_do_texto(nome)
    for chave in escolhidos:
        if procurado in (_chave_do_texto(chave), _chave_do_texto(MERCADOS[chave].nome)):
            return chave
    return None


def link_seguro(link: object, chave_mercado: str) -> str:
    """O link se for https e do site do mercado (o domínio ou um subdomínio dele); senão "".

    Recusa também links com utilizador e palavra-passe ("https://pingodoce.pt@outro.site"), com porta,
    com espaços ou caracteres de controlo, e links compridos demais.
    """
    if not isinstance(link, str) or not link or len(link) > MAX_CARACTERES_LINK:
        return ""
    # Só caracteres ASCII visíveis, e nunca "\\": o browser lê "https://mau.site\.pingodoce.pt" como
    # "https://mau.site/.pingodoce.pt" (outro site), enquanto o Python vê um anfitrião que acaba em .pingodoce.pt.
    if any(letra.isspace() or not 33 <= ord(letra) <= 126 or letra == "\\" for letra in link):
        return ""
    try:
        partes = urlsplit(link)
        porta = partes.port
    except ValueError:
        return ""
    if partes.scheme != "https" or partes.username is not None or partes.password is not None or porta is not None:
        return ""
    anfitriao = (partes.hostname or "").rstrip(".")
    for dominio in MERCADOS[chave_mercado].dominios:
        if anfitriao == dominio or anfitriao.endswith("." + dominio):
            # Devolve o link refeito a partir das partes já lidas (e não o texto que veio).
            return urlunsplit(("https", anfitriao, partes.path, partes.query, partes.fragment))
    return ""


def _preco(valor: object) -> float | None:
    """Um preço aceite (número finito, de 0 a PRECO_MAXIMO, sem incluir o teto) ou None."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if not math.isfinite(valor) or valor < 0 or valor >= PRECO_MAXIMO:
        return None
    return float(valor)


def _embalagens(valor: object) -> int | None:
    """Embalagens aceites (inteiro de 1 a MAX_EMBALAGENS) ou None. 2.0 conta como 2; 2.5 não."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if isinstance(valor, float) and (not math.isfinite(valor) or not valor.is_integer()):
        return None
    valor = int(valor)
    return valor if 1 <= valor <= MAX_EMBALAGENS else None


def _texto(valor: object, maximo: int) -> str:
    return valor.strip()[:maximo] if isinstance(valor, str) else ""


# Endereços escritos como texto ("visita www.x.com", "https://..."): numa nota vinda de uma página, podiam
# levar a pessoa a outro site. Tiram-se (os links verdadeiros vão no campo link, já filtrado).
_ENDERECO_EM_TEXTO = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)


def _nota(valor: object) -> str:
    return _ENDERECO_EM_TEXTO.sub("", _texto(valor, MAX_CARACTERES_NOTA)).strip()


def limpar_itens(itens_ia: object, escolhidos: list[str]) -> list[dict]:
    """Os achados da IA, limpos: só dos mercados escolhidos, com preços e links seguros, no formato da API.

    Um achado com preço ou embalagens fora dos limites conta como "sem preço" (encontrado False, preços 0).
    O preco_total é sempre preco_embalagem x embalagens, calculado aqui.
    """
    if not isinstance(itens_ia, list):
        return []
    limpos = []
    for item in itens_ia[:MAX_ITENS]:
        if not isinstance(item, dict):
            continue
        chave = mercado_do_nome(item.get("mercado"), escolhidos)
        pedido = _texto(item.get("pedido"), MAX_CARACTERES_PEDIDO)
        if chave is None or not pedido:
            continue
        preco = _preco(item.get("preco_embalagem"))
        embalagens = _embalagens(item.get("embalagens"))
        encontrado = item.get("encontrado") is True and preco is not None and preco > 0 and embalagens is not None
        preco = round(preco, 2) if encontrado else 0.0
        limpos.append(
            {
                "pedido": pedido,
                "mercado": MERCADOS[chave].nome,
                "encontrado": encontrado,
                "produto": _texto(item.get("produto"), MAX_CARACTERES_PRODUTO) if encontrado else "",
                "preco_embalagem": preco,
                "embalagens": embalagens if encontrado else 0,
                "preco_total": round(preco * embalagens, 2) if encontrado else 0.0,
                "link": link_seguro(item.get("link"), chave) if encontrado else "",
                "nota": _nota(item.get("nota")),
            }
        )
    return limpos


def calcular_plano(itens: list[dict], escolhidos: list[str], orcamento: float) -> dict:
    """O plano de compras a partir dos achados já limpos (limpar_itens).

    Para cada produto pedido escolhe-se o achado mais barato (empate: o mercado escolhido primeiro).
    Os produtos agrupam-se pelo texto do pedido, sem maiúsculas nem acentos. Devolve itens, plano (por mercado,
    pela ordem escolhida, só os que têm alguma coisa), total, orcamento, diferenca (orçamento - total) e
    sem_preco (os pedidos sem nenhum preço encontrado).
    """
    nomes = [MERCADOS[chave].nome for chave in escolhidos]
    ordem_mercado = {nome: posicao for posicao, nome in enumerate(nomes)}

    por_pedido: dict[str, list[dict]] = {}
    for item in itens:
        por_pedido.setdefault(_chave_do_texto(item["pedido"]) or item["pedido"], []).append(item)

    escolhas: list[dict] = []
    sem_preco: list[str] = []
    for opcoes in por_pedido.values():
        validas = [opcao for opcao in opcoes if opcao["encontrado"] and opcao["preco_total"] > 0]
        if not validas:
            sem_preco.append(opcoes[0]["pedido"])
            continue
        escolhas.append(min(validas, key=lambda opcao: (opcao["preco_total"], ordem_mercado.get(opcao["mercado"], 99))))

    plano = []
    for nome in nomes:
        do_mercado = [escolha for escolha in escolhas if escolha["mercado"] == nome]
        if not do_mercado:
            continue
        plano.append(
            {
                "mercado": nome,
                "total": round(sum(escolha["preco_total"] for escolha in do_mercado), 2),
                "itens": [
                    {campo: escolha[campo] for campo in ("pedido", "produto", "embalagens", "preco_total", "link")}
                    for escolha in do_mercado
                ],
                "mapa_url": mapa_url(nome),
            }
        )

    total = round(sum(mercado["total"] for mercado in plano), 2)
    return {
        "itens": itens,
        "plano": plano,
        "total": total,
        "orcamento": round(orcamento, 2),
        "diferenca": round(orcamento - total, 2),
        "sem_preco": sem_preco,
    }
