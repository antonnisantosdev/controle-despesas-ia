"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apagarToken, pedirApi, SessaoExpirada, type LinhaOrcamento, type ResumoMensal } from "@/lib/api";
import { CATEGORIAS } from "@/lib/opcoes";

import { euros, nomeMes } from "../dashboard/formatos";
import LinhaPlaneamento from "./LinhaPlaneamento";

// "Rendimento" não é um gasto, por isso não faz sentido ter orçamento.
const CATEGORIAS_DE_GASTO = CATEGORIAS.filter((c) => c !== "rendimento");

export default function PaginaPlaneamento() {
  const router = useRouter();
  const [meses, setMeses] = useState<string[]>([]);
  const [mes, setMes] = useState("");
  const [resultado, setResultado] = useState<{ mes: string; linhas: LinhaOrcamento[] } | null>(null);
  const [versao, setVersao] = useState(0);
  const [erro, setErro] = useState("");
  const [novaCategoria, setNovaCategoria] = useState("");
  const aCarregar = resultado?.mes !== mes;
  const linhas = aCarregar ? [] : (resultado?.linhas ?? []);

  function tratarErro(e: unknown) {
    if (e instanceof SessaoExpirada) {
      apagarToken();
      router.replace("/login");
    } else {
      setErro("Não foi possível carregar o planeamento. Confirma que a API está a correr.");
    }
  }

  useEffect(() => {
    pedirApi<ResumoMensal[]>("/dashboard/mensal")
      .then((dados) => {
        const lista = dados.map((d) => d.mes);
        setMeses(lista);
        if (lista.length > 0) setMes(lista[lista.length - 1]);
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
      else setErro("Não foi possível guardar o orçamento. Tenta outra vez.");
    }
  }

  const comOrcamento = linhas.filter((l) => l.limite !== null);
  const totalLimite = comOrcamento.reduce((soma, l) => soma + (l.limite ?? 0), 0);
  const totalGasto = comOrcamento.reduce((soma, l) => soma + l.gasto, 0);
  // Categorias que ainda não aparecem na lista, para o "+ Adicionar orçamento".
  const semLinha = CATEGORIAS_DE_GASTO.filter((c) => !linhas.some((l) => l.categoria === c));

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-destaque">Orçamento mensal</p>
            <h1 className="text-2xl font-semibold text-texto">Planeamento</h1>
          </div>
          <select
            value={mes}
            onChange={(e) => setMes(e.target.value)}
            aria-label="Mês"
            className="rounded-lg border border-borda bg-cartao px-3 py-2 text-sm text-texto"
          >
            {meses.map((m) => (
              <option key={m} value={m}>
                {nomeMes(m)}
              </option>
            ))}
          </select>
        </header>

        {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}

        {comOrcamento.length > 0 && (
          <div className="rounded-xl border border-borda bg-cartao p-4 text-sm text-texto-suave">
            Nas categorias com orçamento, gastaste <span className="font-semibold text-texto">{euros(totalGasto)}</span> de{" "}
            <span className="font-semibold text-texto">{euros(totalLimite)}</span> previstos.
          </div>
        )}

        <section className="divide-y divide-borda rounded-xl border border-borda bg-cartao">
          {aCarregar && <p className="p-6 text-sm text-texto-suave">A carregar...</p>}
          {!aCarregar && linhas.length === 0 && (
            <p className="p-6 text-sm text-texto-suave">Sem gastos nem orçamentos neste mês.</p>
          )}
          {linhas.map((linha) => (
            <LinhaPlaneamento key={linha.categoria} linha={linha} onGuardar={guardar} />
          ))}
        </section>

        {semLinha.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={novaCategoria}
              onChange={(e) => setNovaCategoria(e.target.value)}
              aria-label="Categoria para novo orçamento"
              className="rounded-lg border border-borda bg-cartao px-3 py-2 text-sm capitalize text-texto"
            >
              <option value="">+ Adicionar orçamento para...</option>
              {semLinha.map((c) => (
                <option key={c} value={c}>
                  {c}
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
      </div>
    </main>
  );
}
