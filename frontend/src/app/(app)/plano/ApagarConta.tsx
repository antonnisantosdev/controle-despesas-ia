"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import NotaDemo, { ID_NOTA_DEMO } from "@/components/NotaDemo";
import { apagarToken, eBloqueadoNaDemo, pedirApi, SessaoExpirada, terminarSessaoContaApagada } from "@/lib/api";
import { TEXTOS_APAGAR_CONTA } from "@/lib/textosPlanos";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// Zona "Apagar conta" (DELETE /conta). Só apaga depois de escrever APAGAR; a API pede o mesmo no corpo.
// Na demo fica desligada (a API responde 423 na mesma).
export default function ApagarConta() {
  const router = useRouter();
  const demo = useSessaoDemo();
  const [texto, setTexto] = useState("");
  const [aApagar, setAApagar] = useState(false);
  const [erro, setErro] = useState("");
  const confirmado = texto === TEXTOS_APAGAR_CONTA.palavra;

  async function apagar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!confirmado || demo) return;
    setErro("");
    setAApagar(true);
    try {
      await pedirApi("/conta", { confirmacao: TEXTOS_APAGAR_CONTA.palavra }, "DELETE");
      // A conta já não existe: limpa a sessão e vai para a página inicial (que mostra o aviso no login).
      terminarSessaoContaApagada();
      router.replace("/");
    } catch (e) {
      setAApagar(false);
      if (e instanceof SessaoExpirada) {
        apagarToken();
        router.replace("/login");
      } else if (!eBloqueadoNaDemo(e)) {
        setErro(TEXTOS_APAGAR_CONTA.erro); // 423 da demo: a faixa já explica
      }
    }
  }

  return (
    <section
      aria-labelledby="titulo-apagar-conta"
      className="space-y-3 rounded-xl border border-red-300 bg-cartao p-4 dark:border-red-900 sm:p-6"
    >
      <h2 id="titulo-apagar-conta" className="text-lg font-semibold text-texto">
        {TEXTOS_APAGAR_CONTA.titulo}
      </h2>
      <p id="aviso-apagar-conta" className="text-sm text-red-800 dark:text-red-300">
        {TEXTOS_APAGAR_CONTA.aviso}
      </p>
      <NotaDemo />
      <form onSubmit={apagar} className="space-y-3">
        <label className="block">
          <span className="text-sm text-texto-suave">{TEXTOS_APAGAR_CONTA.rotuloCampo}</span>
          <input
            type="text"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            disabled={demo || aApagar}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            aria-describedby={demo ? `aviso-apagar-conta ${ID_NOTA_DEMO}` : "aviso-apagar-conta"}
            className="mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-texto disabled:opacity-50 sm:max-w-xs"
          />
        </label>
        {erro && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {erro}
          </p>
        )}
        <button
          type="submit"
          disabled={!confirmado || aApagar || demo}
          aria-describedby={demo ? ID_NOTA_DEMO : undefined}
          className="min-h-11 w-full rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {aApagar ? TEXTOS_APAGAR_CONTA.aApagar : TEXTOS_APAGAR_CONTA.botao}
        </button>
      </form>
    </section>
  );
}
