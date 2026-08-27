-- Migración 006: hacer numero_serie opcional y quitar UNIQUE
-- Algunos bienes (gomas, lapiceros, pedestales) no tienen número de serie

-- 1. Permitir NULL en numero_serie
ALTER TABLE fichas_tecnicas ALTER COLUMN numero_serie DROP NOT NULL;

-- 2. Remover UNIQUE constraint de numero_serie (permite bienes sin serie)
ALTER TABLE fichas_tecnicas DROP CONSTRAINT IF EXISTS uq_ficha_numero_serie;

-- 3. Crear un índice parcial solo para series que existen (evita duplicados reales)
CREATE UNIQUE INDEX IF NOT EXISTS uq_ficha_numero_serie_no_null
    ON fichas_tecnicas (numero_serie) WHERE numero_serie IS NOT NULL AND numero_serie != '';
