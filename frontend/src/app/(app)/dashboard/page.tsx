"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  apagarToken,
  lerToken,
  pedirApi,
  SessaoExpirada,
  type GastoCategoria,
  type ResumoMensal,
} from "@/lib/api";

import Chat from "./Chat";
import ResumoCartao from "./ResumoCartao";

// Cores dos gráficos: vêm das variáveis do tema (globals.css), por isso mudam sozinhas no tema escuro.
const COR_RECEITAS = "var(--cor-receitas)";
const COR_DESPESAS = "var(--cor-despesas)";
const COR_GRELHA = "var(--grelha)";
const COR_TEXTO_EIXO = "var(--texto-suave)";
const ESTILO_TOOLTIP = { background: "var(--cartao)", borderColor: "var(--borda)", color: "var(--texto)", borderRadius: 8 };

function euros(valor: number) {
  return valor.toLocaleString("pt-PT", { style: "currency", currency: "EUR" });
}

// "2026-10" -> "out. de 2026"
function nomeMes(mes: string) {
  return new Date(`${mes}-01T00:00:00`).toLocaleDateString("pt-PT", { month: "short", year: "numeric" });
}

type Router = ReturnType<typeof useRouter>;

// Sessão expirada volta ao login; qualquer outro erro aparece na página.
function tratarErro(erro: unknown, router: Router, setErro: (mensagem: string) => void) {
  if (erro instanceof SessaoExpirada) {
    apagarToken();
    router.replace("/login");
  } else {
    setErro("Não foi possível carregar os dados. Confirma que a API está a correr.");
  }
}

export default function PaginaDashboard() {
  const router = useRouter();
  const [mensal, setMensal] = useState<ResumoMensal[]>([]);
  const [mes, setMes] = useState("");
  const [categorias, setCategorias] = useState<GastoCategoria[]>([]);
  const [erro, setErro] = useState("");

  // 1. Ao abrir a página: sem token vai para o login; com token carrega a evolução mensal
  //    e escolhe o mês mais recente.
  useEffect(() => {
    if (!lerToken()) {
      router.replace("/login");
      return;
    }
    pedirApi<ResumoMensal[]>("/dashboard/mensal")
      .then((dados) => {
        setMensal(dados);
        if (dados.length > 0) setMes(dados[dados.length - 1].mes);
      })
      .catch((e) => tratarErro(e, router, setErro));
  }, [router]);

  // 2. Sempre que o mês escolhido muda: carrega os gastos por categoria desse mês.
  useEffect(() => {
    if (!mes) return;
    pedirApi<GastoCategoria[]>(`/dashboard/categorias?mes=${mes}`)
      .then(setCategorias)
      .catch((e) => tratarErro(e, router, setErro));
  }, [mes, router]);

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <header>
          <p className="text-xs font-semibold uppercase tracking-wide text-destaque">Resumo financeiro</p>
          <h1 className="text-2xl font-semibold text-texto">Visão geral</h1>
        </header>

        {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}

        <Chat />

        <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
          <h2 className="mb-4 font-medium text-texto">Receitas e despesas por mês</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={mensal} barGap={2}>
              <CartesianGrid vertical={false} stroke={COR_GRELHA} />
              <XAxis dataKey="mes" tickFormatter={nomeMes} tick={{ fill: COR_TEXTO_EIXO, fontSize: 12 }} />
              <YAxis tickFormatter={(v) => `${v} €`} tick={{ fill: COR_TEXTO_EIXO, fontSize: 12 }} width={70} />
              <Tooltip contentStyle={ESTILO_TOOLTIP} formatter={(valor) => euros(Number(valor))} labelFormatter={(mes) => nomeMes(String(mes))} />
              <Legend wrapperStyle={{ color: "var(--texto-suave)", fontSize: 12 }} />
              <Bar dataKey="receitas" name="Receitas" fill={COR_RECEITAS} radius={[4, 4, 0, 0]} maxBarSize={40} />
              <Bar dataKey="despesas" name="Despesas" fill={COR_DESPESAS} radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="font-medium text-texto">Gastos por categoria</h2>
            <select
              value={mes}
              onChange={(e) => setMes(e.target.value)}
              className="rounded-md border border-borda bg-cartao px-2 py-1 text-sm text-texto"
            >
              {mensal.map((m) => (
                <option key={m.mes} value={m.mes}>
                  {nomeMes(m.mes)}
                </option>
              ))}
            </select>
          </div>

          {categorias.length === 0 ? (
            <p className="text-sm text-texto-suave">Sem despesas neste mês.</p>
          ) : (
            <ResponsiveContainer width="100%" height={categorias.length * 36 + 20}>
              <BarChart data={categorias} layout="vertical" margin={{ right: 90 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="categoria" width={120} tick={{ fill: COR_TEXTO_EIXO, fontSize: 12 }} />
                <Tooltip contentStyle={ESTILO_TOOLTIP} cursor={{ fill: "var(--fundo)" }} formatter={(valor) => euros(Number(valor))} />
                <Bar dataKey="total" name="Gasto" fill={COR_RECEITAS} radius={[0, 4, 4, 0]} barSize={20}>
                  <LabelList dataKey="total" position="right" formatter={(valor) => euros(Number(valor))} fill={COR_TEXTO_EIXO} fontSize={12} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        <ResumoCartao mes={mes} />
      </div>
    </main>
  );
}
