"use client";

import { useState, type FormEvent } from "react";

import { mensagemDaApi, pedirApi, SessaoExpirada, type Transacao } from "@/lib/api";
import { CATEGORIAS, METODOS_PAGAMENTO } from "@/lib/opcoes";

// Data de hoje no formato do <input type="date"> (AAAA-MM-DD), na hora local.
function hoje() {
  const agora = new Date();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  const dia = String(agora.getDate()).padStart(2, "0");
  return `${agora.getFullYear()}-${mes}-${dia}`;
}

const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto";

type Props = { onCriada: (transacao: Transacao) => void; onFechar: () => void };

export default function FormNovaMovimentacao({ onCriada, onFechar }: Props) {
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
      setErro("Escreve um valor maior do que zero.");
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
      setErro(
        e instanceof SessaoExpirada
          ? "A tua sessão expirou. Faz login de novo."
          : mensagemDaApi(e, "Não foi possível guardar. Confirma os dados e tenta outra vez."),
      );
    } finally {
      setAGuardar(false);
    }
  }

  return (
    <form onSubmit={guardar} className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <h2 className="font-medium text-texto">Nova movimentação</h2>
        <button type="button" onClick={onFechar} className="text-sm text-texto-suave hover:text-texto">
          Cancelar
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
            {opcao === "despesa" ? "Despesa" : "Entrada"}
          </button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block sm:col-span-2">
          <span className="text-sm text-texto-suave">Descrição</span>
          <input
            required
            maxLength={200}
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="Ex.: Café com o João"
            className={ESTILO_CAMPO}
          />
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">Valor (€)</span>
          <input
            required
            inputMode="decimal"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder="0,00"
            className={ESTILO_CAMPO}
          />
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">Data</span>
          <input type="date" required value={data} onChange={(e) => setData(e.target.value)} className={ESTILO_CAMPO} />
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">Método de pagamento</span>
          <select value={metodo} onChange={(e) => setMetodo(e.target.value)} className={ESTILO_CAMPO}>
            {Object.entries(METODOS_PAGAMENTO).map(([codigo, nome]) => (
              <option key={codigo} value={codigo}>
                {nome}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">Categoria</span>
          <select value={categoria} onChange={(e) => setCategoria(e.target.value)} className={`${ESTILO_CAMPO} capitalize`}>
            <option value="">✨ Deixar a IA escolher</option>
            {CATEGORIAS.map((c) => (
              <option key={c} value={c}>
                {c}
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
          {aGuardar ? (categoria ? "A guardar..." : "A IA está a categorizar...") : "Guardar"}
        </button>
      </div>
    </form>
  );
}
