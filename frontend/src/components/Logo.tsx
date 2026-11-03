import Image from "next/image";

// As duas versões da logo vão para a página, e o CSS mostra só a do tema atual
// (dark:hidden / dark:block). Assim a logo muda junto com o tema, sem JavaScript.
export default function Logo({ altura = 36 }: { altura?: number }) {
  const largura = Math.round(altura * 3.4);
  return (
    <>
      <Image
        src="/logo-tema-claro.webp"
        alt="Control Prices"
        width={largura}
        height={altura}
        priority
        className="block dark:hidden"
      />
      <Image
        src="/logo-tema-escuro.webp"
        alt="Control Prices"
        width={largura}
        height={altura}
        priority
        className="hidden dark:block"
      />
    </>
  );
}
