// Proteção contra "login CSRF": sem isto, qualquer pessoa podia mandar um link
// /login/google#access_token=<token da conta dela> e pôr a vítima a trabalhar dentro
// da conta do atacante (os extratos importados iam parar lá).
// Ao carregar em "Continuar com Google" guarda-se uma marca neste browser; no regresso,
// o token só é aceite se a marca existir e for recente. Um atacante não consegue criar
// a marca no browser da vítima. Fica no localStorage (e não no sessionStorage) para
// sobreviver à ida ao Google numa app instalada (PWA).

const CHAVE = "login_google_iniciado";
const VALIDADE_MS = 10 * 60 * 1000; // 10 minutos chegam para escolher a conta Google

export function marcarInicioGoogle(): void {
  try {
    localStorage.setItem(CHAVE, String(Date.now()));
  } catch {
    // Sem localStorage (ex. navegação privada muito restrita): o regresso vai falhar fechado.
  }
}

// Diz se o login com Google foi começado neste browser há pouco tempo. Só lê (pode ser chamada
// duas vezes pelo React em desenvolvimento); quem a usa apaga a marca depois, com apagarMarcaGoogle.
export function marcaGoogleValida(agora: number = Date.now()): boolean {
  try {
    const valor = localStorage.getItem(CHAVE);
    if (!valor) return false;
    const criadaEm = Number(valor);
    return Number.isFinite(criadaEm) && agora - criadaEm >= 0 && agora - criadaEm < VALIDADE_MS;
  } catch {
    return false;
  }
}

// Cada marca só serve para um regresso: apaga-se sempre, com ou sem sucesso.
export function apagarMarcaGoogle(): void {
  try {
    localStorage.removeItem(CHAVE);
  } catch {
    // Nada a fazer.
  }
}
