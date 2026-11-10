"use client";

import dynamic from "next/dynamic";

import Logo from "@/components/Logo";
import { TEXTOS_GOOGLE } from "@/lib/textosLogin";

// O código do endereço e o segredo PKCE só existem no browser, por isso esta parte não é desenhada no servidor.
const RegressoGoogle = dynamic(() => import("./RegressoGoogle"), {
  ssr: false,
  loading: () => <p className="text-sm text-texto-suave">{TEXTOS_GOOGLE.aEntrar}</p>,
});

// Página para onde o Supabase volta depois do login com o Google (pública, fora do grupo (app)).
export default function PaginaRegressoGoogle() {
  return (
    <main className="flex flex-1 items-center justify-center bg-fundo p-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-borda bg-cartao p-6 text-center">
        <h1 className="flex justify-center pb-2">
          <Logo altura={48} />
        </h1>
        <RegressoGoogle />
      </div>
    </main>
  );
}
