"use client";

import Link from "next/link";

import { useEstadoPlano } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { TEXTOS_DEMO } from "@/lib/textosDemo";
import { TEXTOS_LIMITE } from "@/lib/textosPlanos";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// O aviso do 429 (limite de pedidos à IA), igual em todos os ecrãs que usam a IA.
// Usa o /plano (do ProvedorConta, no layout da app) para saber o limite, o período (dia ou mês) e o plano: no Completo não há plano maior,
// por isso não há link.
// Numa sessão de demo, o texto é o do limite da demo (por IP ou dos pedidos partilhados), sem link para mudar de plano.
// mensagem: o "detail" do 429 que a API mandou (na demo, mostra-se esse em vez do texto fixo).
export default function AvisoLimite({ mensagem }: { mensagem?: string }) {
  const demo = useSessaoDemo();
  const estado = useEstadoPlano(); // null: sem o número, mostra o aviso sem ele

  // Enquanto o /plano não chega (ou se falhar): "Já usaste os pedidos à IA do teu plano...", sem o número.
  // Sem o /plano não se sabe o período: fica o texto do dia, como antes (o dos planos pagos).
  const doMes = estado?.periodo === "mes";
  const modelo = doMes ? TEXTOS_LIMITE.textoMes : TEXTOS_LIMITE.texto;
  const texto = estado ? preencher(modelo, { limite: estado.limite }) : modelo.replace(" {limite}", "");
  const mostrarLink = estado?.plano !== "completo";

  if (demo) {
    return (
      <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm sm:p-4 dark:border-amber-800 dark:bg-amber-950/40">
        <p className="text-amber-900 dark:text-amber-200">{mensagem ?? TEXTOS_DEMO.limiteDemo}</p>
      </div>
    );
  }

  return (
    <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm sm:p-4 dark:border-amber-800 dark:bg-amber-950/40">
      <p className="font-medium text-amber-900 dark:text-amber-200">{doMes ? TEXTOS_LIMITE.tituloMes : TEXTOS_LIMITE.titulo}</p>
      <p className="mt-1 text-amber-900 dark:text-amber-200">{texto}</p>
      {mostrarLink && (
        <Link
          href="/plano"
          className="mt-1 inline-flex min-h-11 items-center rounded-md font-semibold text-amber-900 underline underline-offset-2 hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque dark:text-amber-200"
        >
          {TEXTOS_LIMITE.link}
        </Link>
      )}
    </div>
  );
}
