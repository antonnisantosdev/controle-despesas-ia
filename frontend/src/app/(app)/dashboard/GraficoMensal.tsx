"use client";

import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { ResumoMensal } from "@/lib/api";

import { ESTILO_TOOLTIP, euros, nomeMes } from "./formatos";

const COR_RECEITAS = "var(--cor-receitas)";
const COR_DESPESAS = "var(--cor-despesas)";
const COR_EIXO = "var(--texto-suave)";

// Evolução das receitas e despesas: duas linhas com uma área esbatida por baixo.
export default function GraficoMensal({ dados }: { dados: ResumoMensal[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={dados} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <defs>
          {/* Degradê de cima (cor) para baixo (transparente), um para cada série. */}
          <linearGradient id="degradeReceitas" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" style={{ stopColor: COR_RECEITAS, stopOpacity: 0.35 }} />
            <stop offset="100%" style={{ stopColor: COR_RECEITAS, stopOpacity: 0 }} />
          </linearGradient>
          <linearGradient id="degradeDespesas" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" style={{ stopColor: COR_DESPESAS, stopOpacity: 0.35 }} />
            <stop offset="100%" style={{ stopColor: COR_DESPESAS, stopOpacity: 0 }} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="var(--grelha)" strokeDasharray="3 3" />
        <XAxis dataKey="mes" tickFormatter={nomeMes} axisLine={false} tickLine={false} tick={{ fill: COR_EIXO, fontSize: 12 }} />
        <YAxis
          tickFormatter={(v) => `${v} €`}
          axisLine={false}
          tickLine={false}
          tick={{ fill: COR_EIXO, fontSize: 12 }}
          width={64}
        />
        <Tooltip
          contentStyle={ESTILO_TOOLTIP}
          formatter={(valor) => euros(Number(valor))}
          labelFormatter={(mes) => nomeMes(String(mes))}
        />
        <Legend iconType="circle" formatter={(nome) => <span style={{ color: COR_EIXO, fontSize: 12 }}>{nome}</span>} />
        <Area
          type="monotone"
          dataKey="receitas"
          name="Receitas"
          stroke={COR_RECEITAS}
          strokeWidth={2}
          fill="url(#degradeReceitas)"
          dot={{ r: 4, fill: COR_RECEITAS, stroke: "var(--cartao)", strokeWidth: 2 }}
          activeDot={{ r: 6 }}
        />
        <Area
          type="monotone"
          dataKey="despesas"
          name="Despesas"
          stroke={COR_DESPESAS}
          strokeWidth={2}
          fill="url(#degradeDespesas)"
          dot={{ r: 4, fill: COR_DESPESAS, stroke: "var(--cartao)", strokeWidth: 2 }}
          activeDot={{ r: 6 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
