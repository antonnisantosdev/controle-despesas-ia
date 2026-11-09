"use client";

import { useEffect, useState } from "react";

import { pedirEstadoPlano } from "@/lib/api";
import { preencher } from "@/lib/planos";
import { TEXTOS_LIMITE_PDF } from "@/lib/textosPlanos";

// O aviso do 429 do limite de extratos PDF do mês. Mesmo aspeto do AvisoLimite.
// O número vem do /plano (pdf_limite); enquanto não chega (ou se falhar), o texto sai sem ele.
export default function AvisoLimitePdf() {
  const [limite, setLimite] = useState<number | null>(null);

  useEffect(() => {
    pedirEstadoPlano()
      .then((estado) => setLimite(estado.pdf_limite > 0 ? estado.pdf_limite : null))
      .catch(() => setLimite(null));
  }, []);

  const texto =
    limite !== null ? preencher(TEXTOS_LIMITE_PDF.texto, { limite }) : TEXTOS_LIMITE_PDF.texto.replace(" {limite}", "");

  return (
    <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm sm:p-4 dark:border-amber-800 dark:bg-amber-950/40">
      <p className="font-medium text-amber-900 dark:text-amber-200">{TEXTOS_LIMITE_PDF.titulo}</p>
      <p className="mt-1 text-amber-900 dark:text-amber-200">{texto}</p>
    </div>
  );
}
