"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AlertasOrcamento from "@/components/AlertasOrcamento";
import AvisoLimite from "@/components/AvisoLimite";
import NotaDemo, { ID_NOTA_DEMO } from "@/components/NotaDemo";
import PagamentosRecorrentes from "@/components/PagamentosRecorrentes";
import {
  eBloqueadoNaDemo,
  apagarToken,
  eLimiteDiario,
  ErroApi,
  pedirApi,
  SessaoExpirada,
  type LinhaOrcamento,
  type ResumoMensal,
  type SugestaoCategoria,
  type SugestaoOrcamento,
} from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { mesAtual } from "@/lib/planos";
import { useOpcoes, useTextos } from "@/lib/textos";
import { DICIONARIO_PLANEAMENTO } from "@/lib/textosPlaneamento";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

import LinhaPlaneamento from "./LinhaPlaneamento";
import SugestoesIA from "./SugestoesIA";

export default function PaginaPlaneamento() {
  const { TEXTOS_PLANEAMENTO } = useTextos(DICIONARIO_PLANEAMENTO);
  const { categorias, rotuloCategoria } = useOpcoes();
  const router = useRouter();
  const f = useFormatos();
  const [meses, setMeses] = useState<string[]>([]);
  const [mes, setMes] = useState("");
  const [resultado, setResultado] = useState<{ mes: string; linhas: LinhaOrcamento[] } | null>(null);
  const [versao, setVersao] = useState(0);
  const [erro, setErro] = useState("");
  const [semPedidos, setSemPedidos] = useState(false); // 429: chegou ao limite de pedidos à IA
  const [novaCategoria, setNovaCategoria] = useState("");
  const [sugestoes, setSugestoes] = useState<SugestaoCategoria[] | null>(null);
  const [aPedirSugestao, setAPedirSugestao] = useState(false);
  const aCarregar = resultado?.mes !== mes;
  // Na demo (só leitura): sem guardar orçamentos nem pedir sugestões à IA; a API recusa-os na mesma (423).
  const demo = useSessaoDemo();
  const linhas = aCarregar ? [] : (resultado?.linhas ?? []);

  function tratarErro(e: unknown) {
    if (e instanceof SessaoExpirada) {
      apagarToken();
      router.replace("/login");
    } else {
      setErro(TEXTOS_PLANEAMENTO.erroCarregar);
    }
  }

  useEffect(() => {
    pedirApi<ResumoMensal[]>("/dashboard/mensal")
      .then((dados) => {
        // Conta nova, ainda sem movimentações: começa no mês atual (senão a página ficava em "A carregar...").
        const lista = dados.length > 0 ? dados.map((d) => d.mes) : [mesAtual()];
        setMeses(lista);
        setMes(lista[lista.length - 1]);
      })
      .catch(tratarErro);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!mes) return;
    let cancelado = false;
    pedirApi<LinhaOrcamento[]>(`/orcamentos?mes=${mes}`)
      .then((dados) => {
        if (!cancelado) setResultado({ mes, linhas: dados });
      })
      .catch(tratarErro);
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mes, versao]);

  // Guarda o limite de uma categoria e volta a pedir a lista (para a ordem e as barras ficarem certas).
  async function guardar(categoria: string, limite: number) {
    setErro("");
    try {
      await pedirApi(`/orcamentos/${encodeURIComponent(categoria)}`, { limite }, "PUT");
      setNovaCategoria("");
      setVersao((v) => v + 1);
    } catch (e) {
      if (e instanceof SessaoExpirada) tratarErro(e);
      else if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      else setErro(TEXTOS_PLANEAMENTO.erroGuardar);
    }
  }

  // Pede à IA um orçamento baseado nos últimos 3 meses (até ao mês escolhido).
  async function pedirSugestao() {
    setAPedirSugestao(true);
    setErro("");
    setSemPedidos(false);
    try {
      const resposta = await pedirApi<SugestaoOrcamento>(`/orcamentos/sugestao?mes=${mes}`, {});
      setSugestoes(resposta.sugestoes);
    } catch (e) {
      if (e instanceof SessaoExpirada) tratarErro(e);
      else if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      else if (eLimiteDiario(e)) setSemPedidos(true);
      // 503 (IA em baixo) já traz uma explicação da API.
      else if (e instanceof ErroApi && typeof e.detalhe === "string") setErro(e.detalhe);
      else setErro(TEXTOS_PLANEAMENTO.erroSugestao);
    } finally {
      setAPedirSugestao(false);
    }
  }

  const comOrcamento = linhas.filter((l) => l.limite !== null);
  const totalLimite = comOrcamento.reduce((soma, l) => soma + (l.limite ?? 0), 0);
  const totalGasto = comOrcamento.reduce((soma, l) => soma + l.gasto, 0);
  // Categorias que ainda não aparecem na lista, para o "+ Adicionar orçamento".
  // "Rendimento" não é um gasto, por isso não faz sentido ter orçamento.
  const semLinha = categorias.filter((c) => c !== "rendimento" && !linhas.some((l) => l.categoria === c));

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-destaque">{TEXTOS_PLANEAMENTO.etiquetaTopo}</p>
            <h1 className="text-2xl font-semibold text-texto">{TEXTOS_PLANEAMENTO.titulo}</h1>
          </div>
          <div className="flex gap-2">
            <select
              value={mes}
              onChange={(e) => setMes(e.target.value)}
              aria-label={TEXTOS_PLANEAMENTO.rotuloMes}
              className="rounded-lg border border-borda bg-cartao px-3 py-2 text-sm text-texto"
            >
              {meses.map((m) => (
                <option key={m} value={m}>
                  {f.mesAno(m)}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={pedirSugestao}
              disabled={aPedirSugestao || !mes || demo}
              aria-describedby={demo ? ID_NOTA_DEMO : undefined}
              className="rounded-lg bg-destaque px-4 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {aPedirSugestao ? TEXTOS_PLANEAMENTO.aSugerir : TEXTOS_PLANEAMENTO.sugerir}
            </button>
          </div>
        </header>

        <NotaDemo />
        {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}
        {semPedidos && <AvisoLimite />}

        {/* Só no mês atual: categorias com 90% ou mais do orçamento gasto. Acompanha cada orçamento guardado. */}
        {mes && <AlertasOrcamento mes={mes} versao={versao} />}

        {sugestoes && (
          <SugestoesIA sugestoes={sugestoes} onAceitar={guardar} onFechar={() => setSugestoes(null)} desligado={demo} />
        )}

        {comOrcamento.length > 0 && (
          <div className="rounded-xl border border-borda bg-cartao p-4 text-sm text-texto-suave">
            {TEXTOS_PLANEAMENTO.totalAntes}
            <span className="font-semibold text-texto">{f.dinheiro(totalGasto)}</span>
            {TEXTOS_PLANEAMENTO.totalMeio}
            <span className="font-semibold text-texto">{f.dinheiro(totalLimite)}</span>
            {TEXTOS_PLANEAMENTO.totalFim}
          </div>
        )}

        <section className="divide-y divide-borda rounded-xl border border-borda bg-cartao">
          {aCarregar && <p className="p-6 text-sm text-texto-suave">{TEXTOS_PLANEAMENTO.aCarregar}</p>}
          {!aCarregar && linhas.length === 0 && (
            <p className="p-6 text-sm text-texto-suave">{TEXTOS_PLANEAMENTO.vazio}</p>
          )}
          {linhas.map((linha) => (
            <LinhaPlaneamento key={linha.categoria} linha={linha} onGuardar={guardar} desligado={demo} />
          ))}
        </section>

        {semLinha.length > 0 && !demo && (
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={novaCategoria}
              onChange={(e) => setNovaCategoria(e.target.value)}
              aria-label={TEXTOS_PLANEAMENTO.rotuloNovaCategoria}
              className="rounded-lg border border-borda bg-cartao px-3 py-2 text-sm capitalize text-texto"
            >
              <option value="">{TEXTOS_PLANEAMENTO.adicionar}</option>
              {semLinha.map((c) => (
                <option key={c} value={c}>
                  {rotuloCategoria(c)}
                </option>
              ))}
            </select>
            {novaCategoria && (
              <LinhaPlaneamento
                key={novaCategoria}
                linha={{ categoria: novaCategoria, limite: null, gasto: 0 }}
                onGuardar={guardar}
                compacta
              />
            )}
          </div>
        )}

        {/* Sem IA (não gasta pedidos): despesas que aparecem todos os meses, como assinaturas. */}
        <PagamentosRecorrentes />
      </div>
    </main>
  );
}
