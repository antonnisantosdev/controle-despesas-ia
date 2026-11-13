"use client";

import { useState, type FormEvent } from "react";

import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import type { LinhaOrcamento } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { useOpcoes, useTextos } from "@/lib/textos";
import { DICIONARIO_PLANEAMENTO } from "@/lib/textosPlaneamento";

// desligado: demo (só leitura), o campo e o botão Guardar ficam desligados.
type Props = {
  linha: LinhaOrcamento;
  onGuardar: (categoria: string, limite: number) => void;
  compacta?: boolean;
  desligado?: boolean;
};

// Cor da barra conforme a percentagem gasta. O texto ao lado diz sempre os números,
// por isso a cor nunca é a única pista.
function corDaBarra(percentagem: number) {
  if (percentagem > 100) return "bg-red-500";
  if (percentagem >= 80) return "bg-amber-500";
  return "bg-destaque";
}

export default function LinhaPlaneamento({ linha, onGuardar, compacta = false, desligado = false }: Props) {
  const { TEXTOS_LINHA_ORCAMENTO } = useTextos(DICIONARIO_PLANEAMENTO);
  const { rotuloCategoria, nomeCategoria } = useOpcoes();
  const f = useFormatos();
  const [valor, setValor] = useState(linha.limite?.toString().replace(".", ",") ?? "");

  function submeter(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const numero = Number(valor.replace(",", "."));
    if (numero > 0 && !desligado) onGuardar(linha.categoria, numero);
  }

  const formulario = (
    <form onSubmit={submeter} className="flex items-center gap-2">
      <input
        inputMode="decimal"
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        disabled={desligado}
        placeholder={preencher(TEXTOS_LINHA_ORCAMENTO.marcador, { simbolo: f.simbolo })}
        aria-label={preencher(TEXTOS_LINHA_ORCAMENTO.rotuloCampo, { categoria: rotuloCategoria(linha.categoria) })}
        className="w-24 rounded-md border border-borda bg-cartao px-2 py-1 text-right text-sm text-texto"
      />
      <button
        type="submit"
        disabled={desligado}
        aria-describedby={desligado ? ID_NOTA_DEMO : undefined}
        className="rounded-md bg-destaque px-3 py-1 text-xs font-medium text-white hover:bg-destaque-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        {TEXTOS_LINHA_ORCAMENTO.guardar}
      </button>
    </form>
  );

  if (compacta) return formulario;

  const percentagem = linha.limite ? (linha.gasto / linha.limite) * 100 : 0;

  return (
    <div className="space-y-2 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-medium text-texto">{nomeCategoria(linha.categoria)}</p>
          <p className="text-xs text-texto-suave">
            {linha.limite === null
              ? preencher(TEXTOS_LINHA_ORCAMENTO.semOrcamento, { gasto: f.dinheiro(linha.gasto) })
              : percentagem > 100
                ? preencher(TEXTOS_LINHA_ORCAMENTO.passaste, {
                    gasto: f.dinheiro(linha.gasto),
                    limite: f.dinheiro(linha.limite),
                    diferenca: f.dinheiro(linha.gasto - linha.limite),
                  })
                : preencher(TEXTOS_LINHA_ORCAMENTO.faltam, {
                    gasto: f.dinheiro(linha.gasto),
                    limite: f.dinheiro(linha.limite),
                    diferenca: f.dinheiro(linha.limite - linha.gasto),
                  })}
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
