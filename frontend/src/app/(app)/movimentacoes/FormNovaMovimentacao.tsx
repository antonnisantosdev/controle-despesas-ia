"use client";

import { useState, type FormEvent } from "react";

import { eBloqueadoNaDemo, mensagemDaApi, pedirApi, SessaoExpirada, type Transacao } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { comValorAtual, useOpcoes, useTextos } from "@/lib/textos";
import { DICIONARIO_COMUNS } from "@/lib/textosComuns";
import { DICIONARIO_MOVIMENTACOES } from "@/lib/textosMovimentacoes";

// Data de hoje no formato do <input type="date"> (AAAA-MM-DD), na hora local.
function hoje() {
  const agora = new Date();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  const dia = String(agora.getDate()).padStart(2, "0");
  return `${agora.getFullYear()}-${mes}-${dia}`;
}

const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto";

// O mesmo teto da API (models.py, VALOR_MAXIMO): acima disto a base de dados não guarda o valor.
const VALOR_MAXIMO = 1_000_000_000;

type Props = { onCriada: (transacao: Transacao) => void; onFechar: () => void };

export default function FormNovaMovimentacao({ onCriada, onFechar }: Props) {
  const { TEXTOS_GERAIS } = useTextos(DICIONARIO_COMUNS);
  const { TEXTOS_NOVA_MOVIMENTACAO } = useTextos(DICIONARIO_MOVIMENTACOES);
  const { categorias, nomeCategoria, metodos, rotuloMetodo } = useOpcoes();
  const f = useFormatos();
  const [tipo, setTipo] = useState<"despesa" | "entrada">("despesa");
  const [descricao, setDescricao] = useState("");
  const [valor, setValor] = useState("");
  const [data, setData] = useState(hoje());
  const [metodo, setMetodo] = useState("cartao_debito");
  const [categoria, setCategoria] = useState(""); // "" = a IA escolhe
  const [aGuardar, setAGuardar] = useState(false);
  const [erro, setErro] = useState("");

  async function guardar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    // Aceita "3,50" e "3.50". O utilizador escreve sempre positivo; o tipo decide o sinal.
    const numero = Number(valor.replace(",", "."));
    if (!(numero > 0)) {
      setErro(TEXTOS_NOVA_MOVIMENTACAO.erroValor);
      return;
    }
    if (numero > VALOR_MAXIMO) {
      setErro(preencher(TEXTOS_NOVA_MOVIMENTACAO.erroValorMaximo, { maximo: f.dinheiro(VALOR_MAXIMO, 0) }));
      return;
    }

    setAGuardar(true);
    setErro("");
    try {
      const criada = await pedirApi<Transacao>("/transacoes", {
        data,
        descricao: descricao.trim(),
        valor: tipo === "despesa" ? -numero : numero,
        metodo_pagamento: metodo,
        categoria: categoria || null,
      });
      onCriada(criada);
    } catch (e) {
      if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      setErro(
        e instanceof SessaoExpirada
          ? TEXTOS_GERAIS.sessaoExpirou
          : mensagemDaApi(e, TEXTOS_NOVA_MOVIMENTACAO.erroGuardar),
      );
    } finally {
      setAGuardar(false);
    }
  }

  return (
    <form onSubmit={guardar} className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <h2 className="font-medium text-texto">{TEXTOS_NOVA_MOVIMENTACAO.titulo}</h2>
        <button type="button" onClick={onFechar} className="text-sm text-texto-suave hover:text-texto">
          {TEXTOS_NOVA_MOVIMENTACAO.cancelar}
        </button>
      </div>

      {/* Despesa ou entrada: dois botões em vez de pedir um valor negativo. */}
      <div className="inline-flex rounded-lg border border-borda p-1">
        {(["despesa", "entrada"] as const).map((opcao) => (
          <button
            key={opcao}
            type="button"
            onClick={() => setTipo(opcao)}
            className={`rounded-md px-4 py-1.5 text-sm ${
              tipo === opcao ? "bg-destaque font-medium text-white" : "text-texto-suave hover:text-texto"
            }`}
          >
            {opcao === "despesa" ? TEXTOS_NOVA_MOVIMENTACAO.despesa : TEXTOS_NOVA_MOVIMENTACAO.entrada}
          </button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block sm:col-span-2">
          <span className="text-sm text-texto-suave">{TEXTOS_NOVA_MOVIMENTACAO.descricao}</span>
          <input
            required
            maxLength={200}
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder={TEXTOS_NOVA_MOVIMENTACAO.marcadorDescricao}
            className={ESTILO_CAMPO}
          />
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">{preencher(TEXTOS_NOVA_MOVIMENTACAO.valor, { simbolo: f.simbolo })}</span>
          <input
            required
            inputMode="decimal"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder={TEXTOS_NOVA_MOVIMENTACAO.marcadorValor}
            className={ESTILO_CAMPO}
          />
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">{TEXTOS_NOVA_MOVIMENTACAO.data}</span>
          <input type="date" required value={data} onChange={(e) => setData(e.target.value)} className={ESTILO_CAMPO} />
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">{TEXTOS_NOVA_MOVIMENTACAO.metodo}</span>
          <select value={metodo} onChange={(e) => setMetodo(e.target.value)} className={ESTILO_CAMPO}>
            {comValorAtual(metodos, metodo).map((codigo) => (
              <option key={codigo} value={codigo}>
                {rotuloMetodo(codigo)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">{TEXTOS_NOVA_MOVIMENTACAO.categoria}</span>
          <select value={categoria} onChange={(e) => setCategoria(e.target.value)} className={ESTILO_CAMPO}>
            <option value="">{TEXTOS_NOVA_MOVIMENTACAO.iaEscolhe}</option>
            {comValorAtual(categorias, categoria).map((c) => (
              <option key={c} value={c}>
                {nomeCategoria(c)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {erro && <p className="text-sm text-red-600 dark:text-red-400">{erro}</p>}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={aGuardar}
          className="rounded-md bg-destaque px-5 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
        >
          {aGuardar
            ? categoria
              ? TEXTOS_NOVA_MOVIMENTACAO.aGuardar
              : TEXTOS_NOVA_MOVIMENTACAO.aCategorizar
            : TEXTOS_NOVA_MOVIMENTACAO.guardar}
        </button>
      </div>
    </form>
  );
}
