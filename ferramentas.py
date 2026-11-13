"""Ferramentas que a IA pode pedir no chat.

A IA escolhe a ferramenta e os parâmetros (por exemplo, o mês). O user_id vem
sempre do token e é este código que o junta: a IA nunca o vê nem o escolhe.
O plano também vem do servidor: é ele que diz até que mês as ferramentas podem ver
(meses_historico em limites.py).

As ferramentas de proposta (propor_nova_movimentacao, propor_alteracao, propor_apagar) NUNCA gravam:
validam tudo no servidor e juntam a proposta à lista do pedido (PropostasDoPedido). Quem grava é a pessoa,
ao carregar "Confirmar" no cartão, pelas rotas de sempre (POST, PATCH e DELETE /transacoes).
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import get_args

from pydantic import ValidationError

from consultas import (
    MAX_AMOSTRA_MOVIMENTOS,
    contar_transacoes,
    gastos_de_varios_meses,
    gastos_do_mes,
    movimentos_entre,
    resumir_movimentos,
    transacao_do_utilizador,
)
from ia import PedidoInvalido
from limites import (
    MAX_APAGAR_POR_RESPOSTA,
    MAX_PROPOSTAS_POR_RESPOSTA,
    MAX_TRANSACOES_POR_CONTA,
    config_ia_do_plano,
    hoje_em_lisboa,
    primeiro_mes_visivel,
)
from mensagens import Local
from models import (
    MAX_CARACTERES_NOTA,
    AlteracaoProposta,
    Categoria,
    MetodoPagamento,
    MovimentoNaProposta,
    NovaMovimentacao,
    PropostaChat,
    TransacaoAtualizar,
    metodo_do_pais,
    numa_linha,
)
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
            "Procura movimentos pela descrição ou pela nota pessoal (termos) e/ou pela categoria entre mes_inicio "
            f"e mes_fim (os dois incluídos, no máximo {MAX_MESES_POR_CHAMADA} meses). Basta um dos termos aparecer "
            "na descrição ou na nota (sem contar acentos nem maiúsculas); com categoria e termos, têm de coincidir "
            "os dois. Devolve total_saidas e total_entradas em euros, n_movimentos, uma amostra dos "
            f"{MAX_AMOSTRA_MOVIMENTOS} de maior valor (com a nota, se a pessoa escreveu uma) e quantos ficaram "
            "de fora (restantes). "
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
                    "description": "Palavras a procurar na descrição e na nota, por exemplo [\"gasolina\", \"portagens\"].",
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


# --- Ferramentas de proposta (só fora da demo; ver ferramentas_para) ---

METODOS = list(get_args(MetodoPagamento))
MAX_CARACTERES_DESCRICAO_NOVA = 200  # igual a NovaMovimentacao.descricao
_ID_TRANSACAO = {
    "type": "integer",
    "minimum": 1,
    "description": "O id da movimentação, tal como veio na amostra de procurar_movimentos.",
}
_AVISO_PROPOSTA = (
    "Não grava nada: prepara uma proposta que o utilizador tem de confirmar num cartão. "
    "Usa só quando o utilizador o pede na pergunta atual."
)

FERRAMENTAS_PROPOSTAS = [
    {
        "name": "propor_nova_movimentacao",
        "description": (
            "Propõe criar uma movimentação nova (por exemplo um pagamento em dinheiro que não está no extrato). "
            "valor em euros: negativo para gastos, positivo para entradas. Se o utilizador não disser a categoria, "
            "escolhe a mais provável. " + _AVISO_PROPOSTA
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data no formato AAAA-MM-DD, por exemplo 2026-11-03."},
                "descricao": {"type": "string", "minLength": 1, "maxLength": MAX_CARACTERES_DESCRICAO_NOVA},
                "valor": {"type": "number"},
                "metodo_pagamento": {"type": "string", "enum": METODOS},
                "categoria": {"type": "string", "enum": CATEGORIAS},
                "nota": {"type": "string", "maxLength": MAX_CARACTERES_NOTA},
            },
            "required": ["data", "descricao", "valor", "metodo_pagamento"],
            "additionalProperties": False,
        },
    },
    {
        "name": "propor_alteracao",
        "description": (
            "Propõe mudar a categoria e/ou a nota pessoal de uma movimentação (a descrição, o valor e a data "
            "não mudam). nota vazia apaga a nota. " + _AVISO_PROPOSTA
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transacao_id": _ID_TRANSACAO,
                "categoria": {"type": "string", "enum": CATEGORIAS},
                "nota": {"type": "string", "maxLength": MAX_CARACTERES_NOTA},
            },
            "required": ["transacao_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "propor_apagar",
        "description": "Propõe apagar uma movimentação (só uma de cada vez). " + _AVISO_PROPOSTA,
        "input_schema": {
            "type": "object",
            "properties": {"transacao_id": _ID_TRANSACAO},
            "required": ["transacao_id"],
            "additionalProperties": False,
        },
    },
]
NOMES_PROPOSTAS = {ferramenta["name"] for ferramenta in FERRAMENTAS_PROPOSTAS}

# O que a IA recebe quando a proposta fica registada (sem repetir os dados: o cartão mostra-os).
PROPOSTA_REGISTADA = "proposta registada; o utilizador tem de confirmar no cartão. Ainda não foi feito nada."


@dataclass
class PropostasDoPedido:
    """As propostas de um pedido ao chat (uma pergunta). Vivem só durante o pedido; nada vai para a base de dados.

    pais: onde a pessoa vive (métodos de pagamento do país). ids_vistos: os ids que procurar_movimentos mostrou
    neste pedido; só esses se podem alterar ou apagar (a IA não aponta para ids que adivinhou ou leu num texto).
    """

    pais: str = "PT"
    lista: list[PropostaChat] = field(default_factory=list)
    ids_vistos: set[int] = field(default_factory=set)


def _trocar_nas_descricoes(valor, trocas: dict[str, str]):
    """Uma cópia de valor (dicts, listas e textos das ferramentas) com as trocas feitas em todos os textos."""
    if isinstance(valor, dict):
        return {chave: _trocar_nas_descricoes(item, trocas) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_trocar_nas_descricoes(item, trocas) for item in valor]
    if isinstance(valor, str):
        for antes, depois in trocas.items():
            valor = valor.replace(antes, depois)
    return valor


def _propostas_do_pais(pais: str) -> list[dict]:
    """As ferramentas de proposta com só os métodos de pagamento do país (sem MB Way no BR, sem Pix em PT)."""
    metodos = [metodo for metodo in METODOS if metodo_do_pais(metodo, pais)]
    nova, *resto = FERRAMENTAS_PROPOSTAS
    propriedades = nova["input_schema"]["properties"]
    nova = {
        **nova,
        "input_schema": {
            **nova["input_schema"],
            "properties": {**propriedades, "metodo_pagamento": {**propriedades["metodo_pagamento"], "enum": metodos}},
        },
    }
    return [nova, *resto]


def ferramentas_para(local: Local | None = None, com_propostas: bool = False) -> list[dict]:
    """As ferramentas do chat para o país e a moeda da conta.

    PT/EUR sem propostas: a lista FERRAMENTAS tal e qual (a mesma de sempre).
    Moeda BRL: os valores são "em reais". Quem vive no Brasil: os exemplos de termos com palavras de lá.
    Os nomes, os parâmetros e as categorias (chaves internas) nunca mudam.
    com_propostas: junta no fim as ferramentas de proposta (nunca na demo, que é só de leitura).
    """
    local = local or Local()
    trocas = {}
    if local.moeda == "BRL":
        trocas["em euros"] = "em reais"
    if local.pais == "BR":
        trocas['["gasolina", "portagens"]'] = '["gasolina", "pedágio"]'
    lista = FERRAMENTAS + _propostas_do_pais(local.pais) if com_propostas else FERRAMENTAS
    return _trocar_nas_descricoes(lista, trocas) if trocas else lista


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


# --- Propostas: validam tudo e NÃO gravam ---


def _erros_de_validacao(erro: ValidationError) -> str:
    """Os erros do Pydantic numa frase curta, para a IA corrigir (sem repetir o valor que ela mandou)."""
    return "; ".join(f"{'.'.join(str(parte) for parte in e['loc']) or 'pedido'}: {e['msg']}" for e in erro.errors())


def _validar_id(valor: object) -> int:
    """O id de uma movimentação: um inteiro positivo dentro de um BIGINT (True e 1.5 não contam)."""
    if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 2**63 - 1:
        raise PedidoInvalido("transacao_id tem de ser o id (número inteiro) de uma movimentação da procura.")
    return valor


def _exigir_espaco_para_proposta(propostas: PropostasDoPedido) -> None:
    if len(propostas.lista) >= MAX_PROPOSTAS_POR_RESPOSTA:
        raise PedidoInvalido(
            f"no máximo {MAX_PROPOSTAS_POR_RESPOSTA} propostas por resposta. Para mudar muitas movimentações, "
            "o utilizador tem de usar a página Movimentações."
        )


def _movimento_da_conta(user_id: str, argumentos: dict, propostas: PropostasDoPedido) -> MovimentoNaProposta:
    """A movimentação lida da base de dados pelo id E pelo dono do pedido (nunca de outra conta).

    Só ids que procurar_movimentos mostrou neste pedido; de outra conta ou inexistente: o mesmo erro.
    """
    transacao_id = _validar_id(argumentos.get("transacao_id"))
    if transacao_id not in propostas.ids_vistos:
        raise PedidoInvalido("usa primeiro procurar_movimentos para encontrar a movimentação e usa o id que lá vem.")
    if any(p.movimento is not None and p.movimento.id == transacao_id for p in propostas.lista):
        raise PedidoInvalido("já há uma proposta para esta movimentação nesta resposta.")
    linha = transacao_do_utilizador(user_id, transacao_id)
    if linha is None:
        raise PedidoInvalido("não existe nenhuma movimentação com esse id nesta conta.")
    return MovimentoNaProposta(**linha)


def _propor_nova(user_id: str, argumentos: dict, propostas: PropostasDoPedido) -> PropostaChat:
    valor = argumentos.get("valor")
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise PedidoInvalido("valor tem de ser um número (negativo para gastos, positivo para entradas).")
    descricao = argumentos.get("descricao")
    campos = {
        "data": argumentos.get("data"),
        # Numa só linha e sem caracteres de controlo, como a nota (o cartão mostra-a tal e qual).
        "descricao": numa_linha(descricao) if isinstance(descricao, str) else descricao,
        "valor": valor,
        "metodo_pagamento": argumentos.get("metodo_pagamento"),
        # Sem categoria, "outros": confirmar nunca pode chamar a IA para categorizar. A pessoa vê-a no cartão.
        "categoria": argumentos.get("categoria") or "outros",
        "nota": argumentos.get("nota"),
    }
    try:
        # O mesmo modelo da rota POST /transacoes: data válida, descrição, teto do valor (sem NaN), método e categoria.
        nova = NovaMovimentacao(**campos)
    except ValidationError as erro:
        raise PedidoInvalido(f"proposta inválida ({_erros_de_validacao(erro)}).")
    if not metodo_do_pais(nova.metodo_pagamento, propostas.pais):
        raise PedidoInvalido(f"o método {nova.metodo_pagamento} não existe no país do utilizador.")
    novas_pendentes = sum(1 for p in propostas.lista if p.tipo == "criar")
    if contar_transacoes(user_id) + novas_pendentes + 1 > MAX_TRANSACOES_POR_CONTA:
        raise PedidoInvalido("a conta já chegou ao máximo de movimentações; não dá para criar mais.")
    return PropostaChat(tipo="criar", nova=nova)


def _propor_alteracao(user_id: str, argumentos: dict, propostas: PropostasDoPedido) -> PropostaChat:
    campos = {chave: argumentos[chave] for chave in ("categoria", "nota") if chave in argumentos}
    try:
        # O mesmo modelo da rota PATCH /transacoes/{id}: categoria das permitidas e/ou nota (até 300 caracteres).
        alteracao = TransacaoAtualizar(**campos)
    except ValidationError as erro:
        raise PedidoInvalido(f"proposta inválida ({_erros_de_validacao(erro)}).")
    movimento = _movimento_da_conta(user_id, argumentos, propostas)
    alteracoes = alteracao.alteracoes()
    # Antes da sql/025 a linha vem sem a chave nota: o PATCH com nota daria 503 ao confirmar.
    if "nota" in alteracoes and "nota" not in movimento.model_fields_set:
        raise PedidoInvalido("as notas ainda não estão disponíveis; só a categoria pode mudar.")
    muda_categoria = "categoria" in alteracoes and alteracoes["categoria"] != movimento.categoria
    muda_nota = "nota" in alteracoes and alteracoes["nota"] != movimento.nota
    if not muda_categoria and not muda_nota:
        raise PedidoInvalido("a movimentação já está assim; não há nada para mudar.")
    return PropostaChat(
        tipo="alterar",
        movimento=movimento,
        alteracao=AlteracaoProposta(
            categoria=alteracoes["categoria"] if muda_categoria else None,
            muda_nota=muda_nota,
            nota=alteracoes.get("nota") if muda_nota else None,
        ),
    )


def _propor_apagar(user_id: str, argumentos: dict, propostas: PropostasDoPedido) -> PropostaChat:
    if sum(1 for p in propostas.lista if p.tipo == "apagar") >= MAX_APAGAR_POR_RESPOSTA:
        raise PedidoInvalido("só se apaga uma movimentação de cada vez; o utilizador confirma esta e pede a seguinte.")
    return PropostaChat(tipo="apagar", movimento=_movimento_da_conta(user_id, argumentos, propostas))


_PROPOR = {
    "propor_nova_movimentacao": _propor_nova,
    "propor_alteracao": _propor_alteracao,
    "propor_apagar": _propor_apagar,
}


def _registar_proposta(nome: str, argumentos: dict, user_id: str, propostas: PropostasDoPedido) -> dict:
    """Valida a proposta e junta-a à lista do pedido. Inválida: PedidoInvalido (volta à IA, sem proposta)."""
    _exigir_espaco_para_proposta(propostas)
    proposta = _PROPOR[nome](user_id, argumentos, propostas)
    propostas.lista.append(proposta)
    # Só o tipo, sem dados da conta.
    print(f"Chat: proposta '{proposta.tipo}' registada (por confirmar).")
    return {"resultado": PROPOSTA_REGISTADA}


def executar_ferramenta(
    nome: str,
    argumentos: dict,
    user_id: str,
    plano: str | None,
    hoje: date | None = None,
    propostas: PropostasDoPedido | None = None,
) -> str:
    """Corre a ferramenta pedida pela IA e devolve o resultado como texto JSON.

    user_id vem sempre do token e plano do servidor (nunca da IA nem do browser).
    hoje: a data no país onde o utilizador vive (limites.hoje_do_utilizador); sem ela, a de Lisboa.
    propostas: a lista de propostas do pedido. Sem ela (demo), as ferramentas de proposta não existem.
    """
    if nome in NOMES_PROPOSTAS:
        if propostas is None:
            raise PedidoInvalido(f"Ferramenta desconhecida: {nome}")
        return json.dumps(_registar_proposta(nome, argumentos, user_id, propostas), ensure_ascii=False)

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
        # Os ids mostrados à IA: só estes se podem propor alterar ou apagar neste pedido.
        if propostas is not None:
            propostas.ids_vistos.update(m["id"] for m in resultado.get("amostra", []) if m.get("id") is not None)
    else:
        raise PedidoInvalido(f"Ferramenta desconhecida: {nome}")
    return json.dumps(resultado, ensure_ascii=False)
