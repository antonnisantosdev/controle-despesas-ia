"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apagarToken, pedirApi, SessaoExpirada, type Objetivo } from "@/lib/api";

import CartaoObjetivo from "./CartaoObjetivo";
import FormNovoObjetivo from "./FormNovoObjetivo";
import SimuladorPoupanca from "./SimuladorPoupanca";

export default function PaginaReserva() {
  const router = useRouter();
  const [objetivos, setObjetivos] = useState<Objetivo[] | null>(null); // null = ainda a carregar
  const [aCriar, setACriar] = useState(false);
  const [erro, setErro] = useState("");

  function tratarSessao(e: unknown) {
    if (e instanceof SessaoExpirada) {
      apagarToken();
      router.replace("/login");
    }
  }

  useEffect(() => {
    pedirApi<Objetivo[]>("/objetivos")
      .then(setObjetivos)
      .catch((e) => {
        if (e instanceof SessaoExpirada) tratarSessao(e);
        else setErro("Não foi possível carregar os objetivos. Confirma que a API está a correr.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function criado(objetivo: Objetivo) {
    setACriar(false);
    // Mantém a ordem da API: do prazo mais próximo para o mais distante.
    setObjetivos((anteriores) =>
      [...(anteriores ?? []), objetivo].sort((a, b) => a.data_alvo.localeCompare(b.data_alvo)),
    );
  }

  function mudou(objetivo: Objetivo) {
    setObjetivos((anteriores) => (anteriores ?? []).map((o) => (o.id === objetivo.id ? objetivo : o)));
  }

  function apagado(id: number) {
    setObjetivos((anteriores) => (anteriores ?? []).filter((o) => o.id !== id));
  }

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-destaque">Objetivos de poupança</p>
            <h1 className="text-2xl font-semibold text-texto">Minha reserva</h1>
          </div>
          <button
            type="button"
            onClick={() => setACriar(true)}
            className="rounded-lg bg-destaque px-4 py-2 text-sm font-medium text-white hover:bg-destaque-hover"
          >
            + Novo objetivo
          </button>
        </header>

        {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}

        {aCriar && <FormNovoObjetivo onCriado={criado} onFechar={() => setACriar(false)} onSessaoExpirada={tratarSessao} />}

        {objetivos === null && !erro && <p className="text-sm text-texto-suave">A carregar...</p>}
        {objetivos?.length === 0 && !aCriar && (
          <p className="rounded-xl border border-borda bg-cartao p-6 text-sm text-texto-suave">
            Ainda não tens objetivos. Cria o primeiro, por exemplo as férias do próximo verão.
          </p>
        )}

        <div className="space-y-4">
          {objetivos?.map((objetivo) => (
            <CartaoObjetivo
              key={objetivo.id}
              objetivo={objetivo}
              onMudou={mudou}
              onApagado={apagado}
              onSessaoExpirada={tratarSessao}
            />
          ))}
        </div>

        <SimuladorPoupanca onSessaoExpirada={tratarSessao} />
      </div>
    </main>
  );
}
