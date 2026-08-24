-- ============================================================
-- Migración 001: Correcciones al módulo de Especificaciones Técnicas
-- Basado en el formato oficial TDR Alicate Crimping.docx
-- ============================================================

-- 1. Nueva tabla: actividades_operativas
CREATE TABLE IF NOT EXISTS actividades_operativas (
    id       SERIAL PRIMARY KEY,
    codigo   VARCHAR(20) NOT NULL,
    nombre   TEXT NOT NULL,
    activo   BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_actividad_codigo UNIQUE (codigo)
);

-- 2. Modificar especificaciones_tecnicas
--    Agregar columnas nuevas
ALTER TABLE especificaciones_tecnicas
    ADD COLUMN IF NOT EXISTS denominacion_adquisicion TEXT;

ALTER TABLE especificaciones_tecnicas
    ADD COLUMN IF NOT EXISTS actividad_operativa_id INTEGER REFERENCES actividades_operativas(id);

ALTER TABLE especificaciones_tecnicas
    ADD COLUMN IF NOT EXISTS centro_costo_id INTEGER REFERENCES dependencias(id);

ALTER TABLE especificaciones_tecnicas
    ADD COLUMN IF NOT EXISTS meta_anio VARCHAR(20);

-- 3. Modificar items_especificacion
--    Agregar campos para condiciones, imagen y reglamentos
ALTER TABLE items_especificacion
    ADD COLUMN IF NOT EXISTS condiciones_previas TEXT DEFAULT 'El bien debe ser entregado en óptimas condiciones de funcionamiento.
El bien deberá de ser original.
El bien deberá incluir accesorios necesarios para su funcionamiento.
Los bienes deberán de estar debidamente sellados.';

ALTER TABLE items_especificacion
    ADD COLUMN IF NOT EXISTS imagen_referencial VARCHAR(300);

ALTER TABLE items_especificacion
    ADD COLUMN IF NOT EXISTS reglamentos_tecnicos TEXT DEFAULT 'No aplica';

-- Cambiar cantidad de INTEGER a NUMERIC para decimales (1.00, 2.50)
ALTER TABLE items_especificacion
    ALTER COLUMN cantidad TYPE NUMERIC(10,2) USING cantidad::NUMERIC(10,2);

ALTER TABLE items_especificacion
    ALTER COLUMN cantidad SET DEFAULT 1.00;

-- 4. Datos iniciales de actividades operativas
INSERT INTO actividades_operativas (codigo, nombre) VALUES
    ('C0023', 'EJECUCIÓN DE SOPORTE TÉCNICO Y MANTENIMIENTO EN EQUIPOS DE LA MPSR-J'),
    ('C0178', 'DIRECCIÓN, PROMOCIÓN Y COORDINACIÓN DE LAS ACTIVIDADES DE EDUCACIÓN Y CULTURA')
ON CONFLICT (codigo) DO NOTHING;

-- 5. Crear índice para la nueva tabla
CREATE INDEX IF NOT EXISTS idx_actividad_codigo ON actividades_operativas (codigo);
