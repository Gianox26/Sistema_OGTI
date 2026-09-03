# Contexto Técnico y Guía de Instalación: Sistema OGTI

Este documento contiene la especificación técnica completa, arquitectura, esquema de base de datos, procedimientos de instalación y despliegue, y flujos de trabajo del **Sistema OGTI** de la **Municipalidad Provincial de San Román — Juliaca**.

---

## 1. Visión General del Proyecto

- **Nombre Institucional:** Sistema OGTI (Oficina General de Tecnologías de la Información).
- **Entidad:** Municipalidad Provincial de San Román — Juliaca (Puno, Perú).
- **Propósito:** Gestión integral, catálogo técnico y generación automatizada de documentos oficiales en Microsoft Word (`.docx`) para:
  1. **Especificaciones Técnicas (ET):** Formulación de Términos de Referencia (TDR) y requerimientos de compra de bienes informáticos/TI.
  2. **Fichas Técnicas (FT):** Registro, verificación física y asignación de bienes tecnológicos recibidos (PCs, Laptops, Impresoras, Redes, etc.) vinculados a cartas de almacén institucionales.

---

## 2. Stack Tecnológico

| Componente | Tecnología | Descripción / Rol |
| :--- | :--- | :--- |
| **Lenguaje Backend** | Python 3.10+ | Lógica de negocio y procesamiento documental |
| **Framework Web** | Flask 3.0.3 | Web App modular orientada a Blueprints |
| **Base de Datos** | PostgreSQL 14+ | Sistema gestor de datos relacionales con soporte JSONB |
| **Conector DB** | `psycopg2-binary` (2.9.9) | Driver de conexión a PostgreSQL con `RealDictCursor` |
| **Motor de Documentos** | `docxtpl` (0.18.0) + `python-docx` | Generación de `.docx` rellenando plantillas Word con Jinja2 |
| **Extracción Inteligente (AI/Web)** | Firecrawl API & BeautifulSoup4 | Búsqueda y scraping de especificaciones técnicas de hardware |
| **Frontend** | HTML5 + Vanilla CSS3 | Interfaz web institucional con dark/light palette, responsive |
| **Seguridad** | Werkzeug Security | Hashing de contraseñas (`pbkdf2:sha256`), sesiones Flask |

---

## 3. Estructura del Proyecto

```text
Sistema_OGTI/
├── app.py                     # Entry point y factoría de la app Flask
├── config.py                  # Configuración centralizada del sistema
├── .env.example               # Plantilla de variables de entorno
├── requirements.txt           # Dependencias de Python
├── setup_postgres.sh          # Script automatizado de instalación de PostgreSQL (Linux)
├── init_db.py                 # Script Python de inicialización y carga de datos semilla
├── preparar_plantillas.py     # Utilidad para validación/preparación de plantillas Word
├── sql/
│   ├── schema.sql             # Esquema DDL completo de la base de datos
│   └── migracion_*.sql        # Scripts de migraciones (001 a 010)
├── routes/
│   ├── auth.py                # Autenticación, login/logout, cambio de clave
│   ├── catalogos.py           # CRUD de Tipos de Bien, Marcas, Modelos, Dependencias
│   ├── especificaciones.py    # Formulación y control de Especificaciones Técnicas (ET)
│   ├── fichas.py              # Registro y verificación de Fichas Técnicas (FT)
│   └── historial.py           # Historial y auditoría de documentos generados
├── services/
│   ├── __init__.py / db.py    # Conexión DB, helpers query() y execute_transaction()
│   ├── docx_service.py        # Inyección de datos en plantillas .docx
│   ├── firecrawl_service.py   # Servicio de búsqueda de especificaciones técnicas web
│   └── numeracion.py          # Generador de correlativos atómicos por año
├── plantillas_docx/
│   ├── especificacion_tecnica_tpl.docx  # Plantilla oficial de ET
│   └── ficha_tecnica_tpl.docx           # Plantilla oficial de FT
├── templates/                 # Plantillas HTML (Jinja2)
└── static/                    # Archivos estáticos (CSS, JS, imágenes)
```

---

## 4. Esquema de Base de Datos (Modelado Entidad-Relación)

Las tablas principales en PostgreSQL son:

1. **`usuarios`**: Control de acceso (`id`, `username`, `password_hash`, `nombre_completo`, `cargo`, `rol`: `JEFE_OGTI` o `OPERADOR`).
2. **`dependencias`**: Áreas u oficinas de la Municipalidad (`id`, `nombre`, `edificio`, `pabellon`).
3. **`proveedores`**: Registro de empresas proveedoras (`id`, `ruc`, `razon_social`, `direccion`, `telefono`, `correo`).
4. **`responsables`**: Personal destinatario de bienes (`id`, `nombre`, `cargo`, `dependencia_id`).
5. **`tipos_bien`**: Catálogo de tipos de equipos (`id`, `nombre`, `caracteristicas_tipicas` [JSONB]).
6. **`especificaciones_tecnicas`**: Cabecera de pedido de ET (`id`, `numero_pedido`, `denominacion_adquisicion`, `centro_costo_id`, `actividad_operativa_id`, `meta_anio`, `fecha_pedido`, `anio_fiscal`, `estado`: `BORRADOR` / `FINALIZADA` / `ANULADA`).
7. **`items_especificacion`**: Bienes contenidos en una ET (`id`, `especificacion_id`, `tipo_bien_id`, `descripcion`, `clasificador`, `unidad_medida`, `cantidad`, `caracteristicas` [JSONB]).
8. **`fichas_tecnicas`**: Ficha individual de equipo recibido (`id`, `numero_correlativo`, `anio`, `especificacion_id`, `item_id`, `marca`, `modelo`, `numero_serie` [ÚNICO], `estado_fisico`, `carta_levantamiento`, `responsable_id`, `caracteristicas_verificadas` [JSONB], `checklist` [JSONB]).
9. **`contador_fichas`**: Control atómico del número correlativo de ficha por año (`anio`, `ultimo_numero`).

---

## 5. Guía Completa de Instalación y Configuración Paso a Paso

### Prerrequisitos
- Sistema Operativo Linux (Ubuntu/Debian recomendado).
- Python 3.10 o superior (`python3 --version`).
- PostgreSQL 14 o superior instalado y corriendo (`sudo service postgresql status`).
- Git y permisos de `sudo`.

### Paso 1: Clonar / Posicionarse en el proyecto
```bash
cd /home/fulanito/Sistema_OGTI
```

### Paso 2: Crear entorno virtual e instalar dependencias Python
```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias requeridas
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 3: Configurar variables de entorno (`.env`)
Copiar la plantilla `.env.example` hacia `.env`:
```bash
cp .env.example .env
```
Contenido de `.env`:
```env
# API Key opcional de Firecrawl para renderizado JS de specs de marcas/modelos
FIRECRAWL_API_KEY=

# Clave secreta Flask para cookies/sesiones
SECRET_KEY=ogti-san-roman-juliaca-2026-dev

# Credenciales PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sistema_ogti
DB_USER=fulanito
DB_PASSWORD=ogti2026
```

### Paso 4: Configuración e Inicialización Automatizada de PostgreSQL
Se puede ejecutar el script de instalación automática:
```bash
sudo bash setup_postgres.sh
```
El script realiza lo siguiente:
1. Crea el rol `fulanito` con contraseña `ogti2026` en PostgreSQL.
2. Crea la base de datos `sistema_ogti`.
3. Ejecuta `sql/schema.sql` para crear todas las tablas, índices y datos iniciales.
4. Ejecuta `python3 init_db.py` para crear los usuarios por defecto y dependencias.

*Alternativa Manual:*
```bash
# Crear BD y usuario via psql
sudo -u postgres psql -c "CREATE ROLE fulanito WITH LOGIN CREATEDB PASSWORD 'ogti2026';"
sudo -u postgres createdb -O fulanito sistema_ogti

# Cargar esquema SQL
PGPASSWORD=ogti2026 psql -h localhost -U fulanito -d sistema_ogti -f sql/schema.sql

# Cargar usuarios y dependencias semilla
export DB_PASSWORD=ogti2026
python3 init_db.py
```

### Paso 5: Iniciar la Aplicación Web
```bash
export DB_PASSWORD=ogti2026
python3 app.py
```
La aplicación estará disponible en: **`http://localhost:8000`**

---

## 6. Usuarios y Credenciales Predeterminadas

| Usuario | Contraseña | Rol | Permisos |
| :--- | :--- | :--- | :--- |
| `admin` | `ogti2026` | `JEFE_OGTI` | Control total, aprobación/finalización de documentos, catálogos |
| `operador` | `ogti2026` | `OPERADOR` | Registro y edición de ET/FT en borrador, consultas |

---

## 7. Reglas de Negocio Clave

1. **Unicidad de Número de Serie:** La columna `numero_serie` en `fichas_tecnicas` es única a nivel de toda la base de datos (`UPPER(TRIM(numero_serie))`). No se permite registrar dos fichas con la misma serie.
2. **Correlativo Atómico de Fichas:** El número correlativo de Ficha Técnica (ej: `181-2026`) se incrementa mediante transacciones con `SELECT ... FOR UPDATE` en `contador_fichas` por cada año fiscal.
3. **Cartas de Almacén:** La carta de almacén de una FT se conforma ingresando el correlativo y adjuntando el sufijo institucional (ej: `058/2026-MPSR-J/OGA/OL/AC/WDB`).
4. **Búsqueda Automatizada de Hardware:** El servicio `firecrawl_service.py` permite al usuario ingresar una Marca + Modelo y buscar automáticamente sus especificaciones técnicas reales en la web para autocompletar la tabla de características.
5. **Exportación DOCX Institucional:** `docx_service.py` lee las plantillas `.docx` con tags Jinja (`{{ denominacion_adquisicion }}`, `{% for item in items %}`, etc.) y produce un documento listo para firma e impresión institucional.

---

## 8. Comandos Útiles de Mantenimiento

- **Ejecutar migraciones pendientes:**
  ```bash
  PGPASSWORD=ogti2026 psql -h localhost -U fulanito -d sistema_ogti -f sql/migracion_010_et_externa.sql
  ```
- **Resetear datos a estado inicial:**
  ```bash
  python3 init_db.py
  ```
