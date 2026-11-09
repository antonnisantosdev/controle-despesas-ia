"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { corDaBarra } from "@/app/(app)/CartaoPlano";
import BotaoPedirAcesso from "@/components/BotaoPedirAcesso";
import { apagarToken, emailDaSessao, pedirEstadoPlano, SessaoExpirada, type EstadoPlano } from "@/lib/api";
import {
  dataPorExtenso,
  deveAvisarRenovar,
  eIdPlano,
  NOMES_PLANOS,
  nomeDoPlano,
  planosSuperiores,
  preencher,
  temFuncoesPagas,
  textoDosPedidos,
} from "@/lib/planos";
import { useLimitesPlanos } from "@/lib/useLimitesPlanos";
import { TEXTOS_CARTOES, TEXTOS_EXPIRADA, TEXTOS_MEU_PLANO } from "@/lib/textosPlanos";

// "O meu plano": o plano atual, os pedidos à IA do período, até quando dura e como mudar ou renovar.
export default function PaginaPlano() {
  const router = useRouter();
  const [estado, setEstado] = useState<EstadoPlano | null>(null);
  const [emailConta, setEmailConta] = useState<string | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    pedirEstadoPlano()
      .then((resposta) => {
        setEstado(resposta);
        setEmailConta(emailDaSessao()); // vai na mensagem do pedido, para sabermos que conta ativar
      })
      .catch((e) => {
        if (e instanceof SessaoExpirada) {
          apagarToken();
          router.replace("/login");
        } else {
          setErro("Não foi possível carregar o teu plano. Confirma que a API está a correr.");
        }
      });
  }, [router]);

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-texto">{TEXTOS_MEU_PLANO.titulo}</h1>
        </header>

        {erro && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}
        {!estado && !erro && (
          <p role="status" className="rounded-xl border border-borda bg-cartao p-4 text-sm text-texto-suave sm:p-6">
            A carregar...
          </p>
        )}

        {estado && <DetalhesPlano estado={estado} emailConta={emailConta} />}

        <Link
          href="/precos"
          className="inline-flex min-h-11 items-center rounded-md text-sm font-semibold text-destaque-hover hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          {TEXTOS_EXPIRADA.botaoPlanos}
        </Link>
      </div>
    </main>
  );
}

function DetalhesPlano({ estado, emailConta }: { estado: EstadoPlano; emailConta: string | null }) {
  const nome = nomeDoPlano(estado.plano) ?? TEXTOS_MEU_PLANO.nomeSemPlano;
  const usadas = Math.min(estado.usadas, estado.limite);
  // O Free conta os pedidos por mês; os pagos, por dia.
  const doMes = estado.periodo === "mes";
  const plano = eIdPlano(estado.plano) ? estado.plano : null;
  const avisar = plano !== null && plano !== "free" && deveAvisarRenovar(estado.ativo_ate);
  const superiores = planosSuperiores(estado.plano);
  const limites = useLimitesPlanos();
  const percentagem = estado.limite > 0 ? (usadas / estado.limite) * 100 : 100;

  return (
    <>
      <section className="space-y-4 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-destaque-hover">{TEXTOS_MEU_PLANO.planoAtual}</p>
          <p className="text-3xl font-bold tracking-tight text-texto">{nome}</p>
        </div>
        {/* Os pedidos do período são o número mais importante do ecrã: texto forte e barra de progresso. */}
        <div className="space-y-2">
          <p id="pedidos-hoje" className="text-base font-semibold text-texto">
            {preencher(doMes ? TEXTOS_MEU_PLANO.pedidosMes : TEXTOS_MEU_PLANO.pedidosHoje, {
              usadas,
              limite: estado.limite,
            })}
          </p>
          <div
            className="h-2 overflow-hidden rounded-full bg-fundo"
            role="progressbar"
            aria-valuenow={usadas}
            aria-valuemin={0}
            aria-valuemax={estado.limite}
            aria-labelledby="pedidos-hoje"
          >
            <div className={`h-full rounded-full ${corDaBarra(usadas, estado.limite)}`} style={{ width: `${percentagem}%` }} />
          </div>
          <p className="text-sm text-texto-suave">{doMes ? TEXTOS_MEU_PLANO.reiniciaMes : TEXTOS_MEU_PLANO.reinicia}</p>
        </div>
        <div className="space-y-1 border-t border-borda pt-4 text-sm">
          <p className="text-texto">
            {estado.ativo_ate
              ? preencher(TEXTOS_MEU_PLANO.ativoAte, { data: dataPorExtenso(estado.ativo_ate) })
              : TEXTOS_MEU_PLANO.semDataFim}
          </p>
          <p className="text-texto-suave">
            {temFuncoesPagas(estado.plano) ? TEXTOS_MEU_PLANO.todasFuncionalidades : TEXTOS_MEU_PLANO.semFuncoesPagas}
          </p>
        </div>
      </section>

      {avisar && plano && estado.ativo_ate && (
        <section className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/40">
          <p className="text-sm text-amber-900 dark:text-amber-200">
            {preencher(TEXTOS_MEU_PLANO.avisoRenovar, { data: dataPorExtenso(estado.ativo_ate) })}
          </p>
          <div className="sm:max-w-xs">
            <BotaoPedirAcesso pedido={{ plano, renovar: true, emailConta }} rotulo={TEXTOS_MEU_PLANO.botaoRenovar} />
          </div>
        </section>
      )}

      {plano === "completo" ? (
        <p className="rounded-xl border border-borda bg-cartao p-4 text-sm text-texto sm:p-6">{TEXTOS_MEU_PLANO.completo}</p>
      ) : (
        superiores.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-texto">{TEXTOS_MEU_PLANO.botaoUpgrade}</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {superiores.map((id) => (
                <div key={id} className="flex flex-col gap-3 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
                  <div className="space-y-1">
                    <p className="text-lg font-semibold text-texto">{NOMES_PLANOS[id]}</p>
                    <p className="text-sm text-texto-suave">{TEXTOS_CARTOES[id].frase}</p>
                  </div>
                  <p className="text-sm font-semibold text-texto">{textoDosPedidos(limites[id])}</p>
                  {/* O que o plano traz além dos pedidos (PDF e talões, para quem vem do Free). */}
                  <ul className="space-y-1 text-sm text-texto-suave">
                    {TEXTOS_CARTOES[id].pontos.map((ponto) => (
                      <li key={ponto}>{ponto}</li>
                    ))}
                  </ul>
                  <div className="mt-auto pt-1">
                    <BotaoPedirAcesso pedido={{ plano: id, renovar: false, emailConta }} rotulo={TEXTOS_CARTOES[id].botao} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )
      )}
    </>
  );
}
