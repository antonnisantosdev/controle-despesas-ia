"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { pedirApi, SessaoExpirada, type AnoSimulado } from "@/lib/api";

import { ESTILO_TOOLTIP, euros } from "../dashboard/formatos";

const COR_VALOR = "var(--destaque)";
const COR_DEPOSITADO = "var(--texto-suave)";

// Taxas de exemplo para comparar cenários. Não são produtos nem recomendações.
const TAXAS = [
  { valor: 0, nome: "0% (dinheiro parado)" },
  { valor: 2, nome: "2% ao ano" },
  { valor: 4, nome: "4% ao ano" },
  { valor: 6, nome: "6% ao ano" },
];

const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto";

type Props = { onSessaoExpirada: (e: unknown) => void };

// Quanto junta quem poupa um valor fixo por mês. As contas são feitas no backend (simulador.py).
export default function SimuladorPoupanca({ onSessaoExpirada }: Props) {
  const [mensal, setMensal] = useState("50");
  const [anos, setAnos] = useState(10);
  const [taxa, setTaxa] = useState(4);
  const [resultado, setResultado] = useState<AnoSimulado[]>([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    const numero = Number(mensal.replace(",", "."));
    if (!(numero > 0)) return;

    // Espera um bocadinho depois da última tecla, para não fazer um pedido por cada algarismo.
    const espera = setTimeout(() => {
      pedirApi<AnoSimulado[]>(`/simulador?mensal=${numero}&anos=${anos}&taxa=${taxa}`)
        .then((anosSimulados) => {
          setResultado(anosSimulados);
          setErro("");
        })
        .catch((e) => {
          if (e instanceof SessaoExpirada) onSessaoExpirada(e);
          else setErro("Não foi possível simular. Confirma os valores (máx. 10 000 € por mês).");
        });
    }, 300);
    return () => clearTimeout(espera);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mensal, anos, taxa]);

  const final = resultado.at(-1);

  return (
    <section className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <div>
        <h2 className="font-medium text-texto">E se poupares todos os meses?</h2>
        <p className="text-sm text-texto-suave">
          Vê quanto juntas com juros compostos, por exemplo com o dinheiro que deixas de gastar numa subscrição.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="block">
          <span className="text-sm text-texto-suave">Poupança por mês (€)</span>
          <input inputMode="decimal" value={mensal} onChange={(e) => setMensal(e.target.value)} className={ESTILO_CAMPO} />
        </label>
        <label className="block">
          <span className="text-sm text-texto-suave">Durante {anos} {anos === 1 ? "ano" : "anos"}</span>
          <input
            type="range"
            min={1}
            max={40}
            value={anos}
            onChange={(e) => setAnos(Number(e.target.value))}
            className="mt-3 w-full accent-destaque"
          />
        </label>
        <label className="block">
          <span className="text-sm text-texto-suave">Rendimento anual (exemplo)</span>
          <select value={taxa} onChange={(e) => setTaxa(Number(e.target.value))} className={ESTILO_CAMPO}>
            {TAXAS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.nome}
              </option>
            ))}
          </select>
        </label>
      </div>

      {erro && <p className="text-sm text-red-600 dark:text-red-400">{erro}</p>}

      {final && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-fundo p-3">
              <p className="text-xs text-texto-suave">Depositaste</p>
              <p className="text-lg font-semibold text-texto">{euros(final.depositado)}</p>
            </div>
            <div className="rounded-lg bg-fundo p-3">
              <p className="text-xs text-texto-suave">Ganho com juros</p>
              <p className="text-lg font-semibold text-texto">{euros(final.valor - final.depositado)}</p>
            </div>
            <div className="rounded-lg bg-fundo p-3">
              <p className="text-xs text-texto-suave">Terias ao fim de {final.ano} anos</p>
              <p className="text-lg font-semibold text-destaque">{euros(final.valor)}</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={resultado} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--grelha)" strokeDasharray="3 3" />
              <XAxis
                dataKey="ano"
                tickFormatter={(ano) => `${ano}.º`}
                axisLine={false}
                tickLine={false}
                tick={{ fill: COR_DEPOSITADO, fontSize: 12 }}
              />
              <YAxis
                tickFormatter={(v) => `${Math.round(v / 1000)} mil €`}
                axisLine={false}
                tickLine={false}
                tick={{ fill: COR_DEPOSITADO, fontSize: 12 }}
                width={64}
              />
              <Tooltip
                contentStyle={ESTILO_TOOLTIP}
                formatter={(valor) => euros(Number(valor))}
                labelFormatter={(ano) => `Ao fim de ${ano} ${Number(ano) === 1 ? "ano" : "anos"}`}
              />
              <Legend iconType="circle" formatter={(nome) => <span style={{ color: COR_DEPOSITADO, fontSize: 12 }}>{nome}</span>} />
              <Area type="monotone" dataKey="depositado" name="Depositado" stroke={COR_DEPOSITADO} fill="none" strokeDasharray="4 4" />
              <Area type="monotone" dataKey="valor" name="Com juros" stroke={COR_VALOR} strokeWidth={2} fill={COR_VALOR} fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        </>
      )}

      {/* Mostrar o efeito dos juros não é aconselhar investimentos: a app nunca diz onde pôr o dinheiro. */}
      <p className="text-xs text-texto-suave">
        Simulação com uma taxa fixa de exemplo, sem impostos, comissões nem inflação. Não é um conselho de investimento:
        os rendimentos reais variam e não são garantidos.
      </p>
    </section>
  );
}
