-- Migración 002: hacer proveedor opcional en Especificaciones Técnicas
-- Ejecutar con: PGPASSWORD=ogti2026 psql -h localhost -U fulanito -d sistema_ogti -f sql/migracion_002_proveedor_opcional.sql

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'especificaciones_tecnicas'
          AND column_name = 'proveedor_id'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE especificaciones_tecnicas ALTER COLUMN proveedor_id DROP NOT NULL;
        RAISE NOTICE 'proveedor_id ahora es opcional';
    ELSE
        RAISE NOTICE 'proveedor_id ya era opcional; nada que hacer';
    END IF;
END
$$;
