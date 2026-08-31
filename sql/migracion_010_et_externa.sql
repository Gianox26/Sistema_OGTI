-- Migración 010: Soporte para ET externa (por referencia)
-- Permite crear fichas técnicas sin una ET redactada en el sistema

-- Campo 'origen' en especificaciones_tecnicas para distinguir
ALTER TABLE especificaciones_tecnicas ADD COLUMN IF NOT EXISTS origen VARCHAR(20) DEFAULT 'INTERNA';

-- Tabla ligera para registrar pedidos de referencia externos
-- Cuando la ET llega en físico, se registran solo los datos mínimos
CREATE TABLE IF NOT EXISTS pedidos_referencia (
    id                       SERIAL PRIMARY KEY,
    numero_pedido            VARCHAR(50) NOT NULL,
    fecha_pedido             DATE,
    denominacion_adquisicion TEXT,
    proveedor_id             INTEGER REFERENCES proveedores(id),
    centro_costo_id          INTEGER REFERENCES dependencias(id),
    notas                    TEXT,
    creado_por               INTEGER REFERENCES usuarios(id),
    fecha_creacion           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_pedido_ref_numero UNIQUE (numero_pedido)
);
