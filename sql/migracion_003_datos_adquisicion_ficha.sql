-- Migración 003: agregar datos de adquisición a fichas_tecnicas
-- Registra N° Orden de Compra, Costo/Valor, Fecha y Tiempo de Garantía
-- del bien recibido.
-- Ejecutar con:
--   PGPASSWORD=ogti2026 psql -h localhost -U fulanito -d sistema_ogti -f sql/migracion_003_datos_adquisicion_ficha.sql

ALTER TABLE fichas_tecnicas ADD COLUMN IF NOT EXISTS orden_compra VARCHAR(50);
ALTER TABLE fichas_tecnicas ADD COLUMN IF NOT EXISTS costo NUMERIC(14,2);
ALTER TABLE fichas_tecnicas ADD COLUMN IF NOT EXISTS fecha_adquisicion DATE;
ALTER TABLE fichas_tecnicas ADD COLUMN IF NOT EXISTS garantia VARCHAR(50);
