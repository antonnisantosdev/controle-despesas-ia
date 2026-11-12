import AvisoServidor from "@/components/AvisoServidor";
import FaixaDemo from "@/components/FaixaDemo";
import RodapeLegal from "@/components/RodapeLegal";
import { ProvedorConta } from "@/lib/conta";

import IrParaBoasVindas from "./IrParaBoasVindas";
import MenuLateral from "./MenuLateral";

// Moldura das páginas da app (depois do login): menu à esquerda, página à direita.
// O menu não volta a ser desenhado quando se muda de página, só o conteúdo.
// Numa sessão de demo, a faixa "Modo demo" fica por cima de tudo (fora da demo não aparece).
// O ProvedorConta pede o GET /plano a cada página: dá o país e a moeda (useFormatos) e o estado do plano
// (useEstadoPlano) a toda a app, sem cada componente fazer o seu pedido.
// Uma conta nova que ainda não fez o questionário de boas-vindas vai para /boas-vindas (IrParaBoasVindas).
export default function LayoutApp({ children }: { children: React.ReactNode }) {
  return (
    <ProvedorConta>
      <IrParaBoasVindas />
      <div className="flex flex-1 flex-col">
        <FaixaDemo />
        <div className="flex flex-1 flex-col md:flex-row">
          <MenuLateral />
          <div className="min-w-0 flex-1">
            {children}
            {/* No telemóvel, os links legais ficam no fundo da página; no computador estão no fundo do menu. */}
            <RodapeLegal className="pb-4 md:hidden print:hidden" />
          </div>
        </div>
        <AvisoServidor />
      </div>
    </ProvedorConta>
  );
}
