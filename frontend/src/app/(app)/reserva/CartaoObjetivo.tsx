"use client";

import { useState, type FormEvent } from "react";

import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import AvisoLimite from "@/components/AvisoLimite";
import { eBloqueadoNaDemo, eLimiteDiario, ErroApi, pedirApi, SessaoExpirada, type Objetivo, type PlanoPoupanca } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import type { Formatos } from "@/lib/formatos";
import { preencher } from "@/lib/planos";
import { useOpcoes, useTextos } from "@/lib/textos";
import { DICIONARIO_RESERVA } from "@/lib/textosReserva";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// Quanto do objetivo já foi poupado, de 0 a 100. É este número que define a largura da barra.
function percentagemPoupada(valorPoupado: number, valorAlvo: number): number {
  if (valorAlvo > 0) return Math.min(Math.round((valorPoupado / valorAlvo) * 100), 100);

  return 0;
}

// "2027-07-01" -> "julho de 2027" (f: os formatos da conta, useFormatos())
function mesDoPrazo(data: string, f: Formatos) {
  return f.data(data, { month: "long", year: "numeric" });
}

type Props = {
  objetivo: Objetivo;
  onMudou: (objetivo: Objetivo) => void;
  onApagado: (id: number) => void;
  onSessaoExpirada: (e: unknown) => void;
};

export default function CartaoObjetivo({ objetivo, onMudou, onApagado, onSessaoExpirada }: Props) {
  const { TEXTOS_OBJETIVO } = useTextos(DICIONARIO_RESERVA);
  const { rotuloCategoria } = useOpcoes();
  const [aJuntar, setAJuntar] = useState(false); // o campo "+ Juntei dinheiro" está aberto
  const [valor, setValor] = useState("");
  const [plano, setPlano] = useState<PlanoPoupanca | null>(null);
  const [aPlanear, setAPlanear] = useState(false);
  const [aConfirmar, setAConfirmar] = useState(false); // a pergunta "Apagar?" está visível
  const [erro, setErro] = useState("");
  const [semPedidos, setSemPedidos] = useState(false); // 429: chegou ao limite de pedidos à IA
  // Na demo (só leitura): juntar, apagar e o plano da IA ficam desligados; a API recusa-os na mesma (423).
  const demo = useSessaoDemo();
  const f = useFormatos();
  const descricaoDemo = demo ? ID_NOTA_DEMO : undefined; // aponta para a explicação (NotaDemo)

  const percentagem = percentagemPoupada(objetivo.valor_poupado, objetivo.valor_alvo);

  function tratarErro(e: unknown, mensagem: string) {
    if (e instanceof SessaoExpirada) onSessaoExpirada(e);
    else if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
    else if (eLimiteDiario(e)) setSemPedidos(true);
    // 503 (IA em baixo) traz uma explicação da API.
    else if (e instanceof ErroApi && typeof e.detalhe === "string") setErro(e.detalhe);
    else setErro(mensagem);
  }

  async function juntar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const numero = Number(valor.replace(",", "."));
    if (!(numero > 0)) {
      setErro(TEXTOS_OBJETIVO.erroValor);
      return;
    }

    setErro("");
    try {
      // A API guarda o total, por isso soma-se aqui. O arredondamento evita totais como 10,100000001.
      const total = Math.round((objetivo.valor_poupado + numero) * 100) / 100;
      onMudou(await pedirApi<Objetivo>(`/objetivos/${objetivo.id}`, { valor_poupado: total }, "PATCH"));
      setValor("");
      setAJuntar(false);
      setPlano(null); // o plano antigo já não conta com este dinheiro
    } catch (e) {
      tratarErro(e, TEXTOS_OBJETIVO.erroAtualizar);
    }
  }

  async function pedirPlano() {
    setAPlanear(true);
    setErro("");
    setSemPedidos(false);
    try {
      setPlano(await pedirApi<PlanoPoupanca>(`/objetivos/${objetivo.id}/plano`, {}));
    } catch (e) {
      tratarErro(e, TEXTOS_OBJETIVO.erroPlano);
    } finally {
      setAPlanear(false);
    }
  }

  async function apagar() {
    setErro("");
    try {
      await pedirApi<void>(`/objetivos/${objetivo.id}`, undefined, "DELETE");
      onApagado(objetivo.id);
    } catch (e) {
      setAConfirmar(false);
      tratarErro(e, TEXTOS_OBJETIVO.erroApagar);
    }
  }

  const estiloBotao =
    "rounded-md border border-borda px-3 py-1.5 text-sm text-texto hover:bg-fundo disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <article className="space-y-3 rounded-xl border border-borda bg-cartao p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="font-medium text-texto">{objetivo.nome}</h2>
          <p className="text-xs text-texto-suave">{preencher(TEXTOS_OBJETIVO.ate, { mes: mesDoPrazo(objetivo.data_alvo, f) })}</p>
        </div>
        <p className="text-sm text-texto-suave">
          <span className="font-semibold text-texto">{f.dinheiro(objetivo.valor_poupado)}</span>
          {preencher(TEXTOS_OBJETIVO.de, { alvo: f.dinheiro(objetivo.valor_alvo) })}
        </p>
      </div>

      <div
        role="progressbar"
        aria-label={preencher(TEXTOS_OBJETIVO.rotuloProgresso, { nome: objetivo.nome })}
        aria-valuenow={percentagem}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 overflow-hidden rounded-full bg-fundo"
      >
        {/* A largura muda com os dados, por isso vem em style e não numa classe do Tailwind. */}
        <div className="h-full rounded-full bg-destaque" style={{ width: `${percentagem}%` }} />
      </div>
      <p className="text-xs text-texto-suave">{preencher(TEXTOS_OBJETIVO.percentagem, { percentagem })}</p>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => setAJuntar(!aJuntar)} disabled={demo} aria-describedby={descricaoDemo} className={estiloBotao}>
          {TEXTOS_OBJETIVO.juntei}
        </button>
        <button type="button" onClick={pedirPlano} disabled={aPlanear || demo} aria-describedby={descricaoDemo} className={estiloBotao}>
          {aPlanear ? TEXTOS_OBJETIVO.aPlanear : TEXTOS_OBJETIVO.planoPoupanca}
        </button>
        {aConfirmar ? (
          <span className="ml-auto flex items-center gap-2 text-sm text-texto-suave">
            {TEXTOS_OBJETIVO.apagarPergunta}
            <button type="button" onClick={apagar} className="font-medium text-red-600 dark:text-red-400">
              {TEXTOS_OBJETIVO.sim}
            </button>
            <button type="button" onClick={() => setAConfirmar(false)} className="hover:text-texto">
              {TEXTOS_OBJETIVO.nao}
            </button>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setAConfirmar(true)}
            disabled={demo}
            aria-describedby={descricaoDemo}
            className="ml-auto text-sm text-texto-suave hover:text-texto disabled:cursor-not-allowed disabled:opacity-50"
          >
            {TEXTOS_OBJETIVO.apagar}
          </button>
        )}
      </div>

      {aJuntar && !demo && (
        <form onSubmit={juntar} className="flex flex-wrap items-center gap-2">
          <input
            required
            autoFocus
            inputMode="decimal"
            aria-label={preencher(TEXTOS_OBJETIVO.rotuloValor, { moeda: f.nomeMoeda })}
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder={preencher(TEXTOS_OBJETIVO.marcadorValor, { zero: f.comSimbolo("0,00") })}
            className="w-32 rounded-md border border-borda bg-cartao px-3 py-1.5 text-sm text-texto"
          />
          <button
            type="submit"
            className="rounded-md bg-destaque px-4 py-1.5 text-sm font-medium text-white hover:bg-destaque-hover"
          >
            {TEXTOS_OBJETIVO.adicionar}
          </button>
        </form>
      )}

      {erro && <p className="text-sm text-red-600 dark:text-red-400">{erro}</p>}
      {semPedidos && <AvisoLimite />}

      {plano && (
        <div className="space-y-2 rounded-lg bg-fundo p-3 text-sm">
          <p className={`font-medium ${plano.viavel ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400"}`}>
            {plano.viavel ? TEXTOS_OBJETIVO.viavel : TEXTOS_OBJETIVO.inviavel}
          </p>
          <p className="text-texto">{plano.explicacao}</p>
          {plano.cortes.length > 0 && (
            <ul className="space-y-1 border-t border-borda pt-2">
              {plano.cortes.map((corte) => (
                <li key={corte.categoria} className="text-texto-suave">
                  <span className="font-medium capitalize text-texto">{rotuloCategoria(corte.categoria)}</span>
                  {preencher(TEXTOS_OBJETIVO.corte, { valor: f.dinheiro(corte.valor_mensal) })}
                  {corte.motivo}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </article>
  );
}
