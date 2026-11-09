"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AvisoServidor from "@/components/AvisoServidor";
import BotaoPedirAcesso from "@/components/BotaoPedirAcesso";
import Logo from "@/components/Logo";
import { emailDaSessao, sessaoPublica, type EstadoPlano } from "@/lib/api";
import {
  CONTACTOS,
  formatarEuros,
  ORDEM_PLANOS,
  pontosDoCartao,
  PRECOS,
  preencher,
  type IdPlano,
  type LimitePlano,
} from "@/lib/planos";
import { TEXTOS_CARTOES, TEXTOS_MEU_PLANO, TEXTOS_PRECOS } from "@/lib/textosPlanos";
import { useLimitesPlanos } from "@/lib/useLimitesPlanos";

// Foco visível ao navegar com o teclado.
const FOCO = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";
// Para linhas dentro de um contentor com overflow-hidden: o contorno fica para dentro, para não ser cortado.
const FOCO_DENTRO = "focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-destaque";

// O que a página sabe de quem a está a ver, segundo a resposta de GET /plano (sessaoPublica, api.ts).
// temConta: o login é válido (esconde o "Criar conta grátis"). podeAbrirApp: o /dashboard não volta a bloquear.
type Sessao = { temConta: boolean; podeAbrirApp: boolean; estado: EstadoPlano | null; emailConta: string | null };

const SEM_SESSAO: Sessao = { temConta: false, podeAbrirApp: false, estado: null, emailConta: null };

// Sem nenhum contacto configurado, a nota que manda carregar em "Pedir acesso" não faz sentido
// (o botão já diz "Contacto ainda não disponível.").
const HA_CONTACTO = Boolean(CONTACTOS.whatsapp || CONTACTOS.email);

async function lerSessao(): Promise<Sessao> {
  const resultado = await sessaoPublica();
  switch (resultado.tipo) {
    case "sem-sessao": // sem token ou 401 (token inválido/expirado): como quem não entrou
      return SEM_SESSAO;
    case "ativa":
      return { temConta: true, podeAbrirApp: true, estado: resultado.estado, emailConta: emailDaSessao() };
    case "plano-terminado":
      // 403: "Abrir a app" voltava a bloquear (ciclo). Fica o "Entrar" e o pedido normal com o email da conta.
      return { temConta: true, podeAbrirApp: false, estado: null, emailConta: emailDaSessao() };
    case "desconhecida":
      // A API falhou: não se sabe o estado. A app trata disso ao abrir.
      return { temConta: true, podeAbrirApp: true, estado: null, emailConta: emailDaSessao() };
  }
}

// O preço do cartão: mensal em grande, com o anual por baixo. Free: "Grátis". Pago sem preço: "Preço em breve".
function PrecoDoCartao({ id }: { id: IdPlano }) {
  const preco = id === "free" ? null : PRECOS[id];
  if (preco === null) {
    const texto = id === "free" ? TEXTOS_PRECOS.precoFree : TEXTOS_PRECOS.precoPorDefinir;
    return <p className="text-3xl font-bold tracking-tight text-texto">{texto}</p>;
  }
  return (
    <div className="space-y-1">
      <p className="text-texto">
        <span className="text-3xl font-bold tracking-tight">{formatarEuros(preco.mensal)}</span>
        <span className="text-sm text-texto-suave">{TEXTOS_PRECOS.porMes}</span>
      </p>
      <p className="text-sm text-texto-suave">{preencher(TEXTOS_PRECOS.precoAnual, { anual: formatarEuros(preco.anual) })}</p>
    </div>
  );
}

// Página pública de preços: fica fora do grupo (app), por isso não tem menu nem precisa de login.
export default function PaginaPrecos() {
  const limites = useLimitesPlanos();
  const [sessao, setSessao] = useState<Sessao>(SEM_SESSAO);

  // Com sessão, marca o plano atual e põe o email da conta na mensagem do pedido.
  // Um plano terminado (403) não manda para outra página: quem vem do "O teu plano terminou" fica aqui.
  useEffect(() => {
    lerSessao().then(setSessao);
  }, []);

  const planoAtual = sessao.estado?.plano ?? null;
  const destinoTopo = sessao.podeAbrirApp ? "/dashboard" : "/login";

  return (
    <main className="flex-1 bg-fundo">
      <header className="mx-auto flex max-w-5xl items-center justify-between p-4">
        <Link href={destinoTopo} aria-label="Control Prices" className={`rounded-md ${FOCO}`}>
          <Logo altura={36} />
        </Link>
        <Link
          href={destinoTopo}
          className={`inline-flex min-h-11 items-center rounded-md border border-borda bg-cartao px-4 text-sm font-medium text-texto hover:border-destaque ${FOCO}`}
        >
          {sessao.podeAbrirApp ? "Abrir a app" : "Entrar"}
        </Link>
      </header>

      <div className="mx-auto max-w-5xl space-y-10 px-4 pb-12 pt-4 sm:space-y-12 sm:pt-8">
        <section className="space-y-3 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-texto sm:text-4xl">{TEXTOS_PRECOS.titulo}</h1>
          <p className="mx-auto max-w-2xl text-sm text-texto-suave sm:text-base">{TEXTOS_PRECOS.subtitulo}</p>
        </section>

        {/* Empilhados no telemóvel, lado a lado a partir do ecrã médio. */}
        <section className="grid items-stretch gap-4 md:grid-cols-3">
          {ORDEM_PLANOS.map((id) => (
            <CartaoDePreco
              key={id}
              id={id}
              limite={limites[id]}
              atual={planoAtual === id}
              temConta={sessao.temConta}
              emailConta={sessao.emailConta}
            />
          ))}
        </section>

        <p className="-mt-6 text-center text-sm text-texto-suave sm:-mt-8">{TEXTOS_PRECOS.notaLancamento}</p>

        {HA_CONTACTO && (
          <p className="mx-auto max-w-2xl rounded-xl border border-borda bg-cartao p-4 text-center text-sm text-texto-suave">
            {TEXTOS_PRECOS.notaPagamento}
          </p>
        )}

        <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
          <h2 className="mb-4 text-lg font-semibold text-texto">{TEXTOS_PRECOS.funcionalidadesTitulo}</h2>
          <ul className="grid gap-x-6 gap-y-3 text-sm text-texto sm:grid-cols-2">
            {TEXTOS_PRECOS.funcionalidades.map((item) => (
              <li key={item} className="flex gap-2">
                <Visto />
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-texto">{TEXTOS_PRECOS.faqTitulo}</h2>
          <div className="divide-y divide-borda overflow-hidden rounded-xl border border-borda bg-cartao">
            {TEXTOS_PRECOS.faq.map(({ pergunta, resposta }) => (
              <details key={pergunta} className="group">
                {/* O padding fica no summary: a linha toda é o alvo de toque e o foco envolve-a. */}
                <summary
                  className={`flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 p-4 text-sm font-medium text-texto hover:bg-fundo [&::-webkit-details-marker]:hidden ${FOCO_DENTRO}`}
                >
                  {pergunta}
                  <span
                    aria-hidden
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-borda text-base leading-none text-texto-suave transition-transform group-open:rotate-45"
                  >
                    +
                  </span>
                </summary>
                <p className="px-4 pb-4 text-sm leading-relaxed text-texto-suave">{resposta}</p>
              </details>
            ))}
          </div>
        </section>
      </div>
      <AvisoServidor />
    </main>
  );
}

type PropsCartao = {
  id: IdPlano;
  limite: LimitePlano; // pedidos à IA e período (o Free conta por mês), e extratos PDF por mês
  atual: boolean; // é o plano de quem tem sessão
  temConta: boolean; // login válido (mesmo com o plano terminado)
  emailConta: string | null;
};

function CartaoDePreco({ id, limite, atual, temConta, emailConta }: PropsCartao) {
  const textos = TEXTOS_CARTOES[id];
  // Pedidos à IA, "Até 15 extratos PDF por mês" (só nos pagos) e os outros pontos do cartão.
  const pontos = pontosDoCartao(id, limite);

  // A partir do ecrã médio, cada cartão ocupa 4 linhas da grelha da secção (subgrid): nome e frase, preço,
  // pontos e botão. As linhas são partilhadas pelos três cartões, por isso o preço fica à mesma altura
  // mesmo quando uma frase tem mais linhas do que as outras.
  return (
    <article
      className={`flex flex-col gap-5 rounded-xl border bg-cartao p-5 sm:p-6 md:row-span-4 md:grid md:grid-rows-subgrid ${atual ? "border-destaque shadow-sm ring-2 ring-destaque" : "border-borda"}`}
    >
      <div className="space-y-1">
        <div className="flex min-h-7 flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-texto">{textos.nome}</h2>
          {atual && (
            <span className="rounded-full bg-destaque px-2.5 py-1 text-xs font-semibold text-white dark:text-fundo">
              {TEXTOS_MEU_PLANO.planoAtual}
            </span>
          )}
        </div>
        <p className="text-sm text-texto-suave">{textos.frase}</p>
      </div>

      {/* O preço é o que mais salta à vista no cartão. */}
      <div className="border-y border-borda py-4">
        <PrecoDoCartao id={id} />
      </div>

      <ul className="space-y-2.5 text-sm text-texto">
        {pontos.map((ponto) => (
          <li key={ponto} className="flex gap-2">
            <Visto />
            {ponto}
          </li>
        ))}
      </ul>

      {/* md:mt-0: na grelha, o mt-auto empurrava o botão do Free para o fundo da linha (os pagos têm mais
          uma linha por baixo do botão), e ficava mais abaixo do que os "Pedir acesso". */}
      <div className="mt-auto pt-2 md:mt-0">
        <BotaoDoCartao id={id} atual={atual} temConta={temConta} emailConta={emailConta} />
      </div>
    </article>
  );
}

// Free: criar conta (só sem sessão: quem já entrou tem conta). Pagos: pedir acesso, ou renovar se já é o plano atual.
function BotaoDoCartao({ id, atual, temConta, emailConta }: Omit<PropsCartao, "limite">) {
  if (id === "free") {
    if (temConta) return null;
    return (
      <Link
        href="/registo"
        className={`flex min-h-11 w-full items-center justify-center rounded-md bg-destaque px-4 py-2 text-center text-sm font-semibold text-white transition-colors hover:bg-destaque-hover dark:text-fundo ${FOCO}`}
      >
        {TEXTOS_CARTOES.free.botao}
      </Link>
    );
  }
  return (
    <BotaoPedirAcesso
      pedido={{ plano: id, renovar: atual, emailConta }}
      rotulo={atual ? TEXTOS_MEU_PLANO.botaoRenovar : TEXTOS_CARTOES[id].botao}
    />
  );
}

function Visto() {
  return (
    <svg viewBox="0 0 24 24" className="mt-0.5 h-4 w-4 shrink-0 text-destaque" fill="none" stroke="currentColor" strokeWidth={2.5} aria-hidden>
      <path d="M5 12l5 5L20 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
