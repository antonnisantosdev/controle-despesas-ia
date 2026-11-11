import type { Metadata } from "next";

import FormularioBrasil from "./FormularioBrasil";
import Logo from "@/components/Logo";
import RodapeLegal from "@/components/RodapeLegal";
import { METADATA_BRASIL, TEXTOS_BRASIL } from "@/lib/textosBrasil";

export const metadata: Metadata = METADATA_BRASIL;

// Lista de espera do Brasil (pública, sem login), em português do Brasil (lang="pt-BR" só nesta página).
export default function PaginaBrasil() {
  return (
    <main lang="pt-BR" className="flex flex-1 items-center justify-center bg-fundo p-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-borda bg-cartao p-6">
        <div className="flex justify-center pb-2">
          <Logo altura={48} />
        </div>
        <h1 className="text-center text-xl font-semibold text-texto">{TEXTOS_BRASIL.titulo}</h1>
        <div className="space-y-1 text-center text-sm text-texto-suave">
          {TEXTOS_BRASIL.explicacao.map((linha) => (
            <p key={linha}>{linha}</p>
          ))}
        </div>
        <FormularioBrasil />
        <RodapeLegal />
      </div>
    </main>
  );
}
