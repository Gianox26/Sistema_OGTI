"""
Rutas de catálogos de apoyo del Sistema OGTI.
Proveedores, Responsables, Dependencias y Tipos de Bien.
"""
from flask import Blueprint, request, jsonify
import os
from services.db import query, execute
from routes.auth import login_required

catalogos_bp = Blueprint('catalogos', __name__)


# ============================================================
# PROVEEDORES
# ============================================================

@catalogos_bp.route('/api/proveedores', methods=['GET'])
@login_required
def listar_proveedores():
    """Lista todos los proveedores activos."""
    proveedores = query(
        """
        SELECT id, ruc, razon_social, direccion, telefono, correo
        FROM proveedores
        WHERE activo = TRUE
        ORDER BY razon_social
        """
    )
    return jsonify(proveedores)


@catalogos_bp.route('/api/proveedores', methods=['POST'])
@login_required
def crear_proveedor():
    """Registra un nuevo proveedor."""
    data = request.get_json()

    ruc = data.get('ruc', '').strip()
    razon_social = data.get('razon_social', '').strip()

    if not ruc or not razon_social:
        return jsonify({'error': 'RUC y razón social son obligatorios'}), 400

    if len(ruc) != 11 or not ruc.isdigit():
        return jsonify({'error': 'El RUC debe tener exactamente 11 dígitos numéricos'}), 400

    # Verificar unicidad de RUC
    existente = query(
        "SELECT id FROM proveedores WHERE ruc = %s",
        (ruc,),
        fetchone=True
    )
    if existente:
        return jsonify({'error': f'Ya existe un proveedor con RUC {ruc}'}), 409

    resultado = execute(
        """
        INSERT INTO proveedores (ruc, razon_social, direccion, telefono, correo)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, ruc, razon_social, direccion, telefono, correo
        """,
        (
            ruc,
            razon_social,
            data.get('direccion', '').strip(),
            data.get('telefono', '').strip(),
            data.get('correo', '').strip(),
        ),
        returning=True
    )
    return jsonify(resultado), 201


@catalogos_bp.route('/api/proveedores/<int:id>', methods=['PUT'])
@login_required
def actualizar_proveedor(id):
    """Actualiza los datos de un proveedor."""
    data = request.get_json()
    execute(
        """
        UPDATE proveedores
        SET razon_social = COALESCE(%s, razon_social),
            direccion = COALESCE(%s, direccion),
            telefono = COALESCE(%s, telefono),
            correo = COALESCE(%s, correo)
        WHERE id = %s
        """,
        (
            data.get('razon_social'),
            data.get('direccion'),
            data.get('telefono'),
            data.get('correo'),
            id,
        )
    )
    return jsonify({'message': 'Proveedor actualizado correctamente'})


# ============================================================
# DEPENDENCIAS
# ============================================================

@catalogos_bp.route('/api/dependencias', methods=['GET'])
@login_required
def listar_dependencias():
    """Lista todas las dependencias activas."""
    deps = query(
        """
        SELECT id, nombre, edificio, pabellon
        FROM dependencias
        WHERE activo = TRUE
        ORDER BY nombre
        """
    )
    return jsonify(deps)


@catalogos_bp.route('/api/dependencias', methods=['POST'])
@login_required
def crear_dependencia():
    """Registra una nueva dependencia."""
    data = request.get_json()
    nombre = data.get('nombre', '').strip()

    if not nombre:
        return jsonify({'error': 'El nombre de la dependencia es obligatorio'}), 400

    resultado = execute(
        """
        INSERT INTO dependencias (nombre, edificio, pabellon)
        VALUES (%s, %s, %s)
        RETURNING id, nombre, edificio, pabellon
        """,
        (nombre, data.get('edificio', '').strip(), data.get('pabellon', '').strip()),
        returning=True
    )
    return jsonify(resultado), 201


# ============================================================
# RESPONSABLES
# ============================================================

@catalogos_bp.route('/api/responsables', methods=['GET'])
@login_required
def listar_responsables():
    """Lista todos los responsables activos, con nombre de dependencia."""
    responsables = query(
        """
        SELECT r.id, r.nombre, r.cargo, r.telefono, r.correo,
               r.dependencia_id, d.nombre AS dependencia_nombre
        FROM responsables r
        LEFT JOIN dependencias d ON r.dependencia_id = d.id
        WHERE r.activo = TRUE
        ORDER BY r.nombre
        """
    )
    return jsonify(responsables)


@catalogos_bp.route('/api/responsables', methods=['POST'])
@login_required
def crear_responsable():
    """Registra un nuevo responsable."""
    data = request.get_json()
    nombre = data.get('nombre', '').strip()

    if not nombre:
        return jsonify({'error': 'El nombre del responsable es obligatorio'}), 400

    resultado = execute(
        """
        INSERT INTO responsables (nombre, cargo, telefono, correo, dependencia_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, nombre, cargo, telefono, correo, dependencia_id
        """,
        (
            nombre,
            data.get('cargo', '').strip(),
            data.get('telefono', '').strip(),
            data.get('correo', '').strip(),
            data.get('dependencia_id'),
        ),
        returning=True
    )
    return jsonify(resultado), 201


# ============================================================
# TIPOS DE BIEN
# ============================================================

@catalogos_bp.route('/api/tipos-bien', methods=['GET'])
@login_required
def listar_tipos_bien():
    """Lista todos los tipos de bien con sus características típicas y flag requiere_serie."""
    tipos = query(
        """
        SELECT id, nombre, caracteristicas_tipicas, requiere_serie
        FROM tipos_bien
        WHERE activo = TRUE
        ORDER BY nombre
        """
    )
    return jsonify(tipos)


@catalogos_bp.route('/api/tipos-bien', methods=['POST'])
@login_required
def crear_tipo_bien():
    """Registra un nuevo tipo de bien con sus características típicas y flag requiere_serie."""
    data = request.get_json()
    nombre = data.get('nombre', '').strip()

    if not nombre:
        return jsonify({'error': 'El nombre del tipo de bien es obligatorio'}), 400

    import json
    caracteristicas = data.get('caracteristicas_tipicas', [])
    requiere_serie = bool(data.get('requiere_serie', True))

    resultado = execute(
        """
        INSERT INTO tipos_bien (nombre, caracteristicas_tipicas, requiere_serie)
        VALUES (%s, %s::jsonb, %s)
        RETURNING id, nombre, caracteristicas_tipicas, requiere_serie
        """,
        (nombre, json.dumps(caracteristicas), requiere_serie),
        returning=True
    )
    return jsonify(resultado), 201


# ============================================================
# ACTIVIDADES OPERATIVAS
# ============================================================

@catalogos_bp.route('/api/actividades-operativas', methods=['GET'])
@login_required
def listar_actividades():
    """Lista todas las actividades operativas activas."""
    actividades = query(
        """
        SELECT id, codigo, nombre
        FROM actividades_operativas
        WHERE activo = TRUE
        ORDER BY codigo
        """
    )
    return jsonify(actividades)


@catalogos_bp.route('/api/actividades-operativas', methods=['POST'])
@login_required
def crear_actividad():
    """Registra una nueva actividad operativa."""
    data = request.get_json()
    codigo = data.get('codigo', '').strip().upper()
    nombre = data.get('nombre', '').strip()

    if not codigo or not nombre:
        return jsonify({'error': 'Código y nombre son obligatorios'}), 400

    existente = query(
        "SELECT id FROM actividades_operativas WHERE codigo = %s",
        (codigo,),
        fetchone=True
    )
    if existente:
        return jsonify({'error': f'Ya existe una actividad con código {codigo}'}), 409

    resultado = execute(
        """
        INSERT INTO actividades_operativas (codigo, nombre)
        VALUES (%s, %s)
        RETURNING id, codigo, nombre
        """,
        (codigo, nombre),
        returning=True
    )
    return jsonify(resultado), 201


# ============================================================
# PLANTILLAS DE CARACTERÍSTICAS DE BIENES (por Marca y Modelo)
# ============================================================

import json

@catalogos_bp.route('/api/plantillas-caracteristicas', methods=['POST'])
@login_required
def guardar_plantilla_caracteristicas():
    """Guarda o actualiza una plantilla de características para un par marca + modelo."""
    data = request.get_json()
    marca = (data.get('marca') or '').strip().upper()
    modelo = (data.get('modelo') or '').strip().upper()
    caracteristicas = data.get('caracteristicas', [])

    if not marca or not modelo:
        return jsonify({'error': 'Marca y modelo son requeridos'}), 400

    if not caracteristicas:
        return jsonify({'error': 'Debe incluir al menos una característica'}), 400

    resultado = execute(
        """
        INSERT INTO plantillas_caracteristicas (marca, modelo, caracteristicas)
        VALUES (%s, %s, %s::jsonb)
        ON CONFLICT (marca, modelo)
        DO UPDATE SET caracteristicas = EXCLUDED.caracteristicas, fecha_creacion = NOW()
        RETURNING id, marca, modelo, caracteristicas
        """,
        (marca, modelo, json.dumps(caracteristicas)),
        returning=True
    )
    return jsonify(resultado), 200


@catalogos_bp.route('/api/plantillas-caracteristicas/buscar', methods=['GET'])
@login_required
def buscar_plantilla_caracteristicas():
    """Busca una plantilla de características guardada por marca y modelo."""
    marca = (request.args.get('marca') or '').strip().upper()
    modelo = (request.args.get('modelo') or '').strip().upper()

    if not marca or not modelo:
        return jsonify(None)

    plantilla = query(
        """
        SELECT id, marca, modelo, caracteristicas, fecha_creacion
        FROM plantillas_caracteristicas
        WHERE UPPER(marca) = %s AND UPPER(modelo) = %s
        """,
        (marca, modelo),
        fetchone=True
    )
    return jsonify(plantilla)


@catalogos_bp.route('/api/catalogos/buscar-modelo', methods=['GET'])
@login_required
def buscar_modelo_cache_aside():
    """
    Patrón Cache-Aside:
    1. Normaliza marca y modelo.
    2. Consulta la base de datos (catalogo_modelos). Si existe, retorna al instante.
    3. Si NO existe en BD, realiza una búsqueda automática en la web con Firecrawl.
    4. Guarda el resultado en catalogo_modelos (fuente = 'WEB', verificado = False).
    5. Retorna las características para que el usuario las revise y confirme.
    """
    from services.firecrawl_service import buscar_caracteristicas_web

    marca = (request.args.get('marca') or '').strip().upper()
    modelo = (request.args.get('modelo') or '').strip().upper()

    if not marca or not modelo:
        return jsonify({'error': 'Marca y modelo son requeridos'}), 400

    # 1. Consulta en PostgreSQL (Cache Hit)
    cat_item = query(
        """
        SELECT id, marca, modelo, caracteristicas, fuente, verificado
        FROM catalogo_modelos
        WHERE UPPER(marca) = %s AND UPPER(modelo) = %s
        """,
        (marca, modelo),
        fetchone=True
    )

    if cat_item:
        return jsonify({
            'encontrado': True,
            'origen': 'DATABASE',
            'verificado': cat_item['verificado'],
            'fuente': cat_item['fuente'],
            'caracteristicas': cat_item['caracteristicas'],
            'mensaje': 'Características cargadas desde el catálogo interno.' if cat_item['verificado']
                       else 'Cargado desde borrador previo — verificar contra el equipo físico.'
        })

    # 2. Cache Miss → Búsqueda Web con Firecrawl
    specs_web = buscar_caracteristicas_web(marca, modelo)

    # 3. Guardar en catalogo_modelos como no verificado
    try:
        execute(
            """
            INSERT INTO catalogo_modelos (marca, modelo, caracteristicas, fuente, verificado)
            VALUES (%s, %s, %s::jsonb, 'WEB', FALSE)
            ON CONFLICT (marca, modelo) DO NOTHING
            """,
            (marca, modelo, json.dumps(specs_web))
        )
    except Exception as e:
        print(f"Error guardando en catalogo_modelos: {e}")

    return jsonify({
        'encontrado': True,
        'origen': 'WEB',
        'verificado': False,
        'fuente': 'WEB',
        'caracteristicas': specs_web,
        'mensaje': '🌐 Sugerido desde la web — verificar contra el equipo físico'
    })


@catalogos_bp.route('/api/catalogos/caracteristicas-web', methods=['GET'])
@login_required
def caracteristicas_web():
    """
    Busca en la web (Firecrawl, con respaldo DuckDuckGo) las especificaciones
    técnicas a partir de la marca y modelo del producto. No usa caché: siempre
    consulta la web para listar las características del fabricante.
    """
    from services.firecrawl_service import buscar_caracteristicas_web

    marca = (request.args.get('marca') or '').strip()
    modelo = (request.args.get('modelo') or '').strip()

    if not marca and not modelo:
        return jsonify({'error': 'Ingrese al menos la marca o el modelo'}), 400

    specs = buscar_caracteristicas_web(marca, modelo)
    return jsonify({
        'marca': marca,
        'modelo': modelo,
        'fuente': 'firecrawl' if os.environ.get('FIRECRAWL_API_KEY') else 'web-fallback',
        'caracteristicas': specs
    })




# ============================================================
# Renderizado de páginas HTML de catálogos
# ============================================================

from flask import render_template

@catalogos_bp.route('/catalogos/proveedores')
@login_required
def pagina_proveedores():
    return render_template('catalogos/proveedores.html')

@catalogos_bp.route('/catalogos/responsables')
@login_required
def pagina_responsables():
    return render_template('catalogos/responsables.html')

@catalogos_bp.route('/catalogos/dependencias')
@login_required
def pagina_dependencias():
    return render_template('catalogos/dependencias.html')

@catalogos_bp.route('/catalogos/tipos-bien')
@login_required
def pagina_tipos_bien():
    return render_template('catalogos/tipos_bien.html')

@catalogos_bp.route('/catalogos/actividades-operativas')
@login_required
def pagina_actividades():
    return render_template('catalogos/actividades_operativas.html')
