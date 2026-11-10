"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { pedirApi, type Recorrente } from "@/lib/api";
import { preencher } from "@/lib/planos";
import { TEXTOS_RECORRENTES } from "@/lib/textosRecorrentes";

// Os valores em euros, à portuguesa: 12.99 -> "12,99 €".
function euros(valor: number): string {
  return valor.toLocaleString("pt-PT", { style: "currency", currency: "EUR" });
}

// "2026-11-05" -> "5 nov."
function dataCurta(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-PT", { day: "numeric", month: "short" });
}

// "Subiu de 10,99 € para 12,99 €" (ou "Desceu..."), ou null se o preço não mudou.
function mudancaDePreco(r: Recorrente): string | null {
  if (r.valor_anterior == null) return null;
  const modelo = r.valor_mensal > r.valor_anterior ? TEXTOS_RECORRENTES.subiu : TEXTOS_RECORRENTES.desceu;
  return preencher(modelo, { antes: euros(r.valor_anterior), depois: euros(r.valor_mensal) });
}

// Quantos se mostram no cartão do dashboard (a lista completa está no Planeamento).
const MAXIMO_NO_CARTAO = 3;

// Pagamentos que se repetem todos os meses (GET /recorrentes). Só contas na API, sem IA: não gasta pedidos.
// compacto: o cartão pequeno do dashboard (só aparece se houver algum). Sem compacto: a secção do Planeamento.
export default function PagamentosRecorrentes({ compacto = false }: { compacto?: boolean }) {
  const [lista, setLista] = useState<Recorrente[] | null>(null);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    let cancelado = false;
    pedirApi<Recorrente[]>("/recorrentes")
      .then((dados) => {
        if (!cancelado) setLista(dados);
      })
      .catch(() => {
        // A página trata da sessão; aqui só se diz que esta parte falhou.
        if (!cancelado) setErro(true);
      });
    return () => {
      cancelado = true;
    };
  }, []);

  const total = (lista ?? []).reduce((soma, r) => soma + r.valor_mensal, 0);

  if (compacto) {
    // No dashboard, sem dados (ou com erro) o cartão não aparece: não há nada de útil para mostrar.
    if (!lista || lista.length === 0) return null;
    const resumo =
      lista.length === 1
        ? preencher(TEXTOS_RECORRENTES.resumoCurtoUm, { total: euros(total) })
        : preencher(TEXTOS_RECORRENTES.resumoCurto, { quantos: lista.length, total: euros(total) });
    return (
      <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-medium text-texto">{TEXTOS_RECORRENTES.tituloCurto}</h2>
          <Link href="/planeamento" className="text-sm font-medium text-destaque hover:text-destaque-hover">
            {TEXTOS_RECORRENTES.verTodos}
          </Link>
        </div>
        <p className="mt-1 text-sm text-texto-suave">{resumo}</p>
        <ul className="mt-3 space-y-1.5 text-sm">
          {lista.slice(0, MAXIMO_NO_CARTAO).map((r) => (
            <li key={`${r.descricao}-${r.ultimo_pagamento}`} className="flex justify-between gap-3">
              <span className="min-w-0 truncate text-texto">{r.descricao}</span>
              <span className="shrink-0 font-medium text-texto">
                {preencher(TEXTOS_RECORRENTES.porMes, { valor: euros(r.valor_mensal) })}
              </span>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  return (
    <section aria-labelledby="titulo-recorrentes" className="rounded-xl border border-borda bg-cartao">
      <div className="border-b border-borda p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="titulo-recorrentes" className="font-medium text-texto">
            {TEXTOS_RECORRENTES.titulo}
          </h2>
          {lista && lista.length > 0 && (
            <p className="text-sm font-semibold text-texto">
              {preencher(TEXTOS_RECORRENTES.totalPorMes, { total: euros(total) })}
            </p>
          )}
        </div>
        <p className="mt-1 text-xs text-texto-suave">{TEXTOS_RECORRENTES.explicacao}</p>
      </div>

      {erro && <p className="p-4 text-sm text-red-700 dark:text-red-300">{TEXTOS_RECORRENTES.erro}</p>}
      {!erro && lista === null && <p className="p-4 text-sm text-texto-suave">{TEXTOS_RECORRENTES.aCarregar}</p>}
      {lista && lista.length === 0 && <p className="p-4 text-sm text-texto-suave">{TEXTOS_RECORRENTES.vazio}</p>}

      {lista && lista.length > 0 && (
        <ul className="divide-y divide-borda">
          {lista.map((r) => (
            <li key={`${r.descricao}-${r.ultimo_pagamento}`} className="flex items-start justify-between gap-3 p-4">
              <div className="min-w-0">
                <p className="break-words font-medium text-texto">{r.descricao}</p>
                <p className="text-xs text-texto-suave">
                  {r.categoria && <span className="capitalize">{r.categoria} · </span>}
                  {preencher(TEXTOS_RECORRENTES.detalhe, {
                    meses: r.meses_seguidos,
                    data: dataCurta(r.ultimo_pagamento),
                  })}
                </p>
                {mudancaDePreco(r) && (
                  <p className="text-xs font-medium text-amber-700 dark:text-amber-300">{mudancaDePreco(r)}</p>
                )}
              </div>
              <p className="shrink-0 text-sm font-semibold text-texto">
                {preencher(TEXTOS_RECORRENTES.porMes, { valor: euros(r.valor_mensal) })}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
