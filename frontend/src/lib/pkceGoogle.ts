// Login com o Google em PKCE (RFC 7636).
// Ao carregar em "Continuar com Google", este browser inventa um segredo (code_verifier) e manda à API
// só o SHA-256 dele (code_challenge). O Supabase volta a /login/google com ?code=, e esse código só
// se troca pelo token junto com o segredo, que nunca saiu deste browser.
// Também protege contra o "login CSRF": um link /login/google?code=<código da conta do atacante>
// não serve, porque o browser da vítima não tem o segredo certo (substitui a antiga marca de início).
// O segredo fica no localStorage (como a marca antiga), para sobreviver à ida ao Google numa app
// instalada (PWA); dura 10 minutos e apaga-se logo que é lido no regresso.

const CHAVE = "login_google_pkce";
const VALIDADE_MS = 10 * 60 * 1000; // 10 minutos chegam para escolher a conta Google

// 43 a 128 caracteres "não reservados" (letras, números e - . _ ~), como pede o RFC 7636 e valida a API.
const FORMATO_VERIFIER = /^[A-Za-z0-9._~-]{43,128}$/;

// base64url sem "=" no fim (o "+" passa a "-" e o "/" a "_"): pode ir num URL sem ser codificado.
function base64url(bytes: Uint8Array): string {
  let binario = "";
  for (let i = 0; i < bytes.length; i++) binario += String.fromCharCode(bytes[i]);
  return btoa(binario).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

// 48 bytes aleatórios do gerador criptográfico do browser = 64 caracteres em base64url.
export function gerarVerifier(): string {
  const bytes = new Uint8Array(48);
  crypto.getRandomValues(bytes);
  return base64url(bytes);
}

// base64url(SHA-256(verifier)): sempre 43 caracteres. O crypto.subtle só existe em https e em localhost.
export async function calcularChallenge(verifier: string): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64url(new Uint8Array(hash));
}

// Guarda o segredo antes de sair para o Google. Se o browser não deixar guardar, lança um erro:
// o login não começa (sem o segredo, o regresso falharia de qualquer forma).
export function guardarVerifier(verifier: string, agora: number = Date.now()): void {
  localStorage.setItem(CHAVE, JSON.stringify({ verifier, criadoEm: agora }));
}

// O segredo guardado, se existir, tiver o formato certo e for recente. Um segredo válido só se lê
// (o React em desenvolvimento pode chamar isto duas vezes); quem o usa apaga-o logo a seguir, com
// apagarVerifier. Um segredo expirado apaga-se logo aqui: já não serve para nada.
export function lerVerifier(agora: number = Date.now()): string | null {
  try {
    const guardado = JSON.parse(localStorage.getItem(CHAVE) ?? "null");
    const verifier = guardado?.verifier;
    const criadoEm = Number(guardado?.criadoEm);
    if (typeof verifier !== "string" || !FORMATO_VERIFIER.test(verifier)) return null;
    if (!Number.isFinite(criadoEm) || agora - criadoEm < 0 || agora - criadoEm >= VALIDADE_MS) {
      localStorage.removeItem(CHAVE);
      return null;
    }
    return verifier;
  } catch {
    return null;
  }
}

// Cada segredo só serve para um regresso: apaga-se sempre, com ou sem sucesso.
// Apaga também a marca da versão antiga (login_google_iniciado), se ainda existir neste browser.
export function apagarVerifier(): void {
  try {
    localStorage.removeItem(CHAVE);
    localStorage.removeItem("login_google_iniciado");
  } catch {
    // Nada a fazer.
  }
}
