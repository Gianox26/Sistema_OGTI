"""
Rutas de Especificaciones Técnicas del Sistema OGTI.
Campos según formato oficial (TDR / Formato N° 01):
  Tabla superior: Centro de Costo, Actividad Operativa, Denominación,
                  Pedido de Compra N°, Meta-Año
  Contenido: Finalidad (auto), Objetivo (auto), Ítems, Características,
             Imagen referencial, Reglamentos
"""
import json
import os
from flask import Blueprint, request, jsonify, render_template, session, send_file, current_app
from werkzeug.utils import secure_filename
from services.db import query, execute
from services.docx_service import generar_especificacion_tecnica
from routes.auth import login_required, rol_required

especificaciones_bp = Blueprint('especificaciones', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# Páginas HTML
# ============================================================

@especificaciones_bp.route('/especificaciones')
@login_required
def pagina_lista():
    """Lista de todas las Especificaciones Técnicas."""
    especificaciones = query(
        """
        SELECT et.id, et.numero_pedido, et.fecha_pedido,
               et.denominacion_adquisicion,
               et.anio_fiscal, et.estado, et.origen,
               et.fecha_creacion, et.fecha_finalizacion,
               d.nombre AS centro_costo_nombre,
               ao.codigo AS actividad_codigo, ao.nombre AS actividad_nombre,
               p.razon_social AS proveedor_nombre,
               u.nombre_completo AS creado_por_nombre,
               (SELECT COUNT(*) FROM items_especificacion ie
                WHERE ie.especificacion_id = et.id) AS total_items
        FROM especificaciones_tecnicas et
        LEFT JOIN dependencias d ON et.centro_costo_id = d.id
        LEFT JOIN actividades_operativas ao ON et.actividad_operativa_id = ao.id
        LEFT JOIN proveedores p ON et.proveedor_id = p.id
        JOIN usuarios u ON et.creado_por = u.id
        ORDER BY et.fecha_creacion DESC
        """
    )
    return render_template('especificacion_lista.html', especificaciones=especificaciones)


@especificaciones_bp.route('/especificaciones/nueva')
@login_required
def pagina_nueva():
    """Pantalla principal: Registro por Referencia de Especificación Técnica recibida (físico)."""
    return render_template('especificacion_referencia.html')


@especificaciones_bp.route('/especificaciones/nueva-interna')
@login_required
def pagina_nueva_interna():
    """Pantalla secundaria: Redacción Interna Completa de Especificación Técnica."""
    return render_template('especificacion_form.html', especificacion=None)


@especificaciones_bp.route('/especificaciones/<int:id>/editar')
@login_required
def pagina_editar(id):
    """Editar una Especificación Técnica en estado BORRADOR."""
    et = query(
        "SELECT * FROM especificaciones_tecnicas WHERE id = %s",
        (id,), fetchone=True
    )
    if not et:
        return "Especificación Técnica no encontrada", 404
    if et['estado'] != 'BORRADOR':
        return "Solo se pueden editar especificaciones en estado BORRADOR", 400

    return render_template('especificacion_form.html', especificacion=et)


@especificaciones_bp.route('/especificaciones/<int:id>')
@login_required
def pagina_ver(id):
    """Vista de detalle de una Especificación Técnica."""
    et = query(
        """
        SELECT et.*,
               d.nombre AS centro_costo_nombre,
               ao.codigo AS actividad_codigo, ao.nombre AS actividad_nombre,
               p.ruc, p.razon_social, p.direccion AS proveedor_direccion,
               p.telefono AS proveedor_telefono, p.correo AS proveedor_correo,
               u.nombre_completo AS creado_por_nombre,
               uf.nombre_completo AS finalizado_por_nombre
        FROM especificaciones_tecnicas et
        LEFT JOIN dependencias d ON et.centro_costo_id = d.id
        LEFT JOIN actividades_operativas ao ON et.actividad_operativa_id = ao.id
        LEFT JOIN proveedores p ON et.proveedor_id = p.id
        JOIN usuarios u ON et.creado_por = u.id
        LEFT JOIN usuarios uf ON et.finalizado_por = uf.id
        WHERE et.id = %s
        """,
        (id,),
        fetchone=True
    )

    if not et:
        return "Especificación Técnica no encontrada", 404

    items = query(
        """
        SELECT ie.*, tb.nombre AS tipo_bien_nombre
        FROM items_especificacion ie
        JOIN tipos_bien tb ON ie.tipo_bien_id = tb.id
        WHERE ie.especificacion_id = %s
        ORDER BY ie.id
        """,
        (id,)
    )

    # Generar textos de finalidad y objetivo automáticamente
    denom = et.get('denominacion_adquisicion', '')
    cc_nombre = et.get('centro_costo_nombre', '')
    finalidad_auto = (
        f"La finalidad de la presente adquisición es garantizar la adquisición de "
        f"{denom.lower()} para el cumplimiento de las actividades de la "
        f"{cc_nombre}, así como también las condiciones de operatividad que permita "
        f"al personal desempeñar adecuadamente sus funciones."
    ) if denom and cc_nombre else ''

    objetivo_auto = (
        f"Contratar la adquisición de {denom.lower()} y garantizar el cumplimiento "
        f"de las metas y actividades programadas de la {cc_nombre}."
    ) if denom and cc_nombre else ''

    return render_template('especificacion_ver.html', et=et, items=items,
                           finalidad_auto=finalidad_auto, objetivo_auto=objetivo_auto)


# ============================================================
# API REST
# ============================================================

@especificaciones_bp.route('/api/especificaciones', methods=['POST'])
@login_required
def crear_especificacion():
    """Crea una nueva Especificación Técnica en estado BORRADOR."""
    data = request.get_json()

    # Validar campos obligatorios del formato oficial
    denominacion = data.get('denominacion_adquisicion', '').strip()
    numero_pedido = data.get('numero_pedido', '').strip()
    fecha_pedido = data.get('fecha_pedido', '')

    if not denominacion:
        return jsonify({'error': 'La denominación de la adquisición es obligatoria'}), 400
    if not numero_pedido:
        return jsonify({'error': 'El número de pedido de compra es obligatorio'}), 400
    if not numero_pedido.isdigit():
        return jsonify({'error': 'El número de pedido debe contener solo dígitos'}), 400
    if not fecha_pedido:
        return jsonify({'error': 'La fecha del pedido es obligatoria'}), 400

    # Verificar que el número de pedido no esté duplicado
    existente = query(
        "SELECT id FROM especificaciones_tecnicas WHERE numero_pedido = %s AND anio_fiscal = %s",
        (numero_pedido, anio_fiscal),
        fetchone=True
    )
    if existente:
        return jsonify({'error': f'Ya existe una ET con pedido N° {numero_pedido} para el año {anio_fiscal}'}), 409

    # Meta-año: combinar código meta + año
    meta_codigo = data.get('meta_codigo', '').strip()
    anio_fiscal = data.get('anio_fiscal', 2026)
    meta_anio = f"{meta_codigo}-{anio_fiscal}" if meta_codigo else ''

    resultado = execute(
        """
        INSERT INTO especificaciones_tecnicas
            (centro_costo_id, actividad_operativa_id, denominacion_adquisicion,
             numero_pedido, meta_anio, fecha_pedido, anio_fiscal,
             proveedor_id, creado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, numero_pedido, estado
        """,
        (
            data.get('centro_costo_id') or None,
            data.get('actividad_operativa_id') or None,
            denominacion,
            numero_pedido,
            meta_anio,
            fecha_pedido,
             anio_fiscal,
             data.get('proveedor_id'),
             session['usuario_id'],
        ),
        returning=True
    )

    return jsonify(resultado), 201


@especificaciones_bp.route('/api/especificaciones/referencia', methods=['POST'])
@login_required
def crear_especificacion_referencia():
    """
    Registra una Especificación Técnica recibida en físico (REFERENCIA_EXTERNA).
    Procesa campos multipart/form-data, adjunto escaneado e ítems del pedido.
    """
    numero_pedido = (request.form.get('numero_pedido', '') or '').strip()
    fecha_pedido = request.form.get('fecha_pedido', '')
    denominacion = (request.form.get('denominacion_adquisicion', '') or '').strip()

    if not numero_pedido:
        return jsonify({'error': 'El número de pedido es obligatorio'}), 400
    if not fecha_pedido:
        return jsonify({'error': 'La fecha del pedido es obligatoria'}), 400
    if not denominacion:
        return jsonify({'error': 'La denominación de la adquisición es obligatoria'}), 400

    anio_fiscal = int(fecha_pedido.split('-')[0]) if '-' in fecha_pedido else datetime.now().year
    existente = query(
        "SELECT id FROM especificaciones_tecnicas WHERE numero_pedido = %s AND anio_fiscal = %s",
        (numero_pedido, anio_fiscal), fetchone=True
    )
    if existente:
        return jsonify({'error': f'Ya existe un registro con pedido N° {numero_pedido} para el año {anio_fiscal}'}), 409

    # Procesar archivo adjunto si se envió
    adjunto_path = None
    if 'documento_adjunto' in request.files:
        file = request.files['documento_adjunto']
        if file and file.filename:
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'et_documentos')
            os.makedirs(upload_dir, exist_ok=True)
            filename = secure_filename(f"et_ref_{numero_pedido}_{file.filename}")
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            adjunto_path = f"uploads/et_documentos/{filename}"

    # Meta-año
    meta_codigo = (request.form.get('meta_codigo', '') or '').strip()
    anio_fiscal = request.form.get('anio_fiscal', type=int) or (int(fecha_pedido.split('-')[0]) if '-' in fecha_pedido else datetime.now().year)
    meta_anio = f"{meta_codigo}-{anio_fiscal}" if meta_codigo else ''

    # Insertar ET con origen REFERENCIA_EXTERNA y estado FINALIZADA
    res_et = execute(
        """
        INSERT INTO especificaciones_tecnicas
            (numero_pedido, fecha_pedido, denominacion_adquisicion,
             centro_costo_id, proveedor_id, meta_anio, anio_fiscal,
             origen, estado, documento_adjunto, creado_por, finalizado_por, fecha_finalizacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'REFERENCIA_EXTERNA', 'FINALIZADA', %s, %s, %s, NOW())
        RETURNING id, numero_pedido
        """,
        (
            numero_pedido,
            fecha_pedido,
            denominacion,
            request.form.get('centro_costo_id') or None,
            request.form.get('proveedor_id') or None,
            meta_anio,
            anio_fiscal,
            adjunto_path,
            session['usuario_id'],
            session['usuario_id'],
        ),
        returning=True
    )

    et_id = res_et['id']

    # Insertar ítems del pedido
    items_json = request.form.get('items', '[]')
    try:
        items = json.loads(items_json)
        for it in items:
            execute(
                """
                INSERT INTO items_especificacion
                    (especificacion_id, tipo_bien_id, descripcion, cantidad, unidad_medida, clasificador)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    et_id,
                    it.get('tipo_bien_id'),
                    it.get('descripcion', '').strip(),
                    it.get('cantidad', 1),
                    it.get('unidad_medida', 'UNIDAD').strip() or 'UNIDAD',
                    it.get('clasificador', '').strip() or None
                )
            )
    except Exception as e:
        print("Error registrando ítems de ET referencia:", e)

    return jsonify({'message': 'Especificación registrada exitosamente', 'id': et_id, 'numero_pedido': numero_pedido}), 201


@especificaciones_bp.route('/api/especificaciones/<int:id>', methods=['PUT'])
@login_required
def actualizar_especificacion(id):
    """Actualiza una ET en BORRADOR."""
    et = query(
        "SELECT estado FROM especificaciones_tecnicas WHERE id = %s",
        (id,), fetchone=True
    )
    if not et:
        return jsonify({'error': 'ET no encontrada'}), 404
    if et['estado'] != 'BORRADOR':
        return jsonify({'error': 'Solo se puede editar una ET en BORRADOR'}), 400

    data = request.get_json()
    sets = []
    params = []

    campos_directos = {
        'denominacion_adquisicion': 'denominacion_adquisicion',
        'numero_pedido': 'numero_pedido',
        'fecha_pedido': 'fecha_pedido',
        'meta_anio': 'meta_anio',
        'anio_fiscal': 'anio_fiscal',
        'centro_costo_id': 'centro_costo_id',
        'actividad_operativa_id': 'actividad_operativa_id',
        'proveedor_id': 'proveedor_id',
    }

    for key, col in campos_directos.items():
        if key in data:
            sets.append(f"{col} = %s")
            params.append(data[key] or None)

    if not sets:
        return jsonify({'error': 'No se enviaron campos para actualizar'}), 400

    params.append(id)
    execute(f"UPDATE especificaciones_tecnicas SET {', '.join(sets)} WHERE id = %s", tuple(params))
    return jsonify({'message': 'ET actualizada'})


@especificaciones_bp.route('/api/especificaciones/<int:id>/items', methods=['GET'])
@login_required
def listar_items(id):
    """Lista todos los ítems de una Especificación Técnica."""
    items = query(
        """
        SELECT ie.*, tb.nombre AS tipo_bien_nombre,
               tb.caracteristicas_tipicas
        FROM items_especificacion ie
        JOIN tipos_bien tb ON ie.tipo_bien_id = tb.id
        WHERE ie.especificacion_id = %s
        ORDER BY ie.id
        """,
        (id,)
    )
    return jsonify(items)


@especificaciones_bp.route('/api/especificaciones/<int:id>/items', methods=['POST'])
@login_required
def agregar_item(id):
    """Agrega un ítem a una Especificación Técnica en BORRADOR."""
    et = query(
        "SELECT estado FROM especificaciones_tecnicas WHERE id = %s",
        (id,), fetchone=True
    )
    if not et:
        return jsonify({'error': 'ET no encontrada'}), 404
    if et['estado'] != 'BORRADOR':
        return jsonify({'error': 'Solo se pueden agregar ítems a una ET en BORRADOR'}), 400

    data = request.get_json()

    if not data.get('tipo_bien_id') or not data.get('descripcion'):
        return jsonify({'error': 'tipo_bien_id y descripcion son obligatorios'}), 400

    caracteristicas = data.get('caracteristicas', [])

    resultado = execute(
        """
        INSERT INTO items_especificacion
            (especificacion_id, tipo_bien_id, descripcion, clasificador,
             unidad_medida, cantidad, caracteristicas,
             condiciones_previas, reglamentos_tecnicos)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
        RETURNING id, tipo_bien_id, descripcion, clasificador,
                  unidad_medida, cantidad
        """,
        (
            id,
            data['tipo_bien_id'],
            data['descripcion'].strip(),
            data.get('clasificador', '').strip(),
            data.get('unidad_medida', 'UNIDAD').strip(),
            data.get('cantidad', 1.00),
            json.dumps(caracteristicas),
            data.get('condiciones_previas', '').strip() or None,
            data.get('reglamentos_tecnicos', 'No aplica').strip(),
        ),
        returning=True
    )

    return jsonify(resultado), 201


@especificaciones_bp.route('/api/especificaciones/<int:id>/items/<int:item_id>', methods=['PUT'])
@login_required
def actualizar_item(id, item_id):
    """Actualiza un ítem de una ET en BORRADOR."""
    et = query(
        "SELECT estado FROM especificaciones_tecnicas WHERE id = %s",
        (id,), fetchone=True
    )
    if not et or et['estado'] != 'BORRADOR':
        return jsonify({'error': 'Solo se pueden editar ítems de una ET en BORRADOR'}), 400

    data = request.get_json()
    sets = []
    params = []

    for campo in ['descripcion', 'clasificador', 'unidad_medida', 'cantidad',
                   'condiciones_previas', 'reglamentos_tecnicos']:
        if campo in data:
            sets.append(f"{campo} = %s")
            params.append(data[campo])

    if 'caracteristicas' in data:
        sets.append("caracteristicas = %s::jsonb")
        params.append(json.dumps(data['caracteristicas']))

    if 'tipo_bien_id' in data:
        sets.append("tipo_bien_id = %s")
        params.append(data['tipo_bien_id'])

    if not sets:
        return jsonify({'error': 'Sin campos para actualizar'}), 400

    params.extend([item_id, id])
    execute(
        f"UPDATE items_especificacion SET {', '.join(sets)} WHERE id = %s AND especificacion_id = %s",
        tuple(params)
    )
    return jsonify({'message': 'Ítem actualizado'})


@especificaciones_bp.route('/api/especificaciones/<int:id>/items/<int:item_id>', methods=['DELETE'])
@login_required
def eliminar_item(id, item_id):
    """Elimina un ítem de una ET en BORRADOR."""
    et = query(
        "SELECT estado FROM especificaciones_tecnicas WHERE id = %s",
        (id,), fetchone=True
    )
    if not et or et['estado'] != 'BORRADOR':
        return jsonify({'error': 'Solo se pueden eliminar ítems de una ET en BORRADOR'}), 400

    execute(
        "DELETE FROM items_especificacion WHERE id = %s AND especificacion_id = %s",
        (item_id, id)
    )
    return jsonify({'message': 'Ítem eliminado'}), 200


@especificaciones_bp.route('/api/especificaciones/<int:id>/items/<int:item_id>/imagen', methods=['POST'])
@login_required
def subir_imagen_item(id, item_id):
    """Sube una imagen referencial para un ítem."""
    if 'imagen' not in request.files:
        return jsonify({'error': 'No se envió ninguna imagen'}), 400

    archivo = request.files['imagen']
    if archivo.filename == '' or not allowed_file(archivo.filename):
        return jsonify({'error': 'Formato de imagen no válido (use PNG, JPG, GIF o WebP)'}), 400

    # Guardar en static/img/items/
    upload_dir = os.path.join(current_app.root_path, 'static', 'img', 'items')
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(f"et{id}_item{item_id}_{archivo.filename}")
    filepath = os.path.join(upload_dir, filename)
    archivo.save(filepath)

    # Guardar ruta relativa en BD
    ruta_relativa = f"img/items/{filename}"
    execute(
        "UPDATE items_especificacion SET imagen_referencial = %s WHERE id = %s AND especificacion_id = %s",
        (ruta_relativa, item_id, id)
    )

    return jsonify({'message': 'Imagen subida', 'ruta': ruta_relativa}), 200


@especificaciones_bp.route('/api/especificaciones/<int:id>/finalizar', methods=['POST'])
@login_required
def finalizar_especificacion(id):
    """Finaliza una ET: cambia estado a FINALIZADA."""
    et = query(
        "SELECT * FROM especificaciones_tecnicas WHERE id = %s",
        (id,), fetchone=True
    )
    if not et:
        return jsonify({'error': 'ET no encontrada'}), 404
    if et['estado'] != 'BORRADOR':
        return jsonify({'error': 'Solo se puede finalizar una ET en BORRADOR'}), 400

    # Verificar que tenga al menos un ítem
    items_count = query(
        "SELECT COUNT(*) as total FROM items_especificacion WHERE especificacion_id = %s",
        (id,), fetchone=True
    )
    if items_count['total'] == 0:
        return jsonify({'error': 'La ET debe tener al menos un ítem'}), 400

    execute(
        """
        UPDATE especificaciones_tecnicas
        SET estado = 'FINALIZADA',
            finalizado_por = %s,
            fecha_finalizacion = NOW()
        WHERE id = %s
        """,
        (session['usuario_id'], id)
    )

    return jsonify({'message': 'Especificación Técnica finalizada correctamente', 'id': id})


@especificaciones_bp.route('/api/especificaciones/<int:id>/documento', methods=['GET'])
@login_required
def descargar_documento_et(id):
    """Genera y descarga el documento .docx de la ET desde la plantilla oficial."""
    et = query(
        """
        SELECT et.*,
               d.nombre AS centro_costo_nombre,
               ao.codigo AS actividad_codigo, ao.nombre AS actividad_nombre,
               p.ruc, p.razon_social, p.direccion AS proveedor_direccion,
               p.telefono AS proveedor_telefono, p.correo AS proveedor_correo
        FROM especificaciones_tecnicas et
        LEFT JOIN dependencias d ON et.centro_costo_id = d.id
        LEFT JOIN actividades_operativas ao ON et.actividad_operativa_id = ao.id
        LEFT JOIN proveedores p ON et.proveedor_id = p.id
        WHERE et.id = %s
        """,
        (id,), fetchone=True
    )
    if not et:
        return jsonify({'error': 'ET no encontrada'}), 404

    items = query(
        """
        SELECT ie.*, tb.nombre AS tipo_bien_nombre
        FROM items_especificacion ie
        JOIN tipos_bien tb ON ie.tipo_bien_id = tb.id
        WHERE ie.especificacion_id = %s
        ORDER BY ie.id
        """,
        (id,)
    )

    # Generar finalidad y objetivo automáticamente
    denom = et.get('denominacion_adquisicion', '')
    cc_nombre = et.get('centro_costo_nombre', '')

    datos = {
        'centro_costo': cc_nombre,
        'actividad_operativa': f"{et.get('actividad_codigo', '')} – {et.get('actividad_nombre', '')}",
        'denominacion_adquisicion': et.get('denominacion_adquisicion', ''),
        'numero_pedido': et['numero_pedido'],
        'meta_anio': et.get('meta_anio', ''),
        'fecha_pedido': et['fecha_pedido'].strftime('%d/%m/%Y') if et['fecha_pedido'] else '',
        'anio_fiscal': et['anio_fiscal'],
        'finalidad_publica': (
            f"La finalidad de la presente adquisición es garantizar la adquisición de "
            f"{denom.lower()} para el cumplimiento de las actividades de la "
            f"{cc_nombre}, así como también las condiciones de operatividad que permita "
            f"al personal desempeñar adecuadamente sus funciones."
        ),
        'objetivo': (
            f"Contratar la adquisición de {denom.lower()} y garantizar el cumplimiento "
            f"de las metas y actividades programadas de la {cc_nombre}."
        ),
        'proveedor_ruc': et['ruc'],
        'proveedor_razon_social': et['razon_social'],
        'proveedor_direccion': et.get('proveedor_direccion', ''),
        'proveedor_telefono': et.get('proveedor_telefono', ''),
        'proveedor_correo': et.get('proveedor_correo', ''),
        'items': items,
    }

    try:
        buffer = generar_especificacion_tecnica(datos)
        denom_archivo = denom.upper().replace(' ', '_')[:50] if denom else 'ET'
        nombre_archivo = f"ET_{et['numero_pedido']}_{denom_archivo}.docx"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 500


@especificaciones_bp.route('/api/especificaciones/finalizadas', methods=['GET'])
@login_required
def listar_finalizadas():
    """Lista las ET finalizadas (para seleccionar al crear Fichas Técnicas)."""
    ets = query(
        """
        SELECT et.id, et.numero_pedido, et.fecha_pedido, et.anio_fiscal,
               et.denominacion_adquisicion, et.proveedor_id,
               d.nombre AS centro_costo_nombre,
               p.razon_social AS proveedor_nombre, p.ruc AS proveedor_ruc,
               p.direccion AS proveedor_direccion, p.telefono AS proveedor_telefono,
               p.correo AS proveedor_correo,
               (SELECT COUNT(*) FROM items_especificacion ie
                WHERE ie.especificacion_id = et.id) AS total_items
        FROM especificaciones_tecnicas et
        LEFT JOIN dependencias d ON et.centro_costo_id = d.id
        LEFT JOIN proveedores p ON et.proveedor_id = p.id
        WHERE et.estado = 'FINALIZADA'
        ORDER BY et.fecha_creacion DESC
        """
    )
    return jsonify(ets)
