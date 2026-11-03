"use client";

import { useRef, useState } from "react";

import { enviarFicheiro, ErroApi, SessaoExpirada, type ResultadoImportacao } from "@/lib/api";

type Props = {
  onImportado: (resultado: ResultadoImportacao) => void;
  onErro: (mensagem: string, erros: string[]) => void;
  onSessaoExpirada: (e: unknown) => void;
};

// Botão que abre a janela "Escolher ficheiro" e envia o CSV para POST /transacoes/importar.
export default function BotaoImportar({ onImportado, onErro, onSessaoExpirada }: Props) {
  // useRef: uma ligação direta ao <input type="file"> escondido, para o "clicar" a partir do botão.
  const entradaFicheiro = useRef<HTMLInputElement>(null);
  const [aImportar, setAImportar] = useState(false);

  async function importar(ficheiro: File) {
    setAImportar(true);
    try {
      const resultado = await enviarFicheiro<ResultadoImportacao>("/transacoes/importar", "ficheiro", ficheiro);
      onImportado(resultado);
    } catch (e) {
      if (e instanceof SessaoExpirada) {
        onSessaoExpirada(e);
        return;
      }
      // O "detail" do FastAPI chega em duas formas: um texto simples, ou o objeto
      // { mensagem, erros } quando o extrato tem linhas inválidas.
      if (e instanceof ErroApi && typeof e.detalhe === "string") {
        onErro(e.detalhe, []);
      } else if (e instanceof ErroApi && e.detalhe && typeof e.detalhe === "object") {
        const { erros } = e.detalhe as { erros: string[] };
        onErro("O extrato tem linhas inválidas. Corrige-as e volta a importar.", erros ?? []);
      } else {
        onErro("Não foi possível ligar à API. Confirma que o fastapi dev está a correr.", []);
      }
    } finally {
      setAImportar(false);
      // Limpa a escolha, para o mesmo ficheiro poder ser enviado outra vez (depois de corrigido).
      if (entradaFicheiro.current) entradaFicheiro.current.value = "";
    }
  }

  return (
    <>
      <input
        ref={entradaFicheiro}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={(e) => {
          const ficheiro = e.target.files?.[0];
          if (ficheiro) importar(ficheiro);
        }}
      />
      <button
        type="button"
        disabled={aImportar}
        onClick={() => entradaFicheiro.current?.click()}
        className="rounded-lg border border-borda bg-cartao px-4 py-2 text-sm font-medium text-texto hover:bg-fundo disabled:opacity-50"
      >
        {aImportar ? "A importar e a categorizar..." : "Importar extrato"}
      </button>
    </>
  );
}
