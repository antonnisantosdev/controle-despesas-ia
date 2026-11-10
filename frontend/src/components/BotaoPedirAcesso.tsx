"use client";

import { CONTACTOS, linkEmail, linkWhatsapp, type Pedido } from "@/lib/planos";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

type Props = {
  pedido: Pedido;
  rotulo: string; // "Pedir acesso" ou "Pedir renovação"
  principal?: boolean; // botão cheio (cor de destaque) ou só com contorno
};

// min-h-11 = 44 px (alvo de toque). Foco visível ao navegar com o teclado.
// No tema escuro o verde é claro, por isso o texto passa a escuro (text-fundo) para ter contraste.
const FOCO = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque";
const ESTILO_BASE = `flex min-h-11 w-full items-center justify-center rounded-md px-4 py-2 text-center text-sm font-semibold transition-colors ${FOCO}`;
const ESTILO_PRINCIPAL = `${ESTILO_BASE} bg-destaque text-white hover:bg-destaque-hover dark:text-fundo`;
const ESTILO_SECUNDARIO = `${ESTILO_BASE} border border-borda text-texto hover:bg-fundo`;
// Desativado sem opacidade: continua legível, mas claramente sem ação.
const ESTILO_DESATIVADO = `${ESTILO_BASE} cursor-not-allowed border border-dashed border-borda bg-fundo text-texto-suave`;

// Abre o WhatsApp (ou o email) com a mensagem do pedido já escrita. Os contactos vêm do .env.local:
// com os dois, o WhatsApp é o botão e o email fica como alternativa; sem nenhum, o botão fica desativado.
// Numa sessão de demo não aparece: a conta é partilhada e não muda de plano.
export default function BotaoPedirAcesso({ pedido, rotulo, principal = true }: Props) {
  const demo = useSessaoDemo();
  const estilo = principal ? ESTILO_PRINCIPAL : ESTILO_SECUNDARIO;
  const { whatsapp, email } = CONTACTOS;

  if (demo) return null;

  if (!whatsapp && !email) {
    return (
      <div className="space-y-1">
        <button type="button" disabled className={ESTILO_DESATIVADO}>
          {rotulo}
        </button>
        <p className="text-center text-xs text-texto-suave">Contacto ainda não disponível.</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {whatsapp ? (
        // O WhatsApp abre noutro separador; o mailto abre o programa de email, sem separador novo.
        <a href={linkWhatsapp(whatsapp, pedido)} target="_blank" rel="noopener noreferrer" className={estilo}>
          {rotulo}
        </a>
      ) : (
        email && (
          <a href={linkEmail(email, pedido)} className={estilo}>
            {rotulo}
          </a>
        )
      )}
      {whatsapp && email && (
        <a
          href={linkEmail(email, pedido)}
          className={`flex min-h-11 items-center justify-center rounded-md text-center text-xs text-texto-suave hover:text-texto hover:underline ${FOCO}`}
        >
          ou por email
        </a>
      )}
    </div>
  );
}
