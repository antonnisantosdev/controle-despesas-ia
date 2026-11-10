"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { MesRelatorio } from "@/lib/api";
import { TEXTOS_RELATORIO } from "@/lib/textosRelatorio";

import { ESTILO_TOOLTIP, euros, nomeMes } from "../dashboard/formatos";

const COR_ENTRADAS = "var(--cor-receitas)";
const COR_SAIDAS = "var(--cor-despesas)";
const COR_EIXO = "var(--texto-suave)";

// "2026-03" -> "mar." (o ano já está no título da página).
function mesCurto(mes: string) {
  return new Date(`${mes}-01T00:00:00`).toLocaleDateString("pt-PT", { month: "short" });
}

// Entradas e saídas de cada mês do ano, lado a lado. Barras em vez de linhas: num ano são 12 valores
// separados, e um mês sem movimentos fica vazio em vez de parecer uma descida.
export default function GraficoAnual({ meses }: { meses: MesRelatorio[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={meses} margin={{ top: 8, right: 4, left: 0, bottom: 0 }} barGap={2}>
        <CartesianGrid vertical={false} stroke="var(--grelha)" strokeDasharray="3 3" />
        <XAxis
          dataKey="mes"
          tickFormatter={mesCurto}
          axisLine={false}
          tickLine={false}
          interval={0}
          tick={{ fill: COR_EIXO, fontSize: 11 }}
        />
        <YAxis
          tickFormatter={(v) => `${Number(v).toLocaleString("pt-PT")} €`}
          axisLine={false}
          tickLine={false}
          tick={{ fill: COR_EIXO, fontSize: 11 }}
          width={64}
        />
        <Tooltip
          contentStyle={ESTILO_TOOLTIP}
          cursor={{ fill: "var(--grelha)", opacity: 0.4 }}
          formatter={(valor) => euros(Number(valor))}
          labelFormatter={(mes) => nomeMes(String(mes))}
        />
        <Legend iconType="circle" formatter={(nome) => <span style={{ color: COR_EIXO, fontSize: 12 }}>{nome}</span>} />
        <Bar dataKey="entradas" name={TEXTOS_RELATORIO.entradas} fill={COR_ENTRADAS} radius={[3, 3, 0, 0]} maxBarSize={18} />
        <Bar dataKey="saidas" name={TEXTOS_RELATORIO.saidas} fill={COR_SAIDAS} radius={[3, 3, 0, 0]} maxBarSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}
