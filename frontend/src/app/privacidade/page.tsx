import type { Metadata } from "next";

import PaginaLegal from "@/components/PaginaLegal";
import { METADATA_LEGAL, PRIVACIDADE_MD } from "@/lib/textosLegais";

export const metadata: Metadata = METADATA_LEGAL.privacidade;

// Política de Privacidade (pública, sem login).
export default function PaginaPrivacidade() {
  return <PaginaLegal markdown={PRIVACIDADE_MD} />;
}
