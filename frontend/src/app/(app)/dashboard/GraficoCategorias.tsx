"use client";

import { Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { GastoCategoria } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { useOpcoes, useTextos } from "@/lib/textos";
import { DICIONARIO_DASHBOARD } from "@/lib/textosDashboard";

import { ESTILO_TOOLTIP } from "./formatos";

const CORES = ["var(--serie-1)", "var(--serie-2)", "var(--serie-3)", "var(--serie-4)", "var(--serie-5)"];
const MAX_FATIAS = 5;

type Fatia = { categoria: string; total: number; fill: string };

// Chave da fatia que junta as categorias pequenas. Não é uma categoria: a categoria "outros" pode estar
// entre as 5 maiores e, com a mesma chave, apareciam duas fatias "Outros" (e duas linhas com a mesma key).
const CHAVE_RESTO = "_resto";

// Mostra as 5 maiores categorias e junta as restantes numa fatia "Outros (soma)":
// com mais fatias ficam finas demais para comparar, e as cores começariam a repetir-se.
function agrupar(dados: GastoCategoria[]): Fatia[] {
  const fatias: Fatia[] = dados.slice(0, MAX_FATIAS).map((d, i) => ({ ...d, fill: CORES[i] }));
  const resto = dados.slice(MAX_FATIAS).reduce((soma, d) => soma + d.total, 0);
  if (resto > 0) fatias.push({ categoria: CHAVE_RESTO, total: resto, fill: "var(--serie-outros)" });
  return fatias;
}

export default function GraficoCategorias({ dados }: { dados: GastoCategoria[] }) {
  const { TEXTOS_GRAFICOS } = useTextos(DICIONARIO_DASHBOARD);
  const formatos = useFormatos();
  const { nomeCategoria } = useOpcoes();
  if (dados.length === 0) {
    return <p className="text-sm text-texto-suave">{TEXTOS_GRAFICOS.semDespesas}</p>;
  }

  // rotulo: o nome mostrado (legenda e tooltip), do país da conta; a chave da categoria não muda.
  const fatias = agrupar(dados).map((fatia) => ({
    ...fatia,
    rotulo: fatia.categoria === CHAVE_RESTO ? TEXTOS_GRAFICOS.restoSoma : nomeCategoria(fatia.categoria),
  }));
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
              nameKey="rotulo"
              innerRadius="68%"
              outerRadius="100%"
              paddingAngle={2}
              cornerRadius={4}
              stroke="var(--cartao)"
              strokeWidth={2}
            />
            <Tooltip contentStyle={ESTILO_TOOLTIP} formatter={(valor) => formatos.dinheiro(Number(valor))} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs text-texto-suave">{TEXTOS_GRAFICOS.total}</span>
          <span className="font-semibold text-texto">{formatos.dinheiro(total)}</span>
        </div>
      </div>

      {/* Legenda em lista: cor, nome, valor e percentagem (a cor nunca é a única pista). */}
      {/* min-w-0 + flex-1: a lista ocupa só o espaço que sobra ao lado do donut (w-full empurrava-a para fora). */}
      <ul className="w-full min-w-0 space-y-2.5 sm:w-auto sm:flex-1">
        {fatias.map((f) => (
          <li key={f.categoria} className="flex items-center gap-3 text-sm">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: f.fill }} />
            <span className="min-w-0 flex-1 truncate text-texto">{f.rotulo}</span>
            <span className="shrink-0 tabular-nums text-texto">{formatos.dinheiro(f.total)}</span>
            <span className="w-9 shrink-0 text-right text-xs tabular-nums text-texto-suave">
              {Math.round((f.total / total) * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
