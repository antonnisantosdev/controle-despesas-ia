// Origem do registo: o canal de onde a pessoa veio (?utm_source= dos links das redes), sem cookies.
// Guarda-se só o canal normalizado no sessionStorage (desaparece ao fechar o separador) e envia-se
// no POST /registo, no regresso do login com o Google e no POST /lista-espera.
// A API volta a normalizar (models.normalizar_origem): esta lista é só para não guardar lixo no browser.

const CHAVE_ORIGEM = "origem";
const CANAIS = ["instagram", "youtube", "tiktok", "linkedin"] as const;

export type Origem = (typeof CANAIS)[number] | "outro";

// Um canal conhecido fica igual (sem espaços, em minúsculas); outro valor passa a "outro"; vazio fica null.
export function normalizarOrigem(valor: string | null): Origem | null {
  const texto = (valor ?? "").trim().toLowerCase();
  if (!texto) return null;
  return (CANAIS as readonly string[]).includes(texto) ? (texto as Origem) : "outro";
}

// Lê o ?utm_source= do endereço e, se houver, guarda o canal. Sem utm_source não mexe no que já estava.
export function guardarOrigemDoEndereco(query: string): void {
  const origem = normalizarOrigem(new URLSearchParams(query).get("utm_source"));
  if (!origem) return;
  try {
    sessionStorage.setItem(CHAVE_ORIGEM, origem);
  } catch {
    // Armazenamento bloqueado (ex.: modo privado restrito): fica sem origem, nada mais.
  }
}

// O canal guardado nesta sessão, ou undefined (assim o JSON.stringify deixa o campo de fora).
export function lerOrigem(): Origem | undefined {
  try {
    return normalizarOrigem(sessionStorage.getItem(CHAVE_ORIGEM)) ?? undefined;
  } catch {
    return undefined;
  }
}
