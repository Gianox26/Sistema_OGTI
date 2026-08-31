-- Migración 009: Clasificar características en principales y secundarias
-- para controlar cuáles se imprimen en el documento (máx 1 página)

-- Añadir campo max_caracteristicas_doc a tipos_bien
ALTER TABLE tipos_bien ADD COLUMN IF NOT EXISTS max_caracteristicas_doc INTEGER DEFAULT 8;

-- NOTA: Las características en items_especificacion y fichas_tecnicas.caracteristicas_verificadas
-- ahora soportan el campo adicional "principal" (boolean) en el JSONB.
-- Ejemplo: [{"nombre": "Procesador", "valor": "Intel i7", "principal": true, "orden": 1}]
-- Si "principal" no está presente, se asume true (retrocompatibilidad).
-- El documento .docx solo renderiza las que tienen principal = true.
-- La base de datos SIEMPRE guarda el conjunto completo.
