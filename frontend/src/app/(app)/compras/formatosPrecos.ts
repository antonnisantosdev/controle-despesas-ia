import { SUFIXO_UNIDADE, TEXTOS_PRECOS_LOJAS as T } from "@/lib/textosPrecosLojas";
import { preencher } from "@/lib/planos";

import { euros } from "../dashboard/formatos";

// "2026-10-28" -> "28/10/2026"
export function dataCurta(data: string) {
  return new Date(`${data}T00:00:00`).toLocaleDateString("pt-PT");
}

// 1.09 + "kg" -> "1,09 €/kg"
export function precoUnitario(valor: number, unidade: string) {
  return `${euros(valor)}${SUFIXO_UNIDADE[unidade] ?? ""}`;
}

export function textoLojas(n: number) {
  return n === 1 ? T.lojas1 : preencher(T.lojasN, { n });
}

export function textoCompras(n: number) {
  return n === 1 ? T.compras1 : preencher(T.comprasN, { n });
}

// Botões e campos com o mesmo aspeto do resto da app (alvo de toque de 44 px).
export const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto";
export const ESTILO_BOTAO =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-borda bg-cartao px-4 text-sm font-medium text-texto hover:bg-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-not-allowed disabled:opacity-50";
export const ESTILO_BOTAO_PRINCIPAL =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-destaque px-4 text-sm font-semibold text-white hover:bg-destaque-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-not-allowed disabled:opacity-50 dark:text-fundo";
export const ESTILO_ERRO = "rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300";
export const ESTILO_SUCESSO =
  "rounded-md bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300";
