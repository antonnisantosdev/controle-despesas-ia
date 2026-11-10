"use client";

import { useState } from "react";

import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import { eBloqueadoNaDemo, eLimiteDiario, ErroApi, pedirApi, SessaoExpirada, type Transacao } from "@/lib/api";
import { preencher } from "@/lib/planos";
import { TEXTOS_CATEGORIZAR } from "@/lib/textosPlanos";

// Pendentes que a API categoriza em cada clique (MAX_PENDENTES_POR_PEDIDO no main.py): as mais recentes primeiro.
const LOTE_POR_CLIQUE = 300;

type Props = {
  quantas: number; // transações sem categoria em todos os meses
  onCategorizadas: (atualizadas: Transacao[]) => void;
  onErro: (mensagem: string) => void;
  onSessaoExpirada: (e: unknown) => void;
  onLimiteDiario: () => void; // 429: a página mostra o AvisoLimite
  desligado?: boolean; // demo (só leitura): o botão fica desligado
};

// Botão que pede à IA as categorias das transações sem categoria (POST /transacoes/categorizar).
// Cada clique manda um lote de até LOTE_POR_CLIQUE numa só chamada: conta como 1 pedido à IA.
// O botão mostra quantas vão neste clique; se houver mais, o número volta a aparecer depois.
export default function BotaoCategorizar({
  quantas,
  onCategorizadas,
  onErro,
  onSessaoExpirada,
  onLimiteDiario,
  desligado = false,
}: Props) {
  const [aCategorizar, setACategorizar] = useState(false);

  async function categorizar() {
    setACategorizar(true);
    try {
      const atualizadas = await pedirApi<Transacao[]>("/transacoes/categorizar", undefined, "POST");
      onCategorizadas(atualizadas);
    } catch (e) {
      if (e instanceof SessaoExpirada) {
        onSessaoExpirada(e);
      } else if (eBloqueadoNaDemo(e)) {
        // 423 da demo: a faixa já explica
      } else if (eLimiteDiario(e)) {
        onLimiteDiario();
      } else if (e instanceof ErroApi && typeof e.detalhe === "string") {
        onErro(e.detalhe); // ex.: 503 "A categorização automática falhou. Tenta mais tarde."
      } else {
        onErro(TEXTOS_CATEGORIZAR.erro);
      }
    } finally {
      setACategorizar(false);
    }
  }

  return (
    <button
      type="button"
      disabled={aCategorizar || desligado}
      aria-describedby={desligado ? ID_NOTA_DEMO : undefined}
      aria-busy={aCategorizar}
      onClick={categorizar}
      className="min-h-11 w-full rounded-lg border border-borda bg-cartao px-4 py-2 text-sm font-medium text-texto hover:bg-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-50 sm:w-auto"
    >
      {aCategorizar ? TEXTOS_CATEGORIZAR.aCategorizar : preencher(TEXTOS_CATEGORIZAR.botao, { n: Math.min(quantas, LOTE_POR_CLIQUE) })}
    </button>
  );
}
