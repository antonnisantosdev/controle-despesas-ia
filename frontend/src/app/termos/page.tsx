import type { Metadata } from "next";

import PaginaLegal from "@/components/PaginaLegal";
import { METADATA_LEGAL, TERMOS_MD } from "@/lib/textosLegais";

export const metadata: Metadata = METADATA_LEGAL.termos;

// Termos de Utilização (pública, sem login).
export default function PaginaTermos() {
  return <PaginaLegal markdown={TERMOS_MD} />;
}
