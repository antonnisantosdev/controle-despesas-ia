"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { pedirApi, type EstadoPlano } from "@/lib/api";
import { preencher } from "@/lib/planos";
import { TEXTOS_LIMITE } from "@/lib/textosPlanos";

// O aviso do 429 (limite diário de pedidos à IA), igual em todos os ecrãs que usam a IA.
// Pede o /plano para saber o limite e o plano: no Completo não há plano maior, por isso não há link.
export default function AvisoLimite() {
  const [estado, setEstado] = useState<EstadoPlano | null>(null);

  useEffect(() => {
    pedirApi<EstadoPlano>("/plano")
      .then(setEstado)
      .catch(() => setEstado(null)); // sem o número, mostra o aviso sem ele
  }, []);

  // Enquanto o /plano não chega (ou se falhar): "Já usaste os pedidos à IA do teu plano...", sem o número.
  const texto = estado
    ? preencher(TEXTOS_LIMITE.texto, { limite: estado.limite })
    : TEXTOS_LIMITE.texto.replace(" {limite}", "");
  const mostrarLink = estado?.plano !== "completo";

  return (
    <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm sm:p-4 dark:border-amber-800 dark:bg-amber-950/40">
      <p className="font-medium text-amber-900 dark:text-amber-200">{TEXTOS_LIMITE.titulo}</p>
      <p className="mt-1 text-amber-900 dark:text-amber-200">{texto}</p>
      {mostrarLink && (
        <Link
          href="/plano"
          className="mt-1 inline-flex min-h-11 items-center rounded-md font-semibold text-amber-900 underline underline-offset-2 hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque dark:text-amber-200"
        >
          {TEXTOS_LIMITE.link}
        </Link>
      )}
    </div>
  );
}
