"use client";

import { useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import { eBloqueadoNaDemo, ErroApi, mensagemDaApi, pedirApi, SessaoExpirada, type Transacao } from "@/lib/api";
import { preencher } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_MOVIMENTACOES } from "@/lib/textosMovimentacoes";

// O mesmo máximo da API (models.py, MAX_CARACTERES_NOTA) e da base de dados (sql/025).
export const MAX_CARACTERES_NOTA = 300;

type Props = {
  transacao: Transacao;
  desligado: boolean; // demo: só leitura (a API responde 423 na mesma)
  onGuardada: (atualizada: Transacao) => void;
  onSessaoExpirada: (erro: unknown) => void;
};

// A nota pessoal de uma movimentação, por baixo da descrição: o texto (mais suave) e um botão para
// adicionar ou editar, que abre um campo com Guardar/Cancelar. Esc cancela. Guardar vazio apaga a nota.
// Usado na tabela (computador) e nos cartões (telemóvel): useId dá ids diferentes às duas cópias.
export default function CampoNota({ transacao, desligado, onGuardada, onSessaoExpirada }: Props) {
  const { TEXTOS_MOVIMENTACOES: T } = useTextos(DICIONARIO_MOVIMENTACOES);
  const id = useId();
  const nota = transacao.nota ?? "";
  const [aEditar, setAEditar] = useState(false);
  const [texto, setTexto] = useState(nota);
  const [aGuardar, setAGuardar] = useState(false);
  const [erro, setErro] = useState("");
  const botaoRef = useRef<HTMLButtonElement>(null);

  // Ao fechar o campo, o foco volta ao botão (quem usa o teclado não se perde na página).
  function fechar() {
    setAEditar(false);
    setErro("");
    requestAnimationFrame(() => botaoRef.current?.focus());
  }

  function abrir() {
    setTexto(nota);
    setErro("");
    setAEditar(true);
  }

  async function guardar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setAGuardar(true);
    setErro("");
    try {
      // A API limpa os espaços; vazio passa a "sem nota".
      const atualizada = await pedirApi<Transacao>(`/transacoes/${transacao.id}`, { nota: texto }, "PATCH");
      onGuardada(atualizada);
      fechar();
    } catch (e) {
      if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      if (e instanceof SessaoExpirada) {
        onSessaoExpirada(e);
        return;
      }
      // 503 antes da sql/025: a API explica no texto dela.
      const daApi = e instanceof ErroApi && e.status === 503 && typeof e.detalhe === "string" ? e.detalhe : null;
      setErro(daApi ?? mensagemDaApi(e, T.erroNota));
    } finally {
      setAGuardar(false);
    }
  }

  function teclas(evento: KeyboardEvent<HTMLFormElement>) {
    if (evento.key === "Escape") {
      evento.preventDefault();
      fechar();
    }
  }

  if (aEditar) {
    return (
      <form onSubmit={guardar} onKeyDown={teclas} className="mt-2 space-y-1.5">
        <label htmlFor={`${id}-campo`} className="sr-only">
          {preencher(T.rotuloCampoNota, { descricao: transacao.descricao })}
        </label>
        <input
          id={`${id}-campo`}
          // Abre por um clique do utilizador: o foco vai logo para o campo.
          autoFocus
          maxLength={MAX_CARACTERES_NOTA}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          aria-describedby={`${id}-contador ${id}-ajuda`}
          className="w-full min-w-0 rounded-md border border-borda bg-cartao px-2.5 py-1.5 text-sm text-texto focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-destaque"
        />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-texto-suave">
            <span id={`${id}-contador`} className="tabular-nums">
              {preencher(T.contadorNota, { n: texto.length, maximo: MAX_CARACTERES_NOTA })}
            </span>
            <span id={`${id}-ajuda`} className="sr-only">
              {T.ajudaNota}
            </span>
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={fechar}
              className="min-h-9 rounded-md px-3 text-xs text-texto-suave hover:text-texto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
            >
              {T.cancelarNota}
            </button>
            <button
              type="submit"
              disabled={aGuardar}
              className="min-h-9 rounded-md bg-destaque px-3 text-xs font-medium text-white hover:bg-destaque-hover dark:text-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:opacity-50"
            >
              {aGuardar ? T.aGuardarNota : T.guardarNota}
            </button>
          </div>
        </div>
        {erro && (
          <p role="alert" className="text-xs text-red-700 dark:text-red-300">
            {erro}
          </p>
        )}
      </form>
    );
  }

  return (
    <div className="mt-0.5">
      {nota && (
        <p className="break-words text-xs text-texto-suave">
          <span className="sr-only">{T.prefixoNota} </span>
          {nota}
        </p>
      )}
      <button
        ref={botaoRef}
        type="button"
        onClick={abrir}
        disabled={desligado}
        aria-label={preencher(nota ? T.rotuloEditarNota : T.rotuloAdicionarNota, { descricao: transacao.descricao })}
        aria-describedby={desligado ? ID_NOTA_DEMO : undefined}
        className="mt-0.5 inline-flex min-h-11 items-center sm:min-h-6 rounded text-xs text-destaque underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:no-underline"
      >
        <span aria-hidden="true" className="mr-1">
          ✎
        </span>
        {nota ? T.editarNota : T.adicionarNota}
      </button>
    </div>
  );
}
