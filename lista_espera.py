"""Lista de espera do Brasil (sql/019): quem pede para ser avisado quando a app abrir no Brasil.

Só se guarda o email (em minúsculas), o país onde vive, os países dos cartões/contas, a origem (canal do utm_source), a data do consentimento
e a versão do texto do consentimento (VERSAO_CONSENTIMENTO, posta aqui e nunca vinda do browser).
Um email que já esteja na lista fica como está (a rota responde igual, para não revelar quem já se inscreveu).
Nada aqui escreve o email nos logs.
"""

from datetime import datetime, timezone

from postgrest.types import ReturnMethod

from database import supabase


# A versão do texto da caixa de consentimento da página /brasil (frontend/src/lib/textosBrasil.ts).
# Mudar sempre que esse texto mudar: assim sabe-se o que cada pessoa aceitou.
VERSAO_CONSENTIMENTO = "br-2026-11-11"


def agora_utc() -> datetime:
    """A hora atual em UTC. Função à parte para os testes poderem fixá-la."""
    return datetime.now(timezone.utc)


def inscrever(email: str, pais: str, paises_cartoes: list[str], origem: str | None) -> None:
    """Junta o email à lista de espera; se já lá estiver, não muda nada (nem a data do consentimento).

    upsert com ignore_duplicates: um INSERT ... ON CONFLICT (email) DO NOTHING, sem erro no segundo pedido.
    Levanta a exceção do Supabase se a gravação falhar (a rota responde 503).
    """
    linha = {
        "email": email,
        "pais": pais,
        "paises_cartoes": paises_cartoes,
        "origem": origem,
        "consentimento_em": agora_utc().isoformat(),
        "consentimento_versao": VERSAO_CONSENTIMENTO,
    }
    # returning minimal: o Supabase não devolve a linha (não há nada a ler de volta).
    supabase.table("lista_espera").upsert(
        linha, on_conflict="email", ignore_duplicates=True, returning=ReturnMethod.minimal
    ).execute()
