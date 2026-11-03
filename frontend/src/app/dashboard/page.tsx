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

// Cores das séries (paleta categórica validada para daltonismo): 1.ª azul, 2.ª laranja.
const COR_RECEITAS = "#2a78d6";
const COR_DESPESAS = "#eb6834";
const COR_GRELHA = "#e5e4e0";
const COR_TEXTO_EIXO = "#52514e";

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

  function sair() {
    apagarToken();
    router.replace("/login");
  }

  return (
    <main className="flex-1 bg-gray-50 p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-gray-900">Controlo de Despesas</h1>
          <button onClick={sair} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100">
            Sair
          </button>
        </header>

        {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{erro}</p>}

        <Chat />

        <section className="rounded-xl bg-white p-4 shadow sm:p-6">
          <h2 className="mb-4 font-medium text-gray-900">Receitas e despesas por mês</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={mensal} barGap={2}>
              <CartesianGrid vertical={false} stroke={COR_GRELHA} />
              <XAxis dataKey="mes" tickFormatter={nomeMes} tick={{ fill: COR_TEXTO_EIXO, fontSize: 12 }} />
              <YAxis tickFormatter={(v) => `${v} €`} tick={{ fill: COR_TEXTO_EIXO, fontSize: 12 }} width={70} />
              <Tooltip formatter={(valor) => euros(Number(valor))} labelFormatter={(mes) => nomeMes(String(mes))} />
              <Legend />
              <Bar dataKey="receitas" name="Receitas" fill={COR_RECEITAS} radius={[4, 4, 0, 0]} maxBarSize={40} />
              <Bar dataKey="despesas" name="Despesas" fill={COR_DESPESAS} radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="rounded-xl bg-white p-4 shadow sm:p-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="font-medium text-gray-900">Gastos por categoria</h2>
            <select
              value={mes}
              onChange={(e) => setMes(e.target.value)}
              className="rounded-md border border-gray-300 px-2 py-1 text-sm text-gray-900"
            >
              {mensal.map((m) => (
                <option key={m.mes} value={m.mes}>
                  {nomeMes(m.mes)}
                </option>
              ))}
            </select>
          </div>

          {categorias.length === 0 ? (
            <p className="text-sm text-gray-500">Sem despesas neste mês.</p>
          ) : (
            <ResponsiveContainer width="100%" height={categorias.length * 36 + 20}>
              <BarChart data={categorias} layout="vertical" margin={{ right: 90 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="categoria" width={120} tick={{ fill: COR_TEXTO_EIXO, fontSize: 12 }} />
                <Tooltip formatter={(valor) => euros(Number(valor))} />
                <Bar dataKey="total" name="Gasto" fill={COR_RECEITAS} radius={[0, 4, 4, 0]} barSize={20}>
                  <LabelList dataKey="total" position="right" formatter={(valor) => euros(Number(valor))} fill={COR_TEXTO_EIXO} fontSize={12} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>
      </div>
    </main>
  );
}
