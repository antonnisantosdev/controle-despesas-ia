from urllib.parse import urlencode

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AuthApiError, AuthError, ClientOptions, create_client

from database import SUPABASE_KEY, SUPABASE_URL, supabase
from demo import config_demo, exigir_permissao_demo, ler_token_demo

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


def fazer_registo(email: str, password: str) -> None:
    """Cria a conta no Supabase Auth. O Supabase envia o email de confirmação,
    e o gatilho do sql/013_registo_publico.sql dá-lhe logo o plano Free."""
    cliente = create_client(SUPABASE_URL, SUPABASE_KEY)
    cliente.auth.sign_up({"email": email, "password": password})


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


def trocar_codigo_google(codigo: str, code_verifier: str) -> str:
    """Troca o ?code= do regresso do Google pelo token de acesso do utilizador (como o fazer_login).

    O Supabase só aceita o código com o segredo cujo SHA-256 recebeu no início (POST /auth/v1/token?grant_type=pkce).
    Levanta AuthError se o código ou o segredo não servirem. O refresh_token fica de fora, como no login com email.
    """
    cliente = cliente_sem_sessao()
    resposta = cliente.auth.exchange_code_for_session({"auth_code": codigo, "code_verifier": code_verifier})
    if not resposta.session or not resposta.session.access_token:
        raise AuthError("Sem sessão na troca do código", None)
    return resposta.session.access_token


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


def obter_utilizador_atual(
    request: Request, credenciais: HTTPAuthorizationCredentials = Depends(esquema_bearer)
) -> str:
    """Devolve o id (UUID) do dono do token: 401 se o token for inválido, 403 sem assinatura.

    Com a demo ligada, tenta primeiro o token da demo (demo.py); se não for um, segue para o Supabase.
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

    try:
        resposta = supabase.auth.get_user(token)
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user_id = resposta.user.id
    # Todas as rotas usam esta função, por isso a verificação da assinatura protege a API inteira.
    verificar_assinatura(user_id)
    # Quem entrar na conta de demo com o email e a palavra-passe fica com as mesmas regras da demo.
    if config.user_id is not None and str(user_id).lower() == config.user_id:
        exigir_permissao_demo(request)
    return user_id
