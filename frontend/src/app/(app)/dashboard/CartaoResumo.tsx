// Um cartão de resumo: ícone, título, valor em euros e uma linha de explicação.
// O valor fica sempre na cor do texto; a cor do ícone só identifica o tipo de cartão.
import { euros } from "./formatos";

type Props = { titulo: string; valor: number; descricao: string; icone: string; corIcone: string };

export default function CartaoResumo({ titulo, valor, descricao, icone, corIcone }: Props) {
  return (
    <div className="rounded-xl border border-borda bg-cartao p-4">
      <span
        className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg"
        style={{ background: `color-mix(in srgb, ${corIcone} 15%, transparent)`, color: corIcone }}
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
          <path d={icone} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <p className="text-xs text-texto-suave">{titulo}</p>
      <p className="mt-1 text-xl font-semibold text-texto">{euros(valor)}</p>
      <p className="mt-1 text-xs text-texto-suave">{descricao}</p>
    </div>
  );
}
