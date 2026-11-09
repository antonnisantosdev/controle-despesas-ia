"use client";

import { useEffect, useState, type FormEvent } from "react";

import AvisoLimite from "@/components/AvisoLimite";
import AvisoQuota from "@/components/AvisoQuota";
import { eLimiteDiario, pedirApi, pedirEstadoPlano, SessaoExpirada, type EstadoPlano, type RespostaChat } from "@/lib/api";

type Mensagem = { autor: "tu" | "ia"; texto: string };

const EXEMPLOS = ["Quanto gastei em restaurantes em outubro?", "Em que gastei mais este mês?"];

export default function Chat() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [aPensar, setAPensar] = useState(false);
  const [erro, setErro] = useState("");
  const [semPedidos, setSemPedidos] = useState(false); // 429: chegou ao limite de pedidos à IA
  // Os pedidos à IA já usados, para o aviso dos 80%. Volta a ser pedido depois de cada pergunta.
  const [estado, setEstado] = useState<EstadoPlano | null>(null);
  const [perguntasFeitas, setPerguntasFeitas] = useState(0);

  useEffect(() => {
    pedirEstadoPlano()
      .then(setEstado)
      .catch(() => setEstado(null)); // sem o estado, o aviso não aparece (o chat funciona na mesma)
  }, [perguntasFeitas]);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const texto = pergunta.trim();
    if (!texto || aPensar) return;

    setMensagens((m) => [...m, { autor: "tu", texto }]);
    setPergunta("");
    setAPensar(true);
    setErro("");
    setSemPedidos(false);

    try {
      const resposta = await pedirApi<RespostaChat>("/chat", { pergunta: texto });
      setMensagens((m) => [...m, { autor: "ia", texto: resposta.resposta }]);
    } catch (e) {
      if (e instanceof SessaoExpirada) {
        setErro("A tua sessão expirou. Faz login de novo.");
      } else if (eLimiteDiario(e)) {
        // Limite diário: o AvisoLimite explica e leva ao "O meu plano".
        setSemPedidos(true);
      } else {
        console.error(e);
        setErro("O chat falhou. Tenta mais tarde.");
      }
    } finally {
      setAPensar(false);
      setPerguntasFeitas((n) => n + 1);
    }
  }

  return (
    <section className="rounded-xl border border-borda bg-cartao p-4 sm:p-6">
      <h2 className="mb-4 font-medium text-texto">Pergunta às tuas finanças</h2>

      {/* No limite já aparece o AvisoLimite; os dois juntos seriam repetidos. */}
      {!semPedidos && (
        <div className="mb-4 empty:hidden">
          <AvisoQuota estado={estado} />
        </div>
      )}

      <div className="mb-4 max-h-80 space-y-3 overflow-y-auto">
        {mensagens.length === 0 && (
          <p className="text-sm text-texto-suave">Experimenta: {EXEMPLOS.map((e) => `"${e}"`).join(" ou ")}</p>
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
              {m.texto}
            </p>
          </div>
        ))}
        {aPensar && <p className="text-sm text-texto-suave">A consultar os teus dados...</p>}
      </div>

      {erro && <p className="mb-3 text-sm text-red-600 dark:text-red-400">{erro}</p>}
      {semPedidos && (
        <div className="mb-3">
          <AvisoLimite />
        </div>
      )}

      <form onSubmit={enviar} className="flex gap-2">
        <input
          value={pergunta}
          onChange={(e) => setPergunta(e.target.value)}
          maxLength={500}
          placeholder="Escreve uma pergunta..."
          className="flex-1 rounded-md border border-borda bg-cartao px-3 py-2 text-sm text-texto"
        />
        <button
          type="submit"
          disabled={aPensar}
          className="rounded-md bg-destaque px-4 py-2 text-sm font-medium text-white hover:bg-destaque-hover disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </section>
  );
}
