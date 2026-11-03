"use client";

import { useState, type FormEvent } from "react";

import type { LinhaOrcamento } from "@/lib/api";

import { euros } from "../dashboard/formatos";

type Props = { linha: LinhaOrcamento; onGuardar: (categoria: string, limite: number) => void; compacta?: boolean };

// Cor da barra conforme a percentagem gasta. O texto ao lado diz sempre os números,
// por isso a cor nunca é a única pista.
function corDaBarra(percentagem: number) {
  if (percentagem > 100) return "bg-red-500";
  if (percentagem >= 80) return "bg-amber-500";
  return "bg-destaque";
}

export default function LinhaPlaneamento({ linha, onGuardar, compacta = false }: Props) {
  const [valor, setValor] = useState(linha.limite?.toString().replace(".", ",") ?? "");

  function submeter(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const numero = Number(valor.replace(",", "."));
    if (numero > 0) onGuardar(linha.categoria, numero);
  }

  const formulario = (
    <form onSubmit={submeter} className="flex items-center gap-2">
      <input
        inputMode="decimal"
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        placeholder="Limite €"
        aria-label={`Orçamento mensal de ${linha.categoria}`}
        className="w-24 rounded-md border border-borda bg-cartao px-2 py-1 text-right text-sm text-texto"
      />
      <button type="submit" className="rounded-md bg-destaque px-3 py-1 text-xs font-medium text-white hover:bg-destaque-hover">
        Guardar
      </button>
    </form>
  );

  if (compacta) return formulario;

  const percentagem = linha.limite ? (linha.gasto / linha.limite) * 100 : 0;

  return (
    <div className="space-y-2 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-medium capitalize text-texto">{linha.categoria}</p>
          <p className="text-xs text-texto-suave">
            {linha.limite === null
              ? `Gastaste ${euros(linha.gasto)} · sem orçamento`
              : percentagem > 100
                ? `${euros(linha.gasto)} de ${euros(linha.limite)} · passaste ${euros(linha.gasto - linha.limite)}`
                : `${euros(linha.gasto)} de ${euros(linha.limite)} · faltam ${euros(linha.limite - linha.gasto)}`}
          </p>
        </div>
        {/* Não dá para pôr orçamento em "sem categoria": primeiro categoriza-se a transação. */}
        {linha.categoria !== "sem categoria" && formulario}
      </div>

      {linha.limite !== null && (
        <div className="h-2 overflow-hidden rounded-full bg-fundo" role="progressbar" aria-valuenow={Math.round(percentagem)}>
          <div className={`h-full rounded-full ${corDaBarra(percentagem)}`} style={{ width: `${Math.min(percentagem, 100)}%` }} />
        </div>
      )}
    </div>
  );
}
