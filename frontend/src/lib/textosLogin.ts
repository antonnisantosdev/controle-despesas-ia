// Textos do login com o Google (botão no login e no registo, e a página /login/google).
// Os marcados com "TEXTO NOVO" ainda não foram revistos pelo copywriter.

export const TEXTOS_GOOGLE = {
  botao: "Continuar com Google", // TEXTO NOVO
  aAbrir: "A abrir o Google...", // TEXTO NOVO
  separador: "ou", // TEXTO NOVO
  // Quando nem se consegue pedir à API o endereço do login (servidor em baixo, sem rede).
  erroAbrir: "Não foi possível abrir o login com o Google. Tenta outra vez daqui a um minuto.", // TEXTO NOVO
  // Na página /login/google, enquanto se guarda o token e se muda para o dashboard.
  aEntrar: "A entrar...", // TEXTO NOVO
  erroEntrar: "Não foi possível entrar com o Google. Tenta outra vez.", // TEXTO NOVO
  voltarLogin: "Voltar ao login", // TEXTO NOVO
};

// Registo e login com o Google: aceitar os termos ao criar conta (sem caixa obrigatória). Texto aprovado pelo CEO.
// As páginas /termos e /privacidade ainda estão a ser escritas.
export const TEXTOS_TERMOS = {
  antes: "Ao criar conta, aceitas os ",
  termos: "Termos de Utilização",
  meio: " e a ",
  privacidade: "Política de Privacidade",
  fim: ".",
};
