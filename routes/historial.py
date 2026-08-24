"""
Rutas de historial y búsqueda del Sistema OGTI.
Filtrado multicriterio de Especificaciones y Fichas Técnicas.
"""
from flask import Blueprint, request, jsonify, render_template
from services.db import query
from routes.auth import login_required

historial_bp = Blueprint('historial', __name__)


@historial_bp.route('/historial')
@login_required
def pagina_historial():
    """Página de búsqueda y consulta histórica."""
    return render_template('historial.html')


@historial_bp.route('/api/historial/fichas', methods=['GET'])
@login_required
def buscar_fichas():
    """
    Búsqueda multicriterio de Fichas Técnicas.
    Filtros: numero_ficha, numero_pedido, tipo_bien, proveedor,
             responsable, anio, estado.
    """
    filtros = []
    params = []

    if request.args.get('numero_ficha'):
        filtros.append("ft.numero_correlativo::text LIKE %s")
        params.append(f"%{request.args['numero_ficha']}%")

    if request.args.get('numero_pedido'):
        filtros.append("et.numero_pedido ILIKE %s")
        params.append(f"%{request.args['numero_pedido']}%")

    if request.args.get('tipo_bien'):
        filtros.append("tb.nombre ILIKE %s")
        params.append(f"%{request.args['tipo_bien']}%")

    if request.args.get('proveedor'):
        filtros.append("(ft.proveedor_razon ILIKE %s OR ft.proveedor_ruc LIKE %s)")
        params.append(f"%{request.args['proveedor']}%")
        params.append(f"%{request.args['proveedor']}%")

    if request.args.get('responsable'):
        filtros.append("r.nombre ILIKE %s")
        params.append(f"%{request.args['responsable']}%")

    if request.args.get('anio'):
        filtros.append("ft.anio = %s")
        params.append(int(request.args['anio']))

    if request.args.get('estado'):
        filtros.append("ft.estado = %s")
        params.append(request.args['estado'].upper())

    if request.args.get('marca'):
        filtros.append("ft.marca ILIKE %s")
        params.append(f"%{request.args['marca']}%")

    if request.args.get('numero_serie'):
        filtros.append("ft.numero_serie ILIKE %s")
        params.append(f"%{request.args['numero_serie']}%")

    where_clause = " AND ".join(filtros) if filtros else "TRUE"

    resultados = query(
        f"""
        SELECT ft.id, ft.numero_correlativo, ft.anio, ft.marca, ft.modelo,
               ft.numero_serie, ft.estado, ft.estado_fisico,
               ft.fecha_creacion, ft.fecha_finalizacion,
               ft.proveedor_razon, ft.proveedor_ruc,
               ie.descripcion AS bien_descripcion,
               tb.nombre AS tipo_bien_nombre,
               et.numero_pedido,
               r.nombre AS responsable_nombre,
               u.nombre_completo AS creado_por_nombre,
               uf.nombre_completo AS finalizado_por_nombre
        FROM fichas_tecnicas ft
        JOIN items_especificacion ie ON ft.item_id = ie.id
        JOIN tipos_bien tb ON ie.tipo_bien_id = tb.id
        JOIN especificaciones_tecnicas et ON ft.especificacion_id = et.id
        LEFT JOIN responsables r ON ft.responsable_id = r.id
        LEFT JOIN usuarios u ON ft.creado_por = u.id
        LEFT JOIN usuarios uf ON ft.finalizado_por = uf.id
        WHERE {where_clause}
        ORDER BY ft.fecha_creacion DESC
        LIMIT 200
        """,
        tuple(params)
    )

    return jsonify(resultados)


@historial_bp.route('/api/historial/especificaciones', methods=['GET'])
@login_required
def buscar_especificaciones():
    """
    Búsqueda multicriterio de Especificaciones Técnicas.
    Filtros: numero_pedido, proveedor, anio, estado.
    """
    filtros = []
    params = []

    if request.args.get('numero_pedido'):
        filtros.append("et.numero_pedido ILIKE %s")
        params.append(f"%{request.args['numero_pedido']}%")

    if request.args.get('proveedor'):
        filtros.append("(p.razon_social ILIKE %s OR p.ruc LIKE %s)")
        params.append(f"%{request.args['proveedor']}%")
        params.append(f"%{request.args['proveedor']}%")

    if request.args.get('anio'):
        filtros.append("et.anio_fiscal = %s")
        params.append(int(request.args['anio']))

    if request.args.get('estado'):
        filtros.append("et.estado = %s")
        params.append(request.args['estado'].upper())

    where_clause = " AND ".join(filtros) if filtros else "TRUE"

    resultados = query(
        f"""
        SELECT et.id, et.numero_pedido, et.fecha_pedido, et.centro_costo,
               et.anio_fiscal, et.estado, et.fecha_creacion, et.fecha_finalizacion,
               p.razon_social AS proveedor_nombre, p.ruc AS proveedor_ruc,
               u.nombre_completo AS creado_por_nombre,
               (SELECT COUNT(*) FROM items_especificacion ie
                WHERE ie.especificacion_id = et.id) AS total_items,
               (SELECT COUNT(*) FROM fichas_tecnicas ft
                WHERE ft.especificacion_id = et.id) AS total_fichas
        FROM especificaciones_tecnicas et
        JOIN proveedores p ON et.proveedor_id = p.id
        JOIN usuarios u ON et.creado_por = u.id
        WHERE {where_clause}
        ORDER BY et.fecha_creacion DESC
        LIMIT 200
        """,
        tuple(params)
    )

    return jsonify(resultados)
