"use client";

import { useEffect, useState } from "react";

import { EVENTO_A_ACORDAR } from "@/lib/api";

// Faixa no fundo do ecrã enquanto a API está a acordar (o api.ts avisa com um evento).
// Fica fora das páginas para funcionar em todas, sem cada uma ter de tratar disto.
export default function AvisoServidor() {
  const [aAcordar, setAAcordar] = useState(false);

  useEffect(() => {
    function mudou(evento: Event) {
      setAAcordar((evento as CustomEvent<boolean>).detail);
    }
    window.addEventListener(EVENTO_A_ACORDAR, mudou);
    return () => window.removeEventListener(EVENTO_A_ACORDAR, mudou);
  }, []);

  if (!aAcordar) return null;

  return (
    <div
      role="status"
      className="fixed print:hidden inset-x-4 bottom-4 z-50 mx-auto max-w-md rounded-lg border border-borda bg-cartao p-3 text-center text-sm text-texto shadow-lg"
    >
      A acordar o servidor, pode demorar até um minuto...
    </div>
  );
}
