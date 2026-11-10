"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";

import AvisoLimite from "@/components/AvisoLimite";
import AvisoPlanoPago from "@/components/AvisoPlanoPago";
import {
  apagarToken,
  descarregarFicheiro,
  eBloqueadoNaDemo,
  eLimiteDiario,
  ErroApi,
  eSoPlanosPagos,
  lerToken,
  pedirApi,
  pedirEstadoPlano,
  SessaoExpirada,
  type ComparacaoAno,
  type RelatorioAnual,
  type ResumoAnualIA,
  type TotaisAno,
} from "@/lib/api";
import { dataPorExtenso, preencher, temFuncoesPagas } from "@/lib/planos";
import { TEXTOS_RELATORIO as T } from "@/lib/textosRelatorio";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

import CartaoResumo from "../dashboard/CartaoResumo";
import { euros } from "../dashboard/formatos";
import GraficoAnual from "./GraficoAnual";

// Anos no seletor: o atual e os 5 anteriores (a API aceita de 2000 até ao ano atual).
const ANOS_NO_SELETOR = 6;

// --- Formatos desta página ---

// "2026-11" -> "novembro de 2026"
function mesLongo(mes: string) {
  return new Date(`${mes}-01T00:00:00`).toLocaleDateString("pt-PT", { month: "long", year: "numeric" });
}

// "2026-03" ou "03" -> "março"
function nomeDoMes(mes: string) {
  const numero = Number(mes.slice(-2));
  return new Date(2000, numero - 1, 1).toLocaleDateString("pt-PT", { month: "long" });
}

// "2026-03" -> "mar."
function mesCurto(mes: string) {
  return new Date(`${mes}-01T00:00:00`).toLocaleDateString("pt-PT", { month: "short" });
}

// "2026-03-14" -> "14/03"
function diaCurto(data: string) {
  return new Date(`${data}T00:00:00`).toLocaleDateString("pt-PT", { day: "2-digit", month: "2-digit" });
}

// +12,30 € / −12,30 € / igual: o sinal escrito, para a diferença não depender só da cor.
function diferencaEuros(valor: number) {
  if (Math.abs(valor) < 0.005) return T.comparacaoIgual;
  return valor > 0 ? preencher(T.comparacaoMais, { valor: euros(valor) }) : euros(valor);
}

// "janeiro a novembro" / "ano inteiro"
function textoDosMeses(meses: string[]) {
  if (meses.length === 0) return "";
  if (meses.length === 12) return T.anoInteiro;
  if (meses.length === 1) return nomeDoMes(meses[0]);
  return preencher(T.mesesAte, { de: nomeDoMes(meses[0]), ate: nomeDoMes(meses[meses.length - 1]) });
}

// --- Peças da página ---

const ESTILO_SECAO = "rounded-xl border border-borda bg-cartao p-4 sm:p-6 break-inside-avoid print:p-4";
const ESTILO_BOTAO =
  "inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-borda bg-cartao px-4 text-sm font-medium text-texto hover:bg-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto";
const ESTILO_BOTAO_PRINCIPAL =
  "inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-destaque px-4 text-sm font-semibold text-white hover:bg-destaque-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto dark:text-fundo";

function Icone({ caminho }: { caminho: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d={caminho} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Titulo({ titulo, texto }: { titulo: string; texto?: string }) {
  return (
    <div className="mb-4">
      <h2 className="font-medium text-texto">{titulo}</h2>
      {texto && <p className="text-xs text-texto-suave">{texto}</p>}
    </div>
  );
}

// Linha de totais da comparação: valor deste ano, do anterior e a diferença.
type PropsLinha = { nome: string; atual: number; anterior: number; ano: number; anoAnterior: number };

function LinhaComparada({ nome, atual, anterior, ano, anoAnterior }: PropsLinha) {
  return (
    <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2 text-sm">
      <span className="text-texto">{nome}</span>
      <span className="flex flex-wrap items-baseline gap-x-3 tabular-nums">
        <span className="text-xs text-texto-suave">
          {ano}: {euros(atual)} · {anoAnterior}: {euros(anterior)}
        </span>
        <span className="font-semibold text-texto">{diferencaEuros(atual - anterior)}</span>
      </span>
    </li>
  );
}

function Comparacao({ comparacao, ano, totais }: { comparacao: ComparacaoAno; ano: number; totais: TotaisAno }) {
  const anterior = comparacao.ano;
  const anos = { ano, anoAnterior: anterior };
  return (
    <section className={ESTILO_SECAO}>
      <Titulo
        titulo={preencher(T.comparacaoTitulo, { ano: anterior })}
        texto={preencher(T.comparacaoMeses, { meses: textoDosMeses(comparacao.meses_comparados) })}
      />
      {comparacao.meses_com_dados < comparacao.meses_comparados.length && (
        <p className="-mt-2 mb-3 text-xs text-texto-suave">
          {preencher(T.comparacaoMesesIncompletos, { ano: anterior, n: comparacao.meses_com_dados })}
        </p>
      )}
      <ul className="divide-y divide-borda">
        <LinhaComparada nome={T.entradas} atual={totais.entradas} anterior={comparacao.totais.entradas} {...anos} />
        <LinhaComparada nome={T.saidas} atual={totais.saidas} anterior={comparacao.totais.saidas} {...anos} />
        <LinhaComparada nome={T.colunaSaldo} atual={totais.saldo} anterior={comparacao.totais.saldo} {...anos} />
      </ul>

      {comparacao.categorias.length > 0 && (
        <>
          <h3 className="mt-5 mb-1 text-sm font-medium text-texto">{T.comparacaoCategorias}</h3>
          <ul className="divide-y divide-borda">
            {comparacao.categorias.map((c) => (
              <LinhaComparada key={c.categoria} nome={c.etiqueta} atual={c.total} anterior={c.total_anterior} {...anos} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function Relatorio({ dados }: { dados: RelatorioAnual }) {
  const maiorCategoria = dados.categorias[0]?.percentagem ?? 0;
  return (
    <>
      {/* Totais: o saldo primeiro, ocupa a linha toda no telemóvel. */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 print:grid-cols-3">
        <div className="col-span-2 sm:col-span-1 print:col-span-1">
          <CartaoResumo
            titulo={T.saldo}
            valor={dados.totais.saldo}
            descricao={T.saldoDescricao}
            icone="M3 7h18v12H3zM3 7l3-3h12l3 3M16 13h2"
            corIcone="var(--destaque)"
          />
        </div>
        <CartaoResumo
          titulo={T.entradas}
          valor={dados.totais.entradas}
          descricao={T.entradasDescricao}
          icone="M7 17L17 7M7 7v10h10"
          corIcone="var(--cor-receitas)"
        />
        <CartaoResumo
          titulo={T.saidas}
          valor={dados.totais.saidas}
          descricao={T.saidasDescricao}
          icone="M7 7l10 10M17 7v10H7"
          corIcone="var(--cor-despesas)"
        />
      </div>

      <section className={ESTILO_SECAO}>
        <Titulo titulo={T.mesAMesTitulo} texto={T.mesAMesTexto} />
        <GraficoAnual meses={dados.meses} />
        {/* A tabela não aparece no ecrã (o gráfico tem os valores ao passar o dedo), mas é lida pelos
            leitores de ecrã e aparece no PDF, onde o gráfico não deixa ler os valores exatos. */}
        <table className="sr-only text-sm print:not-sr-only print:mt-4 print:w-full">
          <caption className="sr-only">{T.mesAMesTitulo}</caption>
          <thead>
            <tr className="border-b border-borda text-left text-xs text-texto-suave">
              <th scope="col" className="py-1 font-medium">{T.colunaMes}</th>
              <th scope="col" className="py-1 text-right font-medium">{T.entradas}</th>
              <th scope="col" className="py-1 text-right font-medium">{T.saidas}</th>
              <th scope="col" className="py-1 text-right font-medium">{T.colunaSaldo}</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {dados.meses.map((m) => (
              <tr key={m.mes} className="border-b border-borda">
                <th scope="row" className="py-1 text-left font-normal capitalize">{nomeDoMes(m.mes)}</th>
                {m.com_dados ? (
                  <>
                    <td className="py-1 text-right">{euros(m.entradas)}</td>
                    <td className="py-1 text-right">{euros(m.saidas)}</td>
                    <td className="py-1 text-right">{euros(m.saldo)}</td>
                  </>
                ) : (
                  <td colSpan={3} className="py-1 text-right text-texto-suave">
                    {T.semMovimentos}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="grid gap-6 lg:grid-cols-2 print:grid-cols-1">
        <section className={ESTILO_SECAO}>
          <Titulo titulo={T.categoriasTitulo} texto={T.categoriasTexto} />
          {dados.categorias.length === 0 ? (
            <p className="text-sm text-texto-suave">{T.categoriasVazio}</p>
          ) : (
            <ul className="space-y-3">
              {dados.categorias.map((c) => (
                <li key={c.categoria} className="text-sm">
                  <div className="flex items-baseline gap-3">
                    <span className="min-w-0 flex-1 truncate capitalize text-texto">{c.etiqueta}</span>
                    <span className="shrink-0 tabular-nums text-texto">{euros(c.total)}</span>
                    <span className="w-12 shrink-0 text-right text-xs tabular-nums text-texto-suave">
                      {c.percentagem.toLocaleString("pt-PT")}%
                    </span>
                  </div>
                  {/* A barra é relativa à maior categoria, para as pequenas ainda se verem. */}
                  <div className="mt-1 h-1.5 rounded-full bg-fundo" aria-hidden>
                    <div
                      className="h-1.5 rounded-full"
                      style={{
                        width: `${maiorCategoria > 0 ? Math.max((c.percentagem / maiorCategoria) * 100, 1) : 0}%`,
                        background: "var(--cor-despesas)",
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-xs text-texto-suave">{dados.nota_categorias}</p>
        </section>

        {dados.comparacao ? (
          <Comparacao comparacao={dados.comparacao} ano={dados.ano} totais={dados.totais} />
        ) : (
          <section className={ESTILO_SECAO}>
            <Titulo titulo={preencher(T.comparacaoTitulo, { ano: dados.ano - 1 })} />
            <p className="text-sm text-texto-suave">{preencher(T.comparacaoSem, { ano: dados.ano - 1 })}</p>
          </section>
        )}
      </div>

      <section className={ESTILO_SECAO}>
        <Titulo titulo={T.maioresTitulo} />
        {dados.maiores_saidas.length === 0 ? (
          <p className="text-sm text-texto-suave">{T.maioresVazio}</p>
        ) : (
          <ol className="divide-y divide-borda">
            {dados.maiores_saidas.map((s, i) => (
              <li key={`${s.data}-${i}`} className="flex items-center gap-3 py-2.5 text-sm">
                <span className="w-5 shrink-0 text-xs tabular-nums text-texto-suave">{i + 1}.</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-texto print:whitespace-normal">{s.descricao}</p>
                  <p className="text-xs text-texto-suave">
                    {diaCurto(s.data)} · <span className="capitalize">{s.etiqueta}</span>
                  </p>
                </div>
                <span className="shrink-0 font-semibold tabular-nums text-texto">{euros(s.valor)}</span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2 print:grid-cols-1">
        <section className={ESTILO_SECAO}>
          <Titulo titulo={T.recorrentesTitulo} texto={T.recorrentesTexto} />
          {dados.recorrentes.length === 0 ? (
            <p className="text-sm text-texto-suave">{T.recorrentesVazio}</p>
          ) : (
            <ul className="divide-y divide-borda">
              {dados.recorrentes.map((r, i) => (
                <li key={`${r.descricao}-${i}`} className="flex items-center gap-3 py-2.5 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-texto print:whitespace-normal">{r.descricao}</p>
                    <p className="text-xs text-texto-suave">
                      <span className="capitalize">{r.etiqueta}</span> ·{" "}
                      {preencher(T.recorrentesPorMes, { valor: euros(r.valor_mensal) })} ·{" "}
                      {r.pagamentos_no_ano === 1
                        ? T.recorrentesUmPagamento
                        : preencher(T.recorrentesPagamentos, { n: r.pagamentos_no_ano })}
                    </p>
                  </div>
                  <span className="shrink-0 font-semibold tabular-nums text-texto">{euros(r.total_no_ano)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className={ESTILO_SECAO}>
          <Titulo titulo={T.objetivosTitulo} texto={T.objetivosTexto} />
          {dados.objetivos.length === 0 ? (
            <>
              <p className="text-sm text-texto-suave">{T.objetivosVazio}</p>
              <Link
                href="/reserva"
                className="mt-1 inline-flex min-h-11 items-center text-sm font-semibold text-destaque underline underline-offset-2 hover:no-underline print:hidden"
              >
                {T.objetivosLink}
              </Link>
            </>
          ) : (
            <ul className="space-y-4">
              {dados.objetivos.map((o, i) => (
                <li key={`${o.nome}-${i}`} className="text-sm">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate font-medium text-texto">{o.nome}</span>
                    <span className="shrink-0 text-xs tabular-nums text-texto-suave">
                      {o.percentagem.toLocaleString("pt-PT")}%
                    </span>
                  </div>
                  <div
                    className="mt-1.5 h-2 rounded-full bg-fundo"
                    role="progressbar"
                    aria-label={o.nome}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.min(o.percentagem, 100)}
                  >
                    <div className="h-2 rounded-full bg-destaque" style={{ width: `${Math.min(o.percentagem, 100)}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-texto-suave">
                    {preencher(T.objetivosPoupado, { poupado: euros(o.valor_poupado), alvo: euros(o.valor_alvo) })} ·{" "}
                    {preencher(T.objetivosPrazo, { data: dataPorExtenso(o.data_alvo) })}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}

// --- A página ---

// O ano atual só se lê no browser: no pré-render do Next (sem visitante) é null e a página mostra "a carregar".
// Assim o ano não fica "congelado" no dia em que se fez o build.
const nadaParaOuvir = () => () => {};
const lerAnoAtual = () => new Date().getFullYear();
const semAnoNoServidor = () => null;

// O resultado guarda o ano a que pertence: se o ano escolhido mudou, o guardado já não serve.
type Resultado = { ano: number; dados?: RelatorioAnual; erro?: string };
type ResumoIA = { ano: number; texto?: string; erro?: string; semPedidos?: boolean; planoPago?: string };

export default function PaginaRelatorio() {
  const router = useRouter();
  const demo = useSessaoDemo();
  const anoAtual = useSyncExternalStore(nadaParaOuvir, lerAnoAtual, semAnoNoServidor);
  const anos = anoAtual === null ? [] : Array.from({ length: ANOS_NO_SELETOR }, (_, i) => anoAtual - i);

  const [anoEscolhido, setAno] = useState<number | null>(null);
  const ano = anoEscolhido ?? anoAtual; // null só no pré-render
  const [tentativa, setTentativa] = useState(0); // "Tentar outra vez" volta a pedir o mesmo ano
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [plano, setPlano] = useState<string | null>(null);

  const [aDescarregar, setADescarregar] = useState(false);
  const [csvErro, setCsvErro] = useState("");
  const [csvPlanoPago, setCsvPlanoPago] = useState("");

  const [aPensar, setAPensar] = useState(false);
  const [resumoIA, setResumoIA] = useState<ResumoIA | null>(null);

  const aCarregar = resultado?.ano !== ano;
  const dados = aCarregar ? undefined : resultado?.dados;
  const erro = aCarregar ? undefined : resultado?.erro;
  const semMovimentos = dados ? !dados.meses.some((m) => m.com_dados) : false;
  const ia = resumoIA?.ano === ano ? resumoIA : null;
  const completo = plano === "completo";

  function sessaoExpirada() {
    apagarToken();
    router.replace("/login");
  }

  useEffect(() => {
    if (ano === null) return;
    if (!lerToken()) {
      router.replace("/login");
      return;
    }
    let cancelado = false;
    pedirApi<RelatorioAnual>(`/relatorio?ano=${ano}`)
      .then((d) => {
        if (!cancelado) setResultado({ ano, dados: d });
      })
      .catch((e) => {
        if (e instanceof SessaoExpirada) {
          apagarToken();
          router.replace("/login");
          return;
        }
        const texto = e instanceof ErroApi && e.status === 422 && typeof e.detalhe === "string" ? e.detalhe : T.erro;
        if (!cancelado) setResultado({ ano, erro: texto });
      });
    return () => {
      cancelado = true;
    };
  }, [ano, tentativa, router]);

  // O plano só decide o que se mostra (a API decide a sério: 402).
  useEffect(() => {
    if (!lerToken()) return;
    pedirEstadoPlano()
      .then((estado) => setPlano(estado.plano))
      .catch(() => setPlano(null));
  }, []);

  function mudarAno(novo: number) {
    setAno(novo);
    setCsvErro("");
    setCsvPlanoPago("");
  }

  function tentarOutraVez() {
    setResultado(null);
    setTentativa((t) => t + 1);
  }

  async function descarregarCsv() {
    if (ano === null) return;
    setCsvErro("");
    setCsvPlanoPago("");
    // No Free nem se faz o pedido: a resposta seria o 402.
    if (plano && !temFuncoesPagas(plano)) {
      setCsvPlanoPago(T.csvPlanoPago);
      return;
    }
    setADescarregar(true);
    try {
      const ficheiro = await descarregarFicheiro(`/relatorio/csv?ano=${ano}`);
      // O nome dá-o a página (o CORS não deixa ler o Content-Disposition).
      const endereco = URL.createObjectURL(ficheiro);
      const ligacao = document.createElement("a");
      ligacao.href = endereco;
      ligacao.download = `relatorio-${ano}.csv`;
      document.body.appendChild(ligacao);
      ligacao.click();
      ligacao.remove();
      setTimeout(() => URL.revokeObjectURL(endereco), 1000);
    } catch (e) {
      if (e instanceof SessaoExpirada) sessaoExpirada();
      else if (eBloqueadoNaDemo(e)) return;
      else if (eSoPlanosPagos(e)) setCsvPlanoPago(typeof e.detalhe === "string" ? e.detalhe : T.csvPlanoPago);
      else setCsvErro(T.csvErro);
    } finally {
      setADescarregar(false);
    }
  }

  async function pedirResumoIA() {
    const doAno = ano;
    if (doAno === null) return;
    setAPensar(true);
    setResumoIA(null);
    try {
      const resposta = await pedirApi<ResumoAnualIA>(`/relatorio/resumo-ia?ano=${doAno}`, {});
      setResumoIA({ ano: doAno, texto: resposta.resumo });
    } catch (e) {
      if (e instanceof SessaoExpirada) sessaoExpirada();
      else if (eBloqueadoNaDemo(e)) setResumoIA({ ano: doAno, erro: T.iaDemo });
      else if (eLimiteDiario(e)) setResumoIA({ ano: doAno, semPedidos: true });
      else if (eSoPlanosPagos(e)) setResumoIA({ ano: doAno, planoPago: typeof e.detalhe === "string" ? e.detalhe : T.iaErro });
      else if (e instanceof ErroApi && e.status === 503 && typeof e.detalhe === "string") setResumoIA({ ano: doAno, erro: e.detalhe });
      else setResumoIA({ ano: doAno, erro: T.iaErro });
    } finally {
      setAPensar(false);
    }
  }

  const titulo = dados?.titulo ?? (ano === null ? T.etiquetaTopo : preencher(T.tituloReserva, { ano }));

  return (
    <main className="p-4 sm:p-8 print:p-0">
      <div className="mx-auto max-w-6xl space-y-6 print:max-w-none print:space-y-4">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-destaque">{T.etiquetaTopo}</p>
            <h1 className="text-2xl font-semibold text-texto">{titulo}</h1>
          </div>
          <select
            value={ano ?? ""}
            onChange={(e) => mudarAno(Number(e.target.value))}
            aria-label={T.seletorAno}
            className="min-h-11 rounded-lg border border-borda bg-cartao px-3 text-sm text-texto print:hidden"
          >
            {anos.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </header>

        {/* O aviso aparece sempre (também no PDF): discreto, mas antes de qualquer número. */}
        {dados && (
          <p className="flex gap-2 rounded-xl border border-borda bg-cartao p-3 text-xs leading-relaxed text-texto-suave sm:text-sm">
            <Icone caminho="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5M12 8h.01" />
            <span>{dados.aviso}</span>
          </p>
        )}

        {aCarregar && (
          <p role="status" className="rounded-xl border border-borda bg-cartao p-6 text-sm text-texto-suave">
            {T.aCarregar}
          </p>
        )}

        {erro && (
          <div role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
            <p>{erro}</p>
            <button
              type="button"
              onClick={tentarOutraVez}
              className="mt-1 inline-flex min-h-11 items-center font-semibold underline underline-offset-2 hover:no-underline"
            >
              {T.tentarOutraVez}
            </button>
          </div>
        )}

        {dados && semMovimentos && (
          <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
            <h2 className="font-medium text-texto">{preencher(T.vazioTitulo, { ano: dados.ano })}</h2>
            <p className="mt-1 text-sm text-texto-suave">{T.vazioTexto}</p>
            <Link
              href="/movimentacoes"
              className="mt-4 inline-flex min-h-11 items-center justify-center rounded-md bg-destaque px-4 text-sm font-semibold text-white transition-colors hover:bg-destaque-hover dark:text-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque print:hidden"
            >
              {T.vazioBotao}
            </Link>
          </section>
        )}

        {dados && !semMovimentos && (
          <>
            {/* Ações: não vão para o PDF. */}
            <div className="space-y-3 print:hidden">
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                <button type="button" onClick={() => window.print()} className={ESTILO_BOTAO_PRINCIPAL}>
                  <Icone caminho="M6 9V3h12v6M6 18H4v-7h16v7h-2M8 14h8v7H8z" />
                  {T.pdf}
                </button>
                <button type="button" onClick={descarregarCsv} disabled={aDescarregar} className={ESTILO_BOTAO}>
                  <Icone caminho="M12 4v11M7 10l5 5 5-5M5 20h14" />
                  {aDescarregar ? T.csvADescarregar : T.csv}
                </button>
                {completo && (
                  <button
                    type="button"
                    onClick={pedirResumoIA}
                    disabled={aPensar || demo}
                    aria-describedby={demo ? "nota-ia-demo" : "nota-ia"}
                    className={ESTILO_BOTAO}
                  >
                    <Icone caminho="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" />
                    {aPensar ? T.iaAPensar : T.ia}
                  </button>
                )}
              </div>
              <p className="text-xs text-texto-suave">
                {T.pdfAjuda}
                {completo && !demo && <span id="nota-ia"> {T.iaGasta}</span>}
                {completo && demo && <span id="nota-ia-demo"> {T.iaDemo}</span>}
              </p>
              {csvPlanoPago && <AvisoPlanoPago mensagem={csvPlanoPago} />}
              {csvErro && (
                <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
                  {csvErro}
                </p>
              )}
              {ia?.semPedidos && <AvisoLimite />}
              {ia?.planoPago && <AvisoPlanoPago mensagem={ia.planoPago} />}
              {ia?.erro && (
                <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
                  {ia.erro}
                </p>
              )}
            </div>

            {dados.ano_incompleto && (
              <div className="rounded-xl border border-l-4 border-borda border-l-amber-500 bg-cartao p-3 text-sm text-texto">
                {dados.ano === anoAtual && <p>{preencher(T.anoAtual, { mes: mesLongo(dados.ate_mes) })}</p>}
                {dados.meses_sem_dados.length > 0 && (
                  <p>{preencher(T.mesesSemDados, {
                      // Os meses abreviados acabam em "." ("nov."): tira-se o do último para não ficar "nov..".
                      meses: dados.meses_sem_dados.map(mesCurto).join(", ").replace(/\.$/, ""),
                    })}</p>
                )}
              </div>
            )}

            {ia?.texto && (
              <section className={ESTILO_SECAO} aria-live="polite">
                <h2 className="mb-3 flex items-center gap-2 font-medium text-texto">
                  <span className="text-destaque">
                    <Icone caminho="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z" />
                  </span>
                  {T.iaTitulo}
                </h2>
                <p className="whitespace-pre-line text-sm leading-relaxed text-texto">{ia.texto}</p>
              </section>
            )}

            <Relatorio dados={dados} />
          </>
        )}

      </div>
    </main>
  );
}
