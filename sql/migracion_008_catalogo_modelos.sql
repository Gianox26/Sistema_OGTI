-- Migración 008: Tabla catalogo_modelos para la arquitectura Cache-Aside
CREATE TABLE IF NOT EXISTS catalogo_modelos (
    id SERIAL PRIMARY KEY,
    marca VARCHAR(100) NOT NULL,
    modelo VARCHAR(100) NOT NULL,
    caracteristicas JSONB NOT NULL DEFAULT '[]'::jsonb,
    fuente VARCHAR(30) NOT NULL DEFAULT 'MANUAL', -- 'DATABASE', 'WEB', 'MANUAL'
    verificado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_catalogo_modelos_marca_modelo UNIQUE (marca, modelo)
);

-- Copiar datos de plantillas_caracteristicas si existían
INSERT INTO catalogo_modelos (marca, modelo, caracteristicas, fuente, verificado)
SELECT UPPER(TRIM(marca)), UPPER(TRIM(modelo)), caracteristicas, 'MANUAL', TRUE
FROM plantillas_caracteristicas
ON CONFLICT (marca, modelo) DO NOTHING;
