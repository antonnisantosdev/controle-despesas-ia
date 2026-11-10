"use client";

import Link from "next/link";

import { TEXTOS_PLANO_PAGO } from "@/lib/textosPlanos";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// O aviso de uma função só dos planos pagos (PDF, talões): o 402 da API, ou o Free antes de tentar.
// Mesmo aspeto do AvisoLimite, com o link "Mudar de plano" para a página O meu plano (/plano).
// Numa sessão de demo, sem o link (a conta de demo não muda de plano).
export default function AvisoPlanoPago({ mensagem }: { mensagem: string }) {
  const demo = useSessaoDemo();
  return (
    <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm sm:p-4 dark:border-amber-800 dark:bg-amber-950/40">
      <p className="text-amber-900 dark:text-amber-200">{mensagem}</p>
      {!demo && (
        <Link
          href="/plano"
          className="mt-1 inline-flex min-h-11 items-center rounded-md font-semibold text-amber-900 underline underline-offset-2 hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque dark:text-amber-200"
        >
          {TEXTOS_PLANO_PAGO.link}
        </Link>
      )}
    </div>
  );
}
