"""
Rutas de Fichas Técnicas del Sistema OGTI.
Creación, validación de serie, checklist, finalización con
numeración atómica, carga masiva y descarga de documento oficial.
"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session, send_file
from psycopg2 import IntegrityError
from services.db import query, execute, get_connection
from services.numeracion import obtener_siguiente_correlativo, formatear_correlativo
from services.docx_service import generar_ficha_tecnica
from routes.auth import login_required, rol_required
import psycopg2.extras

fichas_bp = Blueprint('fichas', __name__)


def normalizar_serie(serie):
    """
    Normaliza el número de serie: elimina espacios y convierte a mayúsculas.
    Previene duplicados por diferencia de capitalización o espacios.
    """
    if serie:
        return serie.strip().upper()
    return serie


# ============================================================
# Páginas HTML
# ============================================================

@fichas_bp.route('/fichas')
@login_required
def pagina_lista():
    """Lista de todas las Fichas Técnicas."""
    fichas = query(
        """
        SELECT ft.id, ft.numero_correlativo, ft.anio, ft.marca, ft.modelo,
               ft.numero_serie, ft.estado, ft.estado_fisico,
               ft.fecha_creacion, ft.fecha_finalizacion,
               ie.descripcion AS bien_descripcion,
               et.numero_pedido,
               u.nombre_completo AS creado_por_nombre
        FROM fichas_tecnicas ft
        JOIN items_especificacion ie ON ft.item_id = ie.id
        JOIN especificaciones_tecnicas et ON ft.especificacion_id = et.id
        LEFT JOIN usuarios u ON ft.creado_por = u.id
        ORDER BY ft.fecha_creacion DESC
        """
    )
    return render_template('ficha_lista.html', fichas=fichas)


@fichas_bp.route('/fichas/nueva')
@login_required
def pagina_nueva():
    """Formulario de nueva Ficha Técnica."""
    return render_template('ficha_form.html', ficha=None)


@fichas_bp.route('/fichas/<int:id>')
@login_required
def pagina_ver(id):
    """Vista de detalle de una Ficha Técnica."""
    ft = query(
        """
        SELECT ft.*,
               ie.descripcion AS bien_descripcion,
               ie.caracteristicas AS caracteristicas_especificadas,
               tb.nombre AS tipo_bien_nombre,
               et.numero_pedido, et.fecha_pedido, et.centro_costo,
               et.anio_fiscal, et.finalidad_publica,
               r.nombre AS responsable_nombre, r.cargo AS responsable_cargo,
               r.telefono AS responsable_telefono,
               d.nombre AS dependencia_nombre,
               u.nombre_completo AS creado_por_nombre,
               uf.nombre_completo AS finalizado_por_nombre
        FROM fichas_tecnicas ft
        JOIN items_especificacion ie ON ft.item_id = ie.id
        JOIN tipos_bien tb ON ie.tipo_bien_id = tb.id
        JOIN especificaciones_tecnicas et ON ft.especificacion_id = et.id
        LEFT JOIN responsables r ON ft.responsable_id = r.id
        LEFT JOIN dependencias d ON r.dependencia_id = d.id
        LEFT JOIN usuarios u ON ft.creado_por = u.id
        LEFT JOIN usuarios uf ON ft.finalizado_por = uf.id
        WHERE ft.id = %s
        """,
        (id,),
        fetchone=True
    )

    if not ft:
        return "Ficha Técnica no encontrada", 404

    return render_template('ficha_ver.html', ft=ft)


# ============================================================
# API REST
# ============================================================

@fichas_bp.route('/api/fichas/validar-serie', methods=['GET'])
@login_required
def validar_serie():
    """
    Chequeo AJAX de unicidad de número de serie.
    Capa de UX — la garantía real es el UNIQUE constraint en PostgreSQL.
    """
    serie = request.args.get('serie', '')
    serie_normalizada = normalizar_serie(serie)

    if not serie_normalizada:
        return jsonify({'disponible': False, 'error': 'Número de serie vacío'}), 400

    existente = query(
        "SELECT id, numero_correlativo, anio FROM fichas_tecnicas WHERE numero_serie = %s",
        (serie_normalizada,),
        fetchone=True
    )

    if existente:
        return jsonify({
            'disponible': False,
            'mensaje': f'Este número de serie ya está registrado en la Ficha {existente["numero_correlativo"]}-{existente["anio"]}'
        })

    return jsonify({'disponible': True, 'mensaje': 'Número de serie disponible'})


@fichas_bp.route('/api/fichas', methods=['POST'])
@login_required
def crear_ficha():
    """
    Crea una nueva Ficha Técnica en estado BORRADOR.
    Hereda automáticamente datos de la ET y el proveedor.
    """
    data = request.get_json()

    campos_requeridos = ['especificacion_id', 'item_id', 'numero_serie']
    for campo in campos_requeridos:
        if not data.get(campo):
            return jsonify({'error': f'El campo "{campo}" es obligatorio'}), 400

    # Verificar que la ET esté finalizada
    et = query(
        """
        SELECT et.*, p.ruc, p.razon_social, p.direccion AS prov_dir,
               p.telefono AS prov_tel, p.correo AS prov_correo
        FROM especificaciones_tecnicas et
        LEFT JOIN proveedores p ON et.proveedor_id = p.id
        WHERE et.id = %s AND et.estado = 'FINALIZADA'
        """,
        (data['especificacion_id'],),
        fetchone=True
    )
    if not et:
        return jsonify({'error': 'La Especificación Técnica no existe o no está finalizada'}), 400

    # Verificar que el ítem pertenece a la ET
    item = query(
        "SELECT * FROM items_especificacion WHERE id = %s AND especificacion_id = %s",
        (data['item_id'], data['especificacion_id']),
        fetchone=True
    )
    if not item:
        return jsonify({'error': 'El ítem no pertenece a esta Especificación Técnica'}), 400

    # Normalizar número de serie
    serie_normalizada = normalizar_serie(data['numero_serie'])

    # Año actual para la ficha
    anio_actual = datetime.now().year

    try:
        resultado = execute(
            """
            INSERT INTO fichas_tecnicas
                (anio, especificacion_id, item_id,
                 marca, modelo, color, numero_serie, estado_fisico,
                 observaciones, carta_levantamiento,
                 proveedor_ruc, proveedor_razon, proveedor_direccion,
                 proveedor_telefono, proveedor_correo,
                 responsable_id,
                 orden_compra, costo, fecha_adquisicion, garantia,
                 caracteristicas_verificadas, checklist,
                 creado_por)
            VALUES (%s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s,
                    %s,
                    %s, %s, %s, %s,
                    %s::jsonb, '{}'::jsonb,
                    %s)
            RETURNING id, numero_serie, estado
            """,
            (
                anio_actual, data['especificacion_id'], data['item_id'],
                data.get('marca', '').strip(),
                data.get('modelo', '').strip(),
                data.get('color', '').strip(),
                serie_normalizada,
                data.get('estado_fisico', ''),
                data.get('observaciones', '').strip(),
                data.get('carta_levantamiento', '').strip(),
                 # Datos del proveedor: se envían desde el formulario (editables)
                 data.get('proveedor_ruc') or None,
                 data.get('proveedor_razon') or None,
                 data.get('proveedor_direccion') or None,
                 data.get('proveedor_telefono') or None,
                 data.get('proveedor_correo') or None,
                data.get('responsable_id'),
                 # Datos de adquisición del bien
                 data.get('orden_compra') or None,
                 data.get('costo') or None,
                 data.get('fecha_adquisicion') or None,
                 data.get('garantia') or None,
                json.dumps(data.get('caracteristicas_verificadas',
                                    item.get('caracteristicas', []))),
                session['usuario_id'],
            ),
            returning=True
        )
        return jsonify(resultado), 201

    except IntegrityError as e:
        if 'uq_ficha_numero_serie' in str(e):
            return jsonify({
                'error': f'El número de serie "{serie_normalizada}" ya está registrado en el sistema'
            }), 409
        raise


@fichas_bp.route('/api/fichas/<int:id>', methods=['PUT'])
@login_required
def actualizar_ficha(id):
    """Actualiza datos de una Ficha Técnica en BORRADOR."""
    ft = query(
        "SELECT estado FROM fichas_tecnicas WHERE id = %s",
        (id,),
        fetchone=True
    )
    if not ft:
        return jsonify({'error': 'Ficha Técnica no encontrada'}), 404
    if ft['estado'] != 'BORRADOR':
        return jsonify({'error': 'Solo se puede editar una Ficha en estado BORRADOR'}), 400

    data = request.get_json()

    # Si se cambia el número de serie, normalizar
    if 'numero_serie' in data:
        data['numero_serie'] = normalizar_serie(data['numero_serie'])

    # Construir UPDATE dinámico solo para campos enviados
    campos_permitidos = [
        'marca', 'modelo', 'color', 'numero_serie', 'estado_fisico',
        'observaciones', 'carta_levantamiento', 'responsable_id',
        'proveedor_ruc', 'proveedor_razon', 'proveedor_direccion',
        'proveedor_telefono', 'proveedor_correo',
        'orden_compra', 'costo', 'fecha_adquisicion', 'garantia'
    ]

    sets = []
    params = []
    for campo in campos_permitidos:
        if campo in data:
            sets.append(f"{campo} = %s")
            params.append(data[campo])

    if 'caracteristicas_verificadas' in data:
        sets.append("caracteristicas_verificadas = %s::jsonb")
        params.append(json.dumps(data['caracteristicas_verificadas']))

    if 'checklist' in data:
        sets.append("checklist = %s::jsonb")
        params.append(json.dumps(data['checklist']))

    if not sets:
        return jsonify({'error': 'No se enviaron campos para actualizar'}), 400

    params.append(id)

    try:
        execute(
            f"UPDATE fichas_tecnicas SET {', '.join(sets)} WHERE id = %s",
            tuple(params)
        )
        return jsonify({'message': 'Ficha actualizada correctamente'})

    except IntegrityError as e:
        if 'uq_ficha_numero_serie' in str(e):
            return jsonify({
                'error': f'El número de serie ya está registrado en otra ficha'
            }), 409
        raise


@fichas_bp.route('/api/fichas/<int:id>/finalizar', methods=['POST'])
@rol_required('JEFE_OGTI')
def finalizar_ficha(id):
    """
    Finaliza una Ficha Técnica:
    1. Verifica el rol JEFE_OGTI (en backend, no solo UI).
    2. Valida que el checklist esté completo (6 casillas).
    3. Asigna el correlativo atómico anual.
    4. Cambia estado a FINALIZADA (inmutable).
    """
    ft = query(
        "SELECT * FROM fichas_tecnicas WHERE id = %s",
        (id,),
        fetchone=True
    )
    if not ft:
        return jsonify({'error': 'Ficha Técnica no encontrada'}), 404
    if ft['estado'] != 'BORRADOR':
        return jsonify({'error': 'Solo se puede finalizar una Ficha en estado BORRADOR'}), 400

    # Validar campos obligatorios
    if not ft.get('numero_serie'):
        return jsonify({'error': 'El número de serie es obligatorio'}), 400
    if not ft.get('marca'):
        return jsonify({'error': 'La marca es obligatoria'}), 400
    if not ft.get('modelo'):
        return jsonify({'error': 'El modelo es obligatorio'}), 400
    if not ft.get('estado_fisico'):
        return jsonify({'error': 'El estado físico es obligatorio'}), 400

    # Validar checklist completo (6 casillas obligatorias)
    checklist = ft.get('checklist', {})
    if isinstance(checklist, str):
        checklist = json.loads(checklist)

    casillas_requeridas = [
        'marca_coincide',
        'modelo_coincide',
        'serie_ingresada',
        'estado_fisico_revisado',
        'caracteristicas_verificadas',
        'datos_proveedor_correctos',
    ]

    casillas_faltantes = [c for c in casillas_requeridas if not checklist.get(c)]
    if casillas_faltantes:
        return jsonify({
            'error': 'El checklist de verificación no está completo',
            'casillas_faltantes': casillas_faltantes
        }), 400

    # Asignar correlativo atómico
    anio = ft['anio']
    numero = obtener_siguiente_correlativo(anio)
    correlativo_formateado = formatear_correlativo(numero, anio)

    execute(
        """
        UPDATE fichas_tecnicas
        SET numero_correlativo = %s,
            estado = 'FINALIZADA',
            finalizado_por = %s,
            fecha_finalizacion = NOW()
        WHERE id = %s
        """,
        (numero, session['usuario_id'], id)
    )

    return jsonify({
        'message': 'Ficha Técnica finalizada correctamente',
        'numero_correlativo': correlativo_formateado,
        'id': id
    })


@fichas_bp.route('/api/fichas/<int:id>/anular', methods=['POST'])
@rol_required('JEFE_OGTI')
def anular_ficha(id):
    """
    Anula una Ficha Técnica finalizada.
    Requiere motivo de anulación. La ficha queda registrada
    con su correlativo original para trazabilidad.
    """
    data = request.get_json()
    motivo = data.get('motivo', '').strip()

    if not motivo:
        return jsonify({'error': 'El motivo de anulación es obligatorio'}), 400

    ft = query(
        "SELECT estado FROM fichas_tecnicas WHERE id = %s",
        (id,),
        fetchone=True
    )
    if not ft:
        return jsonify({'error': 'Ficha Técnica no encontrada'}), 404
    if ft['estado'] != 'FINALIZADA':
        return jsonify({'error': 'Solo se puede anular una Ficha en estado FINALIZADA'}), 400

    execute(
        """
        UPDATE fichas_tecnicas
        SET estado = 'ANULADA',
            motivo_anulacion = %s
        WHERE id = %s
        """,
        (motivo, id)
    )

    return jsonify({'message': 'Ficha Técnica anulada', 'id': id})


@fichas_bp.route('/api/fichas/carga-masiva', methods=['POST'])
@login_required
def carga_masiva():
    """
    Carga masiva de Fichas Técnicas para un mismo ítem de una ET.
    Transacción todo-o-nada: si un número de serie falla, se rechaza
    todo el lote y se informa exactamente cuál serie es el problema.
    """
    data = request.get_json()

    especificacion_id = data.get('especificacion_id')
    item_id = data.get('item_id')
    series = data.get('series', [])  # Lista de dicts con {numero_serie, marca, modelo, ...}

    if not especificacion_id or not item_id or not series:
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    # Verificar ET finalizada
    et = query(
        """
        SELECT et.*, p.ruc, p.razon_social, p.direccion AS prov_dir,
               p.telefono AS prov_tel, p.correo AS prov_correo
        FROM especificaciones_tecnicas et
        LEFT JOIN proveedores p ON et.proveedor_id = p.id
        WHERE et.id = %s AND et.estado = 'FINALIZADA'
        """,
        (especificacion_id,),
        fetchone=True
    )
    if not et:
        return jsonify({'error': 'ET no encontrada o no finalizada'}), 400

    item = query(
        "SELECT * FROM items_especificacion WHERE id = %s AND especificacion_id = %s",
        (item_id, especificacion_id),
        fetchone=True
    )
    if not item:
        return jsonify({'error': 'Ítem no encontrado en la ET'}), 400

    anio_actual = datetime.now().year

    # Normalizar y validar todas las series antes de la transacción
    series_normalizadas = []
    for i, s in enumerate(series):
        serie_norm = normalizar_serie(s.get('numero_serie', ''))
        if not serie_norm:
            return jsonify({
                'error': f'Fila {i + 1}: El número de serie está vacío'
            }), 400
        series_normalizadas.append(serie_norm)

    # Verificar duplicados dentro del mismo lote
    if len(set(series_normalizadas)) != len(series_normalizadas):
        duplicados = [s for s in series_normalizadas if series_normalizadas.count(s) > 1]
        return jsonify({
            'error': f'El lote contiene números de serie duplicados: {list(set(duplicados))}'
        }), 400

    # Transacción atómica: todo-o-nada
    conn = get_connection()
    fichas_creadas = []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for i, s in enumerate(series):
                serie_norm = series_normalizadas[i]
                try:
                    cur.execute(
                        """
                        INSERT INTO fichas_tecnicas
                            (anio, especificacion_id, item_id,
                             marca, modelo, color, numero_serie, estado_fisico,
                             observaciones, carta_levantamiento,
                             proveedor_ruc, proveedor_razon, proveedor_direccion,
                             proveedor_telefono, proveedor_correo,
                             responsable_id,
                             orden_compra, costo, fecha_adquisicion, garantia,
                             caracteristicas_verificadas, checklist,
                             creado_por)
                        VALUES (%s, %s, %s,
                                %s, %s, %s, %s, %s,
                                %s, %s,
                                %s, %s, %s, %s, %s,
                                %s,
                                %s, %s, %s, %s,
                                %s::jsonb, '{}'::jsonb,
                                %s)
                        RETURNING id, numero_serie
                        """,
                        (
                            anio_actual, especificacion_id, item_id,
                            s.get('marca', '').strip(),
                            s.get('modelo', '').strip(),
                            s.get('color', '').strip(),
                            serie_norm,
                            s.get('estado_fisico', ''),
                            s.get('observaciones', '').strip(),
                            s.get('carta_levantamiento', '').strip(),
                             et.get('ruc') or '', et.get('razon_social') or '',
                             et.get('prov_dir') or '', et.get('prov_tel') or '',
                             et.get('prov_correo') or '',
                            s.get('responsable_id'),
                             None, None, None, None,
                            json.dumps(item.get('caracteristicas', [])),
                            session['usuario_id'],
                        )
                    )
                    row = cur.fetchone()
                    fichas_creadas.append(dict(row))

                except IntegrityError as e:
                    conn.rollback()
                    if 'uq_ficha_numero_serie' in str(e):
                        return jsonify({
                            'error': f'Error en la fila {i + 1}: El número de serie '
                                     f'"{serie_norm}" ya existe en el sistema. '
                                     f'Corrija este valor para registrar el lote completo.'
                        }), 409
                    raise

            conn.commit()
            return jsonify({
                'message': f'{len(fichas_creadas)} fichas creadas como borradores',
                'fichas': fichas_creadas
            }), 201

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@fichas_bp.route('/api/fichas/<int:id>/documento', methods=['GET'])
@login_required
def descargar_documento_ft(id):
    """Genera y descarga el documento .docx de la Ficha Técnica."""
    ft = query(
        """
        SELECT ft.*,
               ie.descripcion AS bien_descripcion,
               tb.nombre AS tipo_bien_nombre,
               et.numero_pedido, et.fecha_pedido,
               et.denominacion_adquisicion AS denominacion_adquisicion,
               r.nombre AS responsable_nombre, r.cargo AS responsable_cargo,
               d.nombre AS dependencia_nombre
        FROM fichas_tecnicas ft
        JOIN items_especificacion ie ON ft.item_id = ie.id
        JOIN tipos_bien tb ON ie.tipo_bien_id = tb.id
        JOIN especificaciones_tecnicas et ON ft.especificacion_id = et.id
        LEFT JOIN responsables r ON ft.responsable_id = r.id
        LEFT JOIN dependencias d ON r.dependencia_id = d.id
        WHERE ft.id = %s
        """,
        (id,),
        fetchone=True
    )
    if not ft:
        return jsonify({'error': 'Ficha Técnica no encontrada'}), 404

    if ft['estado'] != 'FINALIZADA':
        return jsonify({'error': 'Solo se pueden descargar documentos de fichas finalizadas'}), 400

    correlativo = formatear_correlativo(ft['numero_correlativo'], ft['anio'])

    # Preparar las características verificadas
    caracteristicas = ft.get('caracteristicas_verificadas', [])
    if isinstance(caracteristicas, str):
        caracteristicas = json.loads(caracteristicas)

    datos = {
        'numero_ficha': correlativo,
        'bien_descripcion': ft['bien_descripcion'],
        'tipo_bien': ft['tipo_bien_nombre'],
        'marca': ft['marca'],
        'modelo': ft['modelo'],
        'color': ft.get('color', ''),
        'numero_serie': ft['numero_serie'],
        'estado_fisico': ft.get('estado_fisico', ''),
        'observaciones': ft.get('observaciones', ''),
        'carta_levantamiento': ft.get('carta_levantamiento', ''),
        'caracteristicas': caracteristicas,
        'proveedor_ruc': ft.get('proveedor_ruc', ''),
        'proveedor_razon_social': ft.get('proveedor_razon', ''),
        'proveedor_direccion': ft.get('proveedor_direccion', ''),
        'proveedor_telefono': ft.get('proveedor_telefono', ''),
        'proveedor_correo': ft.get('proveedor_correo', ''),
        'denominacion_adquisicion': ft.get('denominacion_adquisicion', ''),
        'responsable_nombre': ft.get('responsable_nombre', ''),
        'responsable_cargo': ft.get('responsable_cargo', ''),
        'dependencia': ft.get('dependencia_nombre', ''),
        'numero_pedido': ft['numero_pedido'],
        'fecha_pedido': ft['fecha_pedido'].strftime('%d/%m/%Y') if ft.get('fecha_pedido') else '',
        'fecha_finalizacion': ft['fecha_finalizacion'].strftime('%d/%m/%Y') if ft.get('fecha_finalizacion') else '',
        'orden_compra': ft.get('orden_compra', ''),
        'costo': ft.get('costo', ''),
        'fecha_adquisicion': ft['fecha_adquisicion'].strftime('%d/%m/%Y') if ft.get('fecha_adquisicion') else '',
        'garantia': ft.get('garantia', ''),
    }

    try:
        buffer = generar_ficha_tecnica(datos)
        nombre_archivo = f"FT_{correlativo}_{ft['marca']}_{ft['modelo']}.docx"
        nombre_archivo = nombre_archivo.replace(' ', '_')
        return send_file(
            buffer,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 500
