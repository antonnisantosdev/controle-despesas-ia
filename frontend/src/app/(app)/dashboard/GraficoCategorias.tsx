"use client";

import { Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { GastoCategoria } from "@/lib/api";

import { ESTILO_TOOLTIP, euros } from "./formatos";

const CORES = ["var(--serie-1)", "var(--serie-2)", "var(--serie-3)", "var(--serie-4)", "var(--serie-5)"];
const MAX_FATIAS = 5;

type Fatia = { categoria: string; total: number; fill: string };

// Mostra as 5 maiores categorias e junta as restantes numa fatia "outros":
// com mais fatias ficam finas demais para comparar, e as cores começariam a repetir-se.
function agrupar(dados: GastoCategoria[]): Fatia[] {
  const fatias: Fatia[] = dados.slice(0, MAX_FATIAS).map((d, i) => ({ ...d, fill: CORES[i] }));
  const resto = dados.slice(MAX_FATIAS).reduce((soma, d) => soma + d.total, 0);
  if (resto > 0) fatias.push({ categoria: "outros", total: resto, fill: "var(--serie-outros)" });
  return fatias;
}

export default function GraficoCategorias({ dados }: { dados: GastoCategoria[] }) {
  if (dados.length === 0) {
    return <p className="text-sm text-texto-suave">Sem despesas neste mês.</p>;
  }

  const fatias = agrupar(dados);
  const total = fatias.reduce((soma, f) => soma + f.total, 0);

  return (
    <div className="flex flex-col items-center gap-6 sm:flex-row">
      {/* Donut com o total no centro. */}
      <div className="relative h-48 w-48 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={fatias}
              dataKey="total"
              nameKey="categoria"
              innerRadius="68%"
              outerRadius="100%"
              paddingAngle={2}
              cornerRadius={4}
              stroke="var(--cartao)"
              strokeWidth={2}
            />
            <Tooltip contentStyle={ESTILO_TOOLTIP} formatter={(valor) => euros(Number(valor))} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs text-texto-suave">Total</span>
          <span className="font-semibold text-texto">{euros(total)}</span>
        </div>
      </div>

      {/* Legenda em lista: cor, nome, valor e percentagem (a cor nunca é a única pista). */}
      {/* min-w-0 + flex-1: a lista ocupa só o espaço que sobra ao lado do donut (w-full empurrava-a para fora). */}
      <ul className="w-full min-w-0 space-y-2.5 sm:w-auto sm:flex-1">
        {fatias.map((f) => (
          <li key={f.categoria} className="flex items-center gap-3 text-sm">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: f.fill }} />
            <span className="min-w-0 flex-1 truncate capitalize text-texto">{f.categoria}</span>
            <span className="shrink-0 tabular-nums text-texto">{euros(f.total)}</span>
            <span className="w-9 shrink-0 text-right text-xs tabular-nums text-texto-suave">
              {Math.round((f.total / total) * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
