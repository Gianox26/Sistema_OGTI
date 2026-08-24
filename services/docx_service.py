"""
Servicio de generación de documentos .docx oficiales.

Estrategia híbrida:
  1. docxtpl renderiza las etiquetas simples {{ variable }} (textos)
  2. python-docx manipula la tabla de ítems fila por fila
     y agrega las características + imagen debajo de la tabla

Esto evita los problemas de fragmentación XML de Jinja2 en Word
y permite construir tablas con el número correcto de filas.
"""
import os
import io
import copy
from docxtpl import DocxTemplate
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from config import Config


def _copiar_formato_celda(celda_origen, celda_destino):
    """Copia el formato básico de una celda a otra."""
    for p_dest in celda_destino.paragraphs:
        for p_orig in celda_origen.paragraphs:
            if p_orig.runs:
                p_dest.paragraph_format.alignment = p_orig.paragraph_format.alignment
                break


def _agregar_fila_tabla(tabla, valores, fila_ref_idx=1):
    """
    Agrega una nueva fila a la tabla copiando el formato de la fila de referencia.
    valores: lista de strings, uno por columna.
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    # Copiar la fila de referencia para mantener formato
    fila_ref = tabla.rows[fila_ref_idx]
    tr_ref = fila_ref._tr

    # Crear nueva fila copiando el XML de la referencia
    new_tr = copy.deepcopy(tr_ref)
    tabla._tbl.append(new_tr)

    # Rellenar las celdas con los valores
    nueva_fila = tabla.rows[-1]
    for i, valor in enumerate(valores):
        if i < len(nueva_fila.cells):
            celda = nueva_fila.cells[i]
            for p in celda.paragraphs:
                if p.runs:
                    p.runs[0].text = str(valor)
                    for run in p.runs[1:]:
                        run.text = ''
                else:
                    p.text = str(valor)

    return nueva_fila


def generar_especificacion_tecnica(datos):
    """
    Genera el documento .docx de Especificación Técnica.

    Paso 1: docxtpl renderiza textos simples (tabla superior, finalidad, objetivo)
    Paso 2: python-docx construye la tabla de ítems y las características
    """
    plantilla_path = Config.PLANTILLA_ET

    if not os.path.exists(plantilla_path):
        raise FileNotFoundError(
            f"No se encontró la plantilla de ET en: {plantilla_path}. "
            "Coloque el archivo especificacion_tecnica_tpl.docx en plantillas_docx/"
        )

    items = datos.get('items', [])

    # Datos en MAYÚSCULAS para la tabla superior
    datos_render = {
        'centro_costo': (datos.get('centro_costo', '') or '').upper(),
        'actividad_operativa': (datos.get('actividad_operativa', '') or '').upper(),
        'denominacion_adquisicion': (datos.get('denominacion_adquisicion', '') or '').upper(),
        'numero_pedido': datos.get('numero_pedido', ''),
        'meta_anio': (datos.get('meta_anio', '') or '').upper(),
        # Finalidad y objetivo en minúscula (redacción normal)
        'finalidad_publica': datos.get('finalidad_publica', ''),
        'objetivo': datos.get('objetivo', ''),
        # Placeholder para la tabla de ítems (se reemplazará después)
        'items_tabla': '',
        'caracteristicas_texto': '',
    }

    # ── Paso 1: Renderizar textos simples con docxtpl ──
    doc_tpl = DocxTemplate(plantilla_path)
    doc_tpl.render(datos_render)

    # Guardar en buffer temporal
    temp_buffer = io.BytesIO()
    doc_tpl.save(temp_buffer)
    temp_buffer.seek(0)

    # ── Paso 2: Abrir con python-docx y manipular tabla de ítems ──
    doc = Document(temp_buffer)

    # Encontrar la tabla de ítems (Tabla 2: Ítem | DESCRIPCIÓN | CLASIFICADOR | ...)
    tabla_items = None
    for tabla in doc.tables:
        # Buscar la tabla que tiene "Ítem" o "DESCRIPCIÓN" en la cabecera
        primera_fila_textos = [c.text.strip().upper() for c in tabla.rows[0].cells]
        if any('DESCRIPCI' in t for t in primera_fila_textos):
            tabla_items = tabla
            break

    if tabla_items and items:
        # Limpiar la fila de datos existente (fila 1 = placeholder)
        fila_placeholder = tabla_items.rows[1]
        for celda in fila_placeholder.cells:
            for p in celda.paragraphs:
                if p.runs:
                    for run in p.runs:
                        run.text = ''
                else:
                    p.text = ''

        # Escribir el primer ítem en la fila placeholder
        primer_item = items[0]
        valores_primer = [
            str(1).zfill(3),
            (primer_item.get('descripcion', '') or '').upper(),
            primer_item.get('clasificador', '') or '-',
            primer_item.get('unidad_medida', 'UNIDAD'),
            _format_cantidad(primer_item.get('cantidad', 1)),
        ]
        for i, valor in enumerate(valores_primer):
            if i < len(fila_placeholder.cells):
                celda = fila_placeholder.cells[i]
                for p in celda.paragraphs:
                    if p.runs:
                        p.runs[0].text = valor
                        for run in p.runs[1:]:
                            run.text = ''
                    else:
                        p.text = valor

        # Agregar filas adicionales para los demás ítems
        for idx, item in enumerate(items[1:], 2):
            valores = [
                str(idx).zfill(3),
                (item.get('descripcion', '') or '').upper(),
                item.get('clasificador', '') or '-',
                item.get('unidad_medida', 'UNIDAD'),
                _format_cantidad(item.get('cantidad', 1)),
            ]
            _agregar_fila_tabla(tabla_items, valores, fila_ref_idx=1)

    # ── Paso 3: Insertar características técnicas por ítem ──
    # Buscar el párrafo donde están las características
    # y reemplazar con las de cada ítem
    for i, p in enumerate(doc.paragraphs):
        texto = p.text.strip()
        # Buscar el placeholder de características o el párrafo vacío
        # después de "debidamente sellados"
        if texto == '' and i > 0:
            texto_prev = doc.paragraphs[i - 1].text.strip() if i > 0 else ''
            if 'sellados' in texto_prev.lower() or texto_prev == '':
                # Aquí insertamos las características de cada ítem
                pass

        # Si encontramos el placeholder {{ caracteristicas_texto }}
        if '{{ caracteristicas_texto }}' in texto or texto == '':
            # Verificar contexto
            pass

    # Buscar y reemplazar el texto de características
    for p in doc.paragraphs:
        if p.text.strip() in ('', '{{ caracteristicas_texto }}'):
            continue
        # Dejar intactos los demás párrafos

    # Escribir características después del placeholder
    for p_idx, p in enumerate(doc.paragraphs):
        if p.text.strip() == '' and p_idx > 5:
            # Verificar si el párrafo anterior menciona sellados o CARACTERISTICAS
            if p_idx > 0:
                prev_text = doc.paragraphs[p_idx - 1].text.strip().upper()
                if 'CARACTERISTICAS' in prev_text or 'SELLADOS' in prev_text:
                    # Insertar características de los ítems aquí
                    chars_text = _formatear_todas_caracteristicas(items)
                    if p.runs:
                        p.runs[0].text = chars_text
                    else:
                        p.text = chars_text
                    break

    # ── Paso 4: Manejar imagen referencial ──
    # Eliminar la imagen vieja del crimping y agregar la nueva si existe
    _limpiar_imagenes_existentes(doc)

    for item in items:
        img_path = item.get('imagen_referencial', '')
        if img_path:
            full_path = os.path.join(Config.BASE_DIR, 'static', img_path)
            if os.path.exists(full_path):
                _insertar_imagen_despues_de_caracteristicas(doc, full_path)

    # Guardar resultado final
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def generar_ficha_tecnica(datos):
    """
    Genera el documento .docx de Ficha Técnica rellenando la plantilla oficial.
    """
    plantilla_path = Config.PLANTILLA_FICHA

    if not os.path.exists(plantilla_path):
        raise FileNotFoundError(
            f"No se encontró la plantilla de FT en: {plantilla_path}. "
            "Coloque el archivo ficha_tecnica_tpl.docx en plantillas_docx/"
        )

    # Pre-formatear características como texto
    chars = datos.get('caracteristicas', [])
    if isinstance(chars, list):
        lineas = []
        for c in chars:
            nombre = c.get('nombre', '')
            valor = c.get('valor', c.get('valor_sugerido', ''))
            if nombre:
                lineas.append(f"{nombre}: {valor}")
        datos['caracteristicas_texto'] = ' | '.join(lineas)
    elif isinstance(chars, str):
        datos['caracteristicas_texto'] = chars
    else:
        datos['caracteristicas_texto'] = ''

    doc = DocxTemplate(plantilla_path)
    doc.render(datos)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ============================================================
# Funciones auxiliares
# ============================================================

def _format_cantidad(cant):
    """Formatea cantidad como string decimal."""
    try:
        return f"{float(cant):.2f}"
    except (ValueError, TypeError):
        return str(cant)


def _formatear_todas_caracteristicas(items):
    """Formatea las características de todos los ítems como texto."""
    if not items:
        return ''

    bloques = []
    for i, item in enumerate(items, 1):
        chars = item.get('caracteristicas', [])
        if not chars:
            continue

        lineas = []
        desc = item.get('descripcion', f'Ítem {i}')
        lineas.append(f"CARACTERÍSTICAS - {desc.upper()}:")

        for c in chars:
            nombre = c.get('nombre', '')
            valor = c.get('valor', c.get('valor_sugerido', ''))
            if nombre:
                lineas.append(f"- {nombre}: {valor}")

        bloques.append('\n'.join(lineas))

    return '\n\n'.join(bloques)


def _limpiar_imagenes_existentes(doc):
    """Elimina todas las imágenes incrustadas en párrafos y celdas de tabla."""
    from docx.oxml.ns import qn

    parrafos = list(doc.paragraphs)
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                parrafos.extend(celda.paragraphs)

    for p in parrafos:
        for run in p.runs:
            for drawing in run._element.findall(qn('w:drawing')):
                run._element.remove(drawing)
            for pict in run._element.findall(qn('w:pict')):
                run._element.remove(pict)


def _insertar_imagen_despues_de_caracteristicas(doc, imagen_path):
    """Inserta una imagen referencial después de las características."""
    # Buscar un buen lugar para insertar (después de CARACTERÍSTICAS)
    for i, p in enumerate(doc.paragraphs):
        texto = p.text.strip().upper()
        if 'REGLAMENTOS' in texto or 'ACONDICIONAMIENTO' in texto:
            # Insertar antes de Reglamentos Técnicos
            # Crear un nuevo párrafo antes de este
            new_p = doc.paragraphs[i - 1] if i > 0 else p
            try:
                run = new_p.add_run('\n\nImagen Referencial:\n')
                run.font.size = Pt(10)
                run.bold = True
                run = new_p.add_run()
                run.add_picture(imagen_path, width=Inches(4))
            except Exception:
                pass  # Si la imagen no se puede insertar, continuar sin ella
            break
