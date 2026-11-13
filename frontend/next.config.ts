import type { NextConfig } from "next";

const emDesenvolvimento = process.env.NODE_ENV !== "production";

// Origem da API (ex. https://api.exemplo.com). O mesmo valor por omissão de src/lib/api.ts,
// para a CSP deixar passar exatamente o endereço que o browser vai chamar.
// Em produção a variável é obrigatória: sem ela o build falha (melhor do que uma CSP que bloqueia a API).
// Em dev, se faltar, usa-se o valor por omissão.
function origemDaApi(): string {
  const omissao = "http://127.0.0.1:8000";
  const valor = process.env.NEXT_PUBLIC_API_URL;
  try {
    return new URL(valor ?? omissao).origin;
  } catch {
    if (!emDesenvolvimento) throw new Error("NEXT_PUBLIC_API_URL inválida no build de produção.");
    return omissao;
  }
}
if (!emDesenvolvimento && !process.env.NEXT_PUBLIC_API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL em falta no build de produção.");
}

// Política de conteúdo: o que o browser pode carregar e de onde.
// Sem nonce de propósito: com cacheComponents as páginas ficam em cache e um nonce obrigaria a gerá-las a cada pedido.
const diretivasCsp = [
  "default-src 'self'",
  // 'unsafe-inline': o Next.js e o script do tema (layout.tsx) correm em linha. 'unsafe-eval' só em dev (HMR).
  `script-src 'self' 'unsafe-inline'${emDesenvolvimento ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self' ${origemDaApi()}${emDesenvolvimento ? " ws:" : ""}`,
  "manifest-src 'self'",
  "worker-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const cabecalhosDeSeguranca = [
  // A bloquear desde 2026-11-13 (esteve só a avisar desde 2026-11-10, sem avisos nas páginas públicas nem na app).
  // Se algo deixar de carregar, a consola do browser diz qual diretiva bloqueou.
  // Nota: nos deploys de pré-visualização da Vercel, a barra de comentários (vercel.live) fica bloqueada.
  { key: "Content-Security-Policy", value: diretivasCsp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // Os talões usam <input type="file" capture>, que não precisa desta permissão (não há getUserMedia).
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "X-Frame-Options", value: "DENY" },
  // Páginas abertas a partir da app não conseguem mexer na janela dela (o login Google é navegação, não popup).
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async headers() {
    return [{ source: "/:path*", headers: cabecalhosDeSeguranca }];
  },
};

export default nextConfig;
