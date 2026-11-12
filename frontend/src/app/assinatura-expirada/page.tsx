"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import Logo from "@/components/Logo";
import { apagarToken } from "@/lib/api";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_PLANOS } from "@/lib/textosPlanos";

// Aparece quando a API responde 403: o login está certo, mas a conta não tem assinatura.
// Um plano pago que termina já não manda para aqui (a conta passa a Free sozinha, sem 403).
// Sem botão para o dashboard: a API voltava a responder 403 e a pessoa ficava num ciclo.
export default function PaginaAssinaturaExpirada() {
  const { TEXTOS_EXPIRADA } = useTextos(DICIONARIO_PLANOS);
  const router = useRouter();

  function sair() {
    apagarToken();
    router.replace("/login");
  }

  return (
    <main className="flex flex-1 items-center justify-center bg-fundo p-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-borda bg-cartao p-6 text-center sm:p-8">
        <div className="flex justify-center pb-2">
          <Logo altura={48} />
        </div>
        <h1 className="text-lg font-semibold text-texto">{TEXTOS_EXPIRADA.titulo}</h1>
        <p className="pb-2 text-sm text-texto-suave">{TEXTOS_EXPIRADA.texto1}</p>
        <Link
          href="/precos"
          className="flex min-h-11 w-full items-center justify-center rounded-md bg-destaque px-4 text-sm font-semibold text-white transition-colors hover:bg-destaque-hover dark:text-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          {TEXTOS_EXPIRADA.botaoPlanos}
        </Link>
        <button
          type="button"
          onClick={sair}
          className="flex min-h-11 w-full items-center justify-center rounded-md border border-borda px-4 text-sm font-medium text-texto transition-colors hover:bg-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          {TEXTOS_EXPIRADA.botaoSair}
        </button>
      </div>
    </main>
  );
}
