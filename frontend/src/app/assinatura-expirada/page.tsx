"use client";

import { useRouter } from "next/navigation";

import Logo from "@/components/Logo";
import { apagarToken } from "@/lib/api";

// Aparece quando a API responde 403: o login está certo, mas o acesso já acabou (ou ainda não foi ativado).
export default function PaginaAssinaturaExpirada() {
  const router = useRouter();

  function sair() {
    apagarToken();
    router.replace("/login");
  }

  return (
    <main className="flex flex-1 items-center justify-center bg-fundo p-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-borda bg-cartao p-6 text-center">
        <div className="flex justify-center pb-2">
          <Logo altura={48} />
        </div>
        <h1 className="text-lg font-semibold text-texto">O teu acesso terminou</h1>
        <p className="text-sm text-texto-suave">
          A tua assinatura da Control Prices expirou. Os teus dados continuam guardados: assim que renovares, voltas a
          ver tudo como deixaste.
        </p>
        <p className="text-sm text-texto-suave">Para renovar, fala com quem te deu o acesso.</p>
        <button
          type="button"
          onClick={sair}
          className="w-full rounded-md border border-borda py-2 text-sm text-texto hover:bg-fundo"
        >
          Sair da conta
        </button>
      </div>
    </main>
  );
}
