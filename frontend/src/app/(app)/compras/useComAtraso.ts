import { useEffect, useState } from "react";

// O valor só muda depois de o utilizador parar de escrever (ex.: 350 ms), para não pedir à API a cada tecla.
export function useComAtraso<T>(valor: T, ms = 350): T {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const espera = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(espera);
  }, [valor, ms]);
  return atrasado;
}
