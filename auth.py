from urllib.parse import urlencode

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AuthApiError, create_client

from database import SUPABASE_KEY, SUPABASE_URL, supabase
# Lê o cabeçalho "Authorization: Bearer <token>" de cada pedido.
# Também faz aparecer o botão "Authorize" no /docs.
esquema_bearer = HTTPBearer()


def fazer_login(email: str, password: str) -> str:
    """Faz login no Supabase Auth e devolve o token de acesso do utilizador."""
    # Cliente próprio para o login: a sessão do utilizador não "contamina" o cliente partilhado.
    cliente = create_client(SUPABASE_URL, SUPABASE_KEY)
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


def url_login_google(destino: str) -> str:
    """O endereço do Supabase que abre o login com o Google e, no fim, volta ao destino.

    O Supabase devolve o token no fragmento do URL (#access_token=...), que só o browser vê.
    """
    parametros = urlencode({"provider": "google", "redirect_to": destino})
    return f"{SUPABASE_URL.rstrip('/')}/auth/v1/authorize?{parametros}"


def verificar_assinatura(user_id: str) -> None:
    """Responde 403 se o utilizador não tiver linha na tabela assinaturas.

    Um plano pago que terminou já não bloqueia: a conta passa a valer como Free
    (plano_efetivo em limites.py), sem mudar nada na base de dados.
    """
    resposta = supabase.table("assinaturas").select("user_id").eq("user_id", user_id).execute()
    if not resposta.data:
        raise HTTPException(status_code=403, detail="Sem assinatura ativa")


def obter_utilizador_atual(credenciais: HTTPAuthorizationCredentials = Depends(esquema_bearer)) -> str:
    """Devolve o id (UUID) do dono do token: 401 se o token for inválido, 403 sem assinatura."""
    token = credenciais.credentials
    try:
        resposta = supabase.auth.get_user(token)
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Token inválido")
    # Todas as rotas usam esta função, por isso a verificação da assinatura protege a API inteira.
    verificar_assinatura(resposta.user.id)
    return resposta.user.id
