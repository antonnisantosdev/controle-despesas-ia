"use client";

import { useState } from "react";

import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import type { SugestaoCategoria } from "@/lib/api";

import { euros } from "../dashboard/formatos";

type Props = {
  sugestoes: SugestaoCategoria[];
  onAceitar: (categoria: string, limite: number) => Promise<void>;
  onFechar: () => void;
  desligado?: boolean; // demo (só leitura): não se aceitam sugestões
};

// Lista das propostas da IA. Nada é guardado sem o utilizador clicar em "Aceitar" (a IA sugere, a pessoa decide).
export default function SugestoesIA({ sugestoes, onAceitar, onFechar, desligado = false }: Props) {
  const descricaoDemo = desligado ? ID_NOTA_DEMO : undefined; // aponta para a explicação (NotaDemo)
  const [aceites, setAceites] = useState<string[]>([]);

  async function aceitar(s: SugestaoCategoria) {
    await onAceitar(s.categoria, s.limite);
    setAceites((anteriores) => [...anteriores, s.categoria]);
  }

  async function aceitarTodas() {
    for (const s of sugestoes) {
      if (!aceites.includes(s.categoria)) await aceitar(s);
    }
  }

  return (
    <section className="space-y-3 rounded-xl border border-destaque/40 bg-cartao p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-medium text-texto">✨ Sugestão da IA</h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={aceitarTodas}
            disabled={desligado}
            aria-describedby={descricaoDemo}
            className="rounded-md bg-destaque px-3 py-1.5 text-xs font-medium text-white hover:bg-destaque-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            Aceitar todas
          </button>
          <button type="button" onClick={onFechar} className="px-2 text-sm text-texto-suave hover:text-texto">
            Fechar
          </button>
        </div>
      </div>

      {sugestoes.length === 0 && (
        <p className="text-sm text-texto-suave">Ainda não há gastos suficientes para sugerir um orçamento.</p>
      )}

      <ul className="divide-y divide-borda">
        {sugestoes.map((s) => (
          <li key={s.categoria} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-texto">
                <span className="font-medium capitalize">{s.categoria}</span> · {euros(s.limite)} por mês
              </p>
              <p className="text-xs text-texto-suave">{s.explicacao}</p>
            </div>
            {aceites.includes(s.categoria) ? (
              <span className="text-xs font-medium text-destaque">✓ Aceite</span>
            ) : (
              <button
                type="button"
                onClick={() => aceitar(s)}
                disabled={desligado}
                aria-describedby={descricaoDemo}
                className="rounded-md border border-borda px-3 py-1 text-xs text-texto hover:bg-fundo disabled:cursor-not-allowed disabled:opacity-50"
              >
                Aceitar
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
