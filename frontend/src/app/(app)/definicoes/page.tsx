"use client";

import NotaDemo from "@/components/NotaDemo";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_BOAS_VINDAS } from "@/lib/textosBoasVindas";

import ApagarConta from "./ApagarConta";
import PerfilConta from "./PerfilConta";

// Definições (no BR "Configurações"): o perfil da conta (as respostas do questionário de boas-vindas) e o "Apagar conta".
// Na demo fica tudo desligado, com a nota da demo (uma por página) no topo.
export default function PaginaDefinicoes() {
  const { TEXTOS_DEFINICOES } = useTextos(DICIONARIO_BOAS_VINDAS);

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold text-texto">{TEXTOS_DEFINICOES.titulo}</h1>
          <NotaDemo />
        </header>
        <PerfilConta />
        <ApagarConta />
      </div>
    </main>
  );
}
