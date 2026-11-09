"use client";

import { useEffect, useState } from "react";

import { pedirApi, type AlertasOrcamento as RespostaAlertas } from "@/lib/api";
import { preencher } from "@/lib/planos";
import { TEXTOS_ALERTA_ORCAMENTO } from "@/lib/textosPlanos";

// Os valores em euros, à portuguesa: 1234.5 -> "1234,50 €".
function euros(valor: number): string {
  return valor.toLocaleString("pt-PT", { style: "currency", currency: "EUR" });
}

// Uma frase por categoria: "perto" (>= 90%) ou "atingido" (>= 100%). A regra dos 90% está na API (orcamento.py).
export function textoDoAlerta(alerta: RespostaAlertas["alertas"][number]): string {
  const modelo = alerta.nivel === "atingido" ? TEXTOS_ALERTA_ORCAMENTO.atingido : TEXTOS_ALERTA_ORCAMENTO.perto;
  // A categoria vem em minúsculas da base de dados ("restaurantes"): começa com maiúscula no início da frase.
  const categoria = alerta.categoria.charAt(0).toUpperCase() + alerta.categoria.slice(1);
  return preencher(modelo, { categoria, gasto: euros(alerta.gasto), orcamento: euros(alerta.limite) });
}

// Alertas de orçamento do mês atual (GET /orcamentos/alertas, não gasta pedidos à IA).
// mes: o mês escolhido na página. Só aparecem quando é o mês atual de Lisboa (a API diz qual é).
// versao: muda quando um orçamento é guardado, para os alertas acompanharem.
export default function AlertasOrcamento({ mes, versao = 0 }: { mes: string; versao?: number }) {
  const [resposta, setResposta] = useState<RespostaAlertas | null>(null);

  useEffect(() => {
    let cancelado = false;
    pedirApi<RespostaAlertas>("/orcamentos/alertas")
      .then((dados) => {
        if (!cancelado) setResposta(dados);
      })
      .catch(() => {
        // Sem alertas não se perde nada: a página trata da sessão e dos outros erros.
        if (!cancelado) setResposta(null);
      });
    return () => {
      cancelado = true;
    };
  }, [versao]);

  if (!resposta || resposta.mes !== mes || resposta.alertas.length === 0) return null;

  return (
    <section
      aria-label="Alertas de orçamento"
      className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm sm:p-4 dark:border-amber-800 dark:bg-amber-950/40"
    >
      <ul className="space-y-1.5">
        {resposta.alertas.map((alerta) => (
          <li
            key={alerta.categoria}
            className={alerta.nivel === "atingido" ? "font-medium text-red-700 dark:text-red-300" : "text-amber-900 dark:text-amber-200"}
          >
            {textoDoAlerta(alerta)}
          </li>
        ))}
      </ul>
    </section>
  );
}
