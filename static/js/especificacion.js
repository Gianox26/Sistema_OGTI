/**
 * especificacion.js — Lógica del formulario de Especificación Técnica
 * Campos según formato oficial: Centro de Costo, Actividad Operativa,
 * Denominación, N° Pedido (solo dígitos), Meta-Año, Proveedor.
 * Ítems con condiciones previas, características, imagen y reglamentos.
 */

let etId = null;
let tiposBien = [];

document.addEventListener('DOMContentLoaded', function () {
    Promise.all([
        cargarDependencias(),
        cargarActividades(),
        cargarProveedores(),
        cargarTiposBien()
    ]).then(() => {
        if (window.ET_EXISTENTE) {
            cargarETExistente(window.ET_EXISTENTE);
        }
    });
});

function cargarETExistente(et) {
    etId = et.id;
    if (et.centro_costo_id) document.getElementById('centro_costo_id').value = et.centro_costo_id;
    if (et.actividad_operativa_id) document.getElementById('actividad_operativa_id').value = et.actividad_operativa_id;
    if (et.denominacion_adquisicion) document.getElementById('denominacion_adquisicion').value = et.denominacion_adquisicion;
    if (et.numero_pedido) document.getElementById('numero_pedido').value = et.numero_pedido;
    if (et.meta_anio) {
        const partes = et.meta_anio.split('-');
        document.getElementById('meta_codigo').value = partes[0] || '';
        if (partes[1]) document.getElementById('anio_fiscal').value = partes[1];
    }
    if (et.fecha_pedido) {
        const fecha = new Date(et.fecha_pedido).toISOString().split('T')[0];
        document.getElementById('fecha_pedido').value = fecha;
    }
    if (et.proveedor_id) document.getElementById('proveedor_id').value = et.proveedor_id;

    // Mostrar sección de ítems
    document.getElementById('seccion-items').classList.remove('hidden');
    document.getElementById('btn-guardar-et').textContent = '🔄 Actualizar Datos del Pedido';
    cargarItemsLista();
}

// ============================================================
// Catálogos
// ============================================================

function cargarDependencias() {
    return fetch('/api/dependencias')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('centro_costo_id');
            sel.innerHTML = '<option value="">— Seleccione centro de costo —</option>';
            data.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.id;
                opt.textContent = d.nombre;
                sel.appendChild(opt);
            });
        });
}

function cargarActividades() {
    return fetch('/api/actividades-operativas')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('actividad_operativa_id');
            sel.innerHTML = '<option value="">— Seleccione actividad operativa —</option>';
            data.forEach(a => {
                const opt = document.createElement('option');
                opt.value = a.id;
                opt.textContent = a.codigo + ' – ' + a.nombre;
                sel.appendChild(opt);
            });
        });
}

function cargarProveedores() {
    return fetch('/api/proveedores')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('proveedor_id');
            sel.innerHTML = '<option value="">— Seleccione proveedor —</option>';
            data.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.razon_social + ' (RUC: ' + p.ruc + ')';
                sel.appendChild(opt);
            });
        });
}

function cargarTiposBien() {
    return fetch('/api/tipos-bien')
        .then(r => r.json())
        .then(data => {
            tiposBien = data;
            const sel = document.getElementById('item-tipo-bien');
            if (sel) {
                sel.innerHTML = '<option value="">— Seleccione —</option>';
                data.forEach(t => {
                    const opt = document.createElement('option');
                    opt.value = t.id;
                    opt.textContent = t.nombre;
                    sel.appendChild(opt);
                });
            }
        });
}

// ============================================================
// Modales de catálogos inline
// ============================================================

function abrirModalProveedor() {
    document.getElementById('modal-proveedor').classList.add('show');
}

function guardarProveedor() {
    const body = {
        ruc: document.getElementById('prov-ruc').value.trim(),
        razon_social: document.getElementById('prov-razon').value.trim(),
        direccion: document.getElementById('prov-direccion').value.trim(),
        telefono: document.getElementById('prov-telefono').value.trim(),
        correo: document.getElementById('prov-correo').value.trim(),
    };
    if (!body.ruc || !body.razon_social) { alert('RUC y razón social son obligatorios'); return; }

    fetch('/api/proveedores', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
    })
    .then(r => r.json().then(data => ({status: r.status, data})))
    .then(({status, data}) => {
        if (status >= 400) { alert(data.error || 'Error'); return; }
        cerrarModal('modal-proveedor');
        cargarProveedores();
        setTimeout(() => { document.getElementById('proveedor_id').value = data.id; }, 300);
    });
}

function abrirModalDependencia() {
    document.getElementById('modal-dependencia').classList.add('show');
}

function guardarDependencia() {
    const body = {
        nombre: document.getElementById('dep-nombre').value.trim(),
        edificio: document.getElementById('dep-edificio').value.trim(),
        pabellon: document.getElementById('dep-pabellon').value.trim(),
    };
    if (!body.nombre) { alert('El nombre es obligatorio'); return; }

    fetch('/api/dependencias', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
    })
    .then(r => r.json().then(data => ({status: r.status, data})))
    .then(({status, data}) => {
        if (status >= 400) { alert(data.error || 'Error'); return; }
        cerrarModal('modal-dependencia');
        cargarDependencias();
        setTimeout(() => { document.getElementById('centro_costo_id').value = data.id; }, 300);
    });
}

function abrirModalActividad() {
    document.getElementById('modal-actividad').classList.add('show');
}

function guardarActividad() {
    const body = {
        codigo: document.getElementById('act-codigo').value.trim(),
        nombre: document.getElementById('act-nombre').value.trim(),
    };
    if (!body.codigo || !body.nombre) { alert('Código y nombre son obligatorios'); return; }

    fetch('/api/actividades-operativas', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
    })
    .then(r => r.json().then(data => ({status: r.status, data})))
    .then(({status, data}) => {
        if (status >= 400) { alert(data.error || 'Error'); return; }
        cerrarModal('modal-actividad');
        cargarActividades();
        setTimeout(() => { document.getElementById('actividad_operativa_id').value = data.id; }, 300);
    });
}

// ============================================================
// Guardar ET
// ============================================================

function guardarET() {
    const numero_pedido = document.getElementById('numero_pedido').value.trim();
    const denominacion = document.getElementById('denominacion_adquisicion').value.trim();
    const fecha = document.getElementById('fecha_pedido').value;
    const proveedor_id = document.getElementById('proveedor_id').value;

    if (!denominacion) { alert('La denominación de la adquisición es obligatoria'); return; }
    if (!numero_pedido) { alert('El número de pedido es obligatorio'); return; }
    if (!/^\d+$/.test(numero_pedido)) { alert('El número de pedido debe contener solo dígitos'); return; }
    if (!fecha) { alert('La fecha del pedido es obligatoria'); return; }
    if (!proveedor_id) { alert('Seleccione un proveedor'); return; }

    const meta_codigo = document.getElementById('meta_codigo').value.trim();
    const anio_fiscal = parseInt(document.getElementById('anio_fiscal').value) || 2026;
    const meta_anio = meta_codigo ? (meta_codigo + '-' + anio_fiscal) : '';

    const body = {
        centro_costo_id: document.getElementById('centro_costo_id').value || null,
        actividad_operativa_id: document.getElementById('actividad_operativa_id').value || null,
        denominacion_adquisicion: denominacion,
        numero_pedido: numero_pedido,
        meta_codigo: meta_codigo,
        meta_anio: meta_anio,
        anio_fiscal: anio_fiscal,
        fecha_pedido: fecha,
        proveedor_id: parseInt(proveedor_id),
    };

    const url = etId ? ('/api/especificaciones/' + etId) : '/api/especificaciones';
    const method = etId ? 'PUT' : 'POST';

    fetch(url, {
        method: method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
    })
    .then(r => r.json().then(data => ({status: r.status, data})))
    .then(({status, data}) => {
        if (status >= 400) { alert(data.error || 'Error al guardar'); return; }
        if (!etId && data.id) {
            etId = data.id;
        }
        alert('Datos del pedido guardados correctamente');
        document.getElementById('seccion-items').classList.remove('hidden');
    });
}

// ============================================================
// Ítems
// ============================================================

function abrirModalItem() {
    document.getElementById('modal-item').classList.add('show');
    document.getElementById('item-descripcion').value = '';
    document.getElementById('item-clasificador').value = '';
    document.getElementById('item-unidad').value = 'UNIDAD';
    document.getElementById('item-cantidad').value = '1.00';
    document.getElementById('item-tipo-bien').value = '';
    document.getElementById('item-condiciones').value =
        'El bien debe ser entregado en óptimas condiciones de funcionamiento.\n' +
        'El bien deberá de ser original.\n' +
        'El bien deberá incluir accesorios necesarios para su funcionamiento.\n' +
        'Los bienes deberán de estar debidamente sellados.';
    document.getElementById('caracteristicas-container').classList.add('hidden');
    resetPreview();
}
    const imgInput = document.getElementById('item-imagen');
    if (imgInput) imgInput.value = '';
}

function cargarCaracteristicas() {
    const tipoBienId = parseInt(document.getElementById('item-tipo-bien').value);
    const container = document.getElementById('caracteristicas-container');
    const list = document.getElementById('caracteristicas-list');

    if (!tipoBienId) { container.classList.add('hidden'); return; }

    const tipo = tiposBien.find(t => t.id === tipoBienId);
    if (!tipo) return;

    container.classList.remove('hidden');
    list.innerHTML = '';

    const chars = tipo.caracteristicas_tipicas || [];
    chars.forEach((c, i) => {
        list.innerHTML += `
            <div class="char-row" data-idx="${i}">
                <input type="text" class="form-control" style="max-width:160px;"
                       value="${c.nombre}" id="char-nombre-${i}">
                <input type="text" class="form-control flex-1"
                       value="${c.valor_sugerido || ''}" id="char-valor-${i}"
                       placeholder="Ingrese valor específico">
                <span class="badge badge-suggested">SUGERIDA</span>
                <button class="btn btn-danger btn-sm" onclick="this.parentElement.remove()">✕</button>
            </div>
        `;
    });
}

function agregarCaracteristica() {
    const list = document.getElementById('caracteristicas-list');
    const idx = list.children.length;
    list.innerHTML += `
        <div class="char-row" data-idx="${idx}">
            <input type="text" class="form-control" style="max-width:160px;"
                   placeholder="Nombre" id="char-nombre-${idx}">
            <input type="text" class="form-control flex-1"
                   placeholder="Valor" id="char-valor-${idx}">
            <button class="btn btn-danger btn-sm" onclick="this.parentElement.remove()">✕</button>
        </div>
    `;
}

function guardarItem() {
    const tipoBienId = parseInt(document.getElementById('item-tipo-bien').value);
    const descripcion = document.getElementById('item-descripcion').value.trim();

    if (!tipoBienId || !descripcion) { alert('Tipo de bien y descripción son obligatorios'); return; }

    // Recolectar características
    const charRows = document.querySelectorAll('#caracteristicas-list .char-row');
    const caracteristicas = [];
    charRows.forEach(row => {
        const idx = row.dataset.idx;
        const nombre = document.getElementById('char-nombre-' + idx);
        const valor = document.getElementById('char-valor-' + idx);
        if (nombre && valor && nombre.value.trim()) {
            caracteristicas.push({
                nombre: nombre.value.trim(),
                valor: valor.value.trim(),
                sugerida: !!row.querySelector('.badge-suggested'),
            });
        }
    });

    const body = {
        tipo_bien_id: tipoBienId,
        descripcion: descripcion,
        clasificador: document.getElementById('item-clasificador').value.trim(),
        unidad_medida: document.getElementById('item-unidad').value.trim(),
        cantidad: parseFloat(document.getElementById('item-cantidad').value) || 1.00,
        caracteristicas: caracteristicas,
        condiciones_previas: document.getElementById('item-condiciones').value.trim(),
    };

    fetch('/api/especificaciones/' + etId + '/items', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
    })
    .then(r => r.json().then(data => ({status: r.status, data})))
    .then(({status, data}) => {
        if (status >= 400) { alert(data.error || 'Error'); return; }

        // Subir imagen si hay
        const imgInput = document.getElementById('item-imagen');
        if (imgInput && imgInput.files.length > 0) {
            const formData = new FormData();
            formData.append('imagen', imgInput.files[0]);
            fetch('/api/especificaciones/' + etId + '/items/' + data.id + '/imagen', {
                method: 'POST', body: formData,
            });
        }

        cerrarModal('modal-item');
        cargarItemsLista();
    });
}

function cargarItemsLista() {
    fetch('/api/especificaciones/' + etId + '/items')
        .then(r => r.json())
        .then(items => {
            const container = document.getElementById('items-container');
            if (items.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="icon">📦</div><p>Agregue los bienes del pedido</p></div>';
                return;
            }

            let html = '<div class="table-wrap" style="border:none;"><table class="table"><thead><tr>';
            html += '<th>N° Ítem</th><th>Tipo</th><th>Descripción</th><th>Clasificador</th><th>Cantidad</th><th>Unidad</th><th></th>';
            html += '</tr></thead><tbody>';

            items.forEach((item, i) => {
                const num = String(i + 1).padStart(3, '0');
                html += '<tr>';
                html += '<td><strong>' + num + '</strong></td>';
                html += '<td>' + (item.tipo_bien_nombre || '') + '</td>';
                html += '<td>' + item.descripcion + '</td>';
                html += '<td><code>' + (item.clasificador || '-') + '</code></td>';
                html += '<td>' + parseFloat(item.cantidad).toFixed(2) + '</td>';
                html += '<td>' + item.unidad_medida + '</td>';
                html += '<td>';
                html += '<button class="btn btn-danger btn-sm" onclick="eliminarItem(' + item.id + ')">✕</button>';
                html += '</td>';
                html += '</tr>';

                // Mostrar características debajo
                const chars = item.caracteristicas || [];
                if (chars.length > 0) {
                    html += '<tr><td></td><td colspan="6"><div class="char-list" style="padding:0.5rem 0;">';
                    html += '<strong class="text-sm">Características:</strong><br>';
                    chars.forEach(c => {
                        html += '<span class="text-sm">• <strong>' + c.nombre + ':</strong> ' + (c.valor || c.valor_sugerido || '-') + '</span><br>';
                    });
                    html += '</div></td></tr>';
                }

                // Imagen
                if (item.imagen_referencial) {
                    html += '<tr><td></td><td colspan="6">';
                    html += '<img src="/static/' + item.imagen_referencial + '" style="max-width:300px;border-radius:8px;border:1px solid #e2e8f0;" alt="Imagen referencial">';
                    html += '</td></tr>';
                }
            });

            html += '</tbody></table></div>';
            container.innerHTML = html;
        });
}

function eliminarItem(itemId) {
    if (!confirm('¿Eliminar este ítem?')) return;
    fetch('/api/especificaciones/' + etId + '/items/' + itemId, { method: 'DELETE' })
        .then(r => { if (r.ok) cargarItemsLista(); });
}

// ============================================================
// Finalizar ET
// ============================================================

function finalizarET() {
    if (!confirm('¿Finalizar esta Especificación Técnica? Una vez finalizada, no se podrán modificar los datos.')) return;

    fetch('/api/especificaciones/' + etId + '/finalizar', { method: 'POST' })
        .then(r => r.json().then(data => ({status: r.status, data})))
        .then(({status, data}) => {
            if (status >= 400) { alert(data.error || 'Error al finalizar'); return; }
            alert('Especificación Técnica finalizada correctamente');
            window.location.href = '/especificaciones/' + etId;
        });
}

// ============================================================
// Modales y Preview de Imagen
// ============================================================

function cerrarModal(id) {
    document.getElementById(id).classList.remove('show');
}

function mostrarPreview(file) {
    if (!file || !file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        const zona = document.getElementById('preview-zona');
        zona.innerHTML = '<img src="' + e.target.result + '" style="max-width:100%;max-height:250px;border-radius:8px;" alt="Preview">' +
            '<p class="text-sm text-muted" style="margin-top:0.5rem;">📎 ' + file.name + ' — <a href="#" onclick="resetPreview(); return false;">Cambiar</a></p>';
    };
    reader.readAsDataURL(file);
}

function resetPreview() {
    const zona = document.getElementById('preview-zona');
    zona.innerHTML = '<div style="font-size:2rem;">📎</div>' +
        '<p class="text-sm text-muted">Arrastre una imagen aquí o haga clic para seleccionar</p>' +
        '<p class="text-sm text-muted">(PNG, JPG, GIF, WebP)</p>';
    const imgInput = document.getElementById('item-imagen');
    if (imgInput) imgInput.value = '';
}
