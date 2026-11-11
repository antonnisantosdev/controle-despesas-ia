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

// Página de login (email e palavra-passe). Os textos do Google e da demo estão em TEXTOS_GOOGLE e TEXTOS_DEMO.
export const TEXTOS_LOGIN = {
  erroCredenciais: "Email ou palavra-passe inválidas.",
  entrar: "Entrar",
  aEntrar: "A entrar...",
  semConta: "Ainda não tens conta?",
  criarConta: "Cria uma grátis",
} as const;

// Página de registo. {pedidos}: "30 pedidos à IA por mês" (textoDosPedidos, planos.ts).
export const TEXTOS_REGISTO = {
  introducao: "Cria a tua conta grátis. O plano Free inclui {pedidos} e importação de extratos em CSV.",
  palavraPasse: "Palavra-passe (mínimo 8 caracteres)",
  repetir: "Repetir a palavra-passe",
  erroCurta: "A palavra-passe tem de ter pelo menos 8 caracteres.",
  erroDiferentes: "As palavras-passe não coincidem.",
  erroEmail: "Confirma que o email está bem escrito.",
  erroCriar: "Não foi possível criar a conta.",
  criar: "Criar conta",
  aCriar: "A criar a conta...",
  jaTensConta: "Já tens conta?",
  entra: "Entra",
  // Depois de criar a conta (a mensagem principal vem da API; "criada" só se a API não a mandar).
  criada: "Conta criada. Confirma o email para entrar.",
  quaseLa: "Quase lá!",
  spam: "Não chegou? Vê na pasta de spam.",
  irLogin: "Ir para o login",
} as const;
