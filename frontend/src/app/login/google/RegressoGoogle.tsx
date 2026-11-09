"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { guardarToken } from "@/lib/api";
import { apagarMarcaGoogle, marcaGoogleValida } from "@/lib/marcaGoogle";
import { TEXTOS_GOOGLE } from "@/lib/textosLogin";

// O que o Supabase mandou no regresso do Google: o token, ou null se houve erro ou não veio token.
// O token vem no fragmento (#access_token=...&refresh_token=...), que o browser nunca envia a nenhum servidor.
// Os erros podem vir no fragmento ou na query (?error=...&error_description=...).
function tokenDoRegresso(hash: string, query: string): string | null {
  const fragmento = new URLSearchParams(hash.replace(/^#/, ""));
  const parametros = new URLSearchParams(query);
  if (fragmento.has("error") || parametros.has("error")) return null;
  // O refresh_token fica de fora, como no login com email: quando o token expirar, faz-se login outra vez.
  return fragmento.get("access_token") || null;
}

// Só corre no browser (a page.tsx carrega-o com ssr: false), por isso pode ler o window.location logo ao abrir.
export default function RegressoGoogle() {
  const router = useRouter();
  // Lido uma só vez, quando o componente aparece (antes de o endereço ser limpo).
  // Sem a marca de início neste browser, o token é recusado: pode ser um link de um atacante
  // com o token da conta dele (ver lib/marcaGoogle.ts). A sessão que já existir fica intacta.
  const [token] = useState(() =>
    marcaGoogleValida() ? tokenDoRegresso(window.location.hash, window.location.search) : null,
  );

  useEffect(() => {
    // Tira logo o token do endereço, para não ficar no histórico nem ser copiado com o link.
    window.history.replaceState(null, "", window.location.pathname);
    apagarMarcaGoogle();
    if (!token) return;
    guardarToken(token);
    // O mesmo destino do login com email. Se o plano tiver terminado, a API responde 403
    // no dashboard e o pedirApi manda para /assinatura-expirada, como no login normal.
    router.replace("/dashboard");
  }, [token, router]);

  if (token) {
    return (
      <p className="text-sm text-texto-suave" aria-live="polite">
        {TEXTOS_GOOGLE.aEntrar}
      </p>
    );
  }

  return (
    <>
      <p role="alert" className="text-sm text-texto">
        {TEXTOS_GOOGLE.erroEntrar}
      </p>
      <Link
        href="/login"
        className="flex min-h-11 w-full items-center justify-center rounded-md bg-destaque px-4 text-sm font-semibold text-white transition-colors hover:bg-destaque-hover dark:text-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
      >
        {TEXTOS_GOOGLE.voltarLogin}
      </Link>
    </>
  );
}
