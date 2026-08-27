-- Migración 005: agregar guia_remision a fichas_tecnicas
ALTER TABLE fichas_tecnicas ADD COLUMN IF NOT EXISTS guia_remision VARCHAR(100);
