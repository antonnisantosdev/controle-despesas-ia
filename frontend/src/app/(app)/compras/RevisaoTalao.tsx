"use client";

import { useState, type FormEvent } from "react";

import { eBloqueadoNaDemo, mensagemDaApi, pedirApi, SessaoExpirada, type Compra, type ItemTalao, type Talao } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { comValorAtual, useOpcoes, useTextos } from "@/lib/textos";
import { DICIONARIO_COMPRAS } from "@/lib/textosCompras";

const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto";
const ESTILO_CELULA = "w-full rounded-md border border-borda bg-cartao px-2 py-1 text-sm text-texto";

type Props = {
  talao: Talao;
  onGravada: (compra: Compra) => void;
  onCancelar: () => void;
  onSessaoExpirada: (e: unknown) => void;
};

// O que a IA leu, num formulário: o utilizador corrige o que estiver mal e só depois grava.
export default function RevisaoTalao({ talao, onGravada, onCancelar, onSessaoExpirada }: Props) {
  const { TEXTOS_REVISAO_TALAO } = useTextos(DICIONARIO_COMPRAS);
  const { categorias, nomeCategoria, metodos, rotuloMetodo } = useOpcoes();
  const f = useFormatos();
  const [loja, setLoja] = useState(talao.loja);
  const [data, setData] = useState(talao.data ?? ""); // vazia se a IA não a conseguiu ler
  const [categoria, setCategoria] = useState(talao.categoria);
  const [metodo, setMetodo] = useState("cartao_debito");
  const [total, setTotal] = useState(talao.total);
  const [itens, setItens] = useState<ItemTalao[]>(talao.itens);
  const [aGravar, setAGravar] = useState(false);
  const [erro, setErro] = useState("");

  // Em React não se muda o array diretamente: cria-se um novo, igual ao anterior menos a linha alterada.
  function alterarItem(indice: number, alteracao: Partial<ItemTalao>) {
    setItens(itens.map((item, i) => (i === indice ? { ...item, ...alteracao } : item)));
  }

  function removerItem(indice: number) {
    setItens(itens.filter((_, i) => i !== indice));
  }

  // O preco já é o da linha (com a quantidade incluída): basta somá-los. Recalcula-se a cada alteração.
  const somaItens = itens.reduce((soma, item) => soma + item.preco, 0);
  const diferenca = total - somaItens;

  async function gravar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!data) {
      setErro(TEXTOS_REVISAO_TALAO.erroData);
      return;
    }
    setAGravar(true);
    setErro("");
    try {
      const compra = await pedirApi<Compra>("/compras", {
        loja: loja.trim(),
        data,
        itens,
        total,
        categoria,
        metodo_pagamento: metodo,
      });
      onGravada(compra);
    } catch (e) {
      if (e instanceof SessaoExpirada) onSessaoExpirada(e);
      else if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      else setErro(mensagemDaApi(e, TEXTOS_REVISAO_TALAO.erroGravar));
    } finally {
      setAGravar(false);
    }
  }

  return (
    <form onSubmit={gravar} className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-destaque">{TEXTOS_REVISAO_TALAO.etiquetaTopo}</p>
        <h2 className="text-lg font-semibold text-texto">{TEXTOS_REVISAO_TALAO.titulo}</h2>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm text-texto-suave">
          {TEXTOS_REVISAO_TALAO.loja}
          <input required value={loja} onChange={(e) => setLoja(e.target.value)} className={ESTILO_CAMPO} />
        </label>
        <label className="text-sm text-texto-suave">
          {TEXTOS_REVISAO_TALAO.data}
          <input type="date" value={data} onChange={(e) => setData(e.target.value)} className={ESTILO_CAMPO} />
        </label>
        <label className="text-sm text-texto-suave">
          {TEXTOS_REVISAO_TALAO.categoria}
          <select value={categoria} onChange={(e) => setCategoria(e.target.value)} className={ESTILO_CAMPO}>
            {comValorAtual(categorias, categoria).map((c) => (
              <option key={c} value={c}>
                {nomeCategoria(c)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-texto-suave">
          {TEXTOS_REVISAO_TALAO.metodo}
          <select value={metodo} onChange={(e) => setMetodo(e.target.value)} className={ESTILO_CAMPO}>
            {comValorAtual(metodos, metodo).map((codigo) => (
              <option key={codigo} value={codigo}>
                {rotuloMetodo(codigo)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-texto-suave">
              <th className="pb-2 font-medium">{TEXTOS_REVISAO_TALAO.colunaProduto}</th>
              <th className="w-24 pb-2 font-medium">{TEXTOS_REVISAO_TALAO.colunaQuantidade}</th>
              <th className="w-28 pb-2 font-medium">{preencher(TEXTOS_REVISAO_TALAO.colunaPreco, { simbolo: f.simbolo })}</th>
              <th className="w-10 pb-2" />
            </tr>
          </thead>
          <tbody>
            {itens.map((item, i) => (
              <tr key={i}>
                <td className="py-1 pr-2">
                  <input
                    value={item.descricao}
                    // Descrição corrigida: o nome genérico da IA deixa de valer (null), para o produto
                    // passar a ser agrupado pela descrição nova. A unidade mantém-se.
                    onChange={(e) => alterarItem(i, { descricao: e.target.value, nome_generico: null })}
                    aria-label={TEXTOS_REVISAO_TALAO.rotuloProduto}
                    className={ESTILO_CELULA}
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    type="number"
                    step="0.001"
                    min="0.001"
                    value={item.quantidade}
                    onChange={(e) => alterarItem(i, { quantidade: Number(e.target.value) })}
                    aria-label={TEXTOS_REVISAO_TALAO.rotuloQuantidade}
                    className={ESTILO_CELULA}
                  />
                </td>
                <td className="py-1 pr-2">
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={item.preco}
                    onChange={(e) => alterarItem(i, { preco: Number(e.target.value) })}
                    aria-label={TEXTOS_REVISAO_TALAO.rotuloPreco}
                    className={ESTILO_CELULA}
                  />
                </td>
                <td className="py-1 text-right">
                  <button
                    type="button"
                    onClick={() => removerItem(i)}
                    aria-label={preencher(TEXTOS_REVISAO_TALAO.remover, { descricao: item.descricao })}
                    className="rounded-md px-2 py-1 text-texto-suave hover:bg-fundo hover:text-texto"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-3">
        <label className="text-sm text-texto-suave">
          {preencher(TEXTOS_REVISAO_TALAO.total, { simbolo: f.simbolo })}
          <input
            type="number"
            step="0.01"
            min="0.01"
            required
            value={total}
            onChange={(e) => setTotal(Number(e.target.value))}
            className={`${ESTILO_CAMPO} sm:w-40`}
          />
        </label>
        <p className="text-sm text-texto-suave">
          {TEXTOS_REVISAO_TALAO.soma}
          <span className="font-semibold text-texto">{f.dinheiro(somaItens)}</span>
        </p>
      </div>

      {/* A IA pode ter lido mal um preço: se a soma não bater com o total, avisa (mas deixa gravar). */}
      {Math.abs(diferenca) > 0.01 && (
        <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          {preencher(TEXTOS_REVISAO_TALAO.diferenca, { diferenca: f.dinheiro(Math.abs(diferenca)) })}
        </p>
      )}

      {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancelar}
          className="rounded-lg border border-borda px-4 py-2 text-sm font-medium text-texto hover:bg-fundo"
        >
          {TEXTOS_REVISAO_TALAO.cancelar}
        </button>
        <button
          type="submit"
          disabled={aGravar || itens.length === 0}
          className="rounded-lg bg-destaque px-4 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
        >
          {aGravar ? TEXTOS_REVISAO_TALAO.aGravar : TEXTOS_REVISAO_TALAO.gravar}
        </button>
      </div>
    </form>
  );
}
