"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import AvisoPlanoPago from "@/components/AvisoPlanoPago";
import {
  apagarToken,
  ErroApi,
  eSoPlanosPagos,
  mensagemDaApi,
  pedirApi,
  SessaoExpirada,
  type EstadoListas,
  type ListaCompras,
} from "@/lib/api";
import { useEstadoPlano, useFormatos, usePedidoPlano } from "@/lib/conta";
import { preencher, temFuncoesPagas } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_FAZER_COMPRAS } from "@/lib/textosFazerCompras";
import { DICIONARIO_PLANOS } from "@/lib/textosPlanos";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

import ResultadoPlano from "./ResultadoPlano";

// Limites do formulário: os mesmos que a API valida (POST /compras/lista).
const ORCAMENTO_MAXIMO = 10000;
const MAX_MERCADOS = 3;
const LISTA_MINIMO = 3;
const LISTA_MAXIMO = 600;

const FOCO = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";
// text-base no telemóvel: com menos de 16 px, o iPhone faz zoom ao tocar no campo.
const ESTILO_CAMPO = "w-full rounded-md border border-borda bg-cartao px-3 py-2 text-base text-texto sm:text-sm";
const ESTILO_ERRO = "mt-1 text-sm text-red-700 dark:text-red-300";
const ESTILO_LINK_AVISO =
  "mt-1 inline-flex min-h-11 items-center rounded-md font-semibold text-amber-900 underline underline-offset-2 hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque dark:text-amber-200";

// "100", "100,50" ou "100.50" (até 2 casas decimais) -> número.
// Também "1.000" e "1.000,50" (ponto de milhares, como se escreve em PT-PT e PT-BR) -> 1000 e 1000,5.
// Outro texto -> null.
function lerOrcamento(texto: string): number | null {
  const limpo = texto.trim().replace(/\s/g, "");
  if (/^\d{1,3}(\.\d{3})+(,\d{1,2})?$/.test(limpo)) return Number(limpo.replace(/\./g, "").replace(",", "."));
  if (!/^\d+([.,]\d{1,2})?$/.test(limpo)) return null;
  return Number(limpo.replace(",", "."));
}

// Para onde vai o foco depois de um erro da API (n muda a cada erro, para o efeito correr outra vez).
type FocoErro = { alvo: "envio" | "limite" | "pago"; n: number };

type ErrosCampos = { orcamento?: string; mercados?: string; lista?: string };

export default function PaginaFazerCompras() {
  const { TEXTOS_FAZER_COMPRAS: T, TEXTOS_RESULTADO_COMPRAS: TR } = useTextos(DICIONARIO_FAZER_COMPRAS);
  const { TEXTOS_PLANO_PAGO } = useTextos(DICIONARIO_PLANOS);
  const router = useRouter();
  const f = useFormatos();
  const demo = useSessaoDemo();
  const estadoPlano = useEstadoPlano();
  const { falhou: planoFalhou } = usePedidoPlano();

  const [estado, setEstado] = useState<EstadoListas | null>(null); // null = ainda a carregar
  const [erroEstado, setErroEstado] = useState("");
  const [recusaApi, setRecusaApi] = useState<string | null>(null); // 402 da API (plano Free)
  const [limiteApi, setLimiteApi] = useState<string | null>(null); // 429 da API (listas do mês)

  const [orcamento, setOrcamento] = useState("");
  const [mercados, setMercados] = useState<string[]>([]);
  const [lista, setLista] = useState("");
  const [erros, setErros] = useState<ErrosCampos>({});

  const [aProcurar, setAProcurar] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [erroEnvio, setErroEnvio] = useState("");
  const [resultado, setResultado] = useState<ListaCompras | null>(null);
  const [focoErro, setFocoErro] = useState<FocoErro | null>(null);

  const campoOrcamento = useRef<HTMLInputElement>(null);
  const primeiroMercado = useRef<HTMLInputElement>(null);
  const campoLista = useRef<HTMLTextAreaElement>(null);
  const tituloResultado = useRef<HTMLHeadingElement>(null);
  const caixaErroEnvio = useRef<HTMLParagraphElement>(null);
  const caixaLimite = useRef<HTMLDivElement>(null);
  const caixaPlanoPago = useRef<HTMLDivElement>(null);

  function tratarSessao(e: unknown) {
    if (e instanceof SessaoExpirada) {
      apagarToken();
      router.replace("/login");
    }
  }

  // GET /compras/lista/estado. depoisDeErro: a seguir a um POST que falhou, só para atualizar o contador
  // (a API conta a lista antes de chamar a IA, mesmo que a IA falhe); se este pedido falhar, fica tudo como estava.
  function carregarEstado(depoisDeErro = false) {
    pedirApi<EstadoListas>("/compras/lista/estado")
      .then(setEstado)
      .catch((e) => {
        if (e instanceof SessaoExpirada) tratarSessao(e);
        else if (depoisDeErro) return;
        else if (eSoPlanosPagos(e)) setRecusaApi(typeof e.detalhe === "string" ? e.detalhe : T.soPagos);
        else setErroEstado(T.erroCarregar);
      });
  }

  useEffect(() => {
    carregarEstado();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Contador dos segundos de espera (só visual: os leitores de ecrã ouvem a frase, não cada segundo).
  useEffect(() => {
    if (!aProcurar) return;
    const relogio = setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => clearInterval(relogio);
  }, [aProcurar]);

  // Quando o plano chega, o foco vai para o título do resultado (e a página desliza até lá).
  useEffect(() => {
    if (resultado) tituloResultado.current?.focus();
  }, [resultado]);

  // Depois de um erro da API, o foco vai para a mensagem e a página desliza até ela
  // (no telemóvel podia ficar fora do ecrã).
  useEffect(() => {
    if (!focoErro) return;
    const caixa = { envio: caixaErroEnvio, limite: caixaLimite, pago: caixaPlanoPago }[focoErro.alvo].current;
    if (!caixa) return;
    caixa.focus({ preventScroll: true });
    const reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    caixa.scrollIntoView({ block: "center", behavior: reduzir ? "auto" : "smooth" });
  }, [focoErro]);

  const eFree = estadoPlano !== null && !temFuncoesPagas(estadoPlano.plano);
  // Só planos pagos: o 402 da API, ou o Free (pelo /plano ou pelo "disponivel" do estado).
  // Contas do Brasil: a função ainda não existe lá, por isso nunca se convida a mudar de plano para a ter.
  const eBrasil = estadoPlano?.pais === "BR" || f.pais === "BR";
  // Enquanto o /plano não chega, mostra-se "a carregar": assim o Free não vê "indisponível"
  // (nem o formulário) a piscar antes do convite para mudar de plano.
  const planoPronto = estadoPlano !== null || planoFalhou;
  const soPlanosPagos = eBrasil ? null : (recusaApi ?? (eFree ? T.soPagos : null));
  const indisponivel = eBrasil || (planoPronto && !soPlanosPagos && estado !== null && !estado.disponivel);
  const aCarregar = !eBrasil && !soPlanosPagos && !erroEstado && (!planoPronto || estado === null);
  const semListas =
    limiteApi ??
    (estado && estado.disponivel && estado.limite > 0 && estado.usadas >= estado.limite
      ? preencher(T.limiteTexto, { limite: estado.limite })
      : null);
  const podeUsar =
    planoPronto && !eBrasil && estado !== null && estado.disponivel && !soPlanosPagos && estado.mercados.length > 0;
  const nomes = new Map((estado?.mercados ?? []).map((m) => [m.chave, m.nome]));
  // A API manda o nome do mercado ("Pingo Doce"); se um dia vier a chave, troca-se pelo nome.
  const nomeMercado = (mercado: string) => nomes.get(mercado) ?? mercado;
  const tamanhoLista = lista.trim().length; // igual à validação: sem os espaços das pontas
  const listaLonga = tamanhoLista > LISTA_MAXIMO;

  function alternarMercado(chave: string) {
    setMercados((atuais) => {
      if (atuais.includes(chave)) return atuais.filter((c) => c !== chave);
      if (atuais.length >= MAX_MERCADOS) return atuais;
      return [...atuais, chave];
    });
    setErros((e) => ({ ...e, mercados: undefined }));
  }

  function validar(): { valor: number; texto: string } | null {
    const novos: ErrosCampos = {};
    const valor = lerOrcamento(orcamento);
    if (orcamento.trim() === "") novos.orcamento = T.erroOrcamentoVazio;
    else if (valor === null) novos.orcamento = T.erroOrcamentoFormato;
    else if (!(valor > 0) || valor > ORCAMENTO_MAXIMO)
      novos.orcamento = preencher(T.erroOrcamentoValor, { maximo: f.dinheiro(ORCAMENTO_MAXIMO, "auto") });
    if (mercados.length === 0) novos.mercados = T.erroMercados;
    const texto = lista.trim();
    if (texto.length < LISTA_MINIMO) novos.lista = preencher(T.erroListaCurta, { minimo: LISTA_MINIMO });
    else if (texto.length > LISTA_MAXIMO) novos.lista = preencher(T.erroListaLonga, { maximo: LISTA_MAXIMO });

    setErros(novos);
    // O foco vai para o primeiro campo com erro.
    if (novos.orcamento) campoOrcamento.current?.focus();
    else if (novos.mercados) primeiroMercado.current?.focus();
    else if (novos.lista) campoLista.current?.focus();
    if (valor === null || novos.orcamento || novos.mercados || novos.lista) return null;
    return { valor, texto };
  }

  async function montar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (aProcurar) return;
    const valido = validar();
    if (!valido) return;

    setAProcurar(true);
    setSegundos(0);
    setErroEnvio("");
    setResultado(null);
    try {
      // Os mercados vão pela ordem em que a API os mostrou.
      const escolhidos = (estado?.mercados ?? []).map((m) => m.chave).filter((c) => mercados.includes(c));
      const resposta = await pedirApi<ListaCompras>("/compras/lista", {
        orcamento: valido.valor,
        mercados: escolhidos,
        lista: valido.texto,
      });
      setResultado(resposta);
      setEstado((anterior) => (anterior ? { ...anterior, usadas: resposta.usadas, limite: resposta.limite } : anterior));
    } catch (e) {
      if (e instanceof SessaoExpirada) {
        tratarSessao(e);
        return;
      }
      if (eSoPlanosPagos(e)) {
        setRecusaApi(typeof e.detalhe === "string" ? e.detalhe : T.soPagos);
        setFocoErro((anterior) => ({ alvo: "pago", n: (anterior?.n ?? 0) + 1 }));
        return;
      }
      if (e instanceof ErroApi && e.status === 429) {
        setLimiteApi(typeof e.detalhe === "string" ? e.detalhe : T.limiteTextoSemNumero);
        setFocoErro((anterior) => ({ alvo: "limite", n: (anterior?.n ?? 0) + 1 }));
      } else {
        // 503: a IA falhou; 422 (ex. conta do Brasil) com o texto da API; 423 da demo com o texto da demo;
        // o resto, o genérico.
        const e503 = e instanceof ErroApi && e.status === 503;
        setErroEnvio(e503 ? (typeof e.detalhe === "string" ? e.detalhe : T.erroIA) : mensagemDaApi(e, T.erroGenerico));
        setFocoErro((anterior) => ({ alvo: "envio", n: (anterior?.n ?? 0) + 1 }));
      }
      // A lista pode já ter sido contada: o contador "X de Y" volta a vir da API.
      carregarEstado(true);
    } finally {
      setAProcurar(false);
    }
  }

  const desligado = aProcurar || semListas !== null;
  const cheio = mercados.length >= MAX_MERCADOS;

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-destaque">{T.etiquetaTopo}</p>
            <h1 className="text-2xl font-semibold text-texto">{T.titulo}</h1>
          </div>
          {podeUsar && estado.limite > 0 && (
            <p className="rounded-full border border-borda bg-cartao px-3 py-1 text-sm text-texto-suave tabular-nums">
              {preencher(T.contador, { usadas: estado.usadas, limite: estado.limite })}
            </p>
          )}
        </header>

        <p className="max-w-2xl text-sm text-texto-suave">{T.intro}</p>

        {soPlanosPagos && (
          <div ref={caixaPlanoPago} tabIndex={-1} className="rounded-md focus:outline-none">
            <AvisoPlanoPago mensagem={soPlanosPagos} />
          </div>
        )}

        {!soPlanosPagos && erroEstado && (
          <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
            {erroEstado}
          </p>
        )}

        {aCarregar && (
          <p className="rounded-xl border border-borda bg-cartao p-6 text-sm text-texto-suave">{T.aCarregar}</p>
        )}

        {indisponivel && <p className="rounded-xl border border-borda bg-cartao p-6 text-sm text-texto-suave">{T.indisponivel}</p>}

        {planoPronto && !eBrasil && !soPlanosPagos && estado?.disponivel && estado.mercados.length === 0 && (
          <p className="rounded-xl border border-borda bg-cartao p-6 text-sm text-texto-suave">{T.semMercados}</p>
        )}

        {podeUsar && semListas && (
          <div
            ref={caixaLimite}
            tabIndex={-1}
            role="alert"
            className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm focus:outline-none sm:p-4 dark:border-amber-800 dark:bg-amber-950/40">
            <p className="font-medium text-amber-900 dark:text-amber-200">{T.limiteTitulo}</p>
            <p className="mt-1 text-amber-900 dark:text-amber-200">{semListas}</p>
            {/* No Completo não há plano maior; na demo não se muda de plano. */}
            {!demo && estadoPlano?.plano !== "completo" && (
              <Link href="/plano" className={ESTILO_LINK_AVISO}>
                {TEXTOS_PLANO_PAGO.link}
              </Link>
            )}
          </div>
        )}

        {podeUsar && (
          <form
            onSubmit={montar}
            noValidate
            aria-busy={aProcurar}
            className="space-y-5 rounded-xl border border-borda bg-cartao p-4 sm:p-6"
          >
            {/* Orçamento, com o símbolo da moeda do lado em que o país o escreve. */}
            <div>
              <label htmlFor="orcamento" className="block text-sm font-medium text-texto">
                {preencher(T.orcamento, { moeda: f.nomeMoeda })}
              </label>
              <div
                className={`mt-1 flex max-w-xs items-center rounded-md border bg-cartao focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-destaque ${
                  erros.orcamento ? "border-red-600 dark:border-red-400" : "border-borda"
                } ${f.pais === "BR" ? "flex-row" : "flex-row-reverse"}`}
              >
                <span aria-hidden className="px-3 text-texto-suave">
                  {f.simbolo}
                </span>
                <input
                  ref={campoOrcamento}
                  id="orcamento"
                  inputMode="decimal"
                  autoComplete="off"
                  value={orcamento}
                  onChange={(e) => {
                    setOrcamento(e.target.value);
                    if (erros.orcamento) setErros((er) => ({ ...er, orcamento: undefined }));
                  }}
                  disabled={desligado}
                  aria-invalid={erros.orcamento ? true : undefined}
                  aria-describedby={erros.orcamento ? "orcamento-dica orcamento-erro" : "orcamento-dica"}
                  className={`min-h-11 w-full min-w-0 rounded-md bg-transparent px-3 py-2 text-base text-texto tabular-nums outline-none disabled:opacity-60 sm:text-sm ${
                    f.pais === "BR" ? "pl-0" : "pr-0 text-right"
                  }`}
                />
              </div>
              <p id="orcamento-dica" className="mt-1 text-xs text-texto-suave">
                {T.dicaOrcamento}
              </p>
              {erros.orcamento && (
                <p id="orcamento-erro" className={ESTILO_ERRO}>
                  {erros.orcamento}
                </p>
              )}
            </div>

            {/* Mercados: caixas de seleção (máx. 3). Com 3 escolhidos, as outras ficam desligadas. */}
            <fieldset aria-describedby={erros.mercados ? "mercados-dica mercados-erro" : "mercados-dica"}>
              <legend className="text-sm font-medium text-texto">{T.mercados}</legend>
              <p id="mercados-dica" className="text-xs text-texto-suave">
                {T.dicaMercados}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {estado.mercados.map((m, i) => {
                  const marcado = mercados.includes(m.chave);
                  const bloqueado = desligado || (cheio && !marcado);
                  return (
                    <label
                      key={m.chave}
                      className={`inline-flex min-h-11 items-center gap-2 rounded-lg border px-3 text-sm focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-destaque ${
                        marcado ? "border-destaque bg-destaque/10 font-medium text-texto" : "border-borda text-texto"
                      } ${bloqueado ? "cursor-not-allowed opacity-50" : "cursor-pointer hover:bg-fundo"}`}
                    >
                      <input
                        ref={i === 0 ? primeiroMercado : undefined}
                        type="checkbox"
                        checked={marcado}
                        disabled={bloqueado}
                        onChange={() => alternarMercado(m.chave)}
                        className="h-4 w-4 accent-destaque outline-none"
                      />
                      {m.nome}
                    </label>
                  );
                })}
              </div>
              <p aria-live="polite" className="mt-2 text-xs text-texto-suave empty:hidden">
                {cheio && !aProcurar ? T.mercadosMaximo : ""}
              </p>
              {erros.mercados && (
                <p id="mercados-erro" className={ESTILO_ERRO}>
                  {erros.mercados}
                </p>
              )}
            </fieldset>

            {/* Lista */}
            <div>
              <label htmlFor="lista" className="block text-sm font-medium text-texto">
                {T.lista}
              </label>
              <p id="lista-dica" className="text-xs text-texto-suave">
                {T.dicaLista}
              </p>
              <textarea
                ref={campoLista}
                id="lista"
                rows={6}
                value={lista}
                onChange={(e) => {
                  setLista(e.target.value);
                  if (erros.lista) setErros((er) => ({ ...er, lista: undefined }));
                }}
                placeholder={T.marcadorLista}
                disabled={desligado}
                aria-invalid={erros.lista ? true : undefined}
                aria-describedby={erros.lista ? "lista-dica lista-contador lista-erro" : "lista-dica lista-contador"}
                className={`mt-2 resize-y disabled:opacity-60 ${ESTILO_CAMPO} ${erros.lista ? "border-red-600 dark:border-red-400" : ""}`}
              />
              {/* Sem maxLength (cortava em silêncio): passar dos 600 fica a vermelho e a validação não deixa enviar. */}
              <p
                id="lista-contador"
                className={`mt-1 text-right text-xs tabular-nums ${
                  listaLonga ? "font-semibold text-red-700 dark:text-red-300" : "text-texto-suave"
                }`}
              >
                {preencher(T.contadorLista, { n: tamanhoLista, maximo: LISTA_MAXIMO })}
              </p>
              {erros.lista && (
                <p id="lista-erro" className={ESTILO_ERRO}>
                  {erros.lista}
                </p>
              )}
            </div>

            {erroEnvio && (
              <p
                ref={caixaErroEnvio}
                tabIndex={-1}
                role="alert"
                className="rounded-md bg-red-50 p-3 text-sm text-red-700 focus:outline-none dark:bg-red-950/40 dark:text-red-300"
              >
                {erroEnvio}
              </p>
            )}

            <div className="space-y-2">
              <button
                type="submit"
                disabled={desligado}
                className={`inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-destaque px-5 text-sm font-semibold text-white hover:bg-destaque-hover disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto ${FOCO}`}
              >
                {aProcurar && (
                  <span aria-hidden className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none" />
                )}
                {aProcurar ? T.botaoAProcurar : T.botao}
              </button>
              <p className="text-xs text-texto-suave">{T.envioIA}</p>
            </div>
          </form>
        )}

        {/* Sempre no ecrã (vazia ou não), para os leitores de ecrã anunciarem a espera e o plano pronto. */}
        <div role="status" aria-live="polite">
          {aProcurar && (
            <div className="flex items-start gap-3 rounded-xl border border-destaque/40 bg-cartao p-4 sm:p-6">
              <span
                aria-hidden
                className="mt-0.5 h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-destaque/30 border-t-destaque motion-reduce:animate-none"
              />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-texto">{T.aProcurarTitulo}</p>
                <p className="mt-1 text-sm text-texto-suave">{T.aProcurarTexto}</p>
              </div>
              <span aria-hidden className="shrink-0 text-sm text-texto-suave tabular-nums">
                {preencher(T.segundos, { s: segundos })}
              </span>
            </div>
          )}
          {resultado && !aProcurar && <p className="sr-only">{preencher(TR.pronto, { total: f.dinheiro(resultado.total) })}</p>}
        </div>

        {resultado && <ResultadoPlano resultado={resultado} nomeMercado={nomeMercado} tituloRef={tituloResultado} />}
      </div>
    </main>
  );
}
