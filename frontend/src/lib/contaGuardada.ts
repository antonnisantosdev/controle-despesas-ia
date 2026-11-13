import { eMoeda, ePais, type Conta } from "./formatos";

// O país, a moeda e os países dos cartões da última conta que entrou neste browser (nada mais: sem email nem id).
// Serve só para a app abrir logo na língua e na moeda certas, enquanto o GET /plano não chega
// (antes abria sempre em PT-PT e mudava para PT-BR um instante depois). Quem manda é sempre o /plano.
// Apaga-se ao sair da conta (apagarToken). Se o browser não deixar usar o localStorage, fica tudo como antes.
const CHAVE = "control-prices-conta";

export function lerContaGuardada(): string | null {
  try {
    return localStorage.getItem(CHAVE);
  } catch {
    return null;
  }
}

export function guardarConta(conta: Conta): void {
  try {
    localStorage.setItem(CHAVE, JSON.stringify(conta));
  } catch {
    // Sem localStorage (modo privado, bloqueado): a app só não abre logo na língua da conta.
  }
}

export function esquecerConta(): void {
  try {
    localStorage.removeItem(CHAVE);
  } catch {
    // idem
  }
}

// O texto guardado em Conta, só se for válido (um valor mexido à mão no browser não parte nada).
export function contaDoTexto(texto: string | null): Conta | null {
  if (!texto) return null;
  try {
    const bruto: unknown = JSON.parse(texto);
    if (typeof bruto !== "object" || bruto === null) return null;
    const { pais, moeda, paisesBancos } = bruto as Record<string, unknown>;
    if (!ePais(pais) || !eMoeda(moeda) || !Array.isArray(paisesBancos)) return null;
    const bancos = [...new Set(paisesBancos.filter(ePais))];
    return bancos.length > 0 ? { pais, moeda, paisesBancos: bancos } : null;
  } catch {
    return null;
  }
}
