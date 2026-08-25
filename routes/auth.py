"""
Rutas de autenticación del Sistema OGTI.
Inicio de sesión, cierre de sesión y gestión de usuarios.

Contraseñas almacenadas con hash pbkdf2:sha256 (werkzeug.security).
"""
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from services.db import query, execute
from functools import wraps

auth_bp = Blueprint('auth', __name__)


# ============================================================
# Decoradores de acceso
# ============================================================

def login_required(f):
    """Decorador: exige que el usuario haya iniciado sesión."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debe iniciar sesión para acceder al sistema.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def rol_required(rol):
    """
    Decorador: exige que el usuario tenga un rol específico.
    Validación en backend — no depende de que la UI oculte botones.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'usuario_id' not in session:
                flash('Debe iniciar sesión para acceder al sistema.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('usuario_rol') != rol:
                flash(f'No tiene permisos para esta acción. Se requiere rol: {rol}', 'danger')
                return redirect(url_for('auth.dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================
# Rutas
# ============================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Pantalla de inicio de sesión."""
    if request.method == 'GET':
        # Si ya tiene sesión activa, ir al dashboard
        if 'usuario_id' in session:
            return redirect(url_for('auth.dashboard'))
        return render_template('login.html')

    # POST: validar credenciales
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        flash('Ingrese su usuario y contraseña.', 'warning')
        return render_template('login.html')

    usuario = query(
        "SELECT * FROM usuarios WHERE username = %s AND activo = TRUE",
        (username,),
        fetchone=True
    )

    if not usuario or not check_password_hash(usuario['password_hash'], password):
        flash('Usuario o contraseña incorrectos.', 'danger')
        return render_template('login.html')

    # Establecer sesión
    session['usuario_id'] = usuario['id']
    session['usuario_nombre'] = usuario['nombre_completo']
    session['usuario_rol'] = usuario['rol']
    session['usuario_cargo'] = usuario.get('cargo', '')

    flash(f'Bienvenido(a), {usuario["nombre_completo"]}', 'success')
    return redirect(url_for('auth.dashboard'))


@auth_bp.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/')
@login_required
def dashboard():
    """Pantalla principal del sistema."""
    # Estadísticas rápidas para el dashboard
    stats = {}

    row = query(
        "SELECT COUNT(*) as total FROM especificaciones_tecnicas WHERE estado = 'FINALIZADA'",
        fetchone=True
    )
    stats['et_finalizadas'] = row['total'] if row else 0

    row = query(
        "SELECT COUNT(*) as total FROM especificaciones_tecnicas WHERE estado = 'BORRADOR'",
        fetchone=True
    )
    stats['et_borradores'] = row['total'] if row else 0

    row = query(
        "SELECT COUNT(*) as total FROM fichas_tecnicas WHERE estado = 'FINALIZADA'",
        fetchone=True
    )
    stats['ft_finalizadas'] = row['total'] if row else 0

    row = query(
        "SELECT COUNT(*) as total FROM fichas_tecnicas WHERE estado = 'BORRADOR'",
        fetchone=True
    )
    stats['ft_borradores'] = row['total'] if row else 0

    # Últimas fichas finalizadas
    ultimas_fichas = query(
        """
        SELECT ft.id, ft.numero_correlativo, ft.anio, ft.marca, ft.modelo,
               ft.numero_serie, ft.estado, ft.fecha_finalizacion,
               ie.descripcion AS bien_descripcion,
               u.nombre_completo AS creado_por_nombre
        FROM fichas_tecnicas ft
        JOIN items_especificacion ie ON ft.item_id = ie.id
        LEFT JOIN usuarios u ON ft.creado_por = u.id
        WHERE ft.estado = 'FINALIZADA'
        ORDER BY ft.fecha_finalizacion DESC
        LIMIT 10
        """
    )

    return render_template(
        'dashboard.html',
        stats=stats,
        ultimas_fichas=ultimas_fichas
    )


@auth_bp.route('/usuarios')
@rol_required('JEFE_OGTI')
def usuarios():
    """Pantalla de gestión de cuentas (crear y administrar usuarios)."""
    return render_template('usuarios.html')


# ============================================================
# API: Gestión de usuarios (solo JEFE_OGTI)
# ============================================================

@auth_bp.route('/api/usuarios', methods=['GET'])
@login_required
def listar_usuarios():
    """Lista todos los usuarios activos."""
    usuarios = query(
        "SELECT id, username, nombre_completo, cargo, rol, activo, fecha_creacion "
        "FROM usuarios ORDER BY nombre_completo"
    )
    return jsonify(usuarios)


@auth_bp.route('/api/usuarios', methods=['POST'])
@rol_required('JEFE_OGTI')
def crear_usuario():
    """Crea un nuevo usuario. Solo JEFE_OGTI puede hacerlo."""
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')
    nombre = data.get('nombre_completo', '').strip()
    cargo = data.get('cargo', '').strip()
    rol = data.get('rol', 'OPERADOR')

    if not username or not password or not nombre:
        return jsonify({'error': 'Campos obligatorios: username, password, nombre_completo'}), 400

    if rol not in ('OPERADOR', 'JEFE_OGTI'):
        return jsonify({'error': 'Rol inválido'}), 400

    # Verificar que no exista
    existente = query(
        "SELECT id FROM usuarios WHERE username = %s",
        (username,),
        fetchone=True
    )
    if existente:
        return jsonify({'error': f'El usuario "{username}" ya existe'}), 409

    password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    resultado = execute(
        """
        INSERT INTO usuarios (username, password_hash, nombre_completo, cargo, rol)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, username, nombre_completo, cargo, rol
        """,
        (username, password_hash, nombre, cargo, rol),
        returning=True
    )

    return jsonify(resultado), 201


@auth_bp.route('/api/usuarios/<int:id>/toggle-activo', methods=['PUT'])
@rol_required('JEFE_OGTI')
def toggle_activo_usuario(id):
    """Activa o desactiva una cuenta de usuario. No se puede desactivar a sí mismo."""
    data = request.get_json() or {}
    activo = bool(data.get('activo', True))

    if not activo and id == session.get('usuario_id'):
        return jsonify({'error': 'No puede desactivar su propia cuenta'}), 400

    existente = query("SELECT id FROM usuarios WHERE id = %s", (id,), fetchone=True)
    if not existente:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    execute("UPDATE usuarios SET activo = %s WHERE id = %s", (activo, id))
    return jsonify({'message': 'Usuario actualizado', 'activo': activo})
