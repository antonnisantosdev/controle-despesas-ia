-- Registo público: cada conta nova entra sozinha no plano Free.
-- O Free não tem data de fim (ativo_ate NULL). Os planos pagos continuam a precisar de data.
-- Como correr: Supabase > SQL Editor > New query > colar este ficheiro > Run.

-- 1. O ativo_ate passa a poder ficar vazio, mas só no Free.
--    O CHECK impede um plano pago sem data (o que seria acesso pago para sempre).
ALTER TABLE assinaturas ALTER COLUMN ativo_ate DROP NOT NULL;
ALTER TABLE assinaturas
    ADD CONSTRAINT planos_pagos_tem_data CHECK (plano = 'free' OR ativo_ate IS NOT NULL);

-- 2. Função que cria a assinatura Free de um utilizador novo.
--    SECURITY DEFINER: corre com permissões do dono, porque quem se regista não pode escrever nesta tabela.
--    search_path vazio + nomes completos (public.assinaturas): ninguém consegue trocar a tabela por outra.
CREATE FUNCTION public.criar_assinatura_free()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.assinaturas (user_id, plano, ativo_ate, notas)
    VALUES (NEW.id, 'free', NULL, 'registo público')
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$;

-- 3. Gatilho (como um hook do WordPress, mas na base de dados): corre depois de cada conta nova.
CREATE TRIGGER ao_criar_utilizador
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.criar_assinatura_free();

-- A partir de agora, para dar um plano pago a alguém, ATUALIZA a linha que o gatilho criou:
-- UPDATE assinaturas SET plano = 'essencial', ativo_ate = '2026-12-31', notas = 'MB Way 2026-11-08'
-- WHERE user_id = (SELECT id FROM auth.users WHERE email = 'pessoa@exemplo.com');
