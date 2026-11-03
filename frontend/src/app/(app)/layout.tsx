import MenuLateral from "./MenuLateral";

// Moldura das páginas da app (depois do login): menu à esquerda, página à direita.
// O menu não volta a ser desenhado quando se muda de página, só o conteúdo.
export default function LayoutApp({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col md:flex-row">
      <MenuLateral />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
