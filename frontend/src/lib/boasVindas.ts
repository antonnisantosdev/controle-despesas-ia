// Regras do perfil partilhadas pelo questionário de boas-vindas e pela página Definições.
// As mesmas do backend (perfil.py): com bancos de um só país, a moeda é a desse país; com os dois, escolhe-se.

import type { Moeda, Pais } from "./formatos";

// "ambos" = cartões e contas dos dois países.
export type Bancos = Pais | "ambos";

export const MOEDA_DO_PAIS: Record<Pais, Moeda> = { PT: "EUR", BR: "BRL" };

export function paisesDosBancos(bancos: Bancos): Pais[] {
  return bancos === "ambos" ? ["PT", "BR"] : [bancos];
}

export function bancosDe(paises: readonly Pais[]): Bancos {
  return paises.length > 1 ? "ambos" : (paises[0] ?? "PT");
}

// A moeda a enviar: a escolhida com os dois países, senão a do país.
export function moedaDosBancos(bancos: Bancos, escolhida: Moeda | null): Moeda | null {
  return bancos === "ambos" ? escolhida : MOEDA_DO_PAIS[bancos];
}
