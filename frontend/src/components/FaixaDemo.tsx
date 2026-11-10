"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EVENTO_BLOQUEADO_DEMO } from "@/lib/api";
import { TEXTOS_DEMO } from "@/lib/textosDemo";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// Segundos que a mensagem do 423 fica visível.
const SEGUNDOS_AVISO = 6;

// Faixa no topo da app numa sessão de demo: "Modo demo: dados inventados, só leitura".
// Quando a API recusa uma alteração (423), mostra a explicação por baixo durante uns segundos.
export default function FaixaDemo() {
  const demo = useSessaoDemo();
  const [bloqueado, setBloqueado] = useState(false);

  useEffect(() => {
    let temporizador: ReturnType<typeof setTimeout> | undefined;
    function mostrar() {
      setBloqueado(true);
      clearTimeout(temporizador);
      temporizador = setTimeout(() => setBloqueado(false), SEGUNDOS_AVISO * 1000);
    }
    window.addEventListener(EVENTO_BLOQUEADO_DEMO, mostrar);
    return () => {
      window.removeEventListener(EVENTO_BLOQUEADO_DEMO, mostrar);
      clearTimeout(temporizador);
    };
  }, []);

  if (!demo) return null;

  return (
    <div className="border-b border-amber-300 print:hidden bg-amber-50 px-4 py-2 text-sm dark:border-amber-800 dark:bg-amber-950/40">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <p className="font-medium text-amber-900 dark:text-amber-200">{TEXTOS_DEMO.faixa}</p>
        <Link
          href="/registo"
          className="inline-flex min-h-11 items-center rounded-md font-semibold text-amber-900 underline underline-offset-2 hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque sm:min-h-0 dark:text-amber-200"
        >
          {TEXTOS_DEMO.faixaCriarConta}
        </Link>
      </div>
      {/* role="status": os leitores de ecrã anunciam a mensagem quando aparece. */}
      <p role="status" className="mx-auto max-w-6xl text-amber-900 empty:hidden dark:text-amber-200">
        {bloqueado ? TEXTOS_DEMO.bloqueado : ""}
      </p>
    </div>
  );
}
