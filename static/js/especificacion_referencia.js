/* ============================================================
   JavaScript para Registro de ET Recibida (Físico / Referencia)
   Optimizado para transcripción rápida desde documento físico.
   ============================================================ */

let tiposBienCache = [];
let filaCounter = 0;

document.addEventListener('DOMContentLoaded', async () => {
    await cargarCatalogos();
    agregarFilaItem(); // Una fila por defecto
});

// ============================================================
// Carga de catálogos (dependencias, proveedores, tipos de bien)
// ============================================================

async function cargarCatalogos() {
    try {
        const [respDep, respProv, respTipos] = await Promise.all([
            fetch('/api/dependencias'),
            fetch('/api/proveedores'),
            fetch('/api/tipos-bien')
        ]);

        if (respDep.ok) {
            const deps = await respDep.json();
            const sel = document.getElementById('centro_costo_id');
            const valActual = sel.value;
            sel.innerHTML = '<option value="">-- Seleccionar --</option>';
            deps.forEach(d => {
                sel.innerHTML += `<option value="${d.id}">${d.nombre}</option>`;
            });
            if (valActual) sel.value = valActual;
        }

        if (respProv.ok) {
            const provs = await respProv.json();
            const sel = document.getElementById('proveedor_id');
            const valActual = sel.value;
            sel.innerHTML = '<option value="">-- Seleccionar --</option>';
            provs.forEach(p => {
                sel.innerHTML += `<option value="${p.id}">${p.razon_social} (RUC: ${p.ruc})</option>`;
            });
            if (valActual) sel.value = valActual;
        }

        if (respTipos.ok) {
            tiposBienCache = await respTipos.json();
            actualizarSelectsTipoBien();
        }
    } catch (err) {
        console.error('Error al cargar catálogos:', err);
    }
}

function actualizarSelectsTipoBien() {
    document.querySelectorAll('.select-tipo-bien').forEach(sel => {
        const valActual = sel.value;
        sel.innerHTML = '<option value="">-- Seleccionar --</option>';
        tiposBienCache.forEach(tb => {
            sel.innerHTML += `<option value="${tb.id}">${tb.nombre}</option>`;
        });
        if (valActual) sel.value = valActual;
    });
}

// ============================================================
// Tabla dinámica de ítems del pedido
// ============================================================

function agregarFilaItem() {
    const tbody = document.getElementById('items-tbody');
    const idx = filaCounter++;

    const tr = document.createElement('tr');
    tr.id = `fila-item-${idx}`;
    tr.innerHTML = `
        <td>
            <div style="display:flex; gap:0.25rem;">
                <select class="form-control select-tipo-bien" id="item-tipo-${idx}" required>
                    <option value="">-- Tipo --</option>
                    ${tiposBienCache.map(tb => `<option value="${tb.id}">${tb.nombre}</option>`).join('')}
                </select>
                <button type="button" class="btn btn-secondary btn-sm"
                        onclick="abrirModalTipoBien(${idx})" title="Nuevo tipo">+</button>
            </div>
        </td>
        <td>
            <input type="text" class="form-control" id="item-desc-${idx}"
                   placeholder="Ej: IMPRESORA MULTIFUNCIÓN ECOTANK" required>
        </td>
        <td>
            <input type="number" class="form-control text-center" id="item-cant-${idx}"
                   value="1" min="1" step="1" required style="width:80px;">
        </td>
        <td>
            <input type="text" class="form-control" id="item-unidad-${idx}"
                   value="UNIDAD" style="width:100px;">
        </td>
        <td>
            <input type="text" class="form-control" id="item-clasif-${idx}"
                   placeholder="2.6.3.2.2.1" style="width:120px;">
        </td>
        <td class="text-center">
            <button type="button" class="btn btn-danger btn-sm"
                    onclick="eliminarFilaItem(${idx})" title="Quitar ítem">🗑️</button>
        </td>
    `;
    tbody.appendChild(tr);
}

function eliminarFilaItem(idx) {
    const fila = document.getElementById(`fila-item-${idx}`);
    if (fila) {
        // No permitir eliminar si solo queda una fila
        const filas = document.querySelectorAll('#items-tbody tr');
        if (filas.length <= 1) {
            alert('Debe haber al menos un ítem en el pedido.');
            return;
        }
        fila.remove();
    }
}

// ============================================================
// Modales inline (Dependencia, Proveedor, Tipo de Bien)
// ============================================================

function abrirModal(id) {
    document.getElementById(id).classList.add('active');
}

function cerrarModal(id) {
    document.getElementById(id).classList.remove('active');
}

let targetIndexTipoBien = null;
function abrirModalTipoBien(idx) {
    targetIndexTipoBien = idx;
    abrirModal('modal-tipo-bien');
}

async function guardarDependenciaModal() {
    const nombre = document.getElementById('modal-dep-nombre').value.trim();
    if (!nombre) { alert('Ingrese el nombre de la oficina'); return; }

    try {
        const resp = await fetch('/api/dependencias', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                nombre,
                edificio: document.getElementById('modal-dep-edificio').value.trim(),
                pabellon: document.getElementById('modal-dep-pabellon').value.trim()
            })
        });
        const res = await resp.json();
        if (!resp.ok) { alert(res.error || 'Error al guardar'); return; }

        cerrarModal('modal-dependencia');
        // Limpiar campos del modal
        document.getElementById('modal-dep-nombre').value = '';
        document.getElementById('modal-dep-edificio').value = '';
        document.getElementById('modal-dep-pabellon').value = '';
        await cargarCatalogos();
        document.getElementById('centro_costo_id').value = res.id;
    } catch (e) {
        alert('Error de conexión');
    }
}

async function guardarProveedorModal() {
    const ruc = document.getElementById('modal-prov-ruc').value.trim();
    const razon = document.getElementById('modal-prov-razon').value.trim();

    if (!ruc || ruc.length !== 11 || !/^\d+$/.test(ruc)) {
        alert('Ingrese un RUC válido de 11 dígitos'); return;
    }
    if (!razon) { alert('Ingrese la Razón Social'); return; }

    try {
        const resp = await fetch('/api/proveedores', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                ruc,
                razon_social: razon,
                direccion: document.getElementById('modal-prov-direccion').value.trim(),
                telefono: document.getElementById('modal-prov-telefono').value.trim(),
                correo: document.getElementById('modal-prov-correo').value.trim()
            })
        });
        const res = await resp.json();
        if (!resp.ok) { alert(res.error || 'Error al guardar'); return; }

        cerrarModal('modal-proveedor');
        // Limpiar campos del modal
        ['modal-prov-ruc', 'modal-prov-razon', 'modal-prov-direccion',
         'modal-prov-telefono', 'modal-prov-correo'].forEach(id => {
            document.getElementById(id).value = '';
        });
        await cargarCatalogos();
        document.getElementById('proveedor_id').value = res.id;
    } catch (e) {
        alert('Error de conexión');
    }
}

async function guardarTipoBienModal() {
    const nombre = document.getElementById('modal-tb-nombre').value.trim();
    const requiere_serie = document.getElementById('modal-tb-requiere-serie').checked;

    if (!nombre) { alert('Ingrese el nombre del tipo de bien'); return; }

    try {
        const resp = await fetch('/api/tipos-bien', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                nombre,
                caracteristicas_tipicas: [],
                requiere_serie
            })
        });
        const res = await resp.json();
        if (!resp.ok) { alert(res.error || 'Error al guardar'); return; }

        cerrarModal('modal-tipo-bien');
        document.getElementById('modal-tb-nombre').value = '';
        document.getElementById('modal-tb-requiere-serie').checked = true;
        await cargarCatalogos();
        // Seleccionar el tipo recién creado en la fila correspondiente
        if (targetIndexTipoBien !== null) {
            const sel = document.getElementById(`item-tipo-${targetIndexTipoBien}`);
            if (sel) sel.value = res.id;
        }
    } catch (e) {
        alert('Error de conexión');
    }
}

// ============================================================
// Guardar Registro por Referencia
// ============================================================

async function guardarEspecificacionReferencia() {
    const numero_pedido = document.getElementById('numero_pedido').value.trim();
    const fecha_pedido = document.getElementById('fecha_pedido').value;
    const denominacion = document.getElementById('denominacion_adquisicion').value.trim();

    // Validaciones
    if (!numero_pedido) { alert('Ingrese el número de pedido de compra'); return; }
    if (!fecha_pedido) { alert('Ingrese la fecha del pedido'); return; }
    if (!denominacion) { alert('Ingrese la denominación de la adquisición'); return; }

    // Recolectar ítems visibles
    const items = [];
    const filas = document.querySelectorAll('#items-tbody tr');

    for (const fila of filas) {
        const idx = fila.id.replace('fila-item-', '');
        const tipo_bien_id = document.getElementById(`item-tipo-${idx}`)?.value;
        const descripcion = document.getElementById(`item-desc-${idx}`)?.value.trim();
        const cantidad = parseInt(document.getElementById(`item-cant-${idx}`)?.value || '1', 10);
        const unidad = document.getElementById(`item-unidad-${idx}`)?.value.trim() || 'UNIDAD';
        const clasificador = document.getElementById(`item-clasif-${idx}`)?.value.trim() || '';

        if (!tipo_bien_id) {
            alert(`Seleccione el tipo de bien en el ítem ${items.length + 1}`); return;
        }
        if (!descripcion) {
            alert(`Ingrese la descripción en el ítem ${items.length + 1}`); return;
        }
        if (cantidad <= 0) {
            alert(`La cantidad debe ser mayor a 0 en el ítem ${items.length + 1}`); return;
        }

        items.push({
            tipo_bien_id: parseInt(tipo_bien_id, 10),
            descripcion,
            cantidad,
            unidad_medida: unidad,
            clasificador
        });
    }

    if (items.length === 0) {
        alert('Debe registrar al menos un ítem del pedido'); return;
    }

    // Construir FormData (multipart para adjunto)
    const formData = new FormData();
    formData.append('numero_pedido', numero_pedido);
    formData.append('fecha_pedido', fecha_pedido);
    formData.append('denominacion_adquisicion', denominacion);
    formData.append('centro_costo_id', document.getElementById('centro_costo_id').value || '');
    formData.append('proveedor_id', document.getElementById('proveedor_id').value || '');
    formData.append('meta_codigo', document.getElementById('meta_codigo').value.trim());
    formData.append('anio_fiscal', document.getElementById('anio_fiscal').value.trim());
    formData.append('finalidad_publica', document.getElementById('finalidad_publica').value.trim());
    formData.append('origen', 'REFERENCIA_EXTERNA');
    formData.append('items', JSON.stringify(items));

    const fileInput = document.getElementById('documento_adjunto');
    if (fileInput && fileInput.files[0]) {
        formData.append('documento_adjunto', fileInput.files[0]);
    }

    // Deshabilitar botón mientras se guarda
    const btn = document.getElementById('btn-guardar-ref');
    btn.disabled = true;
    btn.innerHTML = '⌛ Registrando...';

    try {
        const resp = await fetch('/api/especificaciones/referencia', {
            method: 'POST',
            body: formData
        });
        const res = await resp.json();

        if (resp.ok) {
            alert('✅ Especificación Técnica registrada exitosamente.\n\nYa puede crear Fichas Técnicas para los bienes de este pedido.');
            window.location.href = '/especificaciones';
        } else {
            alert('❌ ' + (res.error || 'Error al registrar'));
            btn.disabled = false;
            btn.innerHTML = '💾 Registrar Especificación';
        }
    } catch (err) {
        alert('❌ Error de conexión con el servidor');
        btn.disabled = false;
        btn.innerHTML = '💾 Registrar Especificación';
    }
}
