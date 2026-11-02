import { redirect } from "next/navigation";

// A página inicial não tem conteúdo próprio: manda logo para o login.
export default function PaginaInicial() {
  redirect("/login");
}
