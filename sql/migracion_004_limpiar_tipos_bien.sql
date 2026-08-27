-- ============================================================
-- Migración 004: Limpiar tipos de bien duplicados y remapear referencias
-- ============================================================

-- 1. Remapear referencias en items_especificacion hacia el ID representativo (MIN(id))
UPDATE items_especificacion ie
SET tipo_bien_id = sub.min_id
FROM (
    SELECT tb.id AS old_id, min_tb.min_id
    FROM tipos_bien tb
    JOIN (
        SELECT nombre, MIN(id) AS min_id
        FROM tipos_bien
        GROUP BY nombre
    ) min_tb ON tb.nombre = min_tb.nombre
    WHERE tb.id != min_tb.min_id
) sub
WHERE ie.tipo_bien_id = sub.old_id;

-- 2. Eliminar duplicados en tipos_bien
DELETE FROM tipos_bien
WHERE id NOT IN (
    SELECT MIN(id)
    FROM tipos_bien
    GROUP BY nombre
);

-- 3. Agregar constraint de unicidad si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_tipo_bien_nombre'
    ) THEN
        ALTER TABLE tipos_bien ADD CONSTRAINT uq_tipo_bien_nombre UNIQUE (nombre);
    END IF;
END $$;
