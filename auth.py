from datetime import date

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


def verificar_assinatura(user_id: str) -> None:
    """Responde 403 se o utilizador não tiver assinatura, ou se ela já tiver acabado."""
    resposta = supabase.table("assinaturas").select("ativo_ate").eq("user_id", user_id).execute()

    if not resposta.data or not resposta.data[0]["ativo_ate"]:
        raise HTTPException(status_code=403, detail="Sem assinatura ativa")

    # O ativo_ate conta como dia de acesso: só bloqueia a partir do dia seguinte.
    ativo_ate = date.fromisoformat(resposta.data[0]["ativo_ate"])
    if ativo_ate < date.today():
        raise HTTPException(status_code=403, detail="A tua assinatura expirou")


def obter_utilizador_atual(credenciais: HTTPAuthorizationCredentials = Depends(esquema_bearer)) -> str:
    """Devolve o id (UUID) do dono do token: 401 se o token for inválido, 403 sem assinatura ativa."""
    token = credenciais.credentials
    try:
        resposta = supabase.auth.get_user(token)
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Token inválido")
    # Todas as rotas usam esta função, por isso a verificação da assinatura protege a API inteira.
    verificar_assinatura(resposta.user.id)
    return resposta.user.id
