"use client";

import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { demoTerminou, ErroApi, EVENTO_SESSAO, guardarToken, pedirTokenDemo } from "@/lib/api";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_DEMO, type TextosDemo } from "@/lib/textosDemo";

// Avisa o React quando a marca "a sessão da demo terminou" muda (ver enviarComToken em api.ts).
function subscrever(avisar: () => void) {
  window.addEventListener(EVENTO_SESSAO, avisar);
  return () => window.removeEventListener(EVENTO_SESSAO, avisar);
}

// A mensagem para cada erro do POST /demo: 429 (o texto da API, se vier), 503 (demo desligada) ou outro.
function mensagemDoErro(e: unknown, { TEXTOS_DEMO }: TextosDemo): string {
  if (e instanceof ErroApi && e.status === 429) return typeof e.detalhe === "string" ? e.detalhe : TEXTOS_DEMO.limiteEntradas;
  if (e instanceof ErroApi && e.status === 503) return TEXTOS_DEMO.indisponivel;
  return TEXTOS_DEMO.erroEntrar;
}

// "Ver a demo": pede o token da conta de demo (POST /demo), guarda-o como o login normal
// (marcado como sessão de demo) e abre o dashboard.
export default function BotaoDemo() {
  const textosDemo = useTextos(DICIONARIO_DEMO);
  const { TEXTOS_DEMO } = textosDemo;
  const router = useRouter();
  const [aEntrar, setAEntrar] = useState(false);
  const [erro, setErro] = useState("");
  // A sessão da demo anterior expirou e não deu para a renovar: explica porque se voltou ao login.
  const terminou = useSyncExternalStore(subscrever, demoTerminou, () => false);

  async function entrar() {
    setErro("");
    setAEntrar(true);
    try {
      guardarToken(await pedirTokenDemo(), true);
      router.push("/dashboard");
    } catch (e) {
      setErro(mensagemDoErro(e, textosDemo));
      setAEntrar(false);
    }
  }

  return (
    <div className="space-y-1">
      {terminou && !erro && (
        <p role="status" className="pb-1 text-center text-sm text-texto">
          {TEXTOS_DEMO.sessaoTerminou}
        </p>
      )}
      <button
        type="button"
        onClick={entrar}
        disabled={aEntrar}
        aria-busy={aEntrar}
        className="flex min-h-11 w-full items-center justify-center rounded-md border border-borda px-4 py-2 text-sm font-semibold text-texto hover:bg-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-50"
      >
        {aEntrar ? TEXTOS_DEMO.aEntrar : TEXTOS_DEMO.botao}
      </button>
      <p className="text-center text-xs text-texto-suave">{TEXTOS_DEMO.explicacaoBotao}</p>
      {erro && (
        <p role="alert" className="text-center text-sm text-red-600 dark:text-red-400">
          {erro}
        </p>
      )}
    </div>
  );
}
