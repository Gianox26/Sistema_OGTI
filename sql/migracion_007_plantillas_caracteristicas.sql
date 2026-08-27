-- Migración 007: Tabla de plantillas de características por marca y modelo
CREATE TABLE IF NOT EXISTS plantillas_caracteristicas (
    id SERIAL PRIMARY KEY,
    marca VARCHAR(100) NOT NULL,
    modelo VARCHAR(100) NOT NULL,
    caracteristicas JSONB NOT NULL DEFAULT '[]'::jsonb,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_plantilla_marca_modelo UNIQUE (marca, modelo)
);
