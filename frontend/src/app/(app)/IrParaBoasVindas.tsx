"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useEstadoPlano } from "@/lib/conta";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

export const CAMINHO_BOAS_VINDAS = "/boas-vindas";

// Numa conta nova que ainda não fez o questionário de boas-vindas (GET /plano: boas_vindas_pendente),
// leva-a para /boas-vindas, venha de que página vier. Nunca na demo (a API também diz sempre false).
// Não desenha nada.
export default function IrParaBoasVindas() {
  const estado = useEstadoPlano();
  const demo = useSessaoDemo();
  const pagina = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (demo || !estado?.boas_vindas_pendente || pagina === CAMINHO_BOAS_VINDAS) return;
    router.replace(CAMINHO_BOAS_VINDAS);
  }, [estado, demo, pagina, router]);

  return null;
}
