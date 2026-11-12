"""Textos das respostas da API por país (PT-PT e PT-BR), nas rotas com sessão (Fase 1 Brasil, passo 8).

Cada mensagem tem a versão PT (a de sempre, igual à que a API já mandava) e a BR. msg(chave, pais, **valores)
escolhe pelo país onde a pessoa vive (assinaturas.pais) e troca os {valores}. País desconhecido: PT.
As rotas públicas (/login, /registo, Google, /lista-espera) e a demo ficam só em PT: sem sessão não se sabe o país.

Os textos BR reutilizam os do frontend (lib/textos*.ts, aprovados pelo copywriter) quando a API manda o mesmo texto.
Os marcados com "TEXTO NOVO" ainda não foram revistos pelo copywriter.
"""

from dataclasses import dataclass

PAIS_PADRAO = "PT"


@dataclass(frozen=True)
class Local:
    """O país onde a pessoa vive (língua, fuso, formatos) e a moeda principal da conta (moeda e contexto bancário).

    Por omissão PT/EUR, como todas as contas antes da sql/020.
    """

    pais: str = "PT"
    moeda: str = "EUR"


MENSAGENS: dict[str, dict[str, str]] = {
    # --- Limites de pedidos à IA e de PDF (limites.py) ---
    # BR igual ao frontend (textosPlanos.ts, TEXTOS_LIMITE: título + texto).
    "limite_pedidos_mes": {
        "PT": "Chegaste ao limite deste mês. Já usaste os {limite} pedidos à IA deste mês. O contador volta a zero no dia 1.",
        "BR": "Você chegou ao limite deste mês. Você já usou os {limite} pedidos à IA deste mês. O contador zera no dia 1.",
    },
    "limite_pedidos_dia": {
        "PT": (
            "Chegaste ao limite de hoje. Já usaste os {limite} pedidos à IA do teu plano. "
            "O contador volta a zero à meia-noite."
        ),
        "BR": "Você chegou ao limite de hoje. Você já usou os {limite} pedidos à IA do seu plano. O contador zera à meia-noite.",
    },
    # O frontend distingue este 429 do dos pedidos procurando "extratos PDF" (api.ts, eLimitePdf):
    # as duas versões têm de continuar a ter essas palavras. BR: TEXTO NOVO.
    "limite_pdf": {
        "PT": (
            "Chegaste ao limite de {limite} extratos PDF este mês. O contador volta a zero no dia 1. "
            "Até lá, podes importar o extrato em CSV."
        ),
        "BR": (
            "Você chegou ao limite de {limite} extratos PDF este mês. O contador zera no dia 1. "
            "Até lá, você pode importar o extrato em CSV."
        ),
    },
    "pdf_indisponivel": {  # BR: TEXTO NOVO
        "PT": "Não foi possível importar o PDF agora. Tenta outra vez daqui a pouco.",
        "BR": "Não foi possível importar o PDF agora. Tente de novo daqui a pouco.",
    },
    "conta_cheia": {  # BR: TEXTO NOVO
        "PT": "Chegaste ao máximo de 20 000 movimentações nesta conta. Fala connosco se precisares de mais.",
        "BR": "Você chegou ao máximo de 20.000 movimentações nesta conta. Fale com a gente se precisar de mais.",
    },
    "resumo_sem_pedidos_mes": {  # BR: TEXTO NOVO
        "PT": "Chegaste ao limite de pedidos à IA deste mês. O resumo volta no dia 1.",
        "BR": "Você chegou ao limite de pedidos à IA deste mês. O resumo volta no dia 1.",
    },
    "resumo_sem_pedidos_dia": {  # BR: TEXTO NOVO
        "PT": "Chegaste ao limite de pedidos à IA de hoje. O resumo volta depois da meia-noite.",
        "BR": "Você chegou ao limite de pedidos à IA de hoje. O resumo volta depois da meia-noite.",
    },
    # --- Funções só dos planos pagos (402). BR igual ao frontend, menos onde está marcado. ---
    "funcao_paga_importar_pdf": {
        "PT": (
            "A importação de extratos em PDF está disponível nos planos Essencial e Completo. "
            "No Free, podes importar o extrato em CSV."
        ),
        "BR": (
            "A importação de extratos em PDF está disponível nos planos Essencial e Completo. "
            "No Free, você pode importar o extrato em CSV."
        ),
    },
    "funcao_paga_ler_talao": {
        "PT": "A leitura de talões está disponível nos planos Essencial e Completo.",
        "BR": "A leitura de notas fiscais está disponível nos planos Essencial e Completo.",
    },
    "funcao_paga_precos_por_loja": {
        "PT": "Comparar preços entre as lojas onde compraste está disponível nos planos Essencial e Completo.",
        "BR": "Comparar preços entre as lojas onde você comprou está disponível nos planos Essencial e Completo.",
    },
    # BR: o do frontend (textosRelatorio.ts, csvPlanoPago) com "na app" em vez de "aqui", como o PT da API.
    "funcao_paga_exportar_relatorio": {
        "PT": (
            "Descarregar o resumo anual em CSV (para abrir numa folha de cálculo) está disponível nos planos "
            "Essencial e Completo. No Free, podes ver o resumo na app e guardá-lo em PDF."
        ),
        "BR": (
            "Baixar o resumo anual em CSV (para abrir em uma planilha) está disponível nos planos "
            "Essencial e Completo. No Free, você pode ver o resumo na app e salvar em PDF."
        ),
    },
    "funcao_completo_resumo_anual_ia": {  # BR: TEXTO NOVO
        "PT": (
            "O resumo do ano escrito pela IA está disponível no plano Completo. "
            "Os números do resumo anual continuam disponíveis no teu plano."
        ),
        "BR": (
            "O resumo do ano escrito pela IA está disponível no plano Completo. "
            "Os números do resumo anual continuam disponíveis no seu plano."
        ),
    },
    # --- Conta e perfil ---
    "apagar_conta_sem_confirmacao": {  # BR: TEXTO NOVO (o frontend BR já diz "digite APAGAR")
        "PT": 'Para apagar a conta, escreve "APAGAR" na confirmação.',
        "BR": 'Para apagar a conta, digite "APAGAR" na confirmação.',
    },
    "apagar_conta_falhou": {  # BR: TEXTO NOVO
        "PT": "Não foi possível apagar a conta agora. Tenta mais tarde.",
        "BR": "Não foi possível apagar a conta agora. Tente mais tarde.",
    },
    "perfil_moeda_com_dados": {  # BR: TEXTO NOVO
        "PT": (
            "Só podes mudar a moeda principal enquanto a conta não tiver movimentações, compras, orçamentos "
            "nem objetivos."
        ),
        "BR": (
            "Você só pode mudar a moeda principal enquanto a conta não tiver movimentações, compras, orçamentos "
            "nem metas."
        ),
    },
    "perfil_moeda_incoerente": {  # BR: TEXTO NOVO
        "PT": "A moeda principal tem de ser a de um dos países dos teus cartões e contas.",
        "BR": "A moeda principal precisa ser a de um dos países dos seus cartões e contas.",
    },
    # Interruptor do Brasil (perfil.py). PT e BR: TEXTO NOVO.
    "perfil_brasil_fechado": {
        "PT": "A Control Prices ainda não está disponível para quem vive no Brasil. Podes inscrever-te na lista de espera em /brasil.",
        "BR": "A Control Prices ainda não está disponível para quem mora no Brasil. Você pode entrar na lista de espera em /brasil.",
    },
    "perfil_indisponivel": {  # BR: TEXTO NOVO
        "PT": "Não foi possível guardar as definições agora. Tenta mais tarde.",
        "BR": "Não foi possível salvar as configurações agora. Tente mais tarde.",
    },
    "perfil_muitas_mudancas": {  # PT: proposta ainda por aprovar (limite_ip.py). BR: TEXTO NOVO
        "PT": "Mudaste as definições muitas vezes. Tenta daqui a uma hora.",
        "BR": "Você mudou as configurações muitas vezes. Tente de novo daqui a uma hora.",
    },
    # Questionário de boas-vindas (boas_vindas.py). PT e BR: TEXTO NOVO.
    "boas_vindas_indisponivel": {
        "PT": "Não foi possível guardar as respostas agora. Tenta mais tarde.",
        "BR": "Não foi possível salvar as respostas agora. Tente mais tarde.",
    },
    # --- Movimentações e importação ---
    "transacao_nao_encontrada": {
        "PT": "Transação não encontrada",
        "BR": "Transação não encontrada",
    },
    "categorizacao_falhou": {  # BR: TEXTO NOVO
        "PT": "A categorização automática falhou. Tenta mais tarde.",
        "BR": "A categorização automática falhou. Tente mais tarde.",
    },
    "categorizacao_falhou_importar": {  # BR: TEXTO NOVO
        "PT": "A categorização automática falhou. Tenta importar mais tarde.",
        "BR": "A categorização automática falhou. Tente importar mais tarde.",
    },
    "importacao_sem_ia": {  # BR: TEXTO NOVO
        "PT": (
            "Importámos as movimentações sem categorias porque chegaste ao limite de pedidos à IA. "
            "Podes categorizá-las mais tarde."
        ),
        "BR": (
            "Importamos as movimentações sem categorias porque você chegou ao limite de pedidos à IA. "
            "Você pode categorizá-las mais tarde."
        ),
    },
    "importacao_ia_em_baixo": {  # BR: TEXTO NOVO
        "PT": "Importámos as movimentações sem categorias porque a IA não respondeu. Podes categorizá-las mais tarde.",
        "BR": "Importamos as movimentações sem categorias porque a IA não respondeu. Você pode categorizá-las mais tarde.",
    },
    "ficheiro_sem_transacoes": {  # BR: TEXTO NOVO
        "PT": "O ficheiro não tem transações",
        "BR": "O arquivo não tem transações",
    },
    "csv_grande": {  # BR: TEXTO NOVO
        "PT": "CSV demasiado grande. Máx. 1 MB.",
        "BR": "CSV grande demais. Máx. 1 MB.",
    },
    "csv_movimentos_a_mais": {  # BR: TEXTO NOVO
        "PT": "Este extrato tem mais de {maximo} movimentos. Divide-o em partes mais pequenas.",
        "BR": "Este extrato tem mais de {maximo} movimentações. Divida-o em partes menores.",
    },
    "csv_codificacao": {  # BR: TEXTO NOVO
        "PT": "Não consegui ler o CSV. Grava-o com a codificação UTF-8 e tenta outra vez.",
        "BR": "Não consegui ler o CSV. Salve-o com a codificação UTF-8 e tente de novo.",
    },
    "pdf_grande": {  # BR: TEXTO NOVO
        "PT": "PDF demasiado grande. Máx. 10 MB.",
        "BR": "PDF grande demais. Máx. 10 MB.",
    },
    "pdf_ilegivel": {  # BR: TEXTO NOVO
        "PT": "Não consegui ler o PDF. Se tiver palavra-passe, tira-a.",
        "BR": "Não consegui ler o PDF. Se ele estiver protegido por senha, remova a proteção.",
    },
    "pdf_paginas": {  # BR: TEXTO NOVO ({quantas} é um número ou "mais de N")
        "PT": "Este PDF tem {quantas} páginas. O máximo é {maximo}. Divide o extrato em partes mais pequenas.",
        "BR": "Este PDF tem {quantas} páginas. O máximo é {maximo}. Divida o extrato em partes menores.",
    },
    "pdf_ia_falhou": {  # BR: TEXTO NOVO
        "PT": "Não consegui ler o PDF. Se tiver palavra-passe, tira-a. Senão, tenta mais tarde.",
        "BR": "Não consegui ler o PDF. Se ele estiver protegido por senha, remova a proteção. Se não estiver, tente mais tarde.",
    },
    "pdf_sem_movimentos": {  # BR: TEXTO NOVO
        "PT": "Não encontrei movimentos neste PDF. Confirma que é um extrato bancário.",
        "BR": "Não encontrei movimentações neste PDF. Confira se é um extrato bancário.",
    },
    # --- IA: chat, resumo do mês, orçamento ---
    "chat_falhou": {  # BR: TEXTO NOVO
        "PT": "O chat falhou. Tenta mais tarde.",
        "BR": "O chat falhou. Tente mais tarde.",
    },
    # Resposta do chat quando o orçamento de saída (ou as voltas) acaba sem uma resposta de texto (ia.py).
    "chat_sem_orcamento": {  # BR: TEXTO NOVO
        "PT": (
            "Esta pergunta precisava de uma resposta mais longa do que o teu plano permite. "
            "Tenta reformulá-la de forma mais simples, por exemplo um mês ou uma categoria de cada vez."
        ),
        "BR": (
            "Esta pergunta precisava de uma resposta mais longa do que o seu plano permite. "
            "Tente perguntar de forma mais simples, por exemplo sobre um mês ou uma categoria de cada vez."
        ),
    },
    "resumo_falhou": {  # BR: TEXTO NOVO
        "PT": "O resumo automático falhou. Tenta mais tarde.",
        "BR": "O resumo automático falhou. Tente mais tarde.",
    },
    "sugestao_falhou": {  # BR: TEXTO NOVO
        "PT": "A sugestão automática falhou. Tenta mais tarde.",
        "BR": "A sugestão automática falhou. Tente mais tarde.",
    },
    # --- Talões (Minhas compras) e preços por loja ---
    "imagem_formato": {  # BR: TEXTO NOVO
        "PT": "Formato de imagem não suportado. Usa JPEG, PNG ou WebP.",
        "BR": "Formato de imagem não suportado. Use JPEG, PNG ou WebP.",
    },
    "imagem_grande": {  # BR: TEXTO NOVO
        "PT": "Imagem demasiado grande. Máx. 5 MB.",
        "BR": "Imagem grande demais. Máx. 5 MB.",
    },
    "imagem_pequena": {  # BR: TEXTO NOVO
        "PT": "Imagem demasiado pequena. Tenta outra fotografia.",
        "BR": "Imagem pequena demais. Tente outra foto.",
    },
    "talao_falhou": {  # BR: TEXTO NOVO
        "PT": "A leitura do talão falhou. Tenta mais tarde.",
        "BR": "A leitura da nota fiscal falhou. Tente mais tarde.",
    },
    "talao_ilegivel": {  # BR: TEXTO NOVO
        "PT": "Não consegui ler o talão. Tenta outra fotografia, com mais luz.",
        "BR": "Não consegui ler a nota fiscal. Tente tirar outra foto, com mais luz.",
    },
    "produto_nao_encontrado": {  # BR: TEXTO NOVO
        "PT": "Produto não encontrado nas tuas compras.",
        "BR": "Produto não encontrado nas suas compras.",
    },
    "juncao_nao_existe": {
        "PT": "Esta junção não existe.",
        "BR": "Esta junção não existe.",
    },
    "juntar_iguais": {  # BR: TEXTO NOVO
        "PT": "Escolhe dois produtos diferentes para juntar.",
        "BR": "Escolha dois produtos diferentes para juntar.",
    },
    "juntar_maximo": {  # BR: TEXTO NOVO
        "PT": "Chegaste ao máximo de {maximo} produtos juntos.",
        "BR": "Você chegou ao máximo de {maximo} produtos juntos.",
    },
    "juntar_ao_contrario": {  # BR: TEXTO NOVO
        "PT": "Estes produtos já estão juntos ao contrário.",
        "BR": "Esses produtos já estão juntos ao contrário.",
    },
    # --- Minha reserva (objetivos = "metas" no BR) ---
    "objetivo_nao_encontrado": {  # BR: TEXTO NOVO
        "PT": "Objetivo não encontrado",
        "BR": "Meta não encontrada",
    },
    "objetivo_atingido": {  # BR: TEXTO NOVO
        "PT": "Já atingiste este objetivo. Parabéns!",
        "BR": "Você já atingiu esta meta. Parabéns!",
    },
    "objetivo_prazo_terminou": {  # BR: TEXTO NOVO
        "PT": "O prazo deste objetivo já terminou. Escolhe uma nova data para voltar a planear.",
        "BR": "O prazo desta meta já terminou. Escolha uma nova data para planejar de novo.",
    },
    "objetivo_sem_mes_completo": {  # BR: TEXTO NOVO
        "PT": (
            "Ainda não tens um mês completo de movimentações, por isso não consigo calcular a tua poupança média."
        ),
        "BR": (
            "Você ainda não tem um mês completo de movimentações, por isso não consigo calcular quanto você "
            "guarda em média."
        ),
    },
    "poupanca_falhou": {  # BR: TEXTO NOVO
        "PT": "O plano de poupança falhou. Tenta mais tarde.",
        "BR": "Não foi possível criar o plano da meta agora. Tente mais tarde.",
    },
    # --- Resumo anual ---
    "ano_invalido": {  # BR: TEXTO NOVO
        "PT": "Ano inválido. Escolhe um ano entre 2000 e {ano}.",
        "BR": "Ano inválido. Escolha um ano entre 2000 e {ano}.",
    },
    "ano_sem_movimentos": {  # BR: TEXTO NOVO
        "PT": "Ainda não há movimentos neste ano.",
        "BR": "Ainda não há movimentações neste ano.",
    },
    "resumo_anual_falhou": {  # BR: TEXTO NOVO
        "PT": "O resumo do ano falhou. Tenta mais tarde.",
        "BR": "O resumo do ano falhou. Tente mais tarde.",
    },
}


def preencher(texto: str, **valores) -> str:
    """Troca cada {chave} pelo valor dado (como o preencher() do frontend). As outras chavetas ficam como estão."""
    for nome, valor in valores.items():
        texto = texto.replace("{" + nome + "}", str(valor))
    return texto


def msg(chave: str, pais: str | None, **valores) -> str:
    """A mensagem no país dado (PT ou BR), com os {valores} trocados. País desconhecido ou None: PT."""
    textos = MENSAGENS[chave]
    return preencher(textos.get(pais or PAIS_PADRAO, textos[PAIS_PADRAO]), **valores)
