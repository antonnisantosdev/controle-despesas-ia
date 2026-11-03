import type { Metadata } from "next";
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
