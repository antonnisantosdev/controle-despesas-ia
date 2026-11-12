"use client";

import { useTextos } from "@/lib/textos";
import { DICIONARIO_DEMO } from "@/lib/textosDemo";
import { useSessaoDemo } from "@/lib/useSessaoDemo";

// O id da explicação: os botões desligados na demo apontam para ela com aria-describedby
// (o texto do botão continua a ser o nome acessível; a explicação é lida a seguir).
export const ID_NOTA_DEMO = "nota-demo";

// Explica, junto aos botões de alterar dados, porque estão desligados na demo. Fora da demo não aparece.
// Uma por página.
export default function NotaDemo() {
  const { TEXTOS_DEMO } = useTextos(DICIONARIO_DEMO);
  const demo = useSessaoDemo();
  if (!demo) return null;
  return (
    <p id={ID_NOTA_DEMO} className="text-sm text-texto-suave">
      {TEXTOS_DEMO.soLeitura}
    </p>
  );
}
