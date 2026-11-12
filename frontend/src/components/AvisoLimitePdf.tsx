"use client";

import { useEstadoPlano } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_PLANOS } from "@/lib/textosPlanos";

// O aviso do 429 do limite de extratos PDF do mês. Mesmo aspeto do AvisoLimite.
// O número vem do /plano (pdf_limite, do ProvedorConta no layout da app); enquanto não chega (ou se falhar), o texto sai sem ele.
export default function AvisoLimitePdf() {
  const { TEXTOS_LIMITE_PDF } = useTextos(DICIONARIO_PLANOS);
  const estado = useEstadoPlano();
  const limite = estado && estado.pdf_limite > 0 ? estado.pdf_limite : null;

  const texto =
    limite !== null ? preencher(TEXTOS_LIMITE_PDF.texto, { limite }) : TEXTOS_LIMITE_PDF.texto.replace(" {limite}", "");

  return (
    <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm sm:p-4 dark:border-amber-800 dark:bg-amber-950/40">
      <p className="font-medium text-amber-900 dark:text-amber-200">{TEXTOS_LIMITE_PDF.titulo}</p>
      <p className="mt-1 text-amber-900 dark:text-amber-200">{texto}</p>
    </div>
  );
}
