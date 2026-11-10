"use client";

import { useEffect, useRef, useState } from "react";

import { eBloqueadoNaDemo, ErroApi, pedirApi, SessaoExpirada, type Compra, type Transacao } from "@/lib/api";
import { preencher } from "@/lib/planos";
import { TEXTOS_APAGAR_MOVIMENTO } from "@/lib/textosPlanos";

import { euros } from "../dashboard/formatos";

type Props = {
  transacao: Transacao;
  onApagada: (mensagem: string) => void; // apagou (ou já não existia): a página volta a pedir a lista
  onFechar: () => void; // o diálogo fechou (Cancelar, Esc ou depois de apagar)
  onSessaoExpirada: (e: unknown) => void;
};

// Se a movimentação veio de um talão: "a-verificar" enquanto se pede GET /compras,
// "desconhecido" se esse pedido falhar (mostra-se o aviso na mesma, por precaução).
type EstadoTalao = "a-verificar" | "sim" | "nao" | "desconhecido";

// "2026-10-05" -> "05/10/2026"
function dataCurta(data: string) {
  const [ano, mes, dia] = data.split("-");
  return `${dia}/${mes}/${ano}`;
}

// Confirmação antes de DELETE /transacoes/{id}. <dialog> nativo com showModal(): prende o foco lá dentro,
// fecha com Esc e devolve o foco ao botão que o abriu.
export default function DialogoApagar({ transacao, onApagada, onFechar, onSessaoExpirada }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [talao, setTalao] = useState<EstadoTalao>("a-verificar");
  const [aApagar, setAApagar] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    // Só se ainda não estiver aberto (em desenvolvimento, o React corre os efeitos duas vezes).
    if (dialogo.current && !dialogo.current.open) dialogo.current.showModal();
    // A cascata da base de dados apaga a compra e os produtos do talão: avisa-se antes.
    let cancelado = false;
    pedirApi<Compra[]>("/compras")
      .then((compras) => {
        if (!cancelado) setTalao(compras.some((c) => c.transacao_id === transacao.id) ? "sim" : "nao");
      })
      .catch(() => {
        if (!cancelado) setTalao("desconhecido");
      });
    return () => {
      cancelado = true;
    };
  }, [transacao.id]);

  function fechar() {
    dialogo.current?.close(); // dispara o "close", que chama o onFechar
  }

  async function apagar() {
    setErro("");
    setAApagar(true);
    try {
      await pedirApi(`/transacoes/${transacao.id}`, undefined, "DELETE");
      onApagada(TEXTOS_APAGAR_MOVIMENTO.sucesso);
      fechar();
    } catch (e) {
      setAApagar(false);
      if (e instanceof SessaoExpirada) {
        onSessaoExpirada(e);
      } else if (eBloqueadoNaDemo(e)) {
        fechar(); // 423 da demo: a faixa já explica
      } else if (e instanceof ErroApi && e.status === 404) {
        onApagada(TEXTOS_APAGAR_MOVIMENTO.naoEncontrada);
        fechar();
      } else {
        setErro(TEXTOS_APAGAR_MOVIMENTO.erro);
      }
    }
  }

  return (
    <dialog
      ref={dialogo}
      onClose={onFechar}
      aria-labelledby="titulo-apagar-movimento"
      aria-describedby="texto-apagar-movimento"
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-xl border border-borda bg-cartao p-4 text-texto backdrop:bg-black/60 sm:p-6"
    >
      <h2 id="titulo-apagar-movimento" className="text-lg font-semibold text-texto">
        {TEXTOS_APAGAR_MOVIMENTO.titulo}
      </h2>
      <p id="texto-apagar-movimento" className="mt-2 break-words text-sm text-texto-suave">
        {preencher(TEXTOS_APAGAR_MOVIMENTO.texto, {
          descricao: transacao.descricao,
          valor: euros(transacao.valor),
          data: dataCurta(transacao.data),
        })}
      </p>
      {(talao === "sim" || talao === "desconhecido") && (
        <p className="mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          {TEXTOS_APAGAR_MOVIMENTO.avisoTalao}
        </p>
      )}
      {erro && (
        <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">
          {erro}
        </p>
      )}
      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        {/* autoFocus no Cancelar: um Enter sem pensar não apaga nada. */}
        <button
          type="button"
          autoFocus
          onClick={fechar}
          className="min-h-11 rounded-md border border-borda bg-cartao px-4 py-2 text-sm font-medium text-texto hover:bg-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          {TEXTOS_APAGAR_MOVIMENTO.cancelar}
        </button>
        {/* Espera pela verificação do talão, para o aviso aparecer antes de se poder confirmar. */}
        <button
          type="button"
          onClick={apagar}
          disabled={aApagar || talao === "a-verificar"}
          className="min-h-11 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {aApagar ? TEXTOS_APAGAR_MOVIMENTO.aApagar : TEXTOS_APAGAR_MOVIMENTO.confirmar}
        </button>
      </div>
    </dialog>
  );
}
