import type { MetadataRoute } from "next";

import { TEXTOS_APP } from "@/lib/textosComuns";

// O manifesto da PWA: o que o telemóvel lê para "instalar" o site como uma app.
// O Next.js serve-o em /manifest.webmanifest e põe a ligação no <head> de todas as páginas.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: TEXTOS_APP.nome,
    short_name: TEXTOS_APP.nome, // 14 letras: cabe debaixo do ícone na maioria dos telemóveis
    description: TEXTOS_APP.descricao,
    // Abre direto no resumo. Com a sessão expirada, a página manda para o login sozinha.
    // ("/" mandava sempre para o login, mesmo a quem já tinha sessão.)
    start_url: "/dashboard",
    display: "standalone",
    // Ecrã de arranque com o verde dos ícones (--destaque no globals.css), para o ícone e o arranque combinarem.
    background_color: "#059669",
    // A cor da barra de estado. Depois de a página abrir, o themeColor do layout.tsx troca-a pela do tema.
    theme_color: "#059669",

    // Os ícones têm o recibo da logo no centro, com margem: "maskable" deixa o Android
    // cortá-los em círculo ou quadrado arredondado sem cortar o desenho.
    icons: [
      { src: "/icone-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icone-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icone-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
