"""Demo para recrutadores: o token próprio, a lista de rotas permitidas, os limites por IP e a reposição mensal.

Tudo com dados inventados e um Supabase a fingir: nada é gravado nem pago.
"""

import base64
import hashlib
import hmac
import json
import threading
import time
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import re
from pathlib import Path

import jwt
import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from supabase import AuthApiError

import auth
import compras
import consultas
import dados_demo
import demo
import ia
import limite_ip
import limites
import main
import objetivos
import orcamento
import recorrentes
import resumo
from auth import obter_utilizador_atual

# Valores inventados só para os testes.
SEGREDO = "segredo-de-teste-inventado-com-mais-de-32-caracteres"
DEMO_USER_ID = "11111111-2222-4333-8444-555555555555"
DEMO_EMAIL = "demo@exemplo.pt"
OUTRO_USER_ID = "99999999-8888-4777-8666-555555555555"
CLIENTE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"

# Tokens "do Supabase" que a imitação conhece: token -> id do utilizador.
TOKENS_SUPABASE = {
    "token-supabase-cliente": CLIENTE_ID,
    "token-supabase-da-conta-demo": DEMO_USER_ID,
}

# Hoje fixo nos testes da reposição: 10 de novembro de 2026, ao meio-dia em Lisboa.
AGORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


# --- Imitação do Supabase ---


class Resposta:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class ConsultaFalsa:
    """Uma consulta a uma tabela: guarda a ação, os dados e os filtros .eq(), e executa-os na memória."""

    def __init__(self, base, tabela):
        self.base = base
        self.tabela = tabela
        self.acao = "select"
        self.dados = None
        self.filtros: dict[str, object] = {}
        self.intervalo = None
        self.contar = False

    def select(self, *colunas, count=None, head=False):
        self.contar = count is not None
        return self

    def insert(self, dados, **opcoes):
        self.acao, self.dados = "insert", dados
        return self

    def upsert(self, dados, **opcoes):
        self.acao, self.dados = "upsert", dados
        self.opcoes = opcoes
        return self

    def update(self, dados):
        self.acao, self.dados = "update", dados
        return self

    def delete(self):
        self.acao = "delete"
        return self

    def eq(self, coluna, valor):
        self.filtros[coluna] = valor
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
        return self

    def __getattr__(self, nome):
        # order, gte, lt, is_, limit...: não interessam aqui.
        return lambda *args, **opcoes: self

    def _bate(self, linha):
        return all(linha.get(coluna) == valor for coluna, valor in self.filtros.items())

    def execute(self):
        return self.base.executar(self)


class AdminFalso:
    def __init__(self, base):
        self.base = base

    def get_user_by_id(self, user_id):
        self.base.pedidos_admin.append(user_id)
        email = self.base.emails.get(user_id)
        return SimpleNamespace(user=SimpleNamespace(id=user_id, email=email))


class AuthFalso:
    def __init__(self, base):
        self.base = base
        self.admin = AdminFalso(base)
        self.tokens_pedidos: list[str] = []

    def get_user(self, token):
        self.tokens_pedidos.append(token)
        if token not in TOKENS_SUPABASE:
            raise AuthApiError("invalid JWT", 401, "bad_jwt")
        return SimpleNamespace(user=SimpleNamespace(id=TOKENS_SUPABASE[token]))


class SupabaseFalso:
    """Imita o cliente do Supabase com tabelas na memória.

    operacoes guarda (tabela, ação, dados, filtros) de cada escrita, para ver o que a API gravou e apagou.
    falhar_em = (tabela, ação) faz essa operação lançar um erro (ex.: o Supabase em baixo a meio da reposição).
    """

    def __init__(self):
        self.tabelas: dict[str, list[dict]] = {
            "assinaturas": [
                {"user_id": DEMO_USER_ID, "plano": "essencial", "ativo_ate": "2099-12-31"},
                {"user_id": CLIENTE_ID, "plano": "essencial", "ativo_ate": "2099-12-31"},
            ]
        }
        self.operacoes: list[tuple[str, str, object, dict]] = []
        self.emails = {DEMO_USER_ID: DEMO_EMAIL}
        self.pedidos_admin: list[str] = []
        self.falhar_em: tuple[str, str] | None = None
        self.demora_apagar = 0.0
        self.auth = AuthFalso(self)
        self._proximo_id = 1
        self._cadeado = threading.Lock()

    def table(self, nome):
        return ConsultaFalsa(self, nome)

    def rpc(self, nome, parametros):
        base = self

        class Chamada:
            def execute(self):
                return base.registar_pedido(nome, parametros)

        return Chamada()

    def registar_pedido(self, nome, parametros):
        """O mesmo que a função registar_pedido_ia (sql/016): conta os pedidos do utilizador e regista se houver espaço."""
        assert nome == "registar_pedido_ia"
        with self._cadeado:
            uso = self.tabelas.setdefault("uso_ia", [])
            feitos = sum(1 for linha in uso if linha["user_id"] == parametros["p_user_id"])
            if feitos >= parametros["p_limite"]:
                return Resposta(False)
            uso.append({"user_id": parametros["p_user_id"], "funcao": parametros.get("p_funcao")})
            return Resposta(True)

    def executar(self, consulta: ConsultaFalsa):
        if self.falhar_em == (consulta.tabela, consulta.acao):
            raise RuntimeError("Supabase em baixo (inventado)")
        with self._cadeado:
            linhas = self.tabelas.setdefault(consulta.tabela, [])
            if consulta.acao == "select":
                encontradas = [linha for linha in linhas if consulta._bate(linha)]
                if consulta.intervalo:
                    inicio, fim = consulta.intervalo
                    encontradas = encontradas[inicio : fim + 1]
                return Resposta(encontradas, count=len(encontradas))
            self.operacoes.append((consulta.tabela, consulta.acao, consulta.dados, dict(consulta.filtros)))
            if consulta.acao in ("insert", "upsert"):
                novas = consulta.dados if isinstance(consulta.dados, list) else [consulta.dados]
                gravadas = []
                for linha in novas:
                    gravada = {"id": self._proximo_id, **linha}
                    self._proximo_id += 1
                    linhas.append(gravada)
                    gravadas.append(gravada)
                return Resposta(gravadas)
            if consulta.acao == "delete":
                if self.demora_apagar:
                    time.sleep(self.demora_apagar)
                apagadas = [linha for linha in linhas if consulta._bate(linha)]
                self.tabelas[consulta.tabela] = [linha for linha in linhas if not consulta._bate(linha)]
                return Resposta(apagadas)
            return Resposta([])

    def escritas(self, tabela=None):
        return [op for op in self.operacoes if tabela is None or op[0] == tabela]


# --- Preparação ---


@pytest.fixture
def base(monkeypatch):
    """O Supabase a fingir em todos os módulos que falam com a base de dados, e a demo ligada."""
    falsa = SupabaseFalso()
    for modulo in (auth, compras, consultas, demo, ia, limites, main, objetivos, orcamento, recorrentes, resumo):
        monkeypatch.setattr(modulo, "supabase", falsa)
    monkeypatch.setenv("DEMO_TOKEN_SEGREDO", SEGREDO)
    monkeypatch.setenv("DEMO_USER_ID", DEMO_USER_ID)
    monkeypatch.setenv("DEMO_EMAIL", DEMO_EMAIL)
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA)
    # A IA nunca é chamada a sério: o chat responde sempre o mesmo.
    monkeypatch.setattr(main, "conversar", lambda *args, **opcoes: "Resposta inventada")
    for limite in (demo.LIMITE_ENTRADAS_DEMO, demo.LIMITE_ENTRADAS_DEMO_48, demo.LIMITE_CHAT_DEMO, demo.LIMITE_RESUMO_DEMO):
        limite.limpar()
    demo.esquecer_estado_reposicao()
    resumo.RESUMOS_EM_MEMORIA.clear()
    recorrentes._CACHE.clear()
    main.app.dependency_overrides.clear()
    yield falsa
    demo.esquecer_estado_reposicao()


@pytest.fixture
def api():
    # raise_server_exceptions=False: um erro dentro de uma rota aparece como 500, em vez de parar o teste.
    return TestClient(main.app, raise_server_exceptions=False)


def config_valida() -> demo.ConfigDemo:
    return demo.ConfigDemo(ligada=True, user_id=DEMO_USER_ID, email=DEMO_EMAIL, segredo=SEGREDO)


def token_demo(**alteracoes) -> str:
    return demo.criar_token_demo(config_valida(), **alteracoes)


def cabecalho(token: str, ip: str | None = None) -> dict:
    cabecalhos = {"Authorization": f"Bearer {token}"}
    if ip:
        cabecalhos["X-Forwarded-For"] = ip
    return cabecalhos


def b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def token_a_mao(cabeca: dict, corpo: dict, segredo: str = SEGREDO) -> str:
    """Um JWT montado à mão (para cabeçalhos que o PyJWT não deixa criar), assinado com HMAC-SHA256."""
    inicio = f"{b64(json.dumps(cabeca).encode())}.{b64(json.dumps(corpo).encode())}"
    assinatura = hmac.new(segredo.encode(), inicio.encode(), hashlib.sha256).digest()
    return f"{inicio}.{b64(assinatura)}"


def corpo_valido(**alteracoes) -> dict:
    agora = int(datetime.now(timezone.utc).timestamp())
    corpo = {
        "sub": DEMO_USER_ID,
        "iat": agora,
        "exp": agora + 3600,
        "aud": demo.AUDIENCIA_TOKEN,
        "iss": demo.EMISSOR_TOKEN,
    }
    corpo.update(alteracoes)
    return {chave: valor for chave, valor in corpo.items() if valor is not None}


# --- 1. Token válido ---


def test_token_da_demo_valido_devolve_o_id_da_demo(base, api):
    resposta = api.get("/eu", headers=cabecalho(token_demo()))

    assert resposta.status_code == 200
    assert resposta.json() == {"user_id": DEMO_USER_ID}
    # Com o token da demo, o Supabase Auth nem é chamado.
    assert base.auth.tokens_pedidos == []


def test_o_token_da_demo_nao_tem_email_e_dura_60_minutos():
    agora = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    dados = jwt.decode(
        token_demo(agora=agora), SEGREDO, algorithms=["HS256"], audience=demo.AUDIENCIA_TOKEN,
        options={"verify_exp": False, "verify_iat": False},
    )

    assert set(dados) == {"sub", "iat", "exp", "aud", "iss"}
    assert dados["exp"] - dados["iat"] == 60 * 60
    assert DEMO_EMAIL not in json.dumps(dados)


def test_token_com_o_nosso_segredo_mas_outro_sub_da_401(base, api):
    token = jwt.encode(corpo_valido(sub=OUTRO_USER_ID), SEGREDO, algorithm="HS256")

    resposta = api.get("/eu", headers=cabecalho(token))

    assert resposta.status_code == 401
    assert base.auth.tokens_pedidos == []  # não chega a ir ao Supabase


def test_folga_de_30_segundos_no_relogio(base, api):
    agora = int(datetime.now(timezone.utc).timestamp())
    expirado_ha_pouco = jwt.encode(corpo_valido(iat=agora - 3610, exp=agora - 10), SEGREDO, algorithm="HS256")

    assert api.get("/eu", headers=cabecalho(expirado_ha_pouco)).status_code == 200


# --- 2. Tokens recusados ---


def _tokens_recusados() -> dict[str, str]:
    agora = int(datetime.now(timezone.utc).timestamp())
    return {
        "expirado": jwt.encode(corpo_valido(iat=agora - 7200, exp=agora - 3600), SEGREDO, algorithm="HS256"),
        "outro segredo": jwt.encode(corpo_valido(), "outro-segredo-inventado-com-mais-de-32-caracteres", algorithm="HS256"),
        "alg none": f"{b64(json.dumps({'alg': 'none', 'typ': 'JWT'}).encode())}.{b64(json.dumps(corpo_valido()).encode())}.",
        "HS512": jwt.encode(corpo_valido(), SEGREDO, algorithm="HS512"),
        "RS256 no cabeçalho": token_a_mao({"alg": "RS256", "typ": "JWT"}, corpo_valido()),
        "aud errada": jwt.encode(corpo_valido(aud="authenticated"), SEGREDO, algorithm="HS256"),
        "aud em falta": jwt.encode(corpo_valido(aud=None), SEGREDO, algorithm="HS256"),
        "iss errado": jwt.encode(corpo_valido(iss="supabase"), SEGREDO, algorithm="HS256"),
        "iss em falta": jwt.encode(corpo_valido(iss=None), SEGREDO, algorithm="HS256"),
        "sem exp": jwt.encode(corpo_valido(exp=None), SEGREDO, algorithm="HS256"),
        "sem iat": jwt.encode(corpo_valido(iat=None), SEGREDO, algorithm="HS256"),
        "sem sub": jwt.encode(corpo_valido(sub=None), SEGREDO, algorithm="HS256"),
        "lixo": "isto-nao-e-um-token",
    }


# O PyJWT avisa que o segredo é curto para HS512: é de propósito (o mesmo segredo, outro algoritmo).
@pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
@pytest.mark.parametrize(
    "caso",
    [
        "expirado", "outro segredo", "alg none", "HS512", "RS256 no cabeçalho", "aud errada", "aud em falta",
        "iss errado", "iss em falta", "sem exp", "sem iat", "sem sub", "lixo",
    ],
)
def test_tokens_estragados_nao_entram_como_demo(base, api, caso):
    token = _tokens_recusados()[caso]

    assert demo.ler_token_demo(token, config_valida()) is None
    # Não é um token da demo: segue para o Supabase, que também o recusa.
    resposta = api.get("/eu", headers=cabecalho(token))
    assert resposta.status_code == 401
    assert base.auth.tokens_pedidos == [token]


@pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
def test_os_casos_recusados_estao_todos_testados():
    # A lista do parametrize tem de ter todos os tokens de _tokens_recusados (e nenhum a mais).
    marca = next(m for m in test_tokens_estragados_nao_entram_como_demo.pytestmark if m.name == "parametrize")
    assert set(marca.args[1]) == set(_tokens_recusados())


# --- 3. Token do Supabase ---


def test_token_do_supabase_nao_e_lido_como_demo(base, api):
    # Um JWT do Supabase (HS256, mas com o segredo do Supabase e a audiência "authenticated").
    token_jwt_supabase = jwt.encode(
        corpo_valido(aud="authenticated", iss="https://exemplo.supabase.co/auth/v1"),
        "segredo-do-supabase-inventado-com-mais-de-32-caracteres",
        algorithm="HS256",
    )
    assert demo.ler_token_demo(token_jwt_supabase, config_valida()) is None

    resposta = api.get("/eu", headers=cabecalho("token-supabase-cliente"))

    assert resposta.status_code == 200
    assert resposta.json() == {"user_id": CLIENTE_ID}
    assert base.auth.tokens_pedidos == ["token-supabase-cliente"]


def test_cliente_normal_nao_e_afetado_pela_demo(base, api):
    # As rotas bloqueadas na demo continuam abertas para os clientes (aqui, definir um orçamento).
    resposta = api.put("/orcamentos/casa", json={"limite": 500}, headers=cabecalho("token-supabase-cliente"))

    assert resposta.status_code == 200
    assert base.escritas("orcamentos")[0][2]["user_id"] == CLIENTE_ID


# --- 4. Configuração inválida ---


@pytest.mark.parametrize(
    ("variavel", "valor"),
    [
        ("DEMO_TOKEN_SEGREDO", ""),
        ("DEMO_TOKEN_SEGREDO", "x" * 31),
        ("DEMO_USER_ID", ""),
        ("DEMO_USER_ID", "nao-e-um-uuid"),
        ("DEMO_USER_ID", "11111111222243338444555555555555"),  # sem hífenes
        ("DEMO_EMAIL", ""),
        ("DEMO_EMAIL", "sem-arroba"),
    ],
)
def test_configuracao_invalida_desliga_a_demo(base, api, monkeypatch, capsys, variavel, valor):
    token = token_demo()  # feito com a configuração boa
    monkeypatch.setenv(variavel, valor)
    demo._AVISOS_DADOS.clear()

    entrada = api.post("/demo")
    assert entrada.status_code == 503
    assert entrada.json() == {"detail": main.MENSAGEM_DEMO_DESLIGADA}

    # O token da demo deixa de ser aceite: segue para o Supabase, que o recusa.
    assert api.get("/eu", headers=cabecalho(token)).status_code == 401
    # Nada foi reposto e os logs dizem o que falta, nunca os valores.
    assert base.operacoes == []
    logs = capsys.readouterr().out
    assert "demo desligada" in logs
    assert SEGREDO not in logs and DEMO_USER_ID not in logs and DEMO_EMAIL not in logs


def test_sem_nenhuma_variavel_a_demo_esta_desligada(monkeypatch):
    for variavel in ("DEMO_TOKEN_SEGREDO", "DEMO_USER_ID", "DEMO_EMAIL"):
        monkeypatch.delenv(variavel, raising=False)

    config = demo.config_demo()

    assert config.ligada is False and config.user_id is None
    assert SEGREDO not in repr(demo.config_demo())


# --- 5. Todas as rotas ---

# Rotas públicas (sem login). Uma rota pública nova obriga a acrescentá-la aqui.
ROTAS_PUBLICAS = {
    ("GET", "/"),
    ("POST", "/login"),
    ("GET", "/login/google"),
    ("POST", "/login/google/troca"),
    ("POST", "/registo"),
    ("POST", "/demo"),
    ("GET", "/planos"),
}

# Rotas com login que a demo NÃO pode usar (escritas e pedidos à IA fora do chat).
# Uma rota nova com login tem de entrar aqui ou em demo.PERMISSOES_DEMO: senão este teste falha.
ROTAS_BLOQUEADAS_NA_DEMO = {
    ("POST", "/transacoes"),
    ("PATCH", "/transacoes/{transacao_id}"),
    ("POST", "/transacoes/categorizar"),
    ("POST", "/transacoes/importar"),
    ("PUT", "/orcamentos/{categoria}"),
    ("POST", "/orcamentos/sugestao"),
    ("POST", "/compras/ler"),
    ("POST", "/compras"),
    ("POST", "/objetivos"),
    ("PATCH", "/objetivos/{objetivo_id}"),
    ("DELETE", "/objetivos/{objetivo_id}"),
    ("POST", "/objetivos/{objetivo_id}/plano"),
}

# Valores de exemplo para os pedidos às rotas permitidas.
PARAMETROS = {
    "/dashboard/categorias": {"mes": "2026-11"},
    "/resumo": {"mes": "2026-11"},
    "/orcamentos": {"mes": "2026-11"},
    "/transacoes": {"mes": "2026-11"},
    "/simulador": {"mensal": 50, "anos": 10, "taxa": 3},
}


def _rotas_da_api() -> set[tuple[str, str, bool]]:
    """(método, caminho, precisa de login) de cada rota do main.py."""
    rotas = set()
    for rota in main.app.routes:
        if not isinstance(rota, APIRoute):
            continue
        com_login = any(dependencia.call is obter_utilizador_atual for dependencia in rota.dependant.dependencies)
        for metodo in rota.methods:
            rotas.add((metodo, rota.path, com_login))
    return rotas


def _endereco(caminho: str) -> str:
    return caminho.replace("{transacao_id}", "1").replace("{objetivo_id}", "1").replace("{categoria}", "casa")


def test_cada_rota_tem_uma_decisao_para_a_demo():
    rotas = _rotas_da_api()
    com_login = {(metodo, caminho) for metodo, caminho, login in rotas if login}
    publicas = {(metodo, caminho) for metodo, caminho, login in rotas if not login}

    assert publicas == ROTAS_PUBLICAS
    assert not (demo.PERMISSOES_DEMO & ROTAS_BLOQUEADAS_NA_DEMO)
    # Se este falhar, há uma rota nova: decide se a demo a pode usar (PERMISSOES_DEMO) ou não (lista acima).
    assert com_login == demo.PERMISSOES_DEMO | ROTAS_BLOQUEADAS_NA_DEMO


class NadaDeEscritas:
    """Põe-se no lugar do Supabase do main.py: qualquer acesso falha o teste."""

    def __getattr__(self, nome):
        raise AssertionError(f"A demo chegou à base de dados ({nome}) numa rota bloqueada")


@pytest.mark.parametrize(("metodo", "caminho"), sorted(ROTAS_BLOQUEADAS_NA_DEMO))
def test_rotas_fora_da_lista_dao_423_a_demo(base, api, monkeypatch, metodo, caminho):
    monkeypatch.setattr(main, "supabase", NadaDeEscritas())

    resposta = api.request(metodo, _endereco(caminho), headers=cabecalho(token_demo()))

    assert resposta.status_code == 423
    assert resposta.json() == {"detail": demo.MENSAGEM_BLOQUEIO_DEMO}


@pytest.mark.parametrize(("metodo", "caminho"), sorted(demo.PERMISSOES_DEMO))
def test_rotas_da_lista_funcionam_na_demo(base, api, metodo, caminho):
    corpo = {"pergunta": "Quanto gastei este mês?"} if metodo == "POST" else None

    resposta = api.request(
        metodo, _endereco(caminho), params=PARAMETROS.get(caminho), json=corpo, headers=cabecalho(token_demo())
    )

    # /transacoes/1 dá 404 (não há dados): o que interessa é que a demo passou da autenticação.
    assert resposta.status_code in (200, 404), resposta.text


def test_sugestoes_da_ia_ficam_bloqueadas_na_demo():
    # Decisão do CEO: gastariam os pedidos à IA partilhados por todos os visitantes.
    assert ("POST", "/orcamentos/sugestao") not in demo.PERMISSOES_DEMO
    assert ("POST", "/objetivos/{objetivo_id}/plano") not in demo.PERMISSOES_DEMO


# --- 6. Conta de demo com o token do Supabase ---


@pytest.mark.parametrize(("metodo", "caminho"), sorted(ROTAS_BLOQUEADAS_NA_DEMO))
def test_conta_demo_com_token_do_supabase_tambem_leva_423(base, api, metodo, caminho):
    resposta = api.request(metodo, _endereco(caminho), headers=cabecalho("token-supabase-da-conta-demo"))

    assert resposta.status_code == 423


def test_conta_demo_com_token_do_supabase_ve_os_dados(base, api):
    resposta = api.get("/eu", headers=cabecalho("token-supabase-da-conta-demo"))

    assert resposta.status_code == 200


def test_conta_demo_fica_bloqueada_mesmo_com_a_demo_desligada(base, api, monkeypatch):
    # Sem segredo a demo está desligada, mas o DEMO_USER_ID continua a dizer qual é a conta a proteger.
    monkeypatch.setenv("DEMO_TOKEN_SEGREDO", "")

    resposta = api.post("/transacoes/categorizar", headers=cabecalho("token-supabase-da-conta-demo"))

    assert resposta.status_code == 423


# --- 7. Limites por IP ---


def test_post_demo_10_por_hora_por_ip(base, api, monkeypatch):
    relogio = [1000.0]
    monkeypatch.setattr(limite_ip, "_relogio", lambda: relogio[0])

    for i in range(10):
        # A parte da esquerda do X-Forwarded-For é inventada pelo browser: não conta.
        assert api.post("/demo", headers={"X-Forwarded-For": f"10.9.9.{i}, 203.0.113.7"}).status_code == 200
    bloqueado = api.post("/demo", headers={"X-Forwarded-For": "198.51.100.99, 203.0.113.7"})

    assert bloqueado.status_code == 429
    assert bloqueado.json()["detail"] == demo.LIMITE_ENTRADAS_DEMO.mensagem
    # Outro IP (o da direita) continua a entrar.
    assert api.post("/demo", headers={"X-Forwarded-For": "203.0.113.8"}).status_code == 200
    # Uma hora depois, o primeiro IP volta a entrar.
    relogio[0] += 3600
    assert api.post("/demo", headers={"X-Forwarded-For": "203.0.113.7"}).status_code == 200


def test_sem_x_forwarded_for_usa_o_ip_da_ligacao(base, api):
    for _ in range(10):
        assert api.post("/demo").status_code == 200

    assert api.post("/demo").status_code == 429


def test_chat_da_demo_5_por_dia_por_ip(base, api):
    token = token_demo()
    pergunta = {"pergunta": "Quanto gastei?"}

    for i in range(5):
        assert api.post("/chat", json=pergunta, headers=cabecalho(token, f"1.1.1.{i}, 203.0.113.20")).status_code == 200
    bloqueado = api.post("/chat", json=pergunta, headers=cabecalho(token, "203.0.113.20"))

    assert bloqueado.status_code == 429
    assert bloqueado.json()["detail"] == demo.LIMITE_CHAT_DEMO.mensagem
    # A pergunta recusada não gastou um pedido à IA.
    assert len(base.tabelas["uso_ia"]) == 5


def test_resumo_da_demo_10_por_hora_por_ip(base, api):
    token = token_demo()

    for _ in range(10):
        assert api.get("/resumo", params={"mes": "2026-11"}, headers=cabecalho(token, "203.0.113.30")).status_code == 200
    bloqueado = api.get("/resumo", params={"mes": "2026-11"}, headers=cabecalho(token, "203.0.113.30"))

    assert bloqueado.status_code == 429
    assert bloqueado.json()["detail"] == demo.LIMITE_RESUMO_DEMO.mensagem


def test_clientes_normais_nao_tem_limite_por_ip_no_chat(base, api):
    for _ in range(7):
        resposta = api.post("/chat", json={"pergunta": "Olá"}, headers=cabecalho("token-supabase-cliente", "203.0.113.40"))
        assert resposta.status_code == 200


def test_teto_de_ips_limpa_as_janelas_expiradas_e_fecha_se_cheio(monkeypatch):
    relogio = [0.0]
    monkeypatch.setattr(limite_ip, "_relogio", lambda: relogio[0])
    limite = limite_ip.LimitePorIP(5, 60, "cheio", teto_ips=3)

    for ip in ("a", "b", "c"):
        limite.registar(ip)
    with pytest.raises(Exception) as erro:
        limite.registar("d")
    assert erro.value.status_code == 429
    # Os IPs que já estavam continuam a contar normalmente.
    limite.registar("a")

    relogio[0] = 61  # as janelas acabaram: limpam-se e há espaço outra vez
    limite.registar("d")
    assert len(limite._pedidos) == 1


# --- 8. Reposição dos dados ---


def _gravacoes(base) -> list[tuple]:
    return [op for op in base.operacoes if op[1] in ("insert", "upsert")]


def test_reposicao_grava_tudo_so_com_o_id_da_demo(base, api):
    resposta = api.post("/demo")

    assert resposta.status_code == 200
    assert resposta.json()["token_type"] == "bearer"
    # Apaga só as linhas da conta de demo, nas 4 tabelas.
    apagadas = [(tabela, filtros) for tabela, acao, _, filtros in base.operacoes if acao == "delete"]
    assert apagadas == [(tabela, {"user_id": DEMO_USER_ID}) for tabela in demo.TABELAS_REPOSTAS]
    # Todas as linhas gravadas são da conta de demo (os produtos dos talões vão pela compra).
    for tabela, _, dados, _ in _gravacoes(base):
        for linha in dados if isinstance(dados, list) else [dados]:
            if tabela == "compra_itens":
                assert set(linha) == {"descricao", "quantidade", "preco", "compra_id"}
            else:
                assert linha["user_id"] == DEMO_USER_ID
    # Confirmou o email da conta antes de apagar.
    assert base.pedidos_admin == [DEMO_USER_ID]


def test_reposicao_nunca_mexe_nos_pedidos_a_ia(base, api):
    api.post("/demo")

    tabelas = {tabela for tabela, *_ in base.operacoes}
    assert "uso_ia" not in tabelas and "chamadas_ia" not in tabelas
    assert "uso_ia" not in demo.TABELAS_REPOSTAS and "chamadas_ia" not in demo.TABELAS_REPOSTAS


def test_reposicao_cria_os_dados_da_demo(base, api):
    recorrentes._CACHE[DEMO_USER_ID] = (0.0, date(2026, 11, 10), [])

    api.post("/demo")

    transacoes = base.tabelas["transacoes"]
    assert all(linha["hash_importacao"].startswith("demo-2026-W46-") for linha in transacoes)
    # A marca é a última transação gravada.
    assert transacoes[-1]["hash_importacao"] == "demo-2026-W46-marca"
    assert len(base.tabelas["objetivos"]) == 2
    assert len(base.tabelas["compras"]) >= 1 and base.tabelas["compra_itens"]
    assert base.tabelas["orcamentos"]
    # Os orçamentos e as transações gravam-se com upsert, pelas chaves únicas da base de dados.
    upserts = {tabela: dados for tabela, acao, dados, _ in base.operacoes if acao == "upsert"}
    assert set(upserts) == {"transacoes", "orcamentos"}
    # A cache dos pagamentos que se repetem foi esquecida.
    assert DEMO_USER_ID not in recorrentes._CACHE


def test_dados_inventados_tem_6_meses_e_pagamentos_que_se_repetem():
    hoje = date(2026, 11, 10)
    transacoes = dados_demo.transacoes_demo(hoje) + [dados_demo.marca_demo(hoje)]

    meses = {linha["data"][:7] for linha in transacoes}
    assert meses == {"2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"}
    assert all(linha["data"] <= hoje.isoformat() for linha in transacoes)  # nada no futuro
    assert len({linha["hash_importacao"] for linha in transacoes}) == len(transacoes)  # hashes únicos
    despesas = [linha for linha in transacoes if linha["valor"] < 0]
    assert len(recorrentes.detetar_recorrentes(despesas, hoje)) >= 3
    # Cada talão tem a sua transação, com o mesmo total.
    por_hash = {linha["hash_importacao"]: linha for linha in transacoes}
    for compra in dados_demo.compras_demo(hoje):
        assert por_hash[compra["hash_transacao"]]["valor"] == -compra["total"]
        assert compra["total"] == round(sum(item["preco"] for item in compra["itens"]), 2)
    # Os objetivos têm o prazo no futuro.
    assert all(objetivo["data_alvo"] > hoje.isoformat() for objetivo in dados_demo.objetivos_demo(hoje))


def test_dados_inventados_atravessam_a_mudanca_de_ano():
    hoje = date(2027, 2, 3)
    meses = {linha["data"][:7] for linha in dados_demo.transacoes_demo(hoje)}

    assert {"2026-09", "2026-12", "2027-01", "2027-02"} <= meses
    assert all(linha["data"] <= hoje.isoformat() for linha in dados_demo.transacoes_demo(hoje))


def test_email_errado_nao_apaga_nada(base, api):
    base.emails[DEMO_USER_ID] = "cliente-verdadeiro@exemplo.pt"

    resposta = api.post("/demo")

    assert resposta.status_code == 200  # entra na mesma
    assert base.operacoes == []


def test_conta_sem_email_nao_apaga_nada(base, api):
    base.emails.pop(DEMO_USER_ID)

    api.post("/demo")

    assert base.operacoes == []


def test_dois_pedidos_ao_mesmo_tempo_repoem_uma_so_vez(base):
    base.demora_apagar = 0.05  # a reposição demora um pouco: o segundo pedido chega a meio
    config = config_valida()
    resultados = []
    partida = threading.Barrier(2)

    def entrar():
        partida.wait()
        resultados.append(demo.garantir_dados_da_semana(config, date(2026, 11, 10)))

    fios = [threading.Thread(target=entrar) for _ in range(2)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()

    assert True in resultados
    assert len([op for op in base.operacoes if op[:2] == ("transacoes", "delete")]) == 1


def test_com_uma_reposicao_em_curso_entra_sem_esperar(base, api):
    # Outra reposição tem o cadeado: o POST /demo não espera por ela e entrega logo o token.
    assert demo._CADEADO_REPOSICAO.acquire(blocking=False)
    try:
        inicio = time.monotonic()
        resposta = api.post("/demo")
        demorou = time.monotonic() - inicio
    finally:
        demo._CADEADO_REPOSICAO.release()

    assert resposta.status_code == 200
    assert demo.ler_token_demo(resposta.json()["access_token"], config_valida()) == DEMO_USER_ID
    assert base.operacoes == [] and base.pedidos_admin == []
    assert demorou < 2


def test_falha_entrega_o_token_sem_marca_e_espera_10_minutos(base, api, monkeypatch):
    relogio = [5000.0]
    monkeypatch.setattr(demo, "_relogio", lambda: relogio[0])
    base.falhar_em = ("objetivos", "insert")

    resposta = api.post("/demo")

    assert resposta.status_code == 200
    assert demo.ler_token_demo(resposta.json()["access_token"], config_valida()) == DEMO_USER_ID
    hashes = [linha["hash_importacao"] for linha in base.tabelas["transacoes"]]
    assert "demo-2026-W46-marca" not in hashes

    # Logo a seguir não volta a tentar (nem consulta a base de dados).
    base.falhar_em = None
    feitas = len(base.operacoes)
    api.post("/demo")
    assert len(base.operacoes) == feitas
    assert base.pedidos_admin == [DEMO_USER_ID]

    # Passados 10 minutos, tenta outra vez e fica com a marca.
    relogio[0] += 600
    api.post("/demo")
    assert base.tabelas["transacoes"][-1]["hash_importacao"] == "demo-2026-W46-marca"


def test_segunda_entrada_da_semana_nao_repoe(base, api, monkeypatch):
    api.post("/demo")
    apagou = len([op for op in base.operacoes if op[1] == "delete"])

    # Outro dia da mesma semana ISO (domingo, 15 de novembro).
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA + timedelta(days=5))
    api.post("/demo")
    # Mesmo depois de o servidor reiniciar (sem memória), a marca na base de dados chega.
    demo.esquecer_estado_reposicao()
    api.post("/demo")

    assert len([op for op in base.operacoes if op[1] == "delete"]) == apagou
    assert base.pedidos_admin == [DEMO_USER_ID]


def test_na_semana_seguinte_repoe_outra_vez(base, api, monkeypatch):
    api.post("/demo")
    monkeypatch.setattr(limites, "agora_utc", lambda: AGORA + timedelta(days=7))  # 17 de novembro

    api.post("/demo")

    assert base.tabelas["transacoes"][-1]["hash_importacao"] == "demo-2026-W47-marca"
    assert len(base.pedidos_admin) == 2
    # Os dados novos chegam até ao dia da reposição (há uma movimentação no dia 16), nunca depois.
    datas = {linha["data"] for linha in base.tabelas["transacoes"]}
    assert "2026-11-16" in datas and max(datas) <= "2026-11-17"


def test_semana_iso_usa_o_ano_da_semana():
    assert dados_demo.semana_iso(date(2026, 11, 10)) == "2026-W46"
    # 1 de janeiro de 2027 ainda é da semana 53 de 2026.
    assert dados_demo.semana_iso(date(2027, 1, 1)) == "2026-W53"
    assert dados_demo.hash_da_marca(date(2027, 1, 1)) == "demo-2026-W53-marca"


def test_dados_inventados_nao_tem_numeros_de_telefone():
    for linha in dados_demo.transacoes_demo(date(2026, 11, 10)):
        assert not re.search(r"\d{4,}", linha["descricao"]), linha["descricao"]


# --- Textos iguais aos do frontend ---


def _textos_do_frontend() -> dict[str, str]:
    """As chaves e os textos de TEXTOS_DEMO (frontend/src/lib/textosDemo.ts), juntando as linhas partidas."""
    ficheiro = Path(__file__).parent.parent / "frontend" / "src" / "lib" / "textosDemo.ts"
    conteudo = ficheiro.read_text(encoding="utf-8")
    return dict(re.findall(r'(\w+):\s*"([^"]*)"', conteudo))


def test_mensagens_da_api_iguais_as_do_frontend():
    textos = _textos_do_frontend()

    assert demo.MENSAGEM_BLOQUEIO_DEMO == textos["bloqueado"]
    assert demo.MENSAGEM_DEMO_DESLIGADA == textos["indisponivel"]
    assert demo.LIMITE_ENTRADAS_DEMO.mensagem == textos["limiteEntradas"]
    assert demo.LIMITE_CHAT_DEMO.mensagem == textos["limiteDemo"]
    assert demo.LIMITE_RESUMO_DEMO.mensagem == textos["limiteResumo"]
    assert demo.LIMITE_ENTRADAS_DEMO_48.mensagem == textos["limiteEntradas"]
    assert demo.MENSAGEM_DEMO_CHEIA == textos["demoCheia"]


# --- IPv6 e o registo do X-Forwarded-For ---


@pytest.mark.parametrize(
    ("ip", "chave"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("2001:db8:aaaa:bbbb:1:2:3:4", "2001:db8:aaaa:bbbb::/64"),
        ("2001:db8:aaaa:bbbb:ffff:ffff:ffff:ffff", "2001:db8:aaaa:bbbb::/64"),
        ("::ffff:203.0.113.7", "203.0.113.7"),
        ("desconhecido", "desconhecido"),
    ],
)
def test_chave_do_ip(ip, chave):
    assert limite_ip.chave_do_ip(ip) == chave


def test_ipv6_conta_pelo_prefixo_64(base, api):
    for i in range(10):
        # Endereços diferentes dentro do mesmo /64 contam como um só.
        assert api.post("/demo", headers={"X-Forwarded-For": f"2001:db8:1:2::{i + 1:x}"}).status_code == 200

    assert api.post("/demo", headers={"X-Forwarded-For": "2001:db8:1:2:abcd::99"}).status_code == 429
    # Outro /64 continua a entrar.
    assert api.post("/demo", headers={"X-Forwarded-For": "2001:db8:1:3::1"}).status_code == 200


@pytest.mark.parametrize(
    ("ip", "prefixo"),
    [
        ("2001:db8:1:2::1", "2001:db8:1::/48"),
        ("2001:db8:1:ffff:1:2:3:4", "2001:db8:1::/48"),
        ("203.0.113.7", None),
        ("::ffff:203.0.113.7", None),
        ("desconhecido", None),
    ],
)
def test_prefixo_48_so_no_ipv6(ip, prefixo):
    assert limite_ip.prefixo_48_do_ipv6(ip) == prefixo


def test_ipv6_tambem_conta_pelo_prefixo_48(base, api):
    # 30 entradas de 30 prefixos /64 diferentes, todos no mesmo /48 (cada /64 fica longe do seu limite de 10).
    for i in range(30):
        resposta = api.post("/demo", headers={"X-Forwarded-For": f"2001:db8:7:{i:x}::1"})
        assert resposta.status_code == 200, i

    bloqueado = api.post("/demo", headers={"X-Forwarded-For": "2001:db8:7:ff::1"})
    assert bloqueado.status_code == 429
    assert bloqueado.json()["detail"] == demo.LIMITE_ENTRADAS_DEMO_48.mensagem
    # Outro /48 continua a entrar, e o IPv4 não conta para este limite.
    assert api.post("/demo", headers={"X-Forwarded-For": "2001:db8:8::1"}).status_code == 200
    assert api.post("/demo", headers={"X-Forwarded-For": "203.0.113.50"}).status_code == 200


def test_limite_por_48_tem_teto_e_limpeza(monkeypatch):
    relogio = [0.0]
    monkeypatch.setattr(limite_ip, "_relogio", lambda: relogio[0])
    limite = limite_ip.LimitePorIP(
        30, 60, "rede", teto_ips=2, chave=limite_ip.prefixo_48_do_ipv6, mensagem_teto=demo.MENSAGEM_DEMO_CHEIA
    )

    limite.registar("2001:db8:1::1")
    limite.registar("2001:db8:2::1")
    limite.registar("203.0.113.1")  # IPv4: não conta, nem ocupa lugar
    with pytest.raises(HTTPException) as erro:
        limite.registar("2001:db8:3::1")
    assert erro.value.detail == demo.MENSAGEM_DEMO_CHEIA

    relogio[0] = 61
    limite.registar("2001:db8:3::1")
    assert list(limite._pedidos) == ["2001:db8:3::/48"]


def test_teto_cheio_responde_com_mensagem_generica(monkeypatch):
    monkeypatch.setattr(limite_ip, "_relogio", lambda: 0.0)
    limite = limite_ip.LimitePorIP(5, 60, "mensagem do limite", teto_ips=1, mensagem_teto=demo.MENSAGEM_DEMO_CHEIA)
    limite.registar("203.0.113.1")

    with pytest.raises(HTTPException) as erro:
        limite.registar("203.0.113.2")

    assert erro.value.status_code == 429
    assert erro.value.detail == demo.MENSAGEM_DEMO_CHEIA


def test_forma_do_x_forwarded_for_fica_no_log_sem_ips(base, api, capsys, monkeypatch):
    monkeypatch.setattr(demo, "_VEZES_FORMA_DO_IP", [0])

    api.post(
        "/demo",
        headers={"X-Forwarded-For": "198.51.100.23, 203.0.113.77, 10.0.0.5", "CF-Connecting-IP": "198.51.100.23"},
    )

    logs = [linha for linha in capsys.readouterr().out.splitlines() if "X-Forwarded-For" in linha]
    assert logs == [
        "Demo: X-Forwarded-For com 3 entrada(s) [privada, privada, privada]; IP da ligação: presente, fora da lista; "
        "CF-Connecting-IP: entrada 1; True-Client-IP: ausente; X-Real-IP: ausente."
    ]


def test_forma_do_x_forwarded_for_so_nas_primeiras_vezes(base, api, capsys, monkeypatch):
    monkeypatch.setattr(demo, "_VEZES_FORMA_DO_IP", [0])

    for i in range(5):
        api.post("/demo", headers={"X-Forwarded-For": f"8.8.8.{i}, testclient"})

    logs = [linha for linha in capsys.readouterr().out.splitlines() if "X-Forwarded-For" in linha]
    assert len(logs) == 3
    assert "[pública, inválida]" in logs[0] and "IP da ligação: entrada 2" in logs[0]
    assert all("8.8.8" not in linha for linha in logs)


# --- 9. O chat da demo conta nos pedidos à IA ---


def test_chat_da_demo_conta_no_uso_ia_e_da_429_aos_20(base, api):
    token = token_demo()
    pergunta = {"pergunta": "Quanto gastei em restaurantes?"}

    # 20 perguntas de 4 IPs (5 cada, o máximo por IP): todas respondidas.
    for i in range(20):
        ip = f"203.0.113.{100 + i // 5}"
        assert api.post("/chat", json=pergunta, headers=cabecalho(token, ip)).status_code == 200

    # Os 20 pedidos do plano Essencial são partilhados: a 21.ª, de um IP novo, já não passa.
    resposta = api.post("/chat", json=pergunta, headers=cabecalho(token, "203.0.113.200"))

    assert resposta.status_code == 429
    assert resposta.json()["detail"] == limites.mensagem_do_limite(20, "dia")
    assert base.tabelas["uso_ia"] == [{"user_id": DEMO_USER_ID, "funcao": "chat"}] * 20
