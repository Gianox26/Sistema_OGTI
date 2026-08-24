-- ============================================================
-- Sistema OGTI — Municipalidad Provincial de San Román Juliaca
-- Esquema de Base de Datos PostgreSQL
-- ============================================================

-- Extensión para UUIDs si se necesita en futuro
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLA: usuarios
-- Autenticación y auditoría de operadores OGTI
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL,
    password_hash   VARCHAR(256) NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    cargo           VARCHAR(100),
    rol             VARCHAR(20)  NOT NULL DEFAULT 'OPERADOR'
                        CHECK (rol IN ('OPERADOR', 'JEFE_OGTI')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion  TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_usuario_username UNIQUE (username)
);

-- ============================================================
-- TABLA: dependencias
-- Oficinas / áreas de la Municipalidad
-- ============================================================
CREATE TABLE IF NOT EXISTS dependencias (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(200) NOT NULL,
    edificio  VARCHAR(100),
    pabellon  VARCHAR(100),
    activo    BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- TABLA: actividades_operativas
-- Catálogo de actividades operativas con código y descripción
-- Ej: C0023 – Ejecución de soporte técnico...
-- ============================================================
CREATE TABLE IF NOT EXISTS actividades_operativas (
    id       SERIAL PRIMARY KEY,
    codigo   VARCHAR(20) NOT NULL,
    nombre   TEXT NOT NULL,
    activo   BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_actividad_codigo UNIQUE (codigo)
);

CREATE INDEX IF NOT EXISTS idx_actividad_codigo
    ON actividades_operativas (codigo);

-- ============================================================
-- TABLA: proveedores
-- Empresas que suministran bienes tecnológicos
-- ============================================================
CREATE TABLE IF NOT EXISTS proveedores (
    id            SERIAL PRIMARY KEY,
    ruc           VARCHAR(11) NOT NULL,
    razon_social  VARCHAR(250) NOT NULL,
    direccion     VARCHAR(300),
    telefono      VARCHAR(30),
    correo        VARCHAR(150),
    activo        BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_proveedor_ruc UNIQUE (ruc)
);

-- ============================================================
-- TABLA: responsables
-- Personal que recibe o gestiona bienes
-- ============================================================
CREATE TABLE IF NOT EXISTS responsables (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(150) NOT NULL,
    cargo           VARCHAR(100),
    telefono        VARCHAR(30),
    correo          VARCHAR(150),
    dependencia_id  INTEGER REFERENCES dependencias(id),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLA: tipos_bien
-- Catálogo de bienes tecnológicos con características típicas
-- Las características típicas se almacenan como JSONB para
-- flexibilidad (el sugeridor las propone al crear ítems)
-- Ejemplo de caracteristicas_tipicas:
-- [
--   {"nombre": "Procesador", "valor_sugerido": "Intel Core i7 13va Gen"},
--   {"nombre": "Memoria RAM", "valor_sugerido": "16 GB DDR5"},
--   {"nombre": "Almacenamiento", "valor_sugerido": "SSD 1 TB"}
-- ]
-- ============================================================
CREATE TABLE IF NOT EXISTS tipos_bien (
    id                       SERIAL PRIMARY KEY,
    nombre                   VARCHAR(100) NOT NULL,
    caracteristicas_tipicas  JSONB DEFAULT '[]'::jsonb,
    activo                   BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- TABLA: especificaciones_tecnicas
-- Documento de Especificación Técnica (ET) de un pedido
-- Campos según formato oficial (TDR / Formato N° 01)
-- ============================================================
CREATE TABLE IF NOT EXISTS especificaciones_tecnicas (
    id                       SERIAL PRIMARY KEY,
    -- Tabla superior del documento oficial
    centro_costo_id          INTEGER REFERENCES dependencias(id),
    actividad_operativa_id   INTEGER REFERENCES actividades_operativas(id),
    denominacion_adquisicion TEXT NOT NULL,
    numero_pedido            VARCHAR(20) NOT NULL,   -- Solo dígitos: 002425
    meta_anio                VARCHAR(20),             -- Formato: 0039-2026
    fecha_pedido             DATE NOT NULL,
    anio_fiscal              INTEGER NOT NULL,
    -- Campos heredados (se mantienen por compatibilidad pero ya no se usan directamente)
    centro_costo             VARCHAR(150),
    actividad_operativa      VARCHAR(150),
    meta                     VARCHAR(100),
    finalidad_publica        TEXT,
    objetivo                 TEXT,
    -- Proveedor (no aparece en la tabla superior del TDR, pero se vincula)
    proveedor_id             INTEGER NOT NULL REFERENCES proveedores(id),
    estado                   VARCHAR(20) NOT NULL DEFAULT 'BORRADOR'
                                 CHECK (estado IN ('BORRADOR', 'FINALIZADA', 'ANULADA')),
    creado_por               INTEGER NOT NULL REFERENCES usuarios(id),
    finalizado_por           INTEGER REFERENCES usuarios(id),
    fecha_creacion           TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_finalizacion       TIMESTAMP,
    motivo_anulacion         TEXT,

    CONSTRAINT uq_et_numero_pedido UNIQUE (numero_pedido)
);

CREATE INDEX IF NOT EXISTS idx_et_numero_pedido
    ON especificaciones_tecnicas (numero_pedido);

CREATE INDEX IF NOT EXISTS idx_et_anio_fiscal
    ON especificaciones_tecnicas (anio_fiscal);

CREATE INDEX IF NOT EXISTS idx_et_proveedor
    ON especificaciones_tecnicas (proveedor_id);

-- ============================================================
-- TABLA: items_especificacion
-- Bienes individuales dentro de una Especificación Técnica
-- Las características confirmadas se guardan en JSONB:
-- [
--   {"nombre": "Procesador", "valor": "Intel Core i7-13650HX", "sugerida": false},
--   {"nombre": "RAM", "valor": "16 GB DDR5 4800 MHz", "sugerida": false}
-- ]
-- ============================================================
CREATE TABLE IF NOT EXISTS items_especificacion (
    id                  SERIAL PRIMARY KEY,
    especificacion_id   INTEGER NOT NULL REFERENCES especificaciones_tecnicas(id)
                            ON DELETE CASCADE,
    tipo_bien_id        INTEGER NOT NULL REFERENCES tipos_bien(id),
    descripcion         TEXT NOT NULL,
    clasificador        VARCHAR(50),
    unidad_medida       VARCHAR(30) NOT NULL DEFAULT 'UNIDAD',
    cantidad            NUMERIC(10,2) NOT NULL DEFAULT 1.00
                            CHECK (cantidad > 0),
    caracteristicas     JSONB DEFAULT '[]'::jsonb,
    -- Nuevos campos según formato oficial
    condiciones_previas TEXT DEFAULT 'El bien debe ser entregado en óptimas condiciones de funcionamiento.
El bien deberá de ser original.
El bien deberá incluir accesorios necesarios para su funcionamiento.
Los bienes deberán de estar debidamente sellados.',
    imagen_referencial  VARCHAR(300),
    reglamentos_tecnicos TEXT DEFAULT 'No aplica'
);

CREATE INDEX IF NOT EXISTS idx_item_especificacion
    ON items_especificacion (especificacion_id);

-- ============================================================
-- TABLA: contador_fichas
-- Tabla auxiliar para correlativo atómico anual de Fichas Técnicas
-- Usa SELECT ... FOR UPDATE para garantizar unicidad en
-- transacciones concurrentes (más portable que SEQUENCE por año)
-- ============================================================
CREATE TABLE IF NOT EXISTS contador_fichas (
    anio            INTEGER PRIMARY KEY,
    ultimo_numero   INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- TABLA: fichas_tecnicas
-- Ficha Técnica (FT) de un bien físico recibido
-- ============================================================
CREATE TABLE IF NOT EXISTS fichas_tecnicas (
    id                    SERIAL PRIMARY KEY,
    numero_correlativo    INTEGER,
    anio                  INTEGER NOT NULL,
    especificacion_id     INTEGER NOT NULL REFERENCES especificaciones_tecnicas(id),
    item_id               INTEGER NOT NULL REFERENCES items_especificacion(id),

    -- Datos manuales del bien recibido
    marca                 VARCHAR(100),
    modelo                VARCHAR(100),
    color                 VARCHAR(50),
    numero_serie          VARCHAR(100) NOT NULL,
    estado_fisico         VARCHAR(30)
                              CHECK (estado_fisico IN ('NUEVO', 'BUENO', 'REGULAR', 'MALO')),
    observaciones         TEXT,
    carta_levantamiento   VARCHAR(100),

    -- Datos del proveedor (heredados, editables si hubo cambio)
    proveedor_ruc         VARCHAR(11),
    proveedor_razon       VARCHAR(250),
    proveedor_direccion   VARCHAR(300),
    proveedor_telefono    VARCHAR(30),
    proveedor_correo      VARCHAR(150),

    -- Responsable que recibe
    responsable_id        INTEGER REFERENCES responsables(id),

    -- Características verificadas del bien (copia confirmada)
    caracteristicas_verificadas JSONB DEFAULT '[]'::jsonb,

    -- Checklist de verificación obligatorio
    -- {"marca_coincide": true, "modelo_coincide": true, ...}
    checklist             JSONB DEFAULT '{}'::jsonb,

    -- Estado del documento
    estado                VARCHAR(20) NOT NULL DEFAULT 'BORRADOR'
                              CHECK (estado IN ('BORRADOR', 'FINALIZADA', 'ANULADA')),

    -- Auditoría
    creado_por            INTEGER NOT NULL REFERENCES usuarios(id),
    finalizado_por        INTEGER REFERENCES usuarios(id),
    fecha_creacion        TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_finalizacion    TIMESTAMP,
    motivo_anulacion      TEXT,

    -- =============================================
    -- RESTRICCIONES CLAVE
    -- =============================================

    -- Unicidad del número de serie en TODO el sistema
    -- El número se normaliza con UPPER(TRIM(...)) antes de insertar
    CONSTRAINT uq_ficha_numero_serie UNIQUE (numero_serie),

    -- Unicidad del correlativo por año (ej: 181-2026 solo existe una vez)
    CONSTRAINT uq_ficha_correlativo_anio UNIQUE (numero_correlativo, anio)
);

CREATE INDEX IF NOT EXISTS idx_ft_especificacion
    ON fichas_tecnicas (especificacion_id);

CREATE INDEX IF NOT EXISTS idx_ft_numero_serie
    ON fichas_tecnicas (numero_serie);

CREATE INDEX IF NOT EXISTS idx_ft_correlativo_anio
    ON fichas_tecnicas (numero_correlativo, anio);

CREATE INDEX IF NOT EXISTS idx_ft_anio
    ON fichas_tecnicas (anio);

-- ============================================================
-- DATOS INICIALES
-- ============================================================

-- Contador para el año 2026
INSERT INTO contador_fichas (anio, ultimo_numero)
VALUES (2026, 0)
ON CONFLICT (anio) DO NOTHING;

-- Tipos de bien con características técnicas típicas
INSERT INTO tipos_bien (nombre, caracteristicas_tipicas) VALUES
(
    'Unidad Central de Procesamiento (Desktop)',
    '[
        {"nombre": "Procesador", "valor_sugerido": "Intel Core i7 13va Gen"},
        {"nombre": "Memoria RAM", "valor_sugerido": "16 GB DDR5 4800 MHz"},
        {"nombre": "Almacenamiento", "valor_sugerido": "SSD 1 TB NVMe"},
        {"nombre": "Gráficos", "valor_sugerido": "Intel UHD Graphics integrado"},
        {"nombre": "Puertos USB", "valor_sugerido": "4x USB 3.2, 2x USB 2.0"},
        {"nombre": "Video", "valor_sugerido": "1x HDMI, 1x VGA"},
        {"nombre": "Red", "valor_sugerido": "Ethernet RJ-45 Gigabit + WiFi"},
        {"nombre": "Sistema Operativo", "valor_sugerido": "Windows 11 Pro"},
        {"nombre": "Accesorios", "valor_sugerido": "Teclado USB y Mouse USB"}
    ]'::jsonb
),
(
    'Laptop',
    '[
        {"nombre": "Procesador", "valor_sugerido": "Intel Core i7 13va Gen"},
        {"nombre": "Memoria RAM", "valor_sugerido": "16 GB DDR5"},
        {"nombre": "Almacenamiento", "valor_sugerido": "SSD 512 GB NVMe"},
        {"nombre": "Pantalla", "valor_sugerido": "15.6 pulgadas FHD IPS"},
        {"nombre": "Gráficos", "valor_sugerido": "Intel Iris Xe"},
        {"nombre": "Batería", "valor_sugerido": "Hasta 8 horas"},
        {"nombre": "Sistema Operativo", "valor_sugerido": "Windows 11 Pro"},
        {"nombre": "Conectividad", "valor_sugerido": "WiFi 6, Bluetooth 5.2"}
    ]'::jsonb
),
(
    'Monitor',
    '[
        {"nombre": "Tamaño de Pantalla", "valor_sugerido": "21.5 pulgadas"},
        {"nombre": "Resolución", "valor_sugerido": "1920 x 1080 (Full HD)"},
        {"nombre": "Tipo de Panel", "valor_sugerido": "IPS"},
        {"nombre": "Puertos de Video", "valor_sugerido": "1x HDMI, 1x VGA"},
        {"nombre": "Brillo", "valor_sugerido": "250 cd/m²"}
    ]'::jsonb
),
(
    'Impresora',
    '[
        {"nombre": "Tipo", "valor_sugerido": "Inyección de tinta / Multifuncional"},
        {"nombre": "Funciones", "valor_sugerido": "Impresión, copia, escaneo"},
        {"nombre": "Velocidad de impresión", "valor_sugerido": "33 ppm negro, 15 ppm color"},
        {"nombre": "Conectividad", "valor_sugerido": "USB 2.0, WiFi"},
        {"nombre": "Sistema de tinta", "valor_sugerido": "Tanque de tinta continua (EcoTank)"}
    ]'::jsonb
),
(
    'Switch de Red',
    '[
        {"nombre": "Puertos", "valor_sugerido": "24 puertos RJ-45 Gigabit"},
        {"nombre": "Gestión", "valor_sugerido": "Administrable Layer 2"},
        {"nombre": "Velocidad", "valor_sugerido": "10/100/1000 Mbps"},
        {"nombre": "PoE", "valor_sugerido": "No"},
        {"nombre": "Montaje", "valor_sugerido": "Rack 19 pulgadas 1U"}
    ]'::jsonb
),
(
    'Alicate Crimping / Herramienta de Red',
    '[
        {"nombre": "Tipo", "valor_sugerido": "Crimping para RJ-45 / RJ-11"},
        {"nombre": "Material", "valor_sugerido": "Acero al carbono con mango ergonómico"},
        {"nombre": "Compatibilidad", "valor_sugerido": "Cat5e, Cat6, Cat6a"}
    ]'::jsonb
),
(
    'Access Point / Router',
    '[
        {"nombre": "Estándar WiFi", "valor_sugerido": "WiFi 6 (802.11ax)"},
        {"nombre": "Banda", "valor_sugerido": "Doble banda 2.4 GHz + 5 GHz"},
        {"nombre": "Puertos", "valor_sugerido": "1x WAN Gigabit, 4x LAN Gigabit"},
        {"nombre": "Alimentación", "valor_sugerido": "PoE 802.3af/at"}
    ]'::jsonb
),
(
    'UPS / Estabilizador',
    '[
        {"nombre": "Capacidad", "valor_sugerido": "1000 VA / 600 W"},
        {"nombre": "Tipo", "valor_sugerido": "Línea interactiva"},
        {"nombre": "Tiempo de respaldo", "valor_sugerido": "10-15 minutos a media carga"},
        {"nombre": "Tomacorrientes", "valor_sugerido": "6 salidas con respaldo"}
    ]'::jsonb
)
ON CONFLICT DO NOTHING;

-- Usuario administrador inicial
-- Contraseña: ogti2026 (se cambiará al primer inicio)
-- El hash se generará al ejecutar el seed desde Python
