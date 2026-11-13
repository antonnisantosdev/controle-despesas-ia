// Textos do login, do registo e do login com o Google (páginas públicas, sem sessão).
// PT-PT ou PT-BR pela língua do browser (lib/paisPublico.ts, useTextosPublicos). As mensagens que vêm da API
// (palavra-passe errada, email por confirmar...) continuam em PT-PT.
// Os marcados com "TEXTO NOVO" ainda não foram revistos pelo copywriter. O BR foi revisto pelo copywriter (2026-11-13).

import type { Traducao } from "./textos";

const PT = {
  // Botão "Continuar com Google" (login e registo) e a página /login/google.
  TEXTOS_GOOGLE: {
    botao: "Continuar com Google", // TEXTO NOVO
    aAbrir: "A abrir o Google...", // TEXTO NOVO
    separador: "ou", // TEXTO NOVO
    // Quando nem se consegue pedir à API o endereço do login (servidor em baixo, sem rede).
    erroAbrir: "Não foi possível abrir o login com o Google. Tenta outra vez daqui a um minuto.", // TEXTO NOVO
    // Na página /login/google, enquanto se guarda o token e se muda para o dashboard.
    aEntrar: "A entrar...", // TEXTO NOVO
    erroEntrar: "Não foi possível entrar com o Google. Tenta outra vez.", // TEXTO NOVO
    voltarLogin: "Voltar ao login", // TEXTO NOVO
  },

  // Registo e login com o Google: aceitar os termos ao criar conta (sem caixa obrigatória). Texto aprovado pelo CEO.
  TEXTOS_TERMOS: {
    antes: "Ao criar conta, aceitas os ",
    termos: "Termos de Utilização",
    meio: " e a ",
    privacidade: "Política de Privacidade",
    fim: ".",
  },

  // Página de login (email e palavra-passe). Os textos do Google e da demo estão em TEXTOS_GOOGLE e TEXTOS_DEMO.
  TEXTOS_LOGIN: {
    erroCredenciais: "Email ou palavra-passe inválidas.",
    entrar: "Entrar",
    aEntrar: "A entrar...",
    semConta: "Ainda não tens conta?",
    criarConta: "Cria uma grátis",
  },

  // Página de registo. {pedidos}: "30 pedidos à IA por mês" (textoDosPedidos, planos.ts).
  TEXTOS_REGISTO: {
    introducao: "Cria a tua conta grátis. O plano Free inclui {pedidos}, importação de extratos em CSV e 1 extrato PDF por mês.", // TEXTO NOVO
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
  },

  // Rodapé com os links legais (páginas públicas e fundo da app).
  TEXTOS_RODAPE_LEGAL: { termos: "Termos de Utilização", privacidade: "Política de Privacidade", rotulo: "Informação legal" },
} as const;

const BR: Traducao<typeof PT> = {
  TEXTOS_GOOGLE: {
    botao: "Continuar com Google",
    aAbrir: "Abrindo o Google...",
    separador: "ou",
    erroAbrir: "Não foi possível abrir o login com o Google. Tente novamente daqui a um minuto.",
    aEntrar: "Entrando...",
    erroEntrar: "Não foi possível entrar com o Google. Tente novamente.",
    voltarLogin: "Voltar ao login",
  },
  TEXTOS_TERMOS: {
    antes: "Ao criar a conta, você aceita os ",
    termos: "Termos de Uso",
    meio: " e a ",
    privacidade: "Política de Privacidade",
    fim: ".",
  },
  TEXTOS_LOGIN: {
    erroCredenciais: "E-mail ou senha inválidos.",
    entrar: "Entrar",
    aEntrar: "Entrando...",
    semConta: "Ainda não tem conta?",
    criarConta: "Crie uma grátis",
  },
  TEXTOS_REGISTO: {
    introducao: "Crie sua conta grátis. O plano Free inclui {pedidos}, importação de extratos em CSV e 1 extrato em PDF por mês.", // TEXTO NOVO
    palavraPasse: "Senha (mínimo de 8 caracteres)",
    repetir: "Repetir a senha",
    erroCurta: "A senha precisa ter pelo menos 8 caracteres.",
    erroDiferentes: "As senhas não são iguais.",
    erroEmail: "Confira se o e-mail está correto.",
    erroCriar: "Não foi possível criar a conta.",
    criar: "Criar conta",
    aCriar: "Criando a conta...",
    jaTensConta: "Já tem conta?",
    entra: "Entre",
    criada: "Conta criada. Confirme o e-mail para entrar.",
    quaseLa: "Quase lá!",
    spam: "Não chegou? Veja na pasta de spam.",
    irLogin: "Ir para o login",
  },
  TEXTOS_RODAPE_LEGAL: { termos: "Termos de Uso", privacidade: "Política de Privacidade", rotulo: "Informações legais" },
};

export const DICIONARIO_LOGIN = { PT, BR };

// Para quem ainda importa os textos PT diretamente (fora de componentes).
export const { TEXTOS_GOOGLE, TEXTOS_TERMOS, TEXTOS_LOGIN, TEXTOS_REGISTO } = PT;
