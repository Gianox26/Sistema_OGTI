"""
Rutas de catálogos de apoyo del Sistema OGTI.
Proveedores, Responsables, Dependencias y Tipos de Bien.
"""
from flask import Blueprint, request, jsonify
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
    """Lista todos los tipos de bien con sus características típicas."""
    tipos = query(
        """
        SELECT id, nombre, caracteristicas_tipicas
        FROM tipos_bien
        WHERE activo = TRUE
        ORDER BY nombre
        """
    )
    return jsonify(tipos)


@catalogos_bp.route('/api/tipos-bien', methods=['POST'])
@login_required
def crear_tipo_bien():
    """Registra un nuevo tipo de bien con sus características típicas."""
    data = request.get_json()
    nombre = data.get('nombre', '').strip()

    if not nombre:
        return jsonify({'error': 'El nombre del tipo de bien es obligatorio'}), 400

    import json
    caracteristicas = data.get('caracteristicas_tipicas', [])

    resultado = execute(
        """
        INSERT INTO tipos_bien (nombre, caracteristicas_tipicas)
        VALUES (%s, %s::jsonb)
        RETURNING id, nombre, caracteristicas_tipicas
        """,
        (nombre, json.dumps(caracteristicas)),
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
