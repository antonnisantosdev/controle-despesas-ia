"use client";

import type { Ref } from "react";

import type { ItemListaCompras, ListaCompras } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_FAZER_COMPRAS } from "@/lib/textosFazerCompras";

import { linkSeguro } from "./linkSeguro";

type Props = {
  resultado: ListaCompras;
  nomeMercado: (chave: string) => string; // a chave da API ("pingo_doce") -> o nome ("Pingo Doce")
  tituloRef: Ref<HTMLHeadingElement>; // a página põe o foco no título quando o plano chega
};

const FOCO = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";

// Como a API compara os pedidos: minúsculas, sem acentos e sem os espaços das pontas
// ("Arroz " e "arroz" são o mesmo produto).
function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

// Seta de "abre fora da app" (decorativa: o aria-label do link já o diz).
function IconeExterno() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// O plano devolvido pela IA: resumo (total e orçamento), um cartão por mercado, produtos sem preço
// e a comparação de todos os produtos em todos os mercados (recolhida por omissão).
export default function ResultadoPlano({ resultado, nomeMercado, tituloRef }: Props) {
  const { TEXTOS_RESULTADO_COMPRAS: T } = useTextos(DICIONARIO_FAZER_COMPRAS);
  const f = useFormatos();
  const dentro = resultado.diferenca >= 0;

  // Que produto ficou em que mercado no plano (para a etiqueta "No plano" na comparação).
  const noPlano = new Set(
    resultado.plano.flatMap((m) => m.itens.map((i) => `${normalizar(m.mercado)}\u0000${normalizar(i.pedido)}`)),
  );

  // A comparação agrupada pelo pedido normalizado (como a API faz), pela ordem em que a API os mandou.
  // O título do grupo é o pedido tal como veio no primeiro item.
  const porPedido = new Map<string, { pedido: string; itens: ItemListaCompras[] }>();
  for (const item of resultado.itens) {
    const chave = normalizar(item.pedido);
    const grupo = porPedido.get(chave);
    if (grupo) grupo.itens.push(item);
    else porPedido.set(chave, { pedido: item.pedido, itens: [item] });
  }

  return (
    <section aria-labelledby="titulo-plano" className="space-y-4">
      <h2 id="titulo-plano" ref={tituloRef} tabIndex={-1} className="text-lg font-semibold text-texto focus:outline-none">
        {T.titulo}
      </h2>

      {resultado.exemplo && (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm font-medium text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          {T.exemplo}
        </p>
      )}

      {/* Resumo: o total é o número que salta à vista; ao lado, o orçamento e quanto sobra ou falta. */}
      <div className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-texto-suave">{T.total}</p>
            <p className="text-3xl font-semibold text-texto tabular-nums">{f.dinheiro(resultado.total)}</p>
            <p className="mt-1 text-sm text-texto-suave">
              {T.orcamento}: <span className="font-medium text-texto tabular-nums">{f.dinheiro(resultado.orcamento)}</span>
            </p>
          </div>
          <p
            className={`rounded-lg px-3 py-2 text-sm font-semibold tabular-nums ${
              dentro
                ? "bg-destaque/10 text-destaque"
                : "border border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
            }`}
          >
            {preencher(dentro ? T.sobram : T.passa, { valor: f.dinheiro(Math.abs(resultado.diferenca)) })}
          </p>
        </div>
        <p className="mt-4 border-t border-borda pt-3 text-xs text-texto-suave">{T.aviso}</p>
      </div>

      {resultado.plano.length === 0 ? (
        <p className="rounded-xl border border-borda bg-cartao p-4 text-sm text-texto-suave sm:p-6">{T.planoVazio}</p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {resultado.plano.map((mercado) => {
            const nome = nomeMercado(mercado.mercado);
            const mapa = linkSeguro(mercado.mapa_url);
            return (
              <li key={mercado.mercado} className="flex flex-col rounded-xl border border-borda bg-cartao">
                <div className="flex items-start justify-between gap-3 border-b border-borda p-4">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-texto">{nome}</h3>
                    <p className="text-xs text-texto-suave">
                      {mercado.itens.length === 1 ? T.umProduto : preencher(T.nProdutos, { n: mercado.itens.length })}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-texto-suave">{T.totalMercado}</p>
                    <p className="text-lg font-semibold text-texto tabular-nums">{f.dinheiro(mercado.total)}</p>
                  </div>
                </div>

                <ul className="flex-1 divide-y divide-borda px-4">
                  {mercado.itens.map((item, i) => {
                    const link = linkSeguro(item.link);
                    const produto = item.produto || item.pedido; // "" sem nome: mostra o que a pessoa pediu
                    return (
                      <li key={`${item.pedido}-${i}`} className="flex items-start justify-between gap-3 py-3 text-sm">
                        <div className="min-w-0">
                          <p className="break-words text-texto">
                            {item.embalagens > 0 && (
                              <span className="font-medium tabular-nums">{preencher(T.embalagens, { n: f.numero(item.embalagens) })} </span>
                            )}
                            {produto}
                          </p>
                          <p className="break-words text-xs text-texto-suave">{preencher(T.paraPedido, { pedido: item.pedido })}</p>
                          {link && (
                            <a
                              href={link}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label={preencher(T.verNoSiteRotulo, { produto, mercado: nome })}
                              className={`inline-flex min-h-11 items-center gap-1 rounded-md text-xs font-medium text-destaque underline underline-offset-2 hover:no-underline ${FOCO}`}
                            >
                              {T.verNoSite}
                              <IconeExterno />
                            </a>
                          )}
                        </div>
                        <span className="shrink-0 font-medium text-texto tabular-nums">{f.dinheiro(item.preco_total)}</span>
                      </li>
                    );
                  })}
                </ul>

                {mapa && (
                  <div className="border-t border-borda p-4">
                    <a
                      href={mapa}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={preencher(T.mapaRotulo, { mercado: nome })}
                      className={`flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-borda px-4 text-sm font-medium text-texto hover:bg-fundo ${FOCO}`}
                    >
                      <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
                        <path d="M12 21s-7-6.1-7-11.5A7 7 0 0 1 19 9.5C19 14.9 12 21 12 21zM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      {T.mapa}
                    </a>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {resultado.sem_preco.length > 0 && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950/40">
          <h3 className="font-semibold text-amber-900 dark:text-amber-200">{T.semPrecoTitulo}</h3>
          <p className="mt-1 text-amber-900 dark:text-amber-200">{T.semPrecoTexto}</p>
          <ul className="mt-2 list-disc space-y-0.5 pl-5 text-amber-900 dark:text-amber-200">
            {resultado.sem_preco.map((pedido, i) => (
              <li key={`${pedido}-${i}`} className="break-words">
                {pedido}
              </li>
            ))}
          </ul>
        </div>
      )}

      {porPedido.size > 0 && (
        // <details>: abre e fecha sozinho, sem estado em React (como as compras em Minhas compras).
        <details className="group rounded-xl border border-borda bg-cartao">
          <summary
            className={`flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 rounded-xl px-4 py-3 ${FOCO} [&::-webkit-details-marker]:hidden`}
          >
            <span>
              <span className="block font-medium text-texto">{T.comparacao}</span>
              <span className="block text-xs text-texto-suave">{T.comparacaoDica}</span>
            </span>
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4 shrink-0 text-texto-suave transition-transform group-open:rotate-180 motion-reduce:transition-none"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden
            >
              <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </summary>

          <div className="divide-y divide-borda border-t border-borda">
            {[...porPedido.entries()].map(([chave, { pedido, itens }]) => (
              <div key={chave} className="p-4">
                <h3 className="break-words text-sm font-semibold text-texto">{pedido}</h3>
                <ul className="mt-2 space-y-3">
                  {itens.map((item, i) => {
                    const nome = nomeMercado(item.mercado);
                    const link = linkSeguro(item.link);
                    // Sem preço, a API manda 0 e "" (nunca null).
                    const comPreco = item.encontrado && item.preco_total > 0;
                    const escolhido = noPlano.has(`${normalizar(item.mercado)}\u0000${normalizar(item.pedido)}`);
                    return (
                      <li key={`${item.mercado}-${i}`} className="flex items-start justify-between gap-3 text-sm">
                        <div className="min-w-0">
                          <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
                            <span className="font-medium text-texto">{nome}</span>
                            {escolhido && (
                              <span className="rounded-full bg-destaque/10 px-2 py-0.5 text-xs font-medium text-destaque">{T.noPlano}</span>
                            )}
                          </p>
                          {comPreco && item.produto && (
                            <p className="break-words text-texto-suave">
                              {item.embalagens > 0 && (
                                <span className="tabular-nums">{preencher(T.embalagens, { n: f.numero(item.embalagens) })} </span>
                              )}
                              {item.produto}
                            </p>
                          )}
                          {comPreco && item.preco_embalagem > 0 && (
                            <p className="text-xs text-texto-suave tabular-nums">
                              {preencher(T.porEmbalagem, { preco: f.dinheiro(item.preco_embalagem) })}
                            </p>
                          )}
                          {item.nota && <p className="break-words text-xs text-texto-suave">{item.nota}</p>}
                          {link && (
                            <a
                              href={link}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label={preencher(T.verNoSiteRotulo, { produto: item.produto || item.pedido, mercado: nome })}
                              className={`inline-flex min-h-11 items-center gap-1 rounded-md text-xs font-medium text-destaque underline underline-offset-2 hover:no-underline ${FOCO}`}
                            >
                              {T.verNoSite}
                              <IconeExterno />
                            </a>
                          )}
                        </div>
                        <span className={`shrink-0 tabular-nums ${comPreco ? "font-medium text-texto" : "text-texto-suave"}`}>
                          {comPreco ? f.dinheiro(item.preco_total as number) : T.naoEncontrado}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}
