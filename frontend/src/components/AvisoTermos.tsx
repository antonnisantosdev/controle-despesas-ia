import Link from "next/link";

import { TEXTOS_TERMOS } from "@/lib/textosLogin";

const ESTILO_LINK =
  "font-medium text-destaque-hover underline hover:no-underline focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";

// "Ao criar conta, aceitas os Termos de Utilização e a Política de Privacidade." (registo e login com o Google).
// Sem caixa obrigatória. Os links abrem na mesma aba.
export default function AvisoTermos() {
  return (
    <p className="text-center text-xs text-texto-suave">
      {TEXTOS_TERMOS.antes}
      <Link href="/termos" className={ESTILO_LINK}>
        {TEXTOS_TERMOS.termos}
      </Link>
      {TEXTOS_TERMOS.meio}
      <Link href="/privacidade" className={ESTILO_LINK}>
        {TEXTOS_TERMOS.privacidade}
      </Link>
      {TEXTOS_TERMOS.fim}
    </p>
  );
}
