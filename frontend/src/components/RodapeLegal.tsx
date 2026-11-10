import Link from "next/link";

import { METADATA_LEGAL } from "@/lib/textosLegais";

const ESTILO_LINK =
  "inline-flex min-h-11 items-center rounded-md px-2 text-texto-suave hover:text-texto hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";

// Links para os Termos de Utilização e a Política de Privacidade (páginas públicas, sem login).
// Nas páginas públicas (login, registo, preços, termos, privacidade) e no fundo da app.
export default function RodapeLegal({ className = "" }: { className?: string }) {
  return (
    <nav aria-label={METADATA_LEGAL.rodape.rotulo} className={`flex flex-wrap justify-center gap-x-2 text-xs ${className}`}>
      <Link href="/termos" className={ESTILO_LINK}>
        {METADATA_LEGAL.rodape.termos}
      </Link>
      <Link href="/privacidade" className={ESTILO_LINK}>
        {METADATA_LEGAL.rodape.privacidade}
      </Link>
    </nav>
  );
}
