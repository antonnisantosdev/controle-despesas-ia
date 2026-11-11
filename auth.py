from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AuthApiError, AuthError, ClientOptions, create_client

from database import SUPABASE_KEY, SUPABASE_URL, supabase
from demo import config_demo, exigir_permissao_demo, ler_token_demo
from token_supabase import CacheJWKS, TokenInvalido, emissor_esperado, ler_token_supabase, url_jwks

# Lê o cabeçalho "Authorization: Bearer <token>" de cada pedido.
# Também faz aparecer o botão "Authorize" no /docs.
esquema_bearer = HTTPBearer()


def cliente_sem_sessao():
    """Um cliente do Supabase só para um login: não guarda a sessão nem a renova sozinho.

    Sem isto, cada login deixava no servidor a sessão do utilizador em memória e um temporizador
    para renovar o token (com o refresh_token), que nunca usamos.
    """
    return create_client(
        SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(auto_refresh_token=False, persist_session=False)
    )


def fazer_login(email: str, password: str) -> str:
    """Faz login no Supabase Auth e devolve o token de acesso do utilizador."""
    # Cliente próprio para o login: a sessão do utilizador não "contamina" o cliente partilhado.
    cliente = cliente_sem_sessao()
    resposta = cliente.auth.sign_in_with_password({"email": email, "password": password})
    return resposta.session.access_token


def fazer_registo(email: str, password: str) -> str | None:
    """Cria a conta no Supabase Auth. O Supabase envia o email de confirmação,
    e o gatilho do sql/013_registo_publico.sql dá-lhe logo o plano Free.

    Devolve o id da conta (para guardar a origem) só se a conta acabou de ser criada (created_at há menos
    de JANELA_CONTA_NOVA, como no Google); senão None. Assim um segundo registo com o email de uma conta
    antiga (ainda por confirmar) não lhe muda a origem. Se o email já tiver conta confirmada, o Supabase
    devolve um id inventado: mesmo que passe, o UPDATE da origem não encontra nenhuma linha.
    """
    cliente = create_client(SUPABASE_URL, SUPABASE_KEY)
    resposta = cliente.auth.sign_up({"email": email, "password": password})
    utilizador = getattr(resposta, "user", None)
    if utilizador is None or not getattr(utilizador, "id", None):
        return None
    if not _conta_acabada_de_criar(getattr(utilizador, "created_at", None), datetime.now(timezone.utc)):
        return None
    return str(utilizador.id)


def guardar_origem(user_id: str | None, origem: str | None) -> None:
    """Escreve o canal de origem (sql/019) na assinatura da conta, só se ainda estiver vazio.

    A linha foi criada pelo gatilho do registo (sql/013). Nunca falha: um erro aqui (ex.: a migração
    019 ainda não corrida) só deixa um aviso no log, sem o id nem o email, e o registo segue.
    """
    if not user_id or not origem:
        return
    try:
        supabase.table("assinaturas").update({"origem": origem}).eq("user_id", user_id).is_("origem", "null").execute()
    except Exception as erro:
        print(f"AVISO: origem do registo não gravada ({type(erro).__name__}).")


# Página do frontend que recebe o token depois do login com o Google.
CAMINHO_VOLTA_GOOGLE = "/login/google"


def destino_google_valido(destino: str, origens: list[str]) -> bool:
    """Se o destino é exatamente a página /login/google de uma das origens do frontend.

    Só se aceita a igualdade exata: assim ninguém usa o nosso login para mandar
    o token do utilizador para outro site (redirecionamento aberto).
    """
    return any(destino == origem.strip().rstrip("/") + CAMINHO_VOLTA_GOOGLE for origem in origens if origem.strip())


# PKCE (RFC 7636): o browser inventa um segredo (code_verifier) e manda só o seu SHA-256 em base64url
# (code_challenge, sempre 43 caracteres). O Supabase volta com ?code=, que só vale junto com o segredo:
# um código roubado ou um link de um atacante não chega para entrar.
FORMATO_CODE_CHALLENGE = r"^[A-Za-z0-9_-]{43}$"
# O segredo tem 43 a 128 caracteres "não reservados" (letras, números e - . _ ~), como manda o RFC 7636.
FORMATO_CODE_VERIFIER = r"^[A-Za-z0-9._~-]{43,128}$"
# O código que o Supabase devolve (hoje um UUID). Aceita-se um pouco mais, mas só caracteres seguros e com teto.
FORMATO_CODIGO_GOOGLE = r"^[A-Za-z0-9._~-]{1,256}$"


def url_login_google(destino: str, code_challenge: str) -> str:
    """O endereço do Supabase que abre o login com o Google e, no fim, volta ao destino com ?code=.

    O código troca-se pelo token na API (trocar_codigo_google), com o segredo que ficou no browser.
    O método "s256" é o nome que o Supabase Auth usa (o mesmo que o SDK supabase_auth envia).
    """
    parametros = urlencode(
        {
            "provider": "google",
            "redirect_to": destino,
            "code_challenge": code_challenge,
            "code_challenge_method": "s256",
        }
    )
    return f"{SUPABASE_URL.rstrip('/')}/auth/v1/authorize?{parametros}"


# Uma conta Google criada há menos disto conta como nova (primeiro login): só então se guarda a origem.
JANELA_CONTA_NOVA = timedelta(minutes=10)


@dataclass(frozen=True)
class SessaoGoogle:
    """O resultado da troca do código: o token e, se o Supabase os devolver, o id e se a conta é nova."""

    token: str
    user_id: str | None = None
    conta_nova: bool = False


def _conta_acabada_de_criar(criada_em: object, agora: datetime) -> bool:
    """Se a conta foi criada há menos de JANELA_CONTA_NOVA (aceita datetime ou texto ISO do Supabase)."""
    if isinstance(criada_em, str):
        try:
            criada_em = datetime.fromisoformat(criada_em.replace("Z", "+00:00"))
        except ValueError:
            return False
    if not isinstance(criada_em, datetime):
        return False
    if criada_em.tzinfo is None:
        criada_em = criada_em.replace(tzinfo=timezone.utc)
    return timedelta(0) <= agora - criada_em <= JANELA_CONTA_NOVA


def trocar_codigo_google(codigo: str, code_verifier: str) -> SessaoGoogle:
    """Troca o ?code= do regresso do Google pelo token de acesso do utilizador (como o fazer_login).

    O Supabase só aceita o código com o segredo cujo SHA-256 recebeu no início (POST /auth/v1/token?grant_type=pkce).
    Levanta AuthError se o código ou o segredo não servirem. O refresh_token fica de fora, como no login com email.
    """
    cliente = cliente_sem_sessao()
    resposta = cliente.auth.exchange_code_for_session({"auth_code": codigo, "code_verifier": code_verifier})
    if not resposta.session or not resposta.session.access_token:
        raise AuthError("Sem sessão na troca do código", None)
    utilizador = getattr(resposta, "user", None) or getattr(resposta.session, "user", None)
    if utilizador is None or not getattr(utilizador, "id", None):
        return SessaoGoogle(resposta.session.access_token)
    conta_nova = _conta_acabada_de_criar(getattr(utilizador, "created_at", None), datetime.now(timezone.utc))
    return SessaoGoogle(resposta.session.access_token, str(utilizador.id), conta_nova)


def apagar_utilizador(user_id: str) -> None:
    """Apaga a conta no Supabase Auth (precisa da chave secreta). As tabelas com ON DELETE CASCADE
    apagam os dados dele; a chamadas_ia fica com o user_id a NULL (sql/014), só para as contas de custos."""
    supabase.auth.admin.delete_user(user_id)


def verificar_assinatura(user_id: str) -> None:
    """Responde 403 se o utilizador não tiver linha na tabela assinaturas.

    Um plano pago que terminou já não bloqueia: a conta passa a valer como Free
    (plano_efetivo em limites.py), sem mudar nada na base de dados.
    """
    resposta = supabase.table("assinaturas").select("user_id").eq("user_id", user_id).execute()
    if not resposta.data:
        raise HTTPException(status_code=403, detail="Sem assinatura ativa")


# As chaves públicas do Supabase (JWKS), guardadas em memória: os tokens validam-se aqui (token_supabase.py).
CHAVES_SUPABASE = CacheJWKS(url_jwks(SUPABASE_URL))
EMISSOR_SUPABASE = emissor_esperado(SUPABASE_URL)


def _id_pelo_supabase(request: Request, token: str) -> str:
    """Pergunta ao Supabase de quem é o token (get_user): apanha também contas apagadas e sessões terminadas."""
    try:
        resposta = supabase.auth.get_user(token)
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Token inválido")
    request.state.confirmado_no_supabase = True
    return resposta.user.id


def _id_do_token(request: Request, token: str) -> str:
    """O id do dono do token: validado aqui com o JWKS; se não der para decidir aqui, pelo get_user."""
    try:
        user_id = ler_token_supabase(token, CHAVES_SUPABASE, EMISSOR_SUPABASE)
    except TokenInvalido:
        raise HTTPException(status_code=401, detail="Token inválido")
    if user_id is None:
        return _id_pelo_supabase(request, token)
    return user_id


def obter_utilizador_atual(
    request: Request, credenciais: HTTPAuthorizationCredentials = Depends(esquema_bearer)
) -> str:
    """Devolve o id (UUID) do dono do token: 401 se o token for inválido, 403 sem assinatura.

    Com a demo ligada, tenta primeiro o token da demo (demo.py); se não for um, segue para o token do Supabase,
    validado na API com o JWKS (sem pedir ao Supabase) ou, se não der, pelo get_user.
    Um token validado na API vale até expirar, mesmo de uma conta apagada; mas o verificar_assinatura corre
    em todos os pedidos e a assinatura apaga-se com a conta (ON DELETE CASCADE), por isso essa conta leva 403.
    A conta de demo (pelo id, venha o token de onde vier) só usa as rotas de PERMISSOES_DEMO: as outras dão 423.
    """
    token = credenciais.credentials
    config = config_demo()

    if config.ligada:
        sub = ler_token_demo(token, config)
        if sub is not None:
            # Assinado com o nosso segredo mas para outra conta: nunca devia acontecer, por isso recusa-se.
            if sub != config.user_id:
                raise HTTPException(status_code=401, detail="Token inválido")
            # Devolve-se o id da configuração, nunca o que vem no token.
            exigir_permissao_demo(request)
            verificar_assinatura(config.user_id)
            return config.user_id

    user_id = _id_do_token(request, token)
    # Todas as rotas usam esta função, por isso a verificação da assinatura protege a API inteira.
    verificar_assinatura(user_id)
    # Quem entrar na conta de demo com o email e a palavra-passe fica com as mesmas regras da demo.
    if config.user_id is not None and str(user_id).lower() == config.user_id:
        exigir_permissao_demo(request)
    return user_id


def obter_utilizador_confirmado(
    request: Request,
    user_id: str = Depends(obter_utilizador_atual),
    credenciais: HTTPAuthorizationCredentials = Depends(esquema_bearer),
) -> str:
    """Como o obter_utilizador_atual, mas confirma sempre no Supabase (get_user) que a sessão ainda vale.

    Para as rotas que não se podem desfazer (DELETE /conta): um token roubado de uma sessão terminada
    ou de uma conta bloqueada no painel não chega para apagar a conta.
    """
    if getattr(request.state, "confirmado_no_supabase", False):
        return user_id
    if str(_id_pelo_supabase(request, credenciais.credentials)).lower() != str(user_id).lower():
        raise HTTPException(status_code=401, detail="Token inválido")
    return user_id
