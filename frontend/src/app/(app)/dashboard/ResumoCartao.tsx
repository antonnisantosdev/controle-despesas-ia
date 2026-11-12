"use client";

import { useEffect, useState } from "react";

import { ErroApi, eSessaoDemo, pedirApi, type ResumoMes } from "@/lib/api";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_DASHBOARD } from "@/lib/textosDashboard";
import { DICIONARIO_DEMO } from "@/lib/textosDemo";

// O resultado guarda o mês a que pertence: se o mês escolhido mudou, o que está guardado
// já não serve e a página mostra "a carregar" até chegar o novo.
// erro: o texto da API (limite da demo) ou o tipo de erro; o texto nosso escolhe-se ao desenhar, no país da conta.
type ErroResumo = { texto: string } | "limiteDemo" | "geral";
type Resultado = { mes: string; resumo?: ResumoMes; erro?: ErroResumo };

// "mes" chega de fora (da página do dashboard), como um atributo de um shortcode.
export default function ResumoCartao({ mes }: { mes: string }) {
  const { TEXTOS_RESUMO_MES } = useTextos(DICIONARIO_DASHBOARD);
  const { TEXTOS_DEMO } = useTextos(DICIONARIO_DEMO);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const aCarregar = resultado?.mes !== mes;
  const resumo = aCarregar ? undefined : resultado?.resumo;
  const erro = resultado?.erro;
  const textoDoErro =
    erro === undefined ? null : erro === "geral" ? TEXTOS_RESUMO_MES.erro : erro === "limiteDemo" ? TEXTOS_DEMO.limiteResumo : erro.texto;

  useEffect(() => {
    if (!mes) return;
    // Se o utilizador mudar de mês antes de a IA responder, a resposta antiga é ignorada.
    let cancelado = false;
    pedirApi<ResumoMes>(`/resumo?mes=${mes}`)
      .then((dados) => {
        if (!cancelado) setResultado({ mes, resumo: dados });
      })
      .catch((e) => {
        // Na demo, o resumo tem um limite por hora (429): diz-se porquê, em vez do erro genérico.
        const limiteDemo = e instanceof ErroApi && e.status === 429 && eSessaoDemo();
        const textoDaApi = limiteDemo && typeof e.detalhe === "string" ? e.detalhe : null;
        const erro: ErroResumo = limiteDemo ? (textoDaApi ? { texto: textoDaApi } : "limiteDemo") : "geral";
        if (!cancelado) setResultado({ mes, erro });
      });
    return () => {
      cancelado = true;
    };
  }, [mes]);

  return (
    <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <h2 className="mb-3 font-medium text-texto">{TEXTOS_RESUMO_MES.titulo}</h2>

      {aCarregar && <p className="text-sm text-texto-suave">{TEXTOS_RESUMO_MES.aCarregar}</p>}
      {!aCarregar && textoDoErro && <p className="text-sm text-red-600 dark:text-red-400">{textoDoErro}</p>}

      {resumo && (
        <>
          <p className="text-sm leading-relaxed text-texto">{resumo.resumo}</p>

          {resumo.alertas.length > 0 && (
            <ul className="mt-4 space-y-2">
              {resumo.alertas.map((alerta, i) => (
                <li
                  key={i}
                  className={
                    alerta.nivel === "atencao"
                      ? "rounded-md bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
                      : "rounded-md bg-blue-50 p-3 text-sm text-blue-900 dark:bg-blue-950/40 dark:text-blue-200"
                  }
                >
                  <strong>{alerta.nivel === "atencao" ? TEXTOS_RESUMO_MES.atencao : TEXTOS_RESUMO_MES.nota}</strong>
                  {alerta.mensagem}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
