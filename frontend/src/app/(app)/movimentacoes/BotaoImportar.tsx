"use client";

import { useRef, useState } from "react";

import {
  eBloqueadoNaDemo,
  eLimiteDiario,
  eLimitePdf,
  enviarFicheiro,
  ErroApi,
  eSoPlanosPagos,
  SessaoExpirada,
  type ResultadoImportacao,
} from "@/lib/api";
import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import { TEXTOS_IMPORTAR } from "@/lib/textosMovimentacoes";
import { TEXTOS_PLANO_PAGO } from "@/lib/textosPlanos";

type Props = {
  onImportado: (resultado: ResultadoImportacao) => void;
  onErro: (mensagem: string, erros: string[]) => void;
  onSessaoExpirada: (e: unknown) => void;
  onLimiteDiario: () => void; // 429: a página mostra o AvisoLimite
  onLimitePdf: () => void; // 429 do limite de extratos PDF do mês: a página mostra o AvisoLimitePdf
  onSoPlanosPagos: (mensagem: string) => void; // 402 (PDF no Free): a página mostra o AvisoPlanoPago
  soCsv: boolean; // Free: a janela de escolha só mostra CSV (a API responde 402 ao PDF na mesma)
  desligado?: boolean; // demo (só leitura): o botão fica desligado
};

// Botão que abre a janela "Escolher ficheiro" e envia o CSV ou o PDF para POST /transacoes/importar.
export default function BotaoImportar({
  onImportado,
  onErro,
  onSessaoExpirada,
  onLimiteDiario,
  onLimitePdf,
  onSoPlanosPagos,
  soCsv,
  desligado = false,
}: Props) {
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
      if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      // Antes do eLimiteDiario: os dois são 429, mas o do PDF tem outro aviso (e o CSV continua a funcionar).
      if (eLimitePdf(e)) {
        onLimitePdf();
        return;
      }
      if (eLimiteDiario(e)) {
        onLimiteDiario();
        return;
      }
      if (eSoPlanosPagos(e)) {
        onSoPlanosPagos(typeof e.detalhe === "string" ? e.detalhe : TEXTOS_PLANO_PAGO.pdf);
        return;
      }
      // O "detail" do FastAPI chega em duas formas: um texto simples, ou o objeto
      // { mensagem, erros } quando o extrato tem linhas inválidas.
      if (e instanceof ErroApi && typeof e.detalhe === "string") {
        onErro(e.detalhe, []);
      } else if (e instanceof ErroApi && e.detalhe && typeof e.detalhe === "object") {
        const { erros } = e.detalhe as { erros: string[] };
        onErro(TEXTOS_IMPORTAR.linhasInvalidas, erros ?? []);
      } else {
        onErro(TEXTOS_IMPORTAR.semApi, []);
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
        accept={soCsv ? ".csv,text/csv" : ".csv,text/csv,.pdf,application/pdf"}
        className="hidden"
        onChange={(e) => {
          const ficheiro = e.target.files?.[0];
          if (ficheiro) importar(ficheiro);
        }}
      />
      <button
        type="button"
        disabled={aImportar || desligado}
        aria-describedby={desligado ? ID_NOTA_DEMO : undefined}
        onClick={() => entradaFicheiro.current?.click()}
        className="rounded-lg border border-borda bg-cartao px-4 py-2 text-sm font-medium text-texto hover:bg-fundo disabled:cursor-not-allowed disabled:opacity-50"
      >
        {aImportar ? TEXTOS_IMPORTAR.aImportar : TEXTOS_IMPORTAR.botao}
      </button>
    </>
  );
}
