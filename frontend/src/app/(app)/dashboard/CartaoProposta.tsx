"use client";

import { useEffect, useRef, useState } from "react";

import DialogoApagar from "@/app/(app)/movimentacoes/DialogoApagar";
import {
  ErroApi,
  mensagemDaApi,
  pedirApi,
  SessaoExpirada,
  type MovimentoNaProposta,
  type PropostaChat,
  type Transacao,
} from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { useOpcoes, useTextos } from "@/lib/textos";
import { DICIONARIO_COMUNS } from "@/lib/textosComuns";
import { DICIONARIO_DASHBOARD } from "@/lib/textosDashboard";

type Props = {
  proposta: PropostaChat;
  onFeito: () => void; // gravou: a página volta a pedir os dados
};

// pendente: à espera da pessoa. erro: falhou mas pode tentar outra vez. Os outros três são finais (sem botões).
type Estado = "pendente" | "a-gravar" | "erro" | "feito" | "cancelado" | "nao-existe";
const FINAIS: readonly Estado[] = ["feito", "cancelado", "nao-existe"];

// A proposta só é gravada aqui, quando a pessoa carrega em "Confirmar" (rotas de sempre, sem IA).
// Os textos do cartão vêm dos campos validados pela API (e, para alterar e apagar, lidos da base de dados).
export default function CartaoProposta({ proposta, onFeito }: Props) {
  const { TEXTOS_PROPOSTAS } = useTextos(DICIONARIO_DASHBOARD);
  const { TEXTOS_GERAIS } = useTextos(DICIONARIO_COMUNS);
  const f = useFormatos();
  const { nomeCategoria, rotuloMetodo } = useOpcoes();
  const [estado, setEstado] = useState<Estado>("pendente");
  const [resultado, setResultado] = useState("");
  const [dialogoAberto, setDialogoAberto] = useState(false);
  // O foco vai para o resultado quando os botões desaparecem (quem usa o teclado não fica perdido).
  const refResultado = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (FINAIS.includes(estado)) refResultado.current?.focus();
  }, [estado]);

  const { movimento, nova, alteracao } = proposta;

  function base(m: { descricao: string; data: string; valor: number }) {
    return { descricao: m.descricao, data: f.data(m.data), valor: f.dinheiro(m.valor) };
  }

  function categoria(chave: string | null | undefined) {
    return chave ? nomeCategoria(chave) : TEXTOS_PROPOSTAS.semCategoria;
  }

  // As frases do cartão: o que vai mudar.
  function frases(): string[] {
    if (proposta.tipo === "criar" && nova) {
      const linhas = [
        preencher(TEXTOS_PROPOSTAS.criar, {
          ...base(nova),
          // Sem categoria grava-se "outros" (ver o Confirmar): o cartão mostra o que vai mesmo ficar gravado.
          categoria: categoria(nova.categoria ?? "outros"),
          metodo: rotuloMetodo(nova.metodo_pagamento),
        }),
      ];
      if (nova.nota) linhas.push(preencher(TEXTOS_PROPOSTAS.criarNota, { nota: nova.nota }));
      return linhas;
    }
    if (proposta.tipo === "alterar" && movimento && alteracao) {
      const linhas: string[] = [];
      if (alteracao.categoria) {
        linhas.push(
          preencher(TEXTOS_PROPOSTAS.mudarCategoria, {
            ...base(movimento),
            de: categoria(movimento.categoria),
            para: categoria(alteracao.categoria),
          }),
        );
      }
      if (alteracao.muda_nota) {
        linhas.push(
          alteracao.nota
            ? preencher(TEXTOS_PROPOSTAS.mudarNota, { ...base(movimento), nota: alteracao.nota })
            : preencher(TEXTOS_PROPOSTAS.apagarNota, base(movimento)),
        );
      }
      return linhas;
    }
    if (proposta.tipo === "apagar" && movimento) return [preencher(TEXTOS_PROPOSTAS.apagar, base(movimento))];
    return [];
  }

  function terminar(final: "feito" | "cancelado" | "nao-existe") {
    const textos = { feito: TEXTOS_PROPOSTAS.feito, cancelado: TEXTOS_PROPOSTAS.cancelado, "nao-existe": TEXTOS_PROPOSTAS.naoExiste };
    setResultado(textos[final]);
    setEstado(final);
    if (final === "feito") onFeito();
  }

  function tratarErro(e: unknown) {
    if (e instanceof SessaoExpirada) {
      setDialogoAberto(false); // o diálogo de apagar tapava a mensagem
      setResultado(TEXTOS_GERAIS.sessaoExpirou);
      setEstado("erro");
    } else if (e instanceof ErroApi && e.status === 404) {
      terminar("nao-existe");
    } else {
      if (!(e instanceof ErroApi)) console.error(e);
      // 422 com texto da API (ex. conta cheia, método de outro país); o resto, a mensagem genérica.
      // 503 com texto (ex. notas ainda indisponíveis, nada foi alterado): mostra-se o texto da API.
      const texto503 = e instanceof ErroApi && e.status === 503 && typeof e.detalhe === "string" ? e.detalhe : null;
      setResultado(texto503 ?? mensagemDaApi(e, TEXTOS_PROPOSTAS.erro));
      setEstado("erro");
    }
  }

  async function gravar() {
    setEstado("a-gravar");
    setResultado("");
    try {
      if (proposta.tipo === "criar" && nova) {
        // Com a categoria preenchida: a API não chama a IA para categorizar.
        await pedirApi<Transacao>("/transacoes", {
          data: nova.data,
          descricao: nova.descricao,
          valor: nova.valor,
          metodo_pagamento: nova.metodo_pagamento,
          categoria: nova.categoria ?? "outros",
          ...(nova.nota ? { nota: nova.nota } : {}),
        });
      } else if (proposta.tipo === "alterar" && movimento && alteracao) {
        await pedirApi<Transacao>(
          `/transacoes/${movimento.id}`,
          {
            ...(alteracao.categoria ? { categoria: alteracao.categoria } : {}),
            ...(alteracao.muda_nota ? { nota: alteracao.nota ?? "" } : {}),
          },
          "PATCH",
        );
      } else {
        return;
      }
      terminar("feito");
    } catch (e) {
      tratarErro(e);
    }
  }

  function confirmar() {
    // Apagar pede sempre uma segunda confirmação explícita (o mesmo diálogo das Movimentações).
    if (proposta.tipo === "apagar") setDialogoAberto(true);
    else void gravar();
  }

  function paraTransacao(m: MovimentoNaProposta): Transacao {
    return {
      id: m.id,
      data: m.data,
      descricao: m.descricao,
      valor: m.valor,
      categoria: m.categoria,
      metodo_pagamento: m.metodo_pagamento ?? null,
      nota: m.nota ?? null,
    };
  }

  const linhas = frases();
  if (linhas.length === 0) return null; // proposta incompleta (não devia acontecer): não se mostra nada

  const comBotoes = estado === "pendente" || estado === "a-gravar" || estado === "erro";

  return (
    <div
      role="group"
      aria-label={TEXTOS_PROPOSTAS.rotulo}
      className="max-w-[85%] rounded-lg border border-borda bg-cartao px-3 py-2 text-sm text-texto"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-destaque">{TEXTOS_PROPOSTAS.rotulo}</p>
      {linhas.map((linha, i) => (
        <p key={i} className="mt-1 break-words">
          {linha}
        </p>
      ))}

      {comBotoes && (
        <>
          <p className="mt-1 text-xs text-texto-suave">{TEXTOS_PROPOSTAS.aviso}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={confirmar}
              disabled={estado === "a-gravar"}
              className={`min-h-11 rounded-md px-4 py-2 text-sm font-medium text-white focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
                proposta.tipo === "apagar"
                  ? "bg-red-600 hover:bg-red-700 focus-visible:outline-red-600"
                  : "bg-destaque hover:bg-destaque-hover focus-visible:outline-destaque dark:text-fundo"
              }`}
            >
              {estado === "a-gravar" ? TEXTOS_PROPOSTAS.aGravar : TEXTOS_PROPOSTAS.confirmar}
            </button>
            <button
              type="button"
              onClick={() => terminar("cancelado")}
              disabled={estado === "a-gravar"}
              className="min-h-11 rounded-md border border-borda bg-cartao px-4 py-2 text-sm font-medium text-texto hover:bg-fundo focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque disabled:cursor-not-allowed disabled:opacity-50"
            >
              {TEXTOS_PROPOSTAS.cancelar}
            </button>
          </div>
        </>
      )}

      {/* aria-live: o resultado (Feito, Cancelado ou o erro) é lido sem mudar de sítio. */}
      <p
        ref={refResultado}
        tabIndex={-1}
        aria-live="polite"
        className={`mt-2 empty:hidden focus:outline-none ${
          estado === "erro" || estado === "nao-existe"
            ? "text-red-600 dark:text-red-400"
            : estado === "feito"
              ? "font-medium text-emerald-700 dark:text-emerald-400"
              : "text-texto-suave"
        }`}
      >
        {resultado}
      </p>

      {dialogoAberto && movimento && (
        <DialogoApagar
          transacao={paraTransacao(movimento)}
          onApagada={() => terminar("feito")}
          onNaoEncontrada={() => terminar("nao-existe")}
          onFechar={() => setDialogoAberto(false)}
          onSessaoExpirada={tratarErro}
        />
      )}
    </div>
  );
}
