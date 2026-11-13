"""Demo para recrutadores: uma conta partilhada, só de leitura, com dados inventados.

- POST /demo (main.py) entrega um token próprio (JWT HS256, 60 minutos, sem renovação), assinado
  com o DEMO_TOKEN_SEGREDO. Não tem email nem dados pessoais: só o id da conta de demo.
- O obter_utilizador_atual (auth.py) aceita esse token e só deixa a conta de demo usar as rotas
  da lista PERMISSOES_DEMO (ver e conversar). As outras respondem 423.
- Limites por IP, na memória do servidor, para ninguém gastar os pedidos à IA partilhados.
- No primeiro POST /demo de cada semana, os dados da conta voltam ao estado inicial (dados_demo.py).

A configuração vem do .env: DEMO_TOKEN_SEGREDO, DEMO_USER_ID e DEMO_EMAIL. Sem ela, a demo fica desligada.
"""

import ipaddress
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, Request

from dados_demo import (
    compras_demo,
    hash_da_marca,
    marca_demo,
    objetivos_demo,
    orcamentos_demo,
    semana_iso,
    transacoes_demo,
)
from database import supabase
from limite_ip import (
    DIA,
    HORA,
    LimitePorIP,
    _entradas_encaminhadas,
    _relogio,
    ip_do_pedido,
    prefixo_48_do_ipv6,
)
from limites import hoje_em_lisboa

# --- Configuração ---

# O segredo do token tem de ser comprido: com HS256, um segredo curto adivinha-se.
MIN_CARACTERES_SEGREDO = 32
# Um UUID como os do Supabase ("1b4e28ba-2fa1-11d2-883f-0016d3cca427").
FORMATO_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@dataclass(frozen=True)
class ConfigDemo:
    """A configuração da demo, lida do .env.

    ligada: só é True com as 3 variáveis válidas. Desligada, POST /demo responde 503 e nenhum token de demo entra.
    user_id: o id da conta de demo, sempre que for um UUID válido (mesmo com a demo desligada):
        serve para bloquear a conta, mesmo que alguém entre nela com o email e a palavra-passe.
    O segredo fica fora do repr, para nunca aparecer nos logs.
    """

    ligada: bool
    user_id: str | None
    email: str = ""
    segredo: str = field(default="", repr=False)


# Os problemas já avisados nos logs: cada um aparece uma só vez (a configuração lê-se em cada pedido).
_AVISOS_DADOS: set[str] = set()


def _avisar_uma_vez(problema: str) -> None:
    if problema not in _AVISOS_DADOS:
        _AVISOS_DADOS.add(problema)
        print(f"AVISO: demo desligada: {problema}.")


def config_demo() -> ConfigDemo:
    """Lê e valida a configuração da demo. Os avisos nos logs dizem o que falta, nunca os valores."""
    segredo = os.getenv("DEMO_TOKEN_SEGREDO", "")
    user_id = os.getenv("DEMO_USER_ID", "").strip().lower()
    email = os.getenv("DEMO_EMAIL", "").strip().lower()

    user_id_valido = user_id if FORMATO_UUID.fullmatch(user_id) else None
    problemas = []
    if len(segredo) < MIN_CARACTERES_SEGREDO:
        problemas.append(f"DEMO_TOKEN_SEGREDO em falta ou com menos de {MIN_CARACTERES_SEGREDO} caracteres")
    if user_id_valido is None:
        problemas.append("DEMO_USER_ID em falta ou não é um UUID")
    if "@" not in email:
        problemas.append("DEMO_EMAIL em falta ou inválido")

    if problemas:
        _avisar_uma_vez("; ".join(problemas))
        return ConfigDemo(ligada=False, user_id=user_id_valido)
    return ConfigDemo(ligada=True, user_id=user_id_valido, email=email, segredo=segredo)



def e_conta_demo(user_id: str | None) -> bool:
    """Se o user_id é o da conta de demo (mesmo com a demo desligada, como no DELETE /conta)."""
    id_demo = config_demo().user_id
    return id_demo is not None and user_id is not None and str(user_id).lower() == id_demo


# --- Token da demo ---

ALGORITMO_TOKEN = "HS256"
AUDIENCIA_TOKEN = "control-prices-demo"
EMISSOR_TOKEN = "control-prices-api"
VALIDADE_TOKEN_MINUTOS = 60
# Folga para relógios ligeiramente desacertados entre servidores.
FOLGA_RELOGIO_SEGUNDOS = 30


def criar_token_demo(config: ConfigDemo, agora: datetime | None = None) -> str:
    """O token da demo: só o id da conta, quem o passou, para quem é e quando acaba. Sem email."""
    agora = agora or datetime.now(timezone.utc)
    dados = {
        "sub": config.user_id,
        "iat": int(agora.timestamp()),
        "exp": int((agora + timedelta(minutes=VALIDADE_TOKEN_MINUTOS)).timestamp()),
        "aud": AUDIENCIA_TOKEN,
        "iss": EMISSOR_TOKEN,
    }
    return jwt.encode(dados, config.segredo, algorithm=ALGORITMO_TOKEN)


def ler_token_demo(token: str, config: ConfigDemo) -> str | None:
    """O "sub" de um token da demo válido, ou None se não for um token da demo (ou estiver estragado ou expirado).

    Só se aceita HS256 com o nosso segredo (nunca "none", HS512 nem RS256), para a nossa audiência e emissor,
    e com todos os campos obrigatórios. None não é erro: quem chama tenta então o token do Supabase.
    """
    try:
        dados = jwt.decode(
            token,
            config.segredo,
            algorithms=[ALGORITMO_TOKEN],
            audience=AUDIENCIA_TOKEN,
            issuer=EMISSOR_TOKEN,
            options={"require": ["sub", "exp", "iat", "aud", "iss"]},
            leeway=FOLGA_RELOGIO_SEGUNDOS,
        )
    except jwt.InvalidTokenError:
        return None
    return str(dados["sub"])


# --- O que a conta de demo pode fazer ---

# (método, caminho da rota no main.py). Tudo o resto responde 423 à conta de demo.
# Só leituras e o chat. As sugestões da IA (orçamento, plano de poupança, resumo do ano) ficam de fora:
# gastariam os pedidos à IA partilhados por todos os visitantes.
PERMISSOES_DEMO: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/eu"),
        ("GET", "/transacoes"),
        ("GET", "/transacoes/sem-categoria/contagem"),
        ("GET", "/transacoes/{transacao_id}"),
        ("GET", "/dashboard/categorias"),
        ("GET", "/dashboard/mensal"),
        ("GET", "/resumo"),
        ("GET", "/orcamentos"),
        ("GET", "/orcamentos/alertas"),
        ("GET", "/recorrentes"),
        ("GET", "/compras"),
        # Preço de um produto por loja: só as leituras (juntar e separar produtos ficam bloqueados).
        ("GET", "/compras/produtos"),
        ("GET", "/compras/produtos/{chave}"),
        ("GET", "/compras/produtos/juntar"),
        # Fazer as minhas compras: o estado e um EXEMPLO FIXO (main.py; sem IA, sem pesquisas e sem contar).
        # Sem custo, por isso sem limite por IP.
        ("GET", "/compras/lista/estado"),
        ("POST", "/compras/lista"),
        ("GET", "/objetivos"),
        ("GET", "/simulador"),
        ("GET", "/plano"),
        # Resumo anual: o JSON e o CSV (a demo é Essencial, pode exportar). O resumo pela IA fica de fora.
        ("GET", "/relatorio"),
        ("GET", "/relatorio/csv"),
        ("POST", "/chat"),
    }
)

# Os textos das respostas da demo são os mesmos do frontend (frontend/src/lib/textosDemo.ts; um teste confirma-o).
MENSAGEM_BLOQUEIO_DEMO = (
    "Isto está desligado na demo. Aqui podes ver os dados e usar o chat. "
    "Para usar a app com os teus dados, cria uma conta grátis."
)
MENSAGEM_DEMO_DESLIGADA = "A demo não está disponível de momento. Tenta mais tarde."


def caminho_da_rota(request: Request) -> str | None:
    """O caminho da rota tal como está no main.py ("/transacoes/{transacao_id}"), não o endereço pedido."""
    rota = request.scope.get("route")
    return getattr(rota, "path", None)


def exigir_permissao_demo(request: Request) -> None:
    """423 se a conta de demo pedir uma rota fora de PERMISSOES_DEMO. Depois, os limites por IP do chat e do resumo."""
    pedido = (request.method, caminho_da_rota(request))
    if pedido not in PERMISSOES_DEMO:
        raise HTTPException(status_code=423, detail=MENSAGEM_BLOQUEIO_DEMO)
    limite = LIMITES_DA_DEMO_POR_ROTA.get(pedido)
    if limite is not None:
        limite.registar(ip_do_pedido(request))


# --- Limites por IP (na memória do servidor; as peças genéricas estão em limite_ip.py) ---


# Quantas vezes já se registou nos logs a forma do X-Forwarded-For neste arranque do servidor.
_VEZES_FORMA_DO_IP = [0]
_MAX_VEZES_FORMA_DO_IP = 3
_CADEADO_FORMA_DO_IP = threading.Lock()


def _tipo_de_entrada(entrada: str) -> str:
    try:
        return "pública" if ipaddress.ip_address(entrada).is_global else "privada"
    except ValueError:
        return "inválida"


def _posicao(valor: str | None, entradas: list[str]) -> str:
    """Em que entrada do X-Forwarded-For está este valor (1 = a mais à esquerda), sem dizer o valor."""
    if not valor:
        return "ausente"
    valor = valor.strip()
    return f"entrada {entradas.index(valor) + 1}" if valor in entradas else "presente, fora da lista"


def registar_forma_do_ip(request: Request) -> None:
    """Nas primeiras vezes de cada arranque, deixa nos logs a forma do X-Forwarded-For, sem IPs:
    quantas entradas, se cada uma é pública ou privada, e em que entrada estão o IP da ligação e os
    cabeçalhos de IP que um proxy à frente pode pôr (CF-Connecting-IP, True-Client-IP, X-Real-IP).
    Serve para saber qual das entradas é o visitante (ver ip_do_pedido).
    """
    with _CADEADO_FORMA_DO_IP:
        if _VEZES_FORMA_DO_IP[0] >= _MAX_VEZES_FORMA_DO_IP:
            return
        _VEZES_FORMA_DO_IP[0] += 1
    entradas = _entradas_encaminhadas(request)
    tipos = ", ".join(_tipo_de_entrada(entrada) for entrada in entradas)
    ligacao = request.client.host if request.client else None
    print(
        f"Demo: X-Forwarded-For com {len(entradas)} entrada(s) [{tipos}]; "
        f"IP da ligação: {_posicao(ligacao, entradas)}; "
        f"CF-Connecting-IP: {_posicao(request.headers.get('cf-connecting-ip'), entradas)}; "
        f"True-Client-IP: {_posicao(request.headers.get('true-client-ip'), entradas)}; "
        f"X-Real-IP: {_posicao(request.headers.get('x-real-ip'), entradas)}; "
        f"IP usado nos limites: {_posicao(ip_do_pedido(request), entradas)}."
    )


# Quando o teto de IPs enche: não diz nada sobre quem pediu nem sobre o limite.
MENSAGEM_DEMO_CHEIA = "A demo está com muitos pedidos neste momento. Tenta outra vez daqui a pouco."

LIMITE_ENTRADAS_DEMO = LimitePorIP(
    10,
    HORA,
    "A demo foi aberta muitas vezes a partir desta rede na última hora. Tenta outra vez mais tarde.",
    mensagem_teto=MENSAGEM_DEMO_CHEIA,
)
# Segundo limite das entradas, só para IPv6: por prefixo /48 (vários /64 da mesma rede).
LIMITE_ENTRADAS_DEMO_48 = LimitePorIP(
    30,
    HORA,
    "A demo foi aberta muitas vezes a partir desta rede na última hora. Tenta outra vez mais tarde.",
    chave=prefixo_48_do_ipv6,
    mensagem_teto=MENSAGEM_DEMO_CHEIA,
)
LIMITE_CHAT_DEMO = LimitePorIP(
    5,
    DIA,
    "As perguntas ao chat da demo acabaram por hoje. Amanhã há mais, "
    "ou cria uma conta grátis para usar o chat com os teus dados.",
    mensagem_teto=MENSAGEM_DEMO_CHEIA,
)
LIMITE_RESUMO_DEMO = LimitePorIP(
    10,
    HORA,
    "O resumo da demo foi pedido muitas vezes a partir desta rede na última hora. Tenta outra vez mais tarde.",
    mensagem_teto=MENSAGEM_DEMO_CHEIA,
)


def registar_entrada_demo(ip: str) -> None:
    """Conta uma entrada na demo (POST /demo): primeiro o limite por /48 (só IPv6), depois o por IP (/64 no IPv6)."""
    LIMITE_ENTRADAS_DEMO_48.registar(ip)
    LIMITE_ENTRADAS_DEMO.registar(ip)


LIMITES_DA_DEMO_POR_ROTA: dict[tuple[str, str], LimitePorIP] = {
    ("POST", "/chat"): LIMITE_CHAT_DEMO,
    ("GET", "/resumo"): LIMITE_RESUMO_DEMO,
}


# --- Reposição dos dados inventados (uma vez por semana) ---

# As tabelas que a reposição apaga e volta a preencher. As compras e os produtos vão com as transações
# (ON DELETE CASCADE, sql/009). Nunca uso_ia nem chamadas_ia: os pedidos à IA continuam a contar.
TABELAS_REPOSTAS = ("transacoes", "objetivos", "orcamentos", "resumos_ia")

# Depois de uma reposição falhada, só se tenta outra vez passados 10 minutos (não se martela o Supabase).
INTERVALO_ENTRE_TENTATIVAS = 10 * 60

# Só uma reposição de cada vez: um POST /demo que chegue a meio de outra não espera, entra logo
# com os dados que lá estiverem (a reposição em curso acaba sozinha).
_CADEADO_REPOSICAO = threading.Lock()
# A semana que já se sabe estar reposta (evita perguntar à base de dados em cada POST /demo) e a última falha.
_ESTADO_REPOSICAO: dict[str, Any] = {"semana_reposta": None, "ultima_falha": None}


class ContaDemoErrada(Exception):
    """O DEMO_USER_ID não é a conta do DEMO_EMAIL: não se apaga nada."""


def esquecer_estado_reposicao() -> None:
    """Volta ao estado de arranque (para os testes)."""
    with _CADEADO_REPOSICAO:
        _ESTADO_REPOSICAO["semana_reposta"] = None
        _ESTADO_REPOSICAO["ultima_falha"] = None


def _marca_existe(user_id: str, hoje: date) -> bool:
    resposta = (
        supabase.table("transacoes")
        .select("id")
        .eq("user_id", user_id)
        .eq("hash_importacao", hash_da_marca(hoje))
        .execute()
    )
    return bool(resposta.data)


def _confirmar_conta(config: ConfigDemo) -> None:
    """Confirma no Supabase Auth que o DEMO_USER_ID é mesmo a conta do DEMO_EMAIL. Senão, ContaDemoErrada.

    Protege contra um DEMO_USER_ID trocado (ex.: o id de um cliente colado por engano): a reposição apaga dados.
    """
    resposta = supabase.auth.admin.get_user_by_id(config.user_id)
    utilizador = getattr(resposta, "user", None)
    email = (getattr(utilizador, "email", None) or "").strip().lower()
    if not email or email != config.email:
        raise ContaDemoErrada()


def _apagar_dados(user_id: str) -> None:
    for tabela in TABELAS_REPOSTAS:
        supabase.table(tabela).delete().eq("user_id", user_id).execute()


def _gravar_dados(user_id: str, hoje: date) -> None:
    """Grava os dados inventados, sempre com o user_id da configuração. A marca da semana fica para o fim."""
    transacoes = [linha | {"user_id": user_id} for linha in transacoes_demo(hoje)]
    gravadas = (
        supabase.table("transacoes").upsert(transacoes, on_conflict="user_id,hash_importacao").execute().data
    )
    id_por_hash = {linha["hash_importacao"]: linha["id"] for linha in gravadas}

    for compra in compras_demo(hoje):
        dados_compra = {
            "user_id": user_id,
            "transacao_id": id_por_hash[compra["hash_transacao"]],
            "loja": compra["loja"],
            "data": compra["data"],
            "total": compra["total"],
        }
        compra_id = supabase.table("compras").insert(dados_compra).execute().data[0]["id"]
        # Os itens já trazem nome_generico, produto_chave e unidade: precisa da sql/018 corrida.
        itens = [item | {"compra_id": compra_id} for item in compra["itens"]]
        supabase.table("compra_itens").insert(itens).execute()

    agora = datetime.now(timezone.utc).isoformat()
    orcamentos = [linha | {"user_id": user_id, "atualizado_em": agora} for linha in orcamentos_demo()]
    supabase.table("orcamentos").upsert(orcamentos, on_conflict="user_id,categoria").execute()

    objetivos = [linha | {"user_id": user_id} for linha in objetivos_demo(hoje)]
    supabase.table("objetivos").insert(objetivos).execute()

    # Por último, a marca: se algo acima falhou, não há marca e a reposição volta a correr.
    marca = marca_demo(hoje) | {"user_id": user_id}
    supabase.table("transacoes").upsert(marca, on_conflict="user_id,hash_importacao").execute()

    # Importa-se aqui: o recorrentes.py usa o models.py, que usa o auth.py, que usa este ficheiro.
    from recorrentes import esquecer_recorrentes

    esquecer_recorrentes(user_id)


def garantir_dados_da_semana(config: ConfigDemo, hoje: date | None = None) -> bool:
    """Repõe os dados inventados se ainda não foram repostos esta semana (ISO, de Lisboa). Nunca lança erros.

    Semanal e não mensal: o mês atual só tem as movimentações até ao dia da reposição. Com uma reposição
    por mês, um mês reposto no dia 1 ficava o mês inteiro com quase nada.
    Devolve True se os dados da semana estão repostos. Se já houver uma reposição em curso, não espera:
    devolve False e o visitante entra logo. Uma falha fica nos logs (sem detalhes) e o visitante
    entra na mesma, com os dados que lá estiverem; nova tentativa só passados 10 minutos.
    """
    hoje = hoje or hoje_em_lisboa()
    semana = semana_iso(hoje)
    if not _CADEADO_REPOSICAO.acquire(blocking=False):
        return False
    try:
        if _ESTADO_REPOSICAO["semana_reposta"] == semana:
            return True
        ultima_falha = _ESTADO_REPOSICAO["ultima_falha"]
        if ultima_falha is not None and _relogio() - ultima_falha < INTERVALO_ENTRE_TENTATIVAS:
            return False
        try:
            if not _marca_existe(config.user_id, hoje):
                _confirmar_conta(config)
                _apagar_dados(config.user_id)
                _gravar_dados(config.user_id, hoje)
                print(f"Demo: dados inventados repostos para {semana}.")
        except ContaDemoErrada:
            print("AVISO: demo: o DEMO_USER_ID não é a conta do DEMO_EMAIL. Os dados não foram repostos.")
            _ESTADO_REPOSICAO["ultima_falha"] = _relogio()
            return False
        except Exception as erro:
            print(f"AVISO: demo: a reposição dos dados falhou ({type(erro).__name__}).")
            _ESTADO_REPOSICAO["ultima_falha"] = _relogio()
            return False
        _ESTADO_REPOSICAO["semana_reposta"] = semana
        _ESTADO_REPOSICAO["ultima_falha"] = None
        return True
    finally:
        _CADEADO_REPOSICAO.release()
