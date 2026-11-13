// Os links da IA (sites dos mercados e Google Maps) só se abrem se forem https://.
// Defesa extra: a API já os filtra, mas assim um "javascript:" ou "http:" nunca vira um link clicável.
export function linkSeguro(url: string | null | undefined): string | null {
  if (typeof url !== "string") return null;
  const limpo = url.trim();
  // "\\" é lido pelo browser como "/" (https://mau.site\.pingodoce.pt abre mau.site): recusa-se.
  if (!/^https:\/\//i.test(limpo) || limpo.includes("\\")) return null;
  try {
    const endereco = new URL(limpo);
    // Devolve o endereço tal como o browser o leu (href), nunca o texto original.
    return endereco.protocol === "https:" && !endereco.username && !endereco.password ? endereco.href : null;
  } catch {
    return null;
  }
}
