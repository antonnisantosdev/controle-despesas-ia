"""Ferramentas que a IA pode pedir no chat.

A IA escolhe a ferramenta e os parâmetros (por exemplo, o mês). O user_id vem
sempre do token e é este código que o junta: a IA nunca o vê nem o escolhe.
O plano também vem do servidor: é ele que diz até que mês as ferramentas podem ver
(meses_historico em limites.py).
"""

import json
import re
from datetime import date
from typing import get_args

from consultas import (
    MAX_AMOSTRA_MOVIMENTOS,
    gastos_de_varios_meses,
    gastos_do_mes,
    movimentos_entre,
    resumir_movimentos,
)
from ia import PedidoInvalido
from limites import config_ia_do_plano, hoje_em_lisboa, primeiro_mes_visivel
from models import Categoria
from objetivos import listar_objetivos
from orcamento import planeamento_do_mes

# Meses máximos que gastos_de_varios_meses devolve numa chamada: um ano. Mais do que isso
# enchia o prompt (e o custo) sem ajudar a responder; a IA pode pedir outro intervalo.
MAX_MESES_POR_CHAMADA = 12

# Limites dos termos de procurar_movimentos: poucos termos curtos chegam (sinónimos de um tema).
MAX_TERMOS = 5
MIN_CARACTERES_TERMO = 2
MAX_CARACTERES_TERMO = 40
CATEGORIAS = list(get_args(Categoria))
TIPOS_DE_MOVIMENTO = ["saidas", "entradas", "todos"]

NOMES_DOS_PLANOS = {"free": "Free", "essencial": "Essencial", "completo": "Completo"}

_PROPRIEDADE_MES = {"type": "string", "description": "Mês no formato AAAA-MM, por exemplo 2026-10."}

# A lista que a IA recebe: o nome, para que serve (a IA decide com base nisto)
# e os parâmetros que aceita, descritos em JSON Schema.
FERRAMENTAS = [
    {
        "name": "gastos_por_categoria",
        "description": (
            "Devolve quanto o utilizador gastou em cada categoria num mês, em euros, "
            "do maior gasto para o menor. Usa para perguntas sobre gastos de um mês "
            "ou de uma categoria num mês."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"mes": _PROPRIEDADE_MES},
            "required": ["mes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "gastos_de_varios_meses",
        "description": (
            "Devolve os gastos por categoria, em euros, de cada mês entre mes_inicio e mes_fim "
            f"(os dois incluídos, no máximo {MAX_MESES_POR_CHAMADA} meses por chamada). "
            "Usa para comparar meses, ver a evolução de uma categoria ou somar vários meses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"mes_inicio": _PROPRIEDADE_MES, "mes_fim": _PROPRIEDADE_MES},
            "required": ["mes_inicio", "mes_fim"],
            "additionalProperties": False,
        },
    },
    {
        "name": "orcamentos_do_mes",
        "description": (
            "Devolve o orçamento mensal (limite) de cada categoria e quanto já se gastou nesse mês, em euros. "
            "limite vem vazio nas categorias com gastos mas sem orçamento. Usa para perguntas sobre "
            "orçamentos, sobre quanto falta gastar ou sobre categorias que passaram o limite."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"mes": _PROPRIEDADE_MES},
            "required": ["mes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "objetivos_de_poupanca",
        "description": (
            "Devolve os objetivos de poupança do utilizador: nome, valor alvo, valor já poupado e data alvo, "
            "do prazo mais próximo para o mais distante. Usa para perguntas sobre objetivos e poupança."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "procurar_movimentos",
        "description": (
            "Procura movimentos pela descrição (termos) e/ou pela categoria entre mes_inicio e mes_fim "
            f"(os dois incluídos, no máximo {MAX_MESES_POR_CHAMADA} meses). Basta um dos termos aparecer na "
            "descrição (sem contar acentos nem maiúsculas); com categoria e termos, têm de coincidir os dois. "
            "Devolve total_saidas e total_entradas em euros, n_movimentos, uma amostra dos "
            f"{MAX_AMOSTRA_MOVIMENTOS} de maior valor e quantos ficaram de fora (restantes). "
            "Usa para perguntas sobre um tema, uma loja ou uma pessoa "
            "(por exemplo carros, Netflix, transferências para a Rita)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mes_inicio": _PROPRIEDADE_MES,
                "mes_fim": _PROPRIEDADE_MES,
                "termos": {
                    "type": "array",
                    "items": {"type": "string", "minLength": MIN_CARACTERES_TERMO, "maxLength": MAX_CARACTERES_TERMO},
                    "maxItems": MAX_TERMOS,
                    "description": "Palavras a procurar na descrição, por exemplo [\"gasolina\", \"portagens\"].",
                },
                "categoria": {"type": "string", "enum": CATEGORIAS},
                "tipo": {
                    "type": "string",
                    "enum": TIPOS_DE_MOVIMENTO,
                    "description": "saidas (gastos), entradas (dinheiro recebido) ou todos. Por omissão, todos.",
                },
            },
            "required": ["mes_inicio", "mes_fim"],
            "additionalProperties": False,
        },
    },
]

_FORMATO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validar_mes(mes: object) -> str:
    """O mês, se estiver no formato AAAA-MM. Senão, um erro que volta para a IA corrigir o pedido."""
    if not isinstance(mes, str) or not _FORMATO_MES.match(mes):
        raise PedidoInvalido(f"mês inválido: {mes!r}. Usa o formato AAAA-MM, por exemplo 2026-10.")
    return mes


def meses_entre(primeiro: str, ultimo: str) -> list[str]:
    """Todos os meses de primeiro a ultimo, os dois incluídos: ("2026-11", "2027-01") -> 3 meses."""
    inicio = int(primeiro[:4]) * 12 + int(primeiro[5:]) - 1
    fim = int(ultimo[:4]) * 12 + int(ultimo[5:]) - 1
    return [f"{absoluto // 12:04d}-{absoluto % 12 + 1:02d}" for absoluto in range(inicio, fim + 1)]


def _fora_do_historico(plano: str | None, primeiro: str) -> dict:
    """A resposta para meses que o plano não vê. A IA usa-a para explicar e sugerir mudar de plano."""
    nome = NOMES_DOS_PLANOS.get(plano or "", "Free")
    return {
        "fora_do_historico": True,
        "mensagem": (
            f"O plano {nome} do utilizador só mostra dados desde {primeiro}. "
            "Para ver meses mais antigos, pode mudar para um plano com mais histórico."
        ),
    }


def _gastos_por_categoria(user_id: str, mes: str) -> list[dict]:
    return [gasto.model_dump() for gasto in gastos_do_mes(user_id, mes)]


def _meses_no_historico(plano: str | None, primeiro: str | None, inicio: str, fim: str) -> tuple[list[str], dict]:
    """Os meses do intervalo que o plano vê e o início da resposta (com aviso, se o intervalo foi cortado).

    Se o plano não vê nenhum dos meses, a lista vem vazia e a resposta é a de fora do histórico.
    """
    if inicio > fim:
        raise PedidoInvalido("mes_inicio tem de ser igual ou anterior a mes_fim.")
    if primeiro and fim < primeiro:
        return [], _fora_do_historico(plano, primeiro)
    resultado: dict = {}
    # Um intervalo que começa antes do que o plano vê é cortado, com um aviso para a IA explicar.
    if primeiro and inicio < primeiro:
        inicio = primeiro
        resultado["aviso"] = _fora_do_historico(plano, primeiro)["mensagem"]
    meses = meses_entre(inicio, fim)
    if len(meses) > MAX_MESES_POR_CHAMADA:
        raise PedidoInvalido(f"no máximo {MAX_MESES_POR_CHAMADA} meses por chamada; pede um intervalo mais curto.")
    return meses, resultado


def _gastos_de_varios_meses(user_id: str, plano: str | None, primeiro: str | None, inicio: str, fim: str) -> dict:
    meses, resultado = _meses_no_historico(plano, primeiro, inicio, fim)
    if not meses:
        return resultado
    gastos = gastos_de_varios_meses(user_id, meses)
    resultado["meses"] = {mes: [gasto.model_dump() for gasto in lista] for mes, lista in gastos.items()}
    return resultado


def _validar_termos(termos: object) -> list[str]:
    """Os termos de procura (0 a 5, cada um com 2 a 40 caracteres). Senão, um erro para a IA corrigir."""
    if termos is None:
        return []
    if not isinstance(termos, list) or len(termos) > MAX_TERMOS:
        raise PedidoInvalido(f"termos tem de ser uma lista com no máximo {MAX_TERMOS} palavras.")
    limpos = []
    for termo in termos:
        if not isinstance(termo, str) or not MIN_CARACTERES_TERMO <= len(termo.strip()) <= MAX_CARACTERES_TERMO:
            raise PedidoInvalido(
                f"cada termo tem de ter entre {MIN_CARACTERES_TERMO} e {MAX_CARACTERES_TERMO} caracteres."
            )
        limpos.append(termo.strip())
    return limpos


def _procurar_movimentos(user_id: str, plano: str | None, primeiro: str | None, argumentos: dict) -> dict:
    inicio = _validar_mes(argumentos.get("mes_inicio"))
    fim = _validar_mes(argumentos.get("mes_fim"))
    termos = _validar_termos(argumentos.get("termos"))
    categoria = argumentos.get("categoria")
    if categoria is not None and categoria not in CATEGORIAS:
        raise PedidoInvalido(f"categoria inválida: {categoria!r}. Usa uma destas: {', '.join(CATEGORIAS)}.")
    tipo = argumentos.get("tipo") or "todos"
    if tipo not in TIPOS_DE_MOVIMENTO:
        raise PedidoInvalido(f"tipo inválido: {tipo!r}. Usa saidas, entradas ou todos.")
    if not termos and categoria is None:
        raise PedidoInvalido("indica pelo menos termos ou categoria.")

    meses, resultado = _meses_no_historico(plano, primeiro, inicio, fim)
    if not meses:
        return resultado
    linhas = movimentos_entre(user_id, meses[0], meses[-1], categoria, tipo)
    return resultado | resumir_movimentos(linhas, termos, categoria, tipo)


def executar_ferramenta(
    nome: str, argumentos: dict, user_id: str, plano: str | None, hoje: date | None = None
) -> str:
    """Corre a ferramenta pedida pela IA e devolve o resultado como texto JSON.

    user_id vem sempre do token e plano do servidor (nunca da IA nem do browser).
    hoje: a data no país onde o utilizador vive (limites.hoje_do_utilizador); sem ela, a de Lisboa.
    """
    primeiro = primeiro_mes_visivel(config_ia_do_plano(plano), hoje or hoje_em_lisboa())

    if nome == "gastos_por_categoria":
        mes = _validar_mes(argumentos.get("mes"))
        resultado = _fora_do_historico(plano, primeiro) if primeiro and mes < primeiro else _gastos_por_categoria(user_id, mes)
    elif nome == "gastos_de_varios_meses":
        inicio = _validar_mes(argumentos.get("mes_inicio"))
        fim = _validar_mes(argumentos.get("mes_fim"))
        resultado = _gastos_de_varios_meses(user_id, plano, primeiro, inicio, fim)
    elif nome == "orcamentos_do_mes":
        mes = _validar_mes(argumentos.get("mes"))
        if primeiro and mes < primeiro:
            resultado = _fora_do_historico(plano, primeiro)
        else:
            resultado = [linha.model_dump() for linha in planeamento_do_mes(user_id, mes)]
    elif nome == "objetivos_de_poupanca":
        resultado = [objetivo.model_dump(mode="json") for objetivo in listar_objetivos(user_id)]
    elif nome == "procurar_movimentos":
        resultado = _procurar_movimentos(user_id, plano, primeiro, argumentos)
    else:
        raise PedidoInvalido(f"Ferramenta desconhecida: {nome}")
    return json.dumps(resultado, ensure_ascii=False)
