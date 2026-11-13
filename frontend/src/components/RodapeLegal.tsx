"use client";

import Link from "next/link";

import { useTextosPublicos } from "@/lib/paisPublico";
import { DICIONARIO_LOGIN } from "@/lib/textosLogin";

const ESTILO_LINK =
  "inline-flex min-h-11 items-center rounded-md px-2 text-texto-suave hover:text-texto hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";

// Links para os Termos de Utilização e a Política de Privacidade (páginas públicas, sem login).
// Nas páginas públicas (login, registo, preços, termos, privacidade) e no fundo da app.
export default function RodapeLegal({ className = "" }: { className?: string }) {
  // Na app, o país da conta (guardado no browser); nas páginas públicas, a língua do browser.
  const { TEXTOS_RODAPE_LEGAL } = useTextosPublicos(DICIONARIO_LOGIN);
  return (
    <nav aria-label={TEXTOS_RODAPE_LEGAL.rotulo} className={`flex flex-wrap justify-center gap-x-2 text-xs ${className}`}>
      <Link href="/termos" className={ESTILO_LINK}>
        {TEXTOS_RODAPE_LEGAL.termos}
      </Link>
      <Link href="/privacidade" className={ESTILO_LINK}>
        {TEXTOS_RODAPE_LEGAL.privacidade}
      </Link>
    </nav>
  );
}
