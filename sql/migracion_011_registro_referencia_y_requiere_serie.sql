-- Migración 011: Registro de Especificaciones por Referencia Físicas + Campo requiere_serie en tipos_bien

-- 1. Campo requiere_serie en tipos_bien
ALTER TABLE tipos_bien ADD COLUMN IF NOT EXISTS requiere_serie BOOLEAN NOT NULL DEFAULT TRUE;

-- Actualizar bienes conocidos de mobiliario u otros que no requieren número de serie
UPDATE tipos_bien 
SET requiere_serie = FALSE 
WHERE LOWER(nombre) SIMILAR TO '%(silla|sillon|escritorio|mesa|estante|armario|pedestal|mueble|mobiliario|menaje|repisa|tacho|pizarra)%';

-- 2. Soporte para adjuntos en especificaciones_tecnicas
ALTER TABLE especificaciones_tecnicas ADD COLUMN IF NOT EXISTS documento_adjunto VARCHAR(255);

-- Asegurar que origen por defecto pueda ser REFERENCIA_EXTERNA u INTERNA
ALTER TABLE especificaciones_tecnicas ALTER COLUMN origen SET DEFAULT 'REFERENCIA_EXTERNA';

-- 3. Permitir NULL en numero_serie de fichas_tecnicas para bienes que no exigen serie (ej. Mobiliario)
ALTER TABLE fichas_tecnicas ALTER COLUMN numero_serie DROP NOT NULL;
