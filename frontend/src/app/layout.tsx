import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Corre antes de a página aparecer: aplica o tema guardado (ou o do sistema) sem "piscar" em claro.
const SCRIPT_TEMA = `try {
  var tema = localStorage.getItem("tema");
  var escuro = tema === "escuro" || (!tema && matchMedia("(prefers-color-scheme: dark)").matches);
  if (escuro) document.documentElement.classList.add("dark");
} catch (e) {}`;

export const metadata: Metadata = {
  title: "Control Prices",
  description: "Controlo financeiro pessoal com IA",
  // iPhone: o Safari não lê tudo do manifesto, por isso diz-se aqui que a app abre em ecrã inteiro.
  // O ícone do ecrã inicial vem do apple-icon.png (o Next.js encontra-o sozinho).
  appleWebApp: { capable: true, title: "Control Prices", statusBarStyle: "default" },
};

// A cor da barra de estado do telemóvel, igual ao fundo do menu em cada tema (globals.css).
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#161615" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pt"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
