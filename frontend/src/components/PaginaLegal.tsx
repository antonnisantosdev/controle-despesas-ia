import Link from "next/link";

import DocumentoLegal from "@/components/DocumentoLegal";
import Logo from "@/components/Logo";
import RodapeLegal from "@/components/RodapeLegal";

// Moldura das páginas /termos e /privacidade: públicas (sem login), sem pedidos à API.
export default function PaginaLegal({ markdown }: { markdown: string }) {
  return (
    <main className="flex-1 bg-fundo px-4 py-6 sm:py-10">
      <div className="mx-auto max-w-3xl space-y-6">
        <Link
          href="/login"
          className="inline-flex rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destaque"
        >
          <Logo altura={36} />
        </Link>
        <div className="rounded-xl border border-borda bg-cartao p-4 sm:p-8">
          <DocumentoLegal markdown={markdown} />
        </div>
        <RodapeLegal />
      </div>
    </main>
  );
}
