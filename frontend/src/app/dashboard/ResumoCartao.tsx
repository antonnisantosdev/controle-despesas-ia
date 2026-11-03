"use client";

import { useEffect, useState } from "react";

import { pedirApi, type ResumoMes } from "@/lib/api";

// O resultado guarda o mês a que pertence: se o mês escolhido mudou, o que está guardado
// já não serve e a página mostra "a carregar" até chegar o novo.
type Resultado = { mes: string; resumo?: ResumoMes; erro?: string };

// "mes" chega de fora (da página do dashboard), como um atributo de um shortcode.
export default function ResumoCartao({ mes }: { mes: string }) {
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const aCarregar = resultado?.mes !== mes;
  const resumo = aCarregar ? undefined : resultado?.resumo;

  useEffect(() => {
    if (!mes) return;
    // Se o utilizador mudar de mês antes de a IA responder, a resposta antiga é ignorada.
    let cancelado = false;
    pedirApi<ResumoMes>(`/resumo?mes=${mes}`)
      .then((dados) => {
        if (!cancelado) setResultado({ mes, resumo: dados });
      })
      .catch(() => {
        if (!cancelado) setResultado({ mes, erro: "O resumo não está disponível. Tenta mais tarde." });
      });
    return () => {
      cancelado = true;
    };
  }, [mes]);

  return (
    <section className="rounded-xl bg-white p-4 shadow sm:p-6">
      <h2 className="mb-3 font-medium text-gray-900">Resumo do mês</h2>

      {aCarregar && <p className="text-sm text-gray-500">A IA está a analisar o mês...</p>}
      {!aCarregar && resultado?.erro && <p className="text-sm text-red-600">{resultado.erro}</p>}

      {resumo && (
        <>
          <p className="text-sm leading-relaxed text-gray-800">{resumo.resumo}</p>

          {resumo.alertas.length > 0 && (
            <ul className="mt-4 space-y-2">
              {resumo.alertas.map((alerta, i) => (
                <li
                  key={i}
                  className={
                    alerta.nivel === "atencao"
                      ? "rounded-md bg-amber-50 p-3 text-sm text-amber-900"
                      : "rounded-md bg-blue-50 p-3 text-sm text-blue-900"
                  }
                >
                  <strong>{alerta.nivel === "atencao" ? "⚠ Atenção: " : "ℹ Nota: "}</strong>
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
