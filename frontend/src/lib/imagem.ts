// Reduz uma fotografia antes de a enviar à API.
// Uma foto de telemóvel tem 3 a 8 MB, e a API só aceita até 5 MB. Para ler um talão,
// 1600 píxeis no lado maior chegam, e o envio fica muito mais rápido.

const LADO_MAXIMO = 1600;

export async function reduzirImagem(ficheiro: File): Promise<File> {
  // createImageBitmap abre a imagem (JPEG, PNG, WEBP...) e já a roda conforme a orientação da câmara.
  const imagem = await createImageBitmap(ficheiro);
  const escala = Math.min(1, LADO_MAXIMO / Math.max(imagem.width, imagem.height));
  const largura = Math.round(imagem.width * escala);
  const altura = Math.round(imagem.height * escala);

  // Um <canvas> invisível: desenha-se a imagem mais pequena e exporta-se como JPEG.
  const canvas = document.createElement("canvas");
  canvas.width = largura;
  canvas.height = altura;
  canvas.getContext("2d")?.drawImage(imagem, 0, 0, largura, altura);
  imagem.close();

  const blob = await new Promise<Blob | null>((resolver) => canvas.toBlob(resolver, "image/jpeg", 0.85));
  if (!blob) return ficheiro; // se o browser não conseguir, envia-se a original (a API avisa se for grande)
  return new File([blob], "talao.jpg", { type: "image/jpeg" });
}
