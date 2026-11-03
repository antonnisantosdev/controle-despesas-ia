"use client";

import { useState, type FormEvent } from "react";

import { pedirApi, SessaoExpirada, type RespostaChat } from "@/lib/api";

type Mensagem = { autor: "tu" | "ia"; texto: string };

const EXEMPLOS = ["Quanto gastei em restaurantes em outubro?", "Em que gastei mais este mês?"];

export default function Chat() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [aPensar, setAPensar] = useState(false);
  const [erro, setErro] = useState("");

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const texto = pergunta.trim();
    if (!texto || aPensar) return;

    setMensagens((m) => [...m, { autor: "tu", texto }]);
    setPergunta("");
    setAPensar(true);
    setErro("");

    try {
      const resposta = await pedirApi<RespostaChat>("/chat", { pergunta: texto });
      setMensagens((m) => [...m, { autor: "ia", texto: resposta.resposta }]);
    } catch (e) {
      if (e instanceof SessaoExpirada) {
        setErro("A tua sessão expirou. Faz login de novo.");
      } else {
        console.error(e);
        setErro("O chat falhou. Tenta mais tarde.");
      }
    } finally {
      setAPensar(false);
    }
  }

  return (
    <section className="rounded-xl bg-white p-4 shadow sm:p-6">
      <h2 className="mb-4 font-medium text-gray-900">Pergunta às tuas finanças</h2>

      <div className="mb-4 max-h-80 space-y-3 overflow-y-auto">
        {mensagens.length === 0 && (
          <p className="text-sm text-gray-500">Experimenta: {EXEMPLOS.map((e) => `"${e}"`).join(" ou ")}</p>
        )}
        {mensagens.map((m, i) => (
          <div key={i} className={m.autor === "tu" ? "flex justify-end" : "flex justify-start"}>
            <p
              className={
                m.autor === "tu"
                  ? "max-w-[85%] rounded-lg bg-gray-900 px-3 py-2 text-sm text-white"
                  : "max-w-[85%] whitespace-pre-line rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900"
              }
            >
              {m.texto}
            </p>
          </div>
        ))}
        {aPensar && <p className="text-sm text-gray-500">A consultar os teus dados...</p>}
      </div>

      {erro && <p className="mb-3 text-sm text-red-600">{erro}</p>}

      <form onSubmit={enviar} className="flex gap-2">
        <input
          value={pergunta}
          onChange={(e) => setPergunta(e.target.value)}
          maxLength={500}
          placeholder="Escreve uma pergunta..."
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900"
        />
        <button
          type="submit"
          disabled={aPensar}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </section>
  );
}
