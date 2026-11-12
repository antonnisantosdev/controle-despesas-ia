"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { corDaBarra } from "@/app/(app)/CartaoPlano";
import BotaoPedirAcesso from "@/components/BotaoPedirAcesso";
import { apagarToken, emailDaSessao, type EstadoPlano } from "@/lib/api";
import { useEstadoPlano, useFormatos, usePedidoPlano } from "@/lib/conta";
import {
  dataPorExtenso,
  deveAvisarRenovar,
  eIdPlano,
  NOMES_PLANOS,
  nomeDoPlano,
  planosSuperiores,
  pontosDoCartao,
  preencher,
  temFuncoesPagas,
} from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_BOAS_VINDAS } from "@/lib/textosBoasVindas";
import { DICIONARIO_DEMO } from "@/lib/textosDemo";
import { DICIONARIO_PLANOS } from "@/lib/textosPlanos";
import { useLimitesPlanos } from "@/lib/useLimitesPlanos";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// "O meu plano": o plano atual, os pedidos à IA do período, até quando dura e como mudar ou renovar.
export default function PaginaPlano() {
  const { TEXTOS_DEMO } = useTextos(DICIONARIO_DEMO);
  const { TEXTOS_EXPIRADA, TEXTOS_MEU_PLANO } = useTextos(DICIONARIO_PLANOS);
  const { TEXTOS_DEFINICOES } = useTextos(DICIONARIO_BOAS_VINDAS);
  const router = useRouter();
  // O /plano do ProvedorConta (pedido a cada página nova): esta página já não faz o seu próprio pedido.
  const estado = useEstadoPlano();
  const { falhou, sessaoExpirada } = usePedidoPlano();
  const erro = falhou && !sessaoExpirada; // o texto escolhe-se ao desenhar, no país da conta
  // Vai na mensagem do pedido de acesso, para sabermos que conta ativar. Lido só no browser: os cartões
  // que o usam só aparecem depois de o /plano chegar, por isso não entra no HTML do servidor.
  const [emailConta] = useState<string | null>(() => (typeof window === "undefined" ? null : emailDaSessao()));
  // Na demo a conta é partilhada: mostra-se só que é uma conta de demonstração (sem contador, data nem pedidos de acesso).
  const demo = useSessaoDemo();
  // Contas do Brasil: sem ligação para /precos (página PT, em euros e com MB Way). Decisão do CEO, 2026-11-12.
  // O país vem da mesma resposta do /plano: o link só aparece depois de ela chegar (nunca pisca numa conta BR).
  const mostrarLinkPrecos = !demo && estado !== null && estado.pais !== "BR";

  useEffect(() => {
    if (!sessaoExpirada) return;
    apagarToken();
    router.replace("/login");
  }, [sessaoExpirada, router]);

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-texto">{TEXTOS_MEU_PLANO.titulo}</h1>
        </header>

        {erro && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{TEXTOS_MEU_PLANO.erroCarregar}</p>}
        {!estado && !erro && !demo && (
          <p role="status" className="rounded-xl border border-borda bg-cartao p-4 text-sm text-texto-suave sm:p-6">
            {TEXTOS_MEU_PLANO.aCarregar}
          </p>
        )}

        {/* Na demo: só "Conta de demonstração" e as 5 perguntas por dia (sem o contador partilhado nem a data). */}
        {demo && (
          <section className="space-y-2 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
            <p className="text-3xl font-bold tracking-tight text-texto">{TEXTOS_DEMO.planoDemoNome}</p>
            <p className="text-base font-semibold text-texto">{TEXTOS_DEMO.planoDemoChat}</p>
            <p className="text-sm text-texto-suave">{TEXTOS_DEMO.semMudarPlano}</p>
          </section>
        )}
        {estado && !demo && <DetalhesPlano estado={estado} emailConta={emailConta} />}

        {mostrarLinkPrecos && (
          <Link
            href="/precos"
            className="inline-flex min-h-11 items-center rounded-md text-sm font-semibold text-destaque-hover hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
          >
            {TEXTOS_EXPIRADA.botaoPlanos}
          </Link>
        )}

        {/* O perfil e o "Apagar conta" passaram para as Definições. */}
        <Link
          href="/definicoes"
          className="flex min-h-11 items-center justify-between gap-3 rounded-xl border border-borda bg-cartao p-4 text-sm font-semibold text-texto transition-colors hover:bg-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque sm:p-6"
        >
          <span>{TEXTOS_DEFINICOES.ligacaoPlano}</span>
          <span aria-hidden className="text-texto-suave">
            →
          </span>
        </Link>
      </div>
    </main>
  );
}

function DetalhesPlano({ estado, emailConta }: { estado: EstadoPlano; emailConta: string | null }) {
  const textosPlanos = useTextos(DICIONARIO_PLANOS);
  const { TEXTOS_CARTOES, TEXTOS_MEU_PLANO, TEXTOS_PRECOS } = textosPlanos;
  const f = useFormatos();
  // Brasil: os cartões dizem "Preço em breve" até haver PIX/cartão em R$ (valores em PRECOS_BR, lib/planos.ts).
  const brasil = estado.pais === "BR";
  const nome = nomeDoPlano(estado.plano) ?? TEXTOS_MEU_PLANO.nomeSemPlano;
  const usadas = Math.min(estado.usadas, estado.limite);
  // O Free conta os pedidos por mês; os pagos, por dia.
  const doMes = estado.periodo === "mes";
  const plano = eIdPlano(estado.plano) ? estado.plano : null;
  const avisar = plano !== null && plano !== "free" && deveAvisarRenovar(estado.ativo_ate);
  const superiores = planosSuperiores(estado.plano);
  const limites = useLimitesPlanos();
  const percentagem = estado.limite > 0 ? (usadas / estado.limite) * 100 : 100;
  // Um plano pago que chegou ao fim: a conta está no Free (a API já devolve plano "free").
  const terminado = eIdPlano(estado.plano_terminado) && estado.plano_terminado !== "free" ? estado.plano_terminado : null;

  return (
    <>
      {terminado && estado.terminou_em && (
        <section className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/40">
          <p className="text-sm text-amber-900 dark:text-amber-200">
            {preencher(TEXTOS_MEU_PLANO.avisoTerminou, {
              plano: NOMES_PLANOS[terminado],
              data: dataPorExtenso(estado.terminou_em, f),
            })}
          </p>
          <div className="sm:max-w-xs">
            <BotaoPedirAcesso pedido={{ plano: terminado, renovar: true, emailConta }} rotulo={TEXTOS_MEU_PLANO.botaoRenovar} />
          </div>
        </section>
      )}

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
        {/* Extratos PDF do mês: só nos planos que importam PDF (no Free o limite é 0). */}
        {estado.pdf_limite > 0 && (
          <div className="space-y-1 border-t border-borda pt-4 text-sm">
            <p className="font-medium text-texto">
              {preencher(TEXTOS_MEU_PLANO.pdfMes, {
                usados: Math.min(estado.pdf_usados, estado.pdf_limite),
                limite: estado.pdf_limite,
              })}
            </p>
            <p className="text-texto-suave">{TEXTOS_MEU_PLANO.pdfReinicia}</p>
          </div>
        )}
        <div className="space-y-1 border-t border-borda pt-4 text-sm">
          <p className="text-texto">
            {estado.ativo_ate
              ? preencher(TEXTOS_MEU_PLANO.ativoAte, { data: dataPorExtenso(estado.ativo_ate, f) })
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
            {preencher(TEXTOS_MEU_PLANO.avisoRenovar, { data: dataPorExtenso(estado.ativo_ate, f), plano: NOMES_PLANOS[plano] })}
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
              {superiores.map((id) => {
                // O primeiro ponto (os pedidos à IA) vai em destaque; os outros (PDF, talões...) por baixo.
                const [pedidos, ...outros] = pontosDoCartao(id, limites[id], textosPlanos);
                return (
                  <div key={id} className="flex flex-col gap-3 rounded-xl border border-borda bg-cartao p-4 sm:p-6">
                    <div className="space-y-1">
                      <p className="text-lg font-semibold text-texto">{NOMES_PLANOS[id]}</p>
                      <p className="text-sm text-texto-suave">{TEXTOS_CARTOES[id].frase}</p>
                    </div>
                    {brasil && <p className="text-sm font-semibold text-destaque-hover">{TEXTOS_PRECOS.precoPorDefinir}</p>}
                    <p className="text-sm font-semibold text-texto">{pedidos}</p>
                    {/* O que o plano traz além dos pedidos (PDF e talões, para quem vem do Free). */}
                    <ul className="space-y-1 text-sm text-texto-suave">
                      {outros.map((ponto) => (
                        <li key={ponto}>{ponto}</li>
                      ))}
                    </ul>
                    <div className="mt-auto pt-1">
                      <BotaoPedirAcesso pedido={{ plano: id, renovar: false, emailConta }} rotulo={TEXTOS_CARTOES[id].botao} />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )
      )}
    </>
  );
}
