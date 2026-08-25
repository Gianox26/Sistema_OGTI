/**
 * ficha.js
 * Lógica del formulario de Ficha Técnica:
 * - Selección de ET e ítem con autocompletado
 * - Validación AJAX de serie única
 * - Checklist de 6 casillas que bloquea/habilita el botón Finalizar
 * - Guardado de borrador y finalización
 */

let fichaId = null;
let etSeleccionada = null;
let itemSeleccionado = null;
let serieTimeout = null;

// Inicialización
document.addEventListener('DOMContentLoaded', function () {
    cargarETsFinalizadas();
    cargarResponsables();

    // Pre-seleccionar ET si viene por query param
    const params = new URLSearchParams(window.location.search);
    const etIdParam = params.get('et_id');
    if (etIdParam) {
        setTimeout(() => {
            document.getElementById('et-selector').value = etIdParam;
            cargarItemsET();
        }, 500);
    }
});

// --- Cargar ETs finalizadas ---

function cargarETsFinalizadas() {
    fetch('/api/especificaciones/finalizadas')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('et-selector');
            sel.innerHTML = '<option value="">— Seleccione una ET finalizada —</option>';
            data.forEach(et => {
                const opt = document.createElement('option');
                opt.value = et.id;
                opt.textContent = `${et.numero_pedido} — ${et.denominacion_adquisicion || 'Sin denominación'} (${et.total_items} ítems)`;
                sel.appendChild(opt);
            });
        });
}

function cargarItemsET() {
    const etId = document.getElementById('et-selector').value;
    const itemSel = document.getElementById('item-selector');

    if (!etId) {
        itemSel.innerHTML = '<option value="">— Primero seleccione una ET —</option>';
        return;
    }

    fetch(`/api/especificaciones/${etId}/items`)
        .then(r => r.json())
        .then(items => {
            itemSel.innerHTML = '<option value="">— Seleccione un ítem —</option>';
            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = `${item.tipo_bien_nombre}: ${item.descripcion} (Cant: ${item.cantidad})`;
                opt.dataset.item = JSON.stringify(item);
                itemSel.appendChild(opt);
            });
        });

    // Cargar datos de la ET para autocompletar
    fetch(`/api/especificaciones/${etId}/items`)
        .then(() => {
            // Cargar los datos generales de la ET (vía la página de detalle, simplificado)
            // Para el autocompletado, usamos los datos que ya tenemos
        });
}

function cargarDatosItem() {
    const itemSel = document.getElementById('item-selector');
    const selectedOpt = itemSel.options[itemSel.selectedIndex];

    if (!selectedOpt || !selectedOpt.dataset.item) return;

    itemSeleccionado = JSON.parse(selectedOpt.dataset.item);
    const etId = document.getElementById('et-selector').value;

    // Cargar datos de la ET (proveedor, etc.)
    // Usamos el endpoint de items que ya tiene la data
    fetch(`/api/especificaciones/finalizadas`)
        .then(r => r.json())
        .then(ets => {
            etSeleccionada = ets.find(e => e.id == etId);

            if (etSeleccionada) {
                document.getElementById('h-pedido').value = etSeleccionada.numero_pedido || '';
                document.getElementById('h-fecha').value = etSeleccionada.fecha_pedido || '';
                document.getElementById('h-denominacion').value = etSeleccionada.denominacion_adquisicion || '';
            }

            // Precargar datos del proveedor (editables) desde la ET
            document.getElementById('ft-proveedor-nombre').value = (etSeleccionada && etSeleccionada.proveedor_nombre) || '';
            document.getElementById('ft-proveedor-dir').value = (etSeleccionada && etSeleccionada.proveedor_direccion) || '';
            document.getElementById('ft-proveedor-tel').value = (etSeleccionada && etSeleccionada.proveedor_telefono) || '';

            // Mostrar las secciones ocultas
            document.getElementById('paso-datos-heredados').classList.remove('hidden');
            document.getElementById('paso-datos-manuales').classList.remove('hidden');
            document.getElementById('paso-adquisicion').classList.remove('hidden');
            document.getElementById('paso-checklist').classList.remove('hidden');
            document.getElementById('paso-acciones').classList.remove('hidden');
            document.getElementById('paso-acciones').style.display = 'flex';

            // Mostrar características del ítem
            const charsContainer = document.getElementById('h-caracteristicas');
            const chars = itemSeleccionado.caracteristicas || [];
            if (chars.length > 0) {
                charsContainer.innerHTML = chars.map(c =>
                    `<div class="char-row">
                        <span class="char-name">${c.nombre}:</span>
                        <span class="char-value">${c.valor || c.valor_sugerido || '-'}</span>
                    </div>`
                ).join('');
            } else {
                charsContainer.innerHTML = '<p class="text-muted text-sm">Sin características registradas</p>';
            }
        });
}

// --- Responsables ---

function cargarResponsables() {
    fetch('/api/responsables')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('ft-responsable');
            sel.innerHTML = '<option value="">— Seleccione —</option>';
            data.forEach(r => {
                const opt = document.createElement('option');
                opt.value = r.id;
                opt.textContent = `${r.nombre} — ${r.cargo || ''} (${r.dependencia_nombre || ''})`;
                sel.appendChild(opt);
            });
        });

    // Cargar dependencias para el modal
    fetch('/api/dependencias')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('resp-dependencia');
            if (sel) {
                sel.innerHTML = '<option value="">— Seleccione —</option>';
                data.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = d.nombre;
                    sel.appendChild(opt);
                });
            }
        });
}

function abrirModalResponsable() {
    document.getElementById('modal-responsable').classList.add('show');
}

function guardarResponsable() {
    const body = {
        nombre: document.getElementById('resp-nombre').value.trim(),
        cargo: document.getElementById('resp-cargo').value.trim(),
        telefono: document.getElementById('resp-telefono').value.trim(),
        correo: document.getElementById('resp-correo').value.trim(),
        dependencia_id: document.getElementById('resp-dependencia').value || null,
    };

    if (!body.nombre) {
        alert('El nombre es obligatorio');
        return;
    }

    fetch('/api/responsables', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
        .then(r => r.json().then(data => ({ status: r.status, data })))
        .then(({ status, data }) => {
            if (status >= 400) {
                alert(data.error || 'Error');
                return;
            }
            cerrarModal('modal-responsable');
            cargarResponsables();
            setTimeout(() => {
                document.getElementById('ft-responsable').value = data.id;
            }, 300);
        });
}

// --- Validación AJAX de serie ---

function validarSerieAjax() {
    clearTimeout(serieTimeout);
    const serie = document.getElementById('ft-serie').value.trim();
    const feedback = document.getElementById('serie-feedback');

    if (!serie) {
        feedback.textContent = '';
        feedback.className = 'form-help';
        return;
    }

    serieTimeout = setTimeout(() => {
        fetch(`/api/fichas/validar-serie?serie=${encodeURIComponent(serie)}`)
            .then(r => r.json())
            .then(data => {
                if (data.disponible) {
                    feedback.textContent = '✅ ' + data.mensaje;
                    feedback.className = 'form-help';
                    feedback.style.color = 'var(--green-700)';
                } else {
                    feedback.textContent = '❌ ' + data.mensaje;
                    feedback.className = 'form-error';
                }
            });
    }, 400);
}

// --- Checklist ---

function toggleCheck(campo) {
    const chk = document.getElementById(`chk-${campo}`);
    chk.checked = !chk.checked;
    actualizarChecklist();
}

function actualizarChecklist() {
    const casillas = [
        'marca_coincide', 'modelo_coincide', 'serie_ingresada',
        'estado_fisico_revisado', 'caracteristicas_verificadas',
        'datos_proveedor_correctos'
    ];

    let todasMarcadas = true;
    casillas.forEach(c => {
        const chk = document.getElementById(`chk-${c}`);
        const item = document.getElementById(`chk-${c.replace('_', '-')}-item`) ||
                     chk.closest('.check-item');

        if (chk.checked) {
            if (item) item.classList.add('checked');
        } else {
            if (item) item.classList.remove('checked');
            todasMarcadas = false;
        }
    });

    document.getElementById('btn-finalizar-ft').disabled = !todasMarcadas;
}

// --- Guardar Borrador ---

function guardarFicha() {
    const etId = document.getElementById('et-selector').value;
    const itemId = document.getElementById('item-selector').value;
    const serie = document.getElementById('ft-serie').value.trim();

    if (!etId || !itemId || !serie) {
        alert('Seleccione una ET, un ítem e ingrese el número de serie');
        return;
    }

    const body = {
        especificacion_id: parseInt(etId),
        item_id: parseInt(itemId),
        marca: document.getElementById('ft-marca').value.trim(),
        modelo: document.getElementById('ft-modelo').value.trim(),
        color: document.getElementById('ft-color').value.trim(),
        numero_serie: serie,
        estado_fisico: document.getElementById('ft-estado-fisico').value,
        observaciones: document.getElementById('ft-observaciones').value.trim(),
        carta_levantamiento: document.getElementById('ft-carta').value.trim(),
        responsable_id: document.getElementById('ft-responsable').value || null,
        proveedor_razon: document.getElementById('ft-proveedor-nombre').value.trim(),
        proveedor_direccion: document.getElementById('ft-proveedor-dir').value.trim(),
        proveedor_telefono: document.getElementById('ft-proveedor-tel').value.trim(),
        orden_compra: document.getElementById('ft-orden-compra').value.trim(),
        costo: document.getElementById('ft-costo').value
                  ? parseFloat(document.getElementById('ft-costo').value) : null,
        fecha_adquisicion: document.getElementById('ft-fecha-adquisicion').value || null,
        garantia: document.getElementById('ft-garantia').value.trim(),
        caracteristicas_verificadas: itemSeleccionado ? (itemSeleccionado.caracteristicas || []) : [],
    };

    if (fichaId) {
        // Actualizar
        // Recopilar checklist
        const checklist = {};
        ['marca_coincide', 'modelo_coincide', 'serie_ingresada',
         'estado_fisico_revisado', 'caracteristicas_verificadas',
         'datos_proveedor_correctos'].forEach(c => {
            checklist[c] = document.getElementById(`chk-${c}`).checked;
        });
        body.checklist = checklist;

        fetch(`/api/fichas/${fichaId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        })
            .then(r => r.json().then(data => ({ status: r.status, data })))
            .then(({ status, data }) => {
                if (status >= 400) {
                    alert(data.error || 'Error al actualizar');
                    return;
                }
                alert('Ficha actualizada correctamente');
            });
    } else {
        // Crear nueva
        fetch('/api/fichas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        })
            .then(r => r.json().then(data => ({ status: r.status, data })))
            .then(({ status, data }) => {
                if (status >= 400) {
                    alert(data.error || 'Error al guardar');
                    return;
                }
                fichaId = data.id;
                document.getElementById('btn-guardar-ft').textContent = '💾 Actualizar Borrador';
                alert('Ficha guardada como borrador');
            });
    }
}

// --- Finalizar ---

function finalizarFicha() {
    if (!fichaId) {
        alert('Primero guarde la ficha como borrador');
        return;
    }

    // Guardar checklist antes de finalizar
    const checklist = {};
    ['marca_coincide', 'modelo_coincide', 'serie_ingresada',
     'estado_fisico_revisado', 'caracteristicas_verificadas',
     'datos_proveedor_correctos'].forEach(c => {
        checklist[c] = document.getElementById(`chk-${c}`).checked;
    });

    // Actualizar checklist primero
    fetch(`/api/fichas/${fichaId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ checklist }),
    }).then(() => {
        // Luego finalizar
        if (!confirm('¿Finalizar esta Ficha Técnica? Se asignará un número correlativo permanente y no se podrá editar.')) return;

        fetch(`/api/fichas/${fichaId}/finalizar`, { method: 'POST' })
            .then(r => r.json().then(data => ({ status: r.status, data })))
            .then(({ status, data }) => {
                if (status >= 400) {
                    alert(data.error || 'Error al finalizar');
                    if (data.casillas_faltantes) {
                        alert('Casillas faltantes: ' + data.casillas_faltantes.join(', '));
                    }
                    return;
                }
                alert(`Ficha Técnica finalizada exitosamente\nN° Correlativo: ${data.numero_correlativo}`);
                window.location.href = `/fichas/${fichaId}`;
            });
    });
}

// --- Modal helper ---

function cerrarModal(id) {
    document.getElementById(id).classList.remove('show');
}
