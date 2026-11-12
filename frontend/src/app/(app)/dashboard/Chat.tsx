"use client";

import { useState, type FormEvent } from "react";

import AvisoLimite from "@/components/AvisoLimite";
import AvisoQuota from "@/components/AvisoQuota";
import {
  eLimiteDiario,
  ErroApi,
  pedirApi,
  SessaoExpirada,
  type MensagemHistorico,
  type RespostaChat,
} from "@/lib/api";
import { useEstadoPlano, usePedidoPlano } from "@/lib/conta";
import { preencher } from "@/lib/planos";
import { useTextos } from "@/lib/textos";
import { DICIONARIO_COMUNS } from "@/lib/textosComuns";
import { DICIONARIO_DASHBOARD } from "@/lib/textosDashboard";
import { DICIONARIO_DEMO } from "@/lib/textosDemo";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

type Mensagem = { autor: "tu" | "ia"; texto: string };

// A IA às vezes marca palavras com **negrito** (markdown). Mostra-se como <strong>, sem HTML vindo da resposta:
// o texto é partido nos "**" e cada parte continua a ser texto simples, que o React escapa.
function comNegrito(texto: string) {
  return texto.split("**").map((parte, i) => (i % 2 === 1 ? <strong key={i}>{parte}</strong> : parte));
}

// Tetos do histórico que a API aceita (limites.py): cada pergunta, cada resposta e o total.
// Acima deles a API responde 422, por isso corta-se aqui antes de enviar.
const MAX_CARACTERES_PERGUNTA = 500;
const MAX_CARACTERES_RESPOSTA = 2000;
const MAX_CARACTERES_HISTORICO = 4000;

// As últimas perguntas com resposta, para a IA perceber perguntas como "e no mês anterior?".
// Quantas mensagens vão depende do plano (memoria_mensagens: 0 no Free). Só ficam no ecrã: não se guardam.
// Vão só pares inteiros (pergunta e resposta): uma pergunta que falhou (503, 429) fica de fora, e as
// mensagens de erro nunca entram (não estão na lista de mensagens). A API volta a cortar para o plano.
function historicoParaEnviar(mensagens: Mensagem[], maximo: number): MensagemHistorico[] {
  const pares: [string, string][] = [];
  mensagens.forEach((m, i) => {
    const seguinte = mensagens[i + 1];
    if (m.autor === "tu" && seguinte?.autor === "ia") {
      pares.push([m.texto.trim().slice(0, MAX_CARACTERES_PERGUNTA), seguinte.texto.trim().slice(0, MAX_CARACTERES_RESPOSTA)]);
    }
  });
  let escolhidos = maximo >= 2 ? pares.slice(-Math.floor(maximo / 2)) : [];
  // Os mais antigos saem primeiro até o total caber no teto.
  while (escolhidos.length > 0 && escolhidos.reduce((soma, [p, r]) => soma + p.length + r.length, 0) > MAX_CARACTERES_HISTORICO) {
    escolhidos = escolhidos.slice(1);
  }
  return escolhidos.flatMap(([pergunta, resposta]): MensagemHistorico[] => [
    { papel: "utilizador", texto: pergunta },
    { papel: "ia", texto: resposta },
  ]);
}

// "a", "b" ou "c": vírgulas entre os exemplos e "ou" só antes do último (ou: TEXTOS_CHAT.ou, do país da conta).
function juntarExemplos(exemplos: readonly string[], ou: string): string {
  const comAspas = exemplos.map((e) => `"${e}"`);
  if (comAspas.length < 2) return comAspas.join("");
  return `${comAspas.slice(0, -1).join(", ")} ${ou} ${comAspas[comAspas.length - 1]}`;
}

export default function Chat() {
  const { TEXTOS_GERAIS } = useTextos(DICIONARIO_COMUNS);
  const { TEXTOS_CHAT } = useTextos(DICIONARIO_DASHBOARD);
  const { TEXTOS_DEMO } = useTextos(DICIONARIO_DEMO);
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [aPensar, setAPensar] = useState(false);
  const [erro, setErro] = useState("");
  const [semPedidos, setSemPedidos] = useState(false); // 429: chegou ao limite de pedidos à IA
  const [detalheLimite, setDetalheLimite] = useState<string | undefined>(); // o texto do 429 que a API mandou
  // Os pedidos à IA já usados, para o aviso dos 80%: o /plano do ProvedorConta (sem pedido próprio),
  // pedido outra vez depois de cada pergunta. Sem o estado, o aviso não aparece (o chat funciona na mesma).
  const estado = useEstadoPlano();
  const { atualizar: atualizarPlano } = usePedidoPlano();
  // Na demo: a nota das 5 perguntas por dia em vez do aviso dos pedidos do plano (que são partilhados).
  const demo = useSessaoDemo();

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const texto = pergunta.trim();
    if (!texto || aPensar) return;

    // O histórico é o que estava no ecrã antes desta pergunta (a pergunta vai à parte).
    const historico = historicoParaEnviar(mensagens, estado?.memoria_mensagens ?? 0);
    setMensagens((m) => [...m, { autor: "tu", texto }]);
    setPergunta("");
    setAPensar(true);
    setErro("");
    setSemPedidos(false);

    try {
      const resposta = await pedirApi<RespostaChat>("/chat", { pergunta: texto, historico });
      setMensagens((m) => [...m, { autor: "ia", texto: resposta.resposta }]);
    } catch (e) {
      if (e instanceof SessaoExpirada) {
        setErro(TEXTOS_GERAIS.sessaoExpirou);
      } else if (eLimiteDiario(e)) {
        // Limite diário: o AvisoLimite explica e leva ao "O meu plano". Na demo mostra o texto da API.
        setDetalheLimite(e instanceof ErroApi && typeof e.detalhe === "string" ? e.detalhe : undefined);
        setSemPedidos(true);
      } else {
        console.error(e);
        setErro(TEXTOS_CHAT.erro);
      }
    } finally {
      setAPensar(false);
      atualizarPlano();
    }
  }

  return (
    <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <h2 className="mb-4 font-medium text-texto">{TEXTOS_CHAT.titulo}</h2>

      {demo && <p className="mb-4 text-sm text-texto-suave">{TEXTOS_DEMO.notaChat}</p>}

      {/* No limite já aparece o AvisoLimite; os dois juntos seriam repetidos. */}
      {!semPedidos && !demo && (
        <div className="mb-4 empty:hidden">
          <AvisoQuota estado={estado} />
        </div>
      )}

      <div className="mb-4 max-h-80 space-y-3 overflow-y-auto">
        {mensagens.length === 0 && (
          <p className="text-sm text-texto-suave">
            {preencher(TEXTOS_CHAT.experimenta, { exemplos: juntarExemplos(TEXTOS_CHAT.exemplos, TEXTOS_CHAT.ou) })}
          </p>
        )}
        {mensagens.map((m, i) => (
          <div key={i} className={m.autor === "tu" ? "flex justify-end" : "flex justify-start"}>
            <p
              className={
                m.autor === "tu"
                  ? "max-w-[85%] rounded-lg bg-destaque px-3 py-2 text-sm text-white"
                  : "max-w-[85%] whitespace-pre-line rounded-lg bg-fundo px-3 py-2 text-sm text-texto"
              }
            >
              {m.autor === "ia" ? comNegrito(m.texto) : m.texto}
            </p>
          </div>
        ))}
        {aPensar && <p className="text-sm text-texto-suave">{TEXTOS_CHAT.aPensar}</p>}
      </div>

      {erro && <p className="mb-3 text-sm text-red-600 dark:text-red-400">{erro}</p>}
      {semPedidos && (
        <div className="mb-3">
          <AvisoLimite mensagem={detalheLimite} />
        </div>
      )}

      <form onSubmit={enviar} className="flex gap-2">
        <input
          value={pergunta}
          onChange={(e) => setPergunta(e.target.value)}
          maxLength={500}
          placeholder={TEXTOS_CHAT.marcador}
          className="flex-1 rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto"
        />
        <button
          type="submit"
          disabled={aPensar}
          className="rounded-md bg-destaque px-4 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
        >
          {TEXTOS_CHAT.enviar}
        </button>
      </form>
    </section>
  );
}
