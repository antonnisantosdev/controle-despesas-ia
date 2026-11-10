"use client";

import { useEffect, useRef, useState } from "react";

import {
  ErroApi,
  eSoPlanosPagos,
  pedirApi,
  SessaoExpirada,
  type JuncaoProdutos,
  type PrecosDoProduto,
  type PrecosPorUnidade,
} from "@/lib/api";
import { preencher } from "@/lib/planos";
import { NOME_UNIDADE, TEXTOS_PRECOS_LOJAS as T } from "@/lib/textosPrecosLojas";

import {
  dataCurta,
  ESTILO_BOTAO,
  ESTILO_ERRO,
  precoUnitario,
  textoCompras,
  textoLojas,
} from "./formatosPrecos";
import JuntarProdutos from "./JuntarProdutos";

const HISTORICO_VISIVEL = 8; // o resto fica em "Ver o histórico todo"

type Props = {
  chave: string;
  nomeInicial: string;
  juncoes: JuncaoProdutos[]; // todas: aqui mostram-se as que foram juntadas a este produto
  onVoltar: () => void;
  onMudou: () => void; // juntou ou separou: a lista tem de ser pedida outra vez
  onPlanoPago: (mensagem: string) => void;
  onSessaoExpirada: (e: unknown) => void;
};

type Resultado = { pedido: string; dados: PrecosDoProduto | null; erro: "" | "nao-existe" | "falhou" };

export default function DetalheProduto(props: Props) {
  const { chave, nomeInicial, onVoltar, onPlanoPago, onSessaoExpirada } = props;
  const [versao, setVersao] = useState(0);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const titulo = useRef<HTMLHeadingElement>(null);
  const pedido = `${versao}|${chave}`;

  // Ao abrir, o foco passa para o título: o leitor de ecrã anuncia o produto e o teclado continua daqui.
  useEffect(() => {
    titulo.current?.focus();
  }, [chave]);

  useEffect(() => {
    let cancelado = false;
    pedirApi<PrecosDoProduto>(`/compras/produtos/${encodeURIComponent(chave)}`)
      .then((dados) => {
        if (!cancelado) setResultado({ pedido, dados, erro: "" });
      })
      .catch((e) => {
        if (cancelado) return;
        if (e instanceof SessaoExpirada) onSessaoExpirada(e);
        else if (eSoPlanosPagos(e)) onPlanoPago(typeof e.detalhe === "string" ? e.detalhe : T.soPlanosPagos);
        else if (e instanceof ErroApi && e.status === 404) setResultado({ pedido, dados: null, erro: "nao-existe" });
        else setResultado({ pedido, dados: null, erro: "falhou" });
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pedido]);

  const aCarregar = resultado?.pedido !== pedido;
  const dados = resultado?.dados ?? null;
  const nome = dados?.nome ?? nomeInicial;
  const variasUnidades = (dados?.por_unidade.length ?? 0) > 1;
  const totalCompras = dados?.por_unidade.reduce((soma, u) => soma + u.lojas.reduce((s, l) => s + l.n_compras, 0), 0);

  return (
    <div className="space-y-4">
      <button type="button" onClick={onVoltar} className={ESTILO_BOTAO}>
        <span aria-hidden="true">‹</span> {T.voltar}
      </button>

      <div>
        <h2 ref={titulo} tabIndex={-1} className="break-words text-xl font-semibold text-texto focus:outline-none">
          {nome}
        </h2>
        {dados && totalCompras !== undefined && (
          <p className="text-sm text-texto-suave">{textoCompras(totalCompras)}</p>
        )}
      </div>

      <div aria-live="polite" aria-busy={aCarregar}>
        {aCarregar && !dados && <p className="text-sm text-texto-suave">{T.aCarregarProduto}</p>}
        {!aCarregar && resultado?.erro === "nao-existe" && (
          <p className="rounded-xl border border-borda bg-cartao p-6 text-sm text-texto-suave">{T.naoExiste}</p>
        )}
        {!aCarregar && resultado?.erro === "falhou" && (
          <div className={`${ESTILO_ERRO} flex flex-wrap items-center justify-between gap-2`}>
            <p>{T.erroProduto}</p>
            <button type="button" onClick={() => setVersao((v) => v + 1)} className={ESTILO_BOTAO}>
              {T.tentarOutraVez}
            </button>
          </div>
        )}
      </div>

      {dados && (
        <>
          {variasUnidades && <p className="text-sm text-texto-suave">{T.variasUnidades}</p>}
          {dados.por_unidade.map((grupo) => (
            <PrecosDeUmaUnidade key={grupo.unidade} grupo={grupo} comTitulo={variasUnidades} />
          ))}
          <p className="text-xs text-texto-suave">{T.notaLeitura}</p>
        </>
      )}

      {/* Juntar só com o produto carregado (se deu 404, já não há nada a que juntar). */}
      {dados && (
        <JuntarProdutos
          chave={chave}
          nome={nome}
          juncoes={props.juncoes.filter((j) => j.chave_destino === chave)}
          onMudou={() => {
            setVersao((v) => v + 1);
            props.onMudou();
          }}
          onPlanoPago={onPlanoPago}
          onSessaoExpirada={onSessaoExpirada}
        />
      )}
    </div>
  );
}

function PrecosDeUmaUnidade({ grupo, comTitulo }: { grupo: PrecosPorUnidade; comTitulo: boolean }) {
  const { unidade, lojas, historico } = grupo;
  if (lojas.length === 0) return null;
  const maisBarata = lojas[0]; // a API já as ordena da mais barata agora para a mais cara
  // Empates: todas as lojas com o mesmo preço mais baixo levam a etiqueta.
  const eMaisBarata = (preco: number) => preco === maisBarata.preco_recente;
  const nomeUnidade = NOME_UNIDADE[unidade] ?? unidade;
  const idTitulo = `precos-${unidade}`;

  return (
    <section aria-labelledby={idTitulo} className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <h3 id={idTitulo} className={comTitulo ? "text-base font-semibold text-texto" : "sr-only"}>
        {preencher(T.tituloUnidade, { unidade: nomeUnidade })}
      </h3>

      {/* O número mais importante do ecrã: onde está mais barato agora. */}
      <div className="rounded-lg border-2 border-destaque bg-fundo p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-destaque-hover">{T.maisBaratoAgora}</p>
        <p className="mt-1 text-3xl font-semibold tabular-nums text-texto">
          {precoUnitario(maisBarata.preco_recente, unidade)}
        </p>
        <p className="mt-1 break-words text-sm text-texto">
          {preencher(T.maisBaratoEm, { loja: maisBarata.loja })}
          <span className="text-texto-suave"> · {preencher(T.pagoA, { data: dataCurta(maisBarata.data_recente) })}</span>
        </p>
      </div>
      {lojas.length === 1 && <p className="text-sm text-texto-suave">{T.soUmaLoja}</p>}

      {lojas.length > 1 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-texto">
            {T.porLoja} <span className="font-normal text-texto-suave">({textoLojas(lojas.length)})</span>
          </h4>
          <ul className="space-y-2">
            {lojas.map((loja) => {
              const barata = eMaisBarata(loja.preco_recente);
              return (
                <li
                  key={loja.loja}
                  className={`rounded-lg border p-3 ${barata ? "border-l-4 border-destaque" : "border-borda"}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
                    <div className="min-w-0">
                      <p className="break-words font-medium text-texto">{loja.loja}</p>
                      {/* Não só pela cor: a etiqueta diz por extenso que é a mais barata. */}
                      {barata && (
                        <p className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
                          <span aria-hidden="true">✓</span> {T.etiquetaMaisBarata}
                        </p>
                      )}
                    </div>
                    <p className="ml-auto text-right">
                      <span className="block text-lg font-semibold tabular-nums text-texto">
                        {precoUnitario(loja.preco_recente, unidade)}
                      </span>
                      <span className="block text-xs text-texto-suave">
                        {T.agora} · {dataCurta(loja.data_recente)}
                      </span>
                    </p>
                  </div>
                  <dl className="mt-2 grid grid-cols-3 gap-2 border-t border-borda pt-2 text-xs">
                    <div>
                      <dt className="text-texto-suave">{T.minimo}</dt>
                      <dd className="tabular-nums text-texto">{precoUnitario(loja.preco_minimo, unidade)}</dd>
                    </div>
                    <div>
                      <dt className="text-texto-suave">{T.medio}</dt>
                      <dd className="tabular-nums text-texto">{precoUnitario(loja.preco_medio, unidade)}</dd>
                    </div>
                    <div>
                      <dt className="text-texto-suave">{T.nCompras}</dt>
                      <dd className="tabular-nums text-texto">{loja.n_compras}</dd>
                    </div>
                  </dl>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {historico.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-texto">{T.historico}</h4>
          <ListaHistorico itens={historico.slice(0, HISTORICO_VISIVEL)} unidade={unidade} />
          {historico.length > HISTORICO_VISIVEL && (
            <details className="mt-2">
              <summary className="inline-flex min-h-11 cursor-pointer items-center text-sm font-medium text-destaque-hover hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque">
                {preencher(T.verMaisHistorico, { n: historico.length })}
              </summary>
              <ListaHistorico itens={historico.slice(HISTORICO_VISIVEL)} unidade={unidade} />
            </details>
          )}
        </div>
      )}
    </section>
  );
}

function ListaHistorico({ itens, unidade }: { itens: PrecosPorUnidade["historico"]; unidade: string }) {
  return (
    <ol className="divide-y divide-borda text-sm">
      {itens.map((item, i) => (
        <li key={i} className="flex items-baseline justify-between gap-3 py-2">
          <span className="min-w-0 text-texto-suave">
            <span className="tabular-nums">{dataCurta(item.data)}</span> · <span className="break-words">{item.loja}</span>
          </span>
          <span className="shrink-0 tabular-nums text-texto">{precoUnitario(item.preco_unitario, unidade)}</span>
        </li>
      ))}
    </ol>
  );
}
