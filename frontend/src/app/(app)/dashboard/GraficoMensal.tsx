"use client";

import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { ResumoMensal } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { TEXTOS_GRAFICOS } from "@/lib/textosDashboard";

import { ESTILO_TOOLTIP } from "./formatos";

const COR_RECEITAS = "var(--cor-receitas)";
const COR_DESPESAS = "var(--cor-despesas)";
const COR_EIXO = "var(--texto-suave)";

// Evolução das receitas e despesas: duas linhas com uma área esbatida por baixo.
export default function GraficoMensal({ dados }: { dados: ResumoMensal[] }) {
  const f = useFormatos();
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
        <XAxis dataKey="mes" tickFormatter={(mes) => f.mesAno(String(mes))} axisLine={false} tickLine={false} tick={{ fill: COR_EIXO, fontSize: 12 }} />
        <YAxis
          // O valor tal como o Recharts o dá (em PT, "1500 €" como sempre); nos outros países, à maneira local.
          tickFormatter={(v) => f.comSimbolo(f.pais === "PT" ? String(v) : f.numero(Number(v)))}
          axisLine={false}
          tickLine={false}
          tick={{ fill: COR_EIXO, fontSize: 12 }}
          width={64}
        />
        <Tooltip
          contentStyle={ESTILO_TOOLTIP}
          formatter={(valor) => f.dinheiro(Number(valor))}
          labelFormatter={(mes) => f.mesAno(String(mes))}
        />
        <Legend iconType="circle" formatter={(nome) => <span style={{ color: COR_EIXO, fontSize: 12 }}>{nome}</span>} />
        <Area
          type="monotone"
          dataKey="receitas"
          name={TEXTOS_GRAFICOS.receitas}
          stroke={COR_RECEITAS}
          strokeWidth={2}
          fill="url(#degradeReceitas)"
          dot={{ r: 4, fill: COR_RECEITAS, stroke: "var(--cartao)", strokeWidth: 2 }}
          activeDot={{ r: 6 }}
        />
        <Area
          type="monotone"
          dataKey="despesas"
          name={TEXTOS_GRAFICOS.despesas}
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
