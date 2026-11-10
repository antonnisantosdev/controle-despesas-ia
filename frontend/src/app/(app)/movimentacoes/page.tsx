"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AvisoLimite from "@/components/AvisoLimite";
import AvisoLimitePdf from "@/components/AvisoLimitePdf";
import AvisoPlanoPago from "@/components/AvisoPlanoPago";
import NotaDemo, { ID_NOTA_DEMO } from "@/components/NotaDemo";
import {
  eBloqueadoNaDemo,
  apagarToken,
  pedirApi,
  pedirEstadoPlano,
  SessaoExpirada,
  type ResultadoImportacao,
  type ResumoMensal,
  type Transacao,
} from "@/lib/api";
import { CATEGORIAS, METODOS_PAGAMENTO } from "@/lib/opcoes";
import { mesAtual, preencher, temFuncoesPagas } from "@/lib/planos";
import { TEXTOS_APAGAR_MOVIMENTO, TEXTOS_CATEGORIZAR, TEXTOS_ENVIO_IA, TEXTOS_PLANO_PAGO } from "@/lib/textosPlanos";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

import { euros, nomeMes } from "../dashboard/formatos";
import BotaoCategorizar from "./BotaoCategorizar";
import BotaoImportar from "./BotaoImportar";
import DialogoApagar from "./DialogoApagar";
import FormNovaMovimentacao from "./FormNovaMovimentacao";

// "2026-10-05" -> "05/10"
function diaMes(data: string) {
  const [, mes, dia] = data.split("-");
  return `${dia}/${mes}`;
}

export default function PaginaMovimentacoes() {
  const router = useRouter();
  const [meses, setMeses] = useState<string[]>([]);
  const [mes, setMes] = useState("");
  // Como no resumo: guarda-se o mês a que a lista pertence, para saber se ainda está a carregar.
  const [lista, setLista] = useState<{ mes: string; transacoes: Transacao[] } | null>(null);
  const [erro, setErro] = useState("");
  const [formAberto, setFormAberto] = useState(false);
  // Resultado da última importação: uma mensagem e, se o ficheiro tiver erros, as linhas inválidas.
  // nota: o aviso da API (ex.: importou sem categorias porque acabaram os pedidos à IA).
  const [aviso, setAviso] = useState<{
    tipo: "sucesso" | "erro";
    mensagem: string;
    erros: string[];
    nota?: string | null;
  } | null>(null);
  // A importação usa a IA: true quando a API respondeu 429 (limite de pedidos à IA).
  const [semPedidos, setSemPedidos] = useState(false);
  // 429 do limite de extratos PDF do mês (o CSV continua a funcionar).
  const [semPdf, setSemPdf] = useState(false);
  // 402: o PDF é só dos planos pagos. Guarda a mensagem da API para o AvisoPlanoPago.
  const [soPlanosPagos, setSoPlanosPagos] = useState<string | null>(null);
  // Free: só importa CSV. Avisa antes de escolher o ficheiro. Se o /plano falhar, aceita os dois (a API decide).
  const [soCsv, setSoCsv] = useState(false);
  // Muda sempre que é criada uma movimentação, para a lista voltar a ser pedida à API.
  const [versao, setVersao] = useState(0);
  // Transações sem categoria em TODOS os meses: a lista só tem o mês escolhido, mas o
  // POST /transacoes/categorizar trata as de todos os meses (por lotes). 0 enquanto não se sabe (o botão fica escondido).
  const [semCategoria, setSemCategoria] = useState(0);
  // A movimentação que o utilizador quer apagar (o diálogo de confirmação está aberto), ou null.
  const [aApagar, setAApagar] = useState<Transacao | null>(null);
  const aCarregar = lista?.mes !== mes;
  // Na demo (só leitura) os botões que mudam dados ficam desligados; a API recusa-os na mesma (423).
  const demo = useSessaoDemo();

  function tratarErro(e: unknown) {
    if (e instanceof SessaoExpirada) {
      apagarToken();
      router.replace("/login");
    } else {
      setErro("Não foi possível carregar as movimentações. Confirma que a API está a correr.");
    }
  }

  // 1. Os meses disponíveis vêm do mesmo endpoint do dashboard; começa no mais recente.
  useEffect(() => {
    pedirApi<ResumoMensal[]>("/dashboard/mensal")
      .then((dados) => {
        // Conta nova, ainda sem movimentações: começa no mês atual (senão a página ficava em "A carregar...").
        const lista = dados.length > 0 ? dados.map((d) => d.mes) : [mesAtual()];
        setMeses(lista);
        setMes(lista[lista.length - 1]);
      })
      .catch(tratarErro);
    pedirEstadoPlano()
      .then((estado) => setSoCsv(!temFuncoesPagas(estado.plano)))
      .catch(() => {}); // a sessão expirada já é tratada pelo pedido dos meses
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Depois de criar: fecha o formulário, mostra o mês da movimentação nova e recarrega a lista.
  // Mostra um mês (juntando-o à caixa, se for novo) e volta a pedir a lista à API.
  function mostrarMes(mesNovo: string) {
    setMeses((anteriores) => (anteriores.includes(mesNovo) ? anteriores : [...anteriores, mesNovo].sort()));
    setMes(mesNovo);
    setLista(null);
    setVersao((v) => v + 1);
  }

  function aposCriar(criada: Transacao) {
    setFormAberto(false);
    mostrarMes(criada.data.slice(0, 7));
  }

  // Depois de importar: diz quantas entraram e salta para o mês mais recente do extrato.
  function aposImportar(resultado: ResultadoImportacao) {
    setSemPedidos(false);
    setSoPlanosPagos(null);
    setAviso({
      tipo: "sucesso",
      mensagem: `${resultado.importadas} importada(s), ${resultado.duplicadas} já existia(m).`,
      erros: [],
      nota: resultado.aviso,
    });
    const datas = resultado.transacoes.map((t) => t.data).sort();
    if (datas.length > 0) mostrarMes(datas[datas.length - 1].slice(0, 7));
  }

  // 2. Sempre que o mês muda (ou há uma movimentação nova), carrega as transações desse mês.
  useEffect(() => {
    if (!mes) return;
    let cancelado = false;
    pedirApi<Transacao[]>(`/transacoes?mes=${mes}`)
      .then((transacoes) => {
        if (!cancelado) setLista({ mes, transacoes });
      })
      .catch(tratarErro);
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mes, versao]);

  // 3. Conta as transações sem categoria (todos os meses), para o botão "Categorizar".
  // A API devolve só o número, sem as linhas. Volta a contar depois de criar, importar ou categorizar (versao).
  useEffect(() => {
    let cancelado = false;
    pedirApi<{ total: number }>("/transacoes/sem-categoria/contagem")
      .then((contagem) => {
        if (!cancelado) setSemCategoria(contagem.total);
      })
      .catch(() => {}); // sem a contagem o botão não aparece; a sessão expirada já é tratada pela lista
    return () => {
      cancelado = true;
    };
  }, [versao]);

  // Depois de a IA categorizar: diz quantas mudaram e volta a pedir a lista e a contagem.
  function aposCategorizar(atualizadas: Transacao[]) {
    setSemPedidos(false);
    setSoPlanosPagos(null);
    setAviso({ tipo: "sucesso", mensagem: preencher(TEXTOS_CATEGORIZAR.sucesso, { n: atualizadas.length }), erros: [] });
    setVersao((v) => v + 1);
  }

  // Depois de apagar (ou de a API dizer que já não existia): mostra a mensagem e volta a pedir a lista e a contagem.
  function aposApagar(mensagem: string) {
    setAviso({ tipo: "sucesso", mensagem, erros: [] });
    setVersao((v) => v + 1);
  }

  const transacoes = aCarregar ? [] : (lista?.transacoes ?? []);

  // Muda a categoria de uma transação só no ecrã (sem falar com a API).
  // Cria uma lista nova em vez de alterar a antiga, para o React reparar e redesenhar.
  function trocarNaLista(id: number, categoria: string | null) {
    setLista((atual) =>
      atual && {
        ...atual,
        transacoes: atual.transacoes.map((t) => (t.id === id ? { ...t, categoria } : t)),
      },
    );
  }

  // O utilizador escolheu outra categoria na tabela.
  async function mudarCategoria(transacao: Transacao, nova: string) {
    const antiga = transacao.categoria;
    trocarNaLista(transacao.id, nova);
    try {
      await pedirApi(`/transacoes/${transacao.id}`, { categoria: nova }, "PATCH");
      // Preencheu uma que estava vazia: há menos uma para o botão "Categorizar".
      if (antiga === null) setSemCategoria((n) => Math.max(0, n - 1));
    } catch (e) {
      trocarNaLista(transacao.id, antiga);
      if (eBloqueadoNaDemo(e)) return; // 423 da demo: a faixa já explica
      if (e instanceof SessaoExpirada) {
        tratarErro(e);
      } else {
        setErro("Não foi possível guardar a categoria. Tenta outra vez.");
      }
    }
  }

  return (
    <main className="p-4 sm:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-destaque">As tuas transações</p>
            <h1 className="text-2xl font-semibold text-texto">Movimentações</h1>
          </div>
          <div className="flex gap-2">
            <select
              value={mes}
              onChange={(e) => setMes(e.target.value)}
              aria-label="Mês"
              className="rounded-lg border border-borda bg-cartao px-3 py-2 text-sm text-texto"
            >
              {meses.map((m) => (
                <option key={m} value={m}>
                  {nomeMes(m)}
                </option>
              ))}
            </select>
            <BotaoImportar
              onImportado={aposImportar}
              onErro={(mensagem, erros) => {
                setSemPedidos(false);
                setSemPdf(false);
                setSoPlanosPagos(null);
                setAviso({ tipo: "erro", mensagem, erros });
              }}
              onSessaoExpirada={tratarErro}
              onLimiteDiario={() => {
                setAviso(null);
                setSemPdf(false);
                setSoPlanosPagos(null);
                setSemPedidos(true);
              }}
              onLimitePdf={() => {
                setAviso(null);
                setSemPedidos(false);
                setSoPlanosPagos(null);
                setSemPdf(true);
              }}
              onSoPlanosPagos={(mensagem) => {
                setAviso(null);
                setSemPedidos(false);
                setSemPdf(false);
                setSoPlanosPagos(mensagem);
              }}
              soCsv={soCsv}
              desligado={demo}
            />
            <button
              type="button"
              onClick={() => setFormAberto(true)}
              disabled={demo}
              aria-describedby={demo ? ID_NOTA_DEMO : undefined}
              className="rounded-lg bg-destaque px-4 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              + Nova movimentação
            </button>
          </div>
        </header>

        <NotaDemo />
        {soCsv && !demo && <p className="text-sm text-texto-suave">{TEXTOS_PLANO_PAGO.soCsv}</p>}
        {/* O que vai para a Anthropic ao importar: o PDF inteiro (só nos pagos); no CSV, só a descrição e o valor. */}
        {!demo && (
          <ul className="space-y-1 text-sm text-texto-suave">
            {!soCsv && <li>{TEXTOS_ENVIO_IA.pdf}</li>}
            <li>{TEXTOS_ENVIO_IA.csv}</li>
          </ul>
        )}

        {semCategoria > 0 && (
          <BotaoCategorizar
            quantas={semCategoria}
            desligado={demo}
            onCategorizadas={aposCategorizar}
            onErro={(mensagem) => {
              setSemPedidos(false);
              setSoPlanosPagos(null);
              setAviso({ tipo: "erro", mensagem, erros: [] });
            }}
            onSessaoExpirada={tratarErro}
            onLimiteDiario={() => {
              setAviso(null);
              setSoPlanosPagos(null);
              setSemPedidos(true);
            }}
          />
        )}

        {aviso && (
          <div
            className={`rounded-lg p-3 text-sm ${
              aviso.tipo === "sucesso"
                ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"
                : "bg-red-50 text-red-800 dark:bg-red-950/40 dark:text-red-200"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-medium">{aviso.mensagem}</p>
                {aviso.nota && <p className="mt-1">{aviso.nota}</p>}
              </div>
              <button type="button" onClick={() => setAviso(null)} aria-label="Fechar aviso" className="opacity-70 hover:opacity-100">
                ✕
              </button>
            </div>
            {aviso.erros.length > 0 && (
              <ul className="mt-2 list-disc space-y-0.5 pl-5">
                {aviso.erros.map((linha) => (
                  <li key={linha}>{linha}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {semPedidos && <AvisoLimite />}
        {semPdf && <AvisoLimitePdf />}
        {soPlanosPagos && <AvisoPlanoPago mensagem={soPlanosPagos} />}

        {formAberto && !demo && <FormNovaMovimentacao onCriada={aposCriar} onFechar={() => setFormAberto(false)} />}

        {aApagar && (
          <DialogoApagar
            key={aApagar.id}
            transacao={aApagar}
            onApagada={aposApagar}
            onFechar={() => setAApagar(null)}
            onSessaoExpirada={tratarErro}
          />
        )}

        {erro && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{erro}</p>}

        <section className="overflow-hidden rounded-xl border border-borda bg-cartao">
          {aCarregar && <p className="p-6 text-sm text-texto-suave">A carregar...</p>}
          {!aCarregar && transacoes.length === 0 && (
            <p className="p-6 text-sm text-texto-suave">Sem movimentações neste mês.</p>
          )}

          {transacoes.length > 0 && (
            // overflow-x-auto: no telemóvel a tabela desliza para o lado em vez de sair do ecrã.
            // relative: o "Ações" só para leitores de ecrã (sr-only, absolute) fica preso aqui e não alarga a página.
            <div className="relative overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-borda text-left text-xs text-texto-suave">
                    <th className="px-4 py-3 font-medium">Data</th>
                    <th className="px-4 py-3 font-medium">Descrição</th>
                    <th className="px-4 py-3 font-medium">Categoria</th>
                    <th className="px-4 py-3 font-medium">Método</th>
                    <th className="px-4 py-3 text-right font-medium">Valor</th>
                    <th className="px-2 py-3">
                      <span className="sr-only">Ações</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {transacoes.map((t) => (
                    <tr key={t.id} className="border-b border-borda last:border-0 hover:bg-fundo">
                      <td className="whitespace-nowrap px-4 py-3 tabular-nums text-texto-suave">{diaMes(t.data)}</td>
                      <td className="px-4 py-3 text-texto">{t.descricao}</td>
                      <td className="px-4 py-3">
                        {/* Caixa com ar de "pílula": mudar aqui corrige a categoria escolhida pela IA. */}
                        <select
                          value={t.categoria ?? ""}
                          onChange={(e) => mudarCategoria(t, e.target.value)}
                          disabled={demo}
                          aria-describedby={demo ? ID_NOTA_DEMO : undefined}
                          aria-label={`Categoria de ${t.descricao}`}
                          className="cursor-pointer rounded-full disabled:cursor-default disabled:hover:border-transparent border border-transparent bg-fundo px-2.5 py-1 text-xs capitalize text-texto-suave hover:border-borda"
                        >
                          {t.categoria === null && (
                            <option value="" disabled>
                              sem categoria
                            </option>
                          )}
                          {CATEGORIAS.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-texto-suave">
                        {t.metodo_pagamento ? METODOS_PAGAMENTO[t.metodo_pagamento] ?? t.metodo_pagamento : "—"}
                      </td>
                      {/* Entradas com "+" e a verde; o sinal garante que a cor não é a única pista. */}
                      <td
                        className={`whitespace-nowrap px-4 py-3 text-right font-medium tabular-nums ${
                          t.valor > 0 ? "text-destaque" : "text-texto"
                        }`}
                      >
                        {t.valor > 0 ? "+" : ""}
                        {euros(t.valor)}
                      </td>
                      <td className="px-2 py-1 text-right">
                        <button
                          type="button"
                          onClick={() => setAApagar(t)}
                          disabled={demo}
                          aria-label={preencher(TEXTOS_APAGAR_MOVIMENTO.rotuloBotao, {
                            descricao: t.descricao,
                            data: diaMes(t.data),
                            valor: euros(t.valor),
                          })}
                          aria-describedby={demo ? ID_NOTA_DEMO : undefined}
                          className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md px-2 text-xs font-medium text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent dark:text-red-300 dark:hover:bg-red-950/40"
                        >
                          {TEXTOS_APAGAR_MOVIMENTO.botao}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
