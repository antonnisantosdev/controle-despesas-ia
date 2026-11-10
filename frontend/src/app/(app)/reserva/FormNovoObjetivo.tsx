"use client";

import { useState, type FormEvent } from "react";

import { eBloqueadoNaDemo, pedirApi, SessaoExpirada, type Objetivo } from "@/lib/api";

const ESTILO_CAMPO = "mt-1 w-full rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto";

type Props = {
  onCriado: (objetivo: Objetivo) => void;
  onFechar: () => void;
  onSessaoExpirada: (e: unknown) => void;
};

export default function FormNovoObjetivo({ onCriado, onFechar, onSessaoExpirada }: Props) {
  const [nome, setNome] = useState("");
  const [valor, setValor] = useState("");
  const [data, setData] = useState("");
  const [aGuardar, setAGuardar] = useState(false);
  const [erro, setErro] = useState("");

  async function guardar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    // Aceita "1200,50" e "1200.50".
    const numero = Number(valor.replace(",", "."));
    if (!(numero > 0)) {
      setErro("Escreve um valor maior do que zero.");
      return;
    }

    setAGuardar(true);
    setErro("");
    try {
      onCriado(await pedirApi<Objetivo>("/objetivos", { nome: nome.trim(), valor_alvo: numero, data_alvo: data }));
    } catch (e) {
      if (e instanceof SessaoExpirada) onSessaoExpirada(e);
      else if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      else setErro("Não foi possível guardar. Confirma os dados e tenta outra vez.");
    } finally {
      setAGuardar(false);
    }
  }

  return (
    <form onSubmit={guardar} className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <h2 className="font-medium text-texto">Novo objetivo</h2>
        <button type="button" onClick={onFechar} className="text-sm text-texto-suave hover:text-texto">
          Cancelar
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block sm:col-span-2">
          <span className="text-sm text-texto-suave">Nome</span>
          <input
            required
            maxLength={100}
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Ex.: Férias no verão"
            className={ESTILO_CAMPO}
          />
        </label>

        <label className="block">
          <span className="text-sm text-texto-suave">Quanto queres juntar (€)</span>
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
          <span className="text-sm text-texto-suave">Até quando</span>
          <input type="date" required value={data} onChange={(e) => setData(e.target.value)} className={ESTILO_CAMPO} />
        </label>
      </div>

      {erro && <p className="text-sm text-red-600 dark:text-red-400">{erro}</p>}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={aGuardar}
          className="rounded-md bg-destaque px-5 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
        >
          {aGuardar ? "A guardar..." : "Guardar"}
        </button>
      </div>
    </form>
  );
}
