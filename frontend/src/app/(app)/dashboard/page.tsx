"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AlertasOrcamento from "@/components/AlertasOrcamento";
import PagamentosRecorrentes from "@/components/PagamentosRecorrentes";
import {
  apagarToken,
  lerToken,
  pedirApi,
  SessaoExpirada,
  type GastoCategoria,
  type ResumoMensal,
} from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_DASHBOARD } from "@/lib/textosDashboard";
import { DICIONARIO_PLANOS } from "@/lib/textosPlanos";

import CartaoResumo from "./CartaoResumo";
import Chat from "./Chat";
import GraficoCategorias from "./GraficoCategorias";
import GraficoMensal from "./GraficoMensal";
import ResumoCartao from "./ResumoCartao";
import { calcularTotais } from "./totais";

type Router = ReturnType<typeof useRouter>;

// Sessão expirada volta ao login; qualquer outro erro aparece na página (o texto vem do país da conta, ao desenhar).
function tratarErro(erro: unknown, router: Router, setErro: (houveErro: boolean) => void) {
  if (erro instanceof SessaoExpirada) {
    apagarToken();
    router.replace("/login");
  } else {
    setErro(true);
  }
}

export default function PaginaDashboard() {
  const { TEXTOS_DASHBOARD } = useTextos(DICIONARIO_DASHBOARD);
  const { TEXTOS_SEM_DADOS } = useTextos(DICIONARIO_PLANOS);
  const router = useRouter();
  const f = useFormatos();
  const [mensal, setMensal] = useState<ResumoMensal[]>([]);
  const [mes, setMes] = useState("");
  const [categorias, setCategorias] = useState<GastoCategoria[]>([]);
  const [erro, setErro] = useState(false);
  // Conta nova, ainda sem nenhuma movimentação: mostra como começar em vez de ficar "a analisar" para sempre.
  const [semDados, setSemDados] = useState(false);
  const totais = calcularTotais(mensal, mes);

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
        setSemDados(dados.length === 0);
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
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-destaque">{TEXTOS_DASHBOARD.etiquetaTopo}</p>
            <h1 className="text-2xl font-semibold text-texto">{TEXTOS_DASHBOARD.titulo}</h1>
          </div>
          {/* O mês escolhido aqui muda os cartões, as categorias e o resumo da IA. */}
          <select
            value={mes}
            onChange={(e) => setMes(e.target.value)}
            aria-label={TEXTOS_DASHBOARD.rotuloMes}
            className="rounded-lg border border-borda bg-cartao px-3 py-2 text-sm text-texto"
          >
            {mensal.map((m) => (
              <option key={m.mes} value={m.mes}>
                {f.mesAno(m.mes)}
              </option>
            ))}
          </select>
        </header>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <CartaoResumo titulo={TEXTOS_DASHBOARD.saldoMes} valor={totais.saldoMes} descricao={TEXTOS_DASHBOARD.saldoMesDescricao} icone="M3 7h18v12H3zM3 7l3-3h12l3 3M16 13h2" corIcone="var(--destaque)" />
          <CartaoResumo titulo={TEXTOS_DASHBOARD.entradasMes} valor={totais.entradas} descricao={TEXTOS_DASHBOARD.entradasMesDescricao} icone="M7 17L17 7M7 7v10h10" corIcone="var(--cor-receitas)" />
          <CartaoResumo titulo={TEXTOS_DASHBOARD.despesasMes} valor={totais.despesas} descricao={TEXTOS_DASHBOARD.despesasMesDescricao} icone="M7 7l10 10M17 7v10H7" corIcone="var(--cor-despesas)" />
          <CartaoResumo titulo={TEXTOS_DASHBOARD.saldoAcumulado} valor={totais.saldoTotal} descricao={TEXTOS_DASHBOARD.saldoAcumuladoDescricao} icone="M4 19h16M6 15v-4M10 15V7M14 15v-6M18 15V5" corIcone="var(--texto-suave)" />
        </div>

        {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{TEXTOS_DASHBOARD.erroCarregar}</p>}

        {semDados && (
          <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
            <h2 className="font-medium text-texto">{TEXTOS_SEM_DADOS.titulo}</h2>
            <p className="mt-1 text-sm text-texto-suave">{TEXTOS_SEM_DADOS.texto}</p>
            <Link
              href="/movimentacoes"
              className="mt-4 inline-flex min-h-11 items-center justify-center rounded-md bg-destaque px-4 text-sm font-semibold text-white transition-colors hover:bg-destaque-hover dark:text-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
            >
              {TEXTOS_SEM_DADOS.botao}
            </Link>
          </section>
        )}

        {/* Só aparece quando o mês escolhido é o atual e há categorias com 90% ou mais do orçamento gasto. */}
        {mes && <AlertasOrcamento mes={mes} />}

        {/* Cartão pequeno, só quando há pagamentos que se repetem (sem IA). A lista completa está no Planeamento. */}
        {mes && <PagamentosRecorrentes compacto />}

        <div className="grid gap-6 lg:grid-cols-3">
          <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6 lg:col-span-2">
            <h2 className="font-medium text-texto">{TEXTOS_DASHBOARD.evolucaoTitulo}</h2>
            <p className="mb-4 text-xs text-texto-suave">{TEXTOS_DASHBOARD.evolucaoTexto}</p>
            <GraficoMensal dados={mensal} />
          </section>
          {/* Sem mês (conta nova) não há nada para a IA resumir. */}
          {mes && <ResumoCartao mes={mes} />}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
            <h2 className="font-medium text-texto">{TEXTOS_DASHBOARD.categoriasTitulo}</h2>
            <p className="mb-4 text-xs text-texto-suave">
              {preencher(TEXTOS_DASHBOARD.categoriasTexto, { mes: mes ? f.mesAno(mes) : TEXTOS_DASHBOARD.semMes })}
            </p>
            <GraficoCategorias dados={categorias} />
          </section>
          <Chat />
        </div>
      </div>
    </main>
  );
}
