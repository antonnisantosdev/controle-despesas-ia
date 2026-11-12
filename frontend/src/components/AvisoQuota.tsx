"use client";

import Link from "next/link";

import type { EstadoPlano } from "@/lib/api";
import { avisoDeQuota } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_PLANOS } from "@/lib/textosPlanos";

// Faixa discreta quando já se usou 80% (ou mais) dos pedidos à IA do período, antes de chegar ao limite.
// Abaixo dos 80% e no limite (aí aparece o AvisoLimite) não mostra nada.
// role="status" e não "alert": é uma informação, não um erro, e não deve interromper o leitor de ecrã.
export default function AvisoQuota({ estado }: { estado: EstadoPlano | null }) {
  const textosPlanos = useTextos(DICIONARIO_PLANOS);
  const { TEXTOS_AVISO_QUOTA } = textosPlanos;
  const aviso = estado ? avisoDeQuota(estado, textosPlanos) : null;
  if (!aviso) return null;

  return (
    <div
      role="status"
      className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
    >
      <p>{aviso.texto}</p>
      {aviso.mostrarLink && (
        <Link
          href="/plano"
          className="inline-flex min-h-11 items-center rounded-md font-semibold underline underline-offset-2 hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          {TEXTOS_AVISO_QUOTA.link}
        </Link>
      )}
    </div>
  );
}
