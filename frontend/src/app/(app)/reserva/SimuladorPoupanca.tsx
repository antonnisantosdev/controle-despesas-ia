"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { pedirApi, SessaoExpirada, type AnoSimulado } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_RESERVA } from "@/lib/textosReserva";

import { ESTILO_TOOLTIP } from "../dashboard/formatos";

const COR_VALOR = "var(--destaque)";
const COR_DEPOSITADO = "var(--texto-suave)";

// O máximo por mês que a API aceita (GET /simulador, le=10_000 em main.py); entra na mensagem de erro.
const MAXIMO_MENSAL = 10_000;

const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto";

type Props = { onSessaoExpirada: (e: unknown) => void };

// Quanto junta quem poupa um valor fixo por mês. As contas são feitas no backend (simulador.py).
export default function SimuladorPoupanca({ onSessaoExpirada }: Props) {
  const { TEXTOS_SIMULADOR, TEXTOS_NOVO_OBJETIVO } = useTextos(DICIONARIO_RESERVA);
  // Taxas de exemplo para comparar cenários. Não são produtos nem recomendações.
  const TAXAS = TEXTOS_SIMULADOR.taxas;
  const f = useFormatos();
  const [mensal, setMensal] = useState("50");
  const [anos, setAnos] = useState(10);
  const [taxa, setTaxa] = useState(4);
  const [resultado, setResultado] = useState<AnoSimulado[]>([]);
  // O erro guarda os valores a que pertence: com outros valores no campo já não aparece (não pisca o antigo).
  const [erro, setErro] = useState<{ texto: string; de: string } | null>(null);

  const numero = Number(mensal.replace(",", "."));
  // Valor vazio ou inválido: não se mostra o resultado (nem o erro) de um valor que já não é o do campo.
  const valido = numero > 0;
  const pedidoAtual = `${numero}|${anos}|${taxa}`;
  // Campo com algo que não é um valor positivo (ex. -20): diz-se porquê, em vez de só esconder o resultado.
  // Campo vazio: nada (a pessoa ainda está a escrever).
  const erroAtual = !valido
    ? mensal.trim()
      ? TEXTOS_NOVO_OBJETIVO.erroValor
      : ""
    : erro?.de === pedidoAtual
      ? erro.texto
      : "";

  useEffect(() => {
    if (!valido) return;

    // Espera um bocadinho depois da última tecla, para não fazer um pedido por cada algarismo.
    // Uma resposta que chegue depois de o campo mudar já não é a certa: ignora-se.
    let atual = true;
    const espera = setTimeout(() => {
      pedirApi<AnoSimulado[]>(`/simulador?mensal=${numero}&anos=${anos}&taxa=${taxa}`)
        .then((anosSimulados) => {
          if (!atual) return;
          setResultado(anosSimulados);
          setErro(null);
        })
        .catch((e) => {
          if (e instanceof SessaoExpirada) onSessaoExpirada(e);
          else if (atual) {
            // Sem o resultado anterior: ficava à vista por baixo do erro, como se fosse do valor novo.
            setResultado([]);
            setErro({ texto: TEXTOS_SIMULADOR.erro, de: pedidoAtual });
          }
        });
    }, 300);
    return () => {
      atual = false;
      clearTimeout(espera);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mensal, anos, taxa]);

  const final = valido ? resultado.at(-1) : undefined;
  // "10 000 €" (ou "R$ 10.000"), com espaços normais como o texto sempre teve.
  const maximoMensal = f.comSimbolo(f.numero(MAXIMO_MENSAL).replace(/\s/g, " "));

  return (
    <section className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <div>
        <h2 className="font-medium text-texto">{TEXTOS_SIMULADOR.titulo}</h2>
        <p className="text-sm text-texto-suave">{TEXTOS_SIMULADOR.texto}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="block">
          <span className="text-sm text-texto-suave">{preencher(TEXTOS_SIMULADOR.mensal, { simbolo: f.simbolo })}</span>
          <input inputMode="decimal" value={mensal} onChange={(e) => setMensal(e.target.value)} className={ESTILO_CAMPO} />
        </label>
        <label className="block">
          <span className="text-sm text-texto-suave">
            {anos === 1 ? TEXTOS_SIMULADOR.duranteUmAno : preencher(TEXTOS_SIMULADOR.duranteAnos, { anos })}
          </span>
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
          <span className="text-sm text-texto-suave">{TEXTOS_SIMULADOR.taxa}</span>
          <select value={taxa} onChange={(e) => setTaxa(Number(e.target.value))} className={ESTILO_CAMPO}>
            {TAXAS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.nome}
              </option>
            ))}
          </select>
        </label>
      </div>

      {erroAtual && <p className="text-sm text-red-600 dark:text-red-400">{preencher(erroAtual, { maximo: maximoMensal })}</p>}

      {final && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-fundo p-3">
              <p className="text-xs text-texto-suave">{TEXTOS_SIMULADOR.depositaste}</p>
              <p className="text-lg font-semibold text-texto">{f.dinheiro(final.depositado)}</p>
            </div>
            <div className="rounded-lg bg-fundo p-3">
              <p className="text-xs text-texto-suave">{TEXTOS_SIMULADOR.ganhoJuros}</p>
              <p className="text-lg font-semibold text-texto">{f.dinheiro(final.valor - final.depositado)}</p>
            </div>
            <div className="rounded-lg bg-fundo p-3">
              <p className="text-xs text-texto-suave">{preencher(TEXTOS_SIMULADOR.terias, { anos: final.ano })}</p>
              <p className="text-lg font-semibold text-destaque">{f.dinheiro(final.valor)}</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={resultado} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--grelha)" strokeDasharray="3 3" />
              <XAxis
                dataKey="ano"
                tickFormatter={(ano) => preencher(TEXTOS_SIMULADOR.eixoAno, { ano: String(ano) })}
                axisLine={false}
                tickLine={false}
                tick={{ fill: COR_DEPOSITADO, fontSize: 12 }}
              />
              <YAxis
                tickFormatter={(v) => f.dinheiroMil(Number(v))}
                axisLine={false}
                tickLine={false}
                tick={{ fill: COR_DEPOSITADO, fontSize: 12 }}
                width={72}
              />
              <Tooltip
                contentStyle={ESTILO_TOOLTIP}
                formatter={(valor) => f.dinheiro(Number(valor))}
                labelFormatter={(ano) =>
                  Number(ano) === 1 ? TEXTOS_SIMULADOR.aoFimDeUmAno : preencher(TEXTOS_SIMULADOR.aoFimDeAnos, { anos: String(ano) })
                }
              />
              <Legend iconType="circle" formatter={(nome) => <span style={{ color: COR_DEPOSITADO, fontSize: 12 }}>{nome}</span>} />
              <Area type="monotone" dataKey="depositado" name={TEXTOS_SIMULADOR.depositado} stroke={COR_DEPOSITADO} fill="none" strokeDasharray="4 4" />
              <Area type="monotone" dataKey="valor" name={TEXTOS_SIMULADOR.comJuros} stroke={COR_VALOR} strokeWidth={2} fill={COR_VALOR} fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        </>
      )}

      {/* Mostrar o efeito dos juros não é aconselhar investimentos: a app nunca diz onde pôr o dinheiro. */}
      <p className="text-xs text-texto-suave">{TEXTOS_SIMULADOR.aviso}</p>
    </section>
  );
}
