"use client";

import { useState } from "react";

import { ID_NOTA_DEMO } from "@/components/NotaDemo";
import { eBloqueadoNaDemo, ErroApi, eSoPlanosPagos, pedirApi, SessaoExpirada, type JuncaoProdutos } from "@/lib/api";
import { useFormatos } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { TEXTOS_PRECOS_LOJAS as T } from "@/lib/textosPrecosLojas";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

import { ESTILO_BOTAO, ESTILO_BOTAO_PRINCIPAL, ESTILO_ERRO, ESTILO_SUCESSO } from "./formatosPrecos";

type Props = {
  juncoes: JuncaoProdutos[];
  onMudou: () => void; // desfez uma junção: lista, junções e detalhe são pedidos outra vez
  onPlanoPago: (mensagem: string) => void;
  onSessaoExpirada: (e: unknown) => void;
};

type Mensagem = { tipo: "sucesso" | "erro"; texto: string } | null;

// As junções ("origem → destino"), cada uma com "Desfazer" e confirmação no próprio ecrã.
// Na demo o botão fica desligado (a API responderia 423) e a NotaDemo do topo explica porquê.
export default function ListaJuncoes({ juncoes, onMudou, onPlanoPago, onSessaoExpirada }: Props) {
  const demo = useSessaoDemo();
  const f = useFormatos();
  const [aConfirmar, setAConfirmar] = useState<string | null>(null); // chave_origem
  const [aEnviar, setAEnviar] = useState(false);
  const [mensagem, setMensagem] = useState<Mensagem>(null);

  async function desfazer(juncao: JuncaoProdutos) {
    setAEnviar(true);
    setMensagem(null);
    try {
      await pedirApi<void>(`/compras/produtos/juntar/${encodeURIComponent(juncao.chave_origem)}`, undefined, "DELETE");
      setMensagem({ tipo: "sucesso", texto: preencher(T.desfeito, { nome: juncao.nome_origem }) });
      onMudou();
    } catch (e) {
      if (e instanceof SessaoExpirada) onSessaoExpirada(e);
      else if (eBloqueadoNaDemo(e)) return; // a faixa da demo já explica
      else if (eSoPlanosPagos(e)) onPlanoPago(typeof e.detalhe === "string" ? e.detalhe : T.soPlanosPagos);
      else {
        // 404: já não existe (ex.: desfeita noutro separador). Mostra a explicação e atualiza a lista.
        const texto = e instanceof ErroApi && typeof e.detalhe === "string" ? e.detalhe : T.erroDesfazer;
        setMensagem({ tipo: "erro", texto });
        if (e instanceof ErroApi && e.status === 404) onMudou();
      }
    } finally {
      setAEnviar(false);
      setAConfirmar(null);
    }
  }

  return (
    <div className="space-y-2">
      <div aria-live="polite">
        {mensagem && <p className={mensagem.tipo === "erro" ? ESTILO_ERRO : ESTILO_SUCESSO}>{mensagem.texto}</p>}
      </div>
      {juncoes.length > 0 && (
        <ul className="divide-y divide-borda text-sm">
          {juncoes.map((j) => (
            <li key={j.chave_origem} className="space-y-2 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="min-w-0 break-words text-texto">
                  <span className="sr-only">{preencher(T.rotuloJuncao, { origem: j.nome_origem, destino: j.nome_destino })}</span>
                  <span aria-hidden="true">
                    {j.nome_origem} <span className="text-texto-suave">→</span> {j.nome_destino}
                  </span>
                  <span className="block text-xs text-texto-suave">
                    {preencher(T.juntadoEm, { data: f.data(j.criado_em) })}
                  </span>
                </p>
                {aConfirmar !== j.chave_origem && (
                  <button
                    type="button"
                    disabled={aEnviar || demo}
                    aria-describedby={demo ? ID_NOTA_DEMO : undefined}
                    aria-label={preencher(T.desfazerRotulo, { nome: j.nome_origem })}
                    onClick={() => {
                      setMensagem(null);
                      setAConfirmar(j.chave_origem);
                    }}
                    className={ESTILO_BOTAO}
                  >
                    {T.desfazer}
                  </button>
                )}
              </div>
              {aConfirmar === j.chave_origem && (
                <div
                  role="alert"
                  className="space-y-3 rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/40"
                >
                  <p className="break-words text-amber-900 dark:text-amber-200">
                    {preencher(T.desfazerConfirmar, { origem: j.nome_origem, destino: j.nome_destino })}
                  </p>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <button type="button" disabled={aEnviar} onClick={() => desfazer(j)} className={ESTILO_BOTAO_PRINCIPAL}>
                      {aEnviar ? T.aDesfazer : T.desfazerSim}
                    </button>
                    <button type="button" disabled={aEnviar} onClick={() => setAConfirmar(null)} className={ESTILO_BOTAO}>
                      {T.juntarNao}
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
