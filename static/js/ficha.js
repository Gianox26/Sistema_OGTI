/**
 * ficha.js
 * Lógica del formulario de Ficha Técnica:
 * - Selección de ET e ítem con autocompletado
 * - Proveedor seleccionable desde la base de datos (con modal para crear nuevo)
 * - Validación AJAX de serie única
 * - Checklist dinámico basado en las características de la ET
 * - Guardado de borrador y finalización
 */

let fichaId = null;
let etSeleccionada = null;
let itemSeleccionado = null;
let serieTimeout = null;
let proveedoresCache = [];

// ============================================================
// Inicialización
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
    cargarETsFinalizadas();
    cargarResponsables();
    cargarProveedoresFT();

    // Listener para buscar plantilla automáticamente al ingresar marca y modelo
    const marcaEl = document.getElementById('ft-marca');
    const modeloEl = document.getElementById('ft-modelo');
    if (marcaEl && modeloEl) {
        marcaEl.addEventListener('blur', () => verificarPlantillaExistente(false));
        modeloEl.addEventListener('blur', () => verificarPlantillaExistente(false));
        modeloEl.addEventListener('change', () => verificarPlantillaExistente(false));
    }

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

// ============================================================
// Cargar ETs finalizadas
// ============================================================

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
}

function cargarDatosItem() {
    const itemSel = document.getElementById('item-selector');
    const selectedOpt = itemSel.options[itemSel.selectedIndex];

    if (!selectedOpt || !selectedOpt.dataset.item) return;

    itemSeleccionado = JSON.parse(selectedOpt.dataset.item);
    const etId = document.getElementById('et-selector').value;

    // Cargar datos de la ET para autocompletar campos heredados
    fetch(`/api/especificaciones/finalizadas`)
        .then(r => r.json())
        .then(ets => {
            etSeleccionada = ets.find(e => e.id == etId);

            if (etSeleccionada) {
                document.getElementById('h-pedido').value = etSeleccionada.numero_pedido || '';
                document.getElementById('h-fecha').value = etSeleccionada.fecha_pedido || '';
                document.getElementById('h-denominacion').value = etSeleccionada.denominacion_adquisicion || '';

                // Pre-seleccionar proveedor de la ET si existe
                if (etSeleccionada.proveedor_id) {
                    const provSel = document.getElementById('ft-proveedor-id');
                    if (provSel) {
                        provSel.value = etSeleccionada.proveedor_id;
                        cargarDatosProveedor();
                    }
                }
            }

            // Mostrar SIEMPRE todas las secciones del formulario
            document.getElementById('paso-datos-heredados').classList.remove('hidden');
            document.getElementById('paso-datos-manuales').classList.remove('hidden');
            document.getElementById('paso-caracteristicas').classList.remove('hidden');
            document.getElementById('paso-adquisicion').classList.remove('hidden');
            document.getElementById('paso-acciones').classList.remove('hidden');
            document.getElementById('paso-acciones').style.display = 'flex';

            // Renderizar campos dinámicos de series según la cantidad requerida en el ítem de la ET
            const cantItem = Math.round(parseFloat(itemSeleccionado.cantidad) || 1);
            renderizarCamposSeries(cantItem, true);

            // Mostrar características del ítem en datos heredados
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

            // Renderizar características editables
            renderCaracteristicasEditables(chars);

            // Verificar si el tipo de bien exige número de serie
            if (itemSeleccionado && itemSeleccionado.tipo_bien_id) {
                actualizarFormatoSerie(itemSeleccionado.tipo_bien_id);
            }
        });
}

function actualizarFormatoSerie(tipoBienId) {
    if (!tipoBienId) return;
    fetch('/api/tipos-bien')
        .then(r => r.json())
        .then(tipos => {
            const tb = tipos.find(t => t.id == tipoBienId);
            const feedbackSerie = document.getElementById('serie-feedback');
            const cantItem = itemSeleccionado ? Math.round(parseFloat(itemSeleccionado.cantidad) || 1) : 1;
            const requiere = tb ? (tb.requiere_serie !== false) : true;

            renderizarCamposSeries(cantItem, requiere);

            if (feedbackSerie) {
                if (!requiere) {
                    feedbackSerie.innerHTML = '<span class="text-muted">ℹ️ Este tipo de bien no exige número de serie obligatorio.</span>';
                } else {
                    feedbackSerie.innerHTML = '';
                }
            }
        })
}

// ============================================================
// Proveedores
// ============================================================

function cargarProveedoresFT() {
    return fetch('/api/proveedores')
        .then(r => r.json())
        .then(data => {
            proveedoresCache = data;
            const sel = document.getElementById('ft-proveedor-id');
            if (sel) {
                sel.innerHTML = '<option value="">— Seleccione proveedor —</option>';
                data.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = `${p.razon_social} (RUC: ${p.ruc})`;
                    sel.appendChild(opt);
                });
            }
        });
}

function cargarDatosProveedor() {
    const sel = document.getElementById('ft-proveedor-id');
    const provId = sel ? parseInt(sel.value) : null;

    if (!provId) {
        // Limpiar campos
        document.getElementById('ft-proveedor-ruc').value = '';
        document.getElementById('ft-proveedor-nombre').value = '';
        document.getElementById('ft-proveedor-dir').value = '';
        document.getElementById('ft-proveedor-tel').value = '';
        document.getElementById('ft-proveedor-correo').value = '';
        return;
    }

    const prov = proveedoresCache.find(p => p.id === provId);
    if (prov) {
        document.getElementById('ft-proveedor-ruc').value = prov.ruc || '';
        document.getElementById('ft-proveedor-nombre').value = prov.razon_social || '';
        document.getElementById('ft-proveedor-dir').value = prov.direccion || '';
        document.getElementById('ft-proveedor-tel').value = prov.telefono || '';
        document.getElementById('ft-proveedor-correo').value = prov.correo || '';
    }
}

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

    if (!body.ruc || !body.razon_social) {
        alert('RUC y Razón Social son obligatorios');
        return;
    }

    fetch('/api/proveedores', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
    .then(r => r.json().then(data => ({ status: r.status, data })))
    .then(({ status, data }) => {
        if (status >= 400) { alert(data.error || 'Error al guardar proveedor'); return; }
        cerrarModal('modal-proveedor');
        cargarProveedoresFT().then(() => {
            const sel = document.getElementById('ft-proveedor-id');
            if (sel) {
                sel.value = data.id;
                cargarDatosProveedor();
            }
        });
    });
}

// ============================================================
// Responsables
// ============================================================

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

// ============================================================
// Validación AJAX de serie
// ============================================================

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

// ============================================================
// Checklist dinámico basado en características de la ET
// ============================================================

function generarChecklistDinamico(caracteristicas) {
    const container = document.getElementById('checklist-caracteristicas-inline');
    if (!container) return;

    let html = '';

    // Siempre incluir verificaciones base
    const checksBase = [
        { id: 'marca_coincide', label: '¿La marca del bien recibido coincide con lo solicitado?' },
        { id: 'modelo_coincide', label: '¿El modelo del bien recibido coincide con lo solicitado?' },
        { id: 'serie_ingresada', label: '¿El número de serie fue verificado e ingresado correctamente?' },
        { id: 'datos_proveedor_correctos', label: '¿Los datos del proveedor son correctos?' },
    ];

    checksBase.forEach(chk => {
        html += `
            <div class="check-item" onclick="toggleCheck('${chk.id}')">
                <input type="checkbox" id="chk-${chk.id}" onchange="actualizarChecklist()">
                <label for="chk-${chk.id}">${chk.label}</label>
            </div>`;
    });

    // Agregar un checkbox por cada característica de la ET
    if (caracteristicas && caracteristicas.length > 0) {
        html += '<div class="checklist-title" style="margin-top:0.75rem;">📋 Características Técnicas de la ET</div>';
        caracteristicas.forEach((c, idx) => {
            const nombre = c.nombre || '';
            const valor = c.valor || c.valor_sugerido || '';
            const checkId = `caract_${idx}`;
            html += `
                <div class="check-item" onclick="toggleCheck('${checkId}')">
                    <input type="checkbox" id="chk-${checkId}" onchange="actualizarChecklist()">
                    <label for="chk-${checkId}">
                        ¿<strong>${nombre}</strong> cumple con lo especificado? <span class="text-muted text-sm">(Esperado: ${valor || 'según ET'})</span>
                    </label>
                </div>`;
        });
    }

    container.innerHTML = html;
}

function toggleCheck(campo) {
    const chk = document.getElementById(`chk-${campo}`);
    if (chk) {
        chk.checked = !chk.checked;
        actualizarChecklist();
    }
}

function actualizarChecklist() {
    const container = document.getElementById('checklist-caracteristicas-inline');
    if (!container) return;

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    let todasMarcadas = true;

    checkboxes.forEach(chk => {
        const item = chk.closest('.check-item');
        if (chk.checked) {
            if (item) item.classList.add('checked');
        } else {
            if (item) item.classList.remove('checked');
            todasMarcadas = false;
        }
    });

    const btnFinalizar = document.getElementById('btn-finalizar-ft');
    if (btnFinalizar) {
        btnFinalizar.disabled = !todasMarcadas;
    }
}

// ============================================================
// Guardar Borrador
// ============================================================

function guardarFicha() {
    const etId = document.getElementById('et-selector').value;
    const itemId = document.getElementById('item-selector').value;

    if (!etId || !itemId) {
        alert('Seleccione una Especificación Técnica y un ítem');
        return;
    }

    const seriesInputs = document.querySelectorAll('.ft-serie-input');
    const seriesVals = Array.from(seriesInputs).map(inp => ({
        numero_serie: inp.value.trim(),
        estado_fisico: 'NUEVO'
    }));

    const provIdEl = document.getElementById('ft-proveedor-id');
    const checklistData = recopilarChecklist();
    const charsData = (recopilarCaracteristicasFT().length > 0) 
        ? recopilarCaracteristicasFT() 
        : (itemSeleccionado ? (itemSeleccionado.caracteristicas || []) : []);

    const body = {
        especificacion_id: parseInt(etId),
        item_id: parseInt(itemId),
        finalizar: false,
        marca: document.getElementById('ft-marca').value.trim(),
        modelo: document.getElementById('ft-modelo').value.trim(),
        color: document.getElementById('ft-color').value.trim(),
        carta_levantamiento: document.getElementById('ft-carta').value.trim(),
        guia_remision: document.getElementById('ft-guia-remision').value.trim(),
        responsable_id: document.getElementById('ft-responsable').value || null,
        proveedor_id: (provIdEl && provIdEl.value) ? parseInt(provIdEl.value) : null,
        proveedor_razon: document.getElementById('ft-proveedor-nombre').value.trim(),
        proveedor_direccion: document.getElementById('ft-proveedor-dir').value.trim(),
        proveedor_telefono: document.getElementById('ft-proveedor-tel').value.trim(),
        proveedor_correo: document.getElementById('ft-proveedor-correo').value.trim(),
        observaciones: document.getElementById('ft-observaciones').value.trim(),
        orden_compra: document.getElementById('ft-orden-compra').value.trim(),
        costo: document.getElementById('ft-costo').value
                  ? parseFloat(document.getElementById('ft-costo').value) : null,
        fecha_adquisicion: document.getElementById('ft-fecha-adquisicion').value || null,
        garantia: document.getElementById('ft-garantia').value.trim(),
        caracteristicas_verificadas: charsData,
        checklist: checklistData,
        series: seriesVals
    };

    fetch('/api/fichas/carga-masiva', {
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
        alert(seriesVals.length > 1 ? `Se guardaron ${seriesVals.length} borradores de Ficha Técnica` : 'Ficha guardada como borrador');
    })
    .catch(err => {
        alert('Error de conexión al guardar');
    });
}

function recopilarChecklist() {
    const container = document.getElementById('checklist-caracteristicas-inline');
    if (!container) return {};

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    const resultado = {};
    checkboxes.forEach(chk => {
        resultado[chk.id.replace('chk-', '')] = chk.checked;
    });
    return resultado;
}

// ============================================================
// Finalizar Ficha(s) Técnica(s)
// ============================================================

function finalizarFicha() {
    const etId = document.getElementById('et-selector').value;
    const itemId = document.getElementById('item-selector').value;

    if (!etId || !itemId) {
        alert('Seleccione una Especificación Técnica y un ítem');
        return;
    }

    const seriesInputs = document.querySelectorAll('.ft-serie-input');
    const seriesVals = Array.from(seriesInputs).map(inp => ({
        numero_serie: inp.value.trim(),
        estado_fisico: 'NUEVO'
    }));

    const marca = document.getElementById('ft-marca').value.trim();
    const modelo = document.getElementById('ft-modelo').value.trim();

    if (!marca || !modelo) {
        alert('Debe ingresar la Marca y Modelo del bien recibido.');
        return;
    }

    const cant = seriesVals.length;
    const confirmMsg = cant > 1 
        ? `¿Finalizar las ${cant} Fichas Técnicas? Se asignarán números correlativos permanentes y no se podrán editar.`
        : `¿Finalizar esta Ficha Técnica? Se asignará un número correlativo permanente y no se podrá editar.`;

    if (!confirm(confirmMsg)) return;

    const provIdEl = document.getElementById('ft-proveedor-id');
    const checklistData = recopilarChecklist();
    const charsData = (recopilarCaracteristicasFT().length > 0) 
        ? recopilarCaracteristicasFT() 
        : (itemSeleccionado ? (itemSeleccionado.caracteristicas || []) : []);

    const body = {
        especificacion_id: parseInt(etId),
        item_id: parseInt(itemId),
        finalizar: true,
        marca: marca,
        modelo: modelo,
        color: document.getElementById('ft-color').value.trim(),
        carta_levantamiento: document.getElementById('ft-carta').value.trim(),
        guia_remision: document.getElementById('ft-guia-remision').value.trim(),
        responsable_id: document.getElementById('ft-responsable').value || null,
        proveedor_id: (provIdEl && provIdEl.value) ? parseInt(provIdEl.value) : null,
        proveedor_razon: document.getElementById('ft-proveedor-nombre').value.trim(),
        proveedor_direccion: document.getElementById('ft-proveedor-dir').value.trim(),
        proveedor_telefono: document.getElementById('ft-proveedor-tel').value.trim(),
        proveedor_correo: document.getElementById('ft-proveedor-correo').value.trim(),
        observaciones: document.getElementById('ft-observaciones').value.trim(),
        orden_compra: document.getElementById('ft-orden-compra').value.trim(),
        costo: document.getElementById('ft-costo').value
                  ? parseFloat(document.getElementById('ft-costo').value) : null,
        fecha_adquisicion: document.getElementById('ft-fecha-adquisicion').value || null,
        garantia: document.getElementById('ft-garantia').value.trim(),
        caracteristicas_verificadas: charsData,
        checklist: checklistData,
        series: seriesVals
    };

    const btnFinalizar = document.getElementById('btn-finalizar-ft');
    if (btnFinalizar) {
        btnFinalizar.disabled = true;
        btnFinalizar.textContent = '⏳ Finalizando...';
    }

    fetch('/api/fichas/carga-masiva', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    .then(r => r.json().then(data => ({ status: r.status, data })))
    .then(({ status, data }) => {
        if (status >= 400) {
            alert('⚠️ ' + (data.error || 'Error al finalizar'));
            if (btnFinalizar) {
                btnFinalizar.disabled = false;
                btnFinalizar.textContent = cant > 1 ? `🔒 Finalizar ${cant} Fichas Técnicas` : '🔒 Finalizar Ficha Técnica';
            }
            return;
        }

        let downloadUrl = '';
        if (cant === 1 && data.fichas && data.fichas.length > 0) {
            downloadUrl = `/api/fichas/${data.fichas[0].id}/documento`;
        } else {
            downloadUrl = `/api/especificaciones/${etId}/fichas/zip`;
        }

        // Iniciar descarga automática del documento Word o ZIP
        const downloadAnchor = document.createElement('a');
        downloadAnchor.href = downloadUrl;
        downloadAnchor.download = '';
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        document.body.removeChild(downloadAnchor);

        let msgFinal = cant === 1 
            ? `🎉 Ficha Técnica finalizada exitosamente.\nN° Correlativo: ${data.fichas[0].correlativo_formateado}\n\n📄 La descarga del documento Word (.docx) ha comenzado automáticamente.`
            : `🎉 ¡${cant} Fichas Técnicas finalizadas exitosamente!\n\n📦 La descarga del archivo comprimido (.ZIP) con todas las Fichas Técnicas ha comenzado automáticamente.`;

        if (data.et_finalizada) {
            msgFinal += `\n\n✅ ¡Todos los ítems han sido completados! La Especificación Técnica ha cambiado automáticamente su estado a FINALIZADA.`;
        }

        alert(msgFinal);

        setTimeout(() => {
            if (cant === 1 && data.fichas && data.fichas.length > 0) {
                window.location.href = `/fichas/${data.fichas[0].id}`;
            } else {
                window.location.href = '/fichas';
            }
        }, 1200);
    })
    .catch(err => {
        if (btnFinalizar) {
            btnFinalizar.disabled = false;
            btnFinalizar.textContent = cant > 1 ? `🔒 Finalizar ${cant} Fichas Técnicas` : '🔒 Finalizar Ficha Técnica';
        }
        alert('Error de conexión al finalizar');
    });
}

// ============================================================
// Modal helper
// ============================================================

function cerrarModal(id) {
    document.getElementById(id).classList.remove('show');
}

// ============================================================
// Preview de Carta de Almacén (formato institucional automático)
// ============================================================

function previsualizarCarta() {
    const num = (document.getElementById('ft-carta').value || '').trim();
    const preview = document.getElementById('carta-preview');
    if (!preview) return;
    
    if (num) {
        const anio = new Date().getFullYear();
        preview.textContent = `→ CARTA N°${num} -${anio}-MPSR-J/OGA/OL/AC/WDB`;
    } else {
        preview.textContent = '';
    }
}

// ============================================================
// Corrección de modelo y búsqueda de especificaciones
// ============================================================

let webSearchController = null;

function corregirModelo() {
    const marca = (document.getElementById('ft-marca').value || '').trim();
    const modelo = (document.getElementById('ft-modelo').value || '').trim();

    if (!marca && !modelo) {
        alert('Ingrese la marca o el modelo para corregir');
        return;
    }

    const dropdown = document.getElementById('sugerencias-modelo');
    if (!dropdown) return;

    dropdown.innerHTML = '<div class="text-sm p-2">⏳ Buscando...</div>';

    const q = new URLSearchParams({ marca, modelo });
    fetch(`/api/catalogos/sugerir-modelo?${q.toString()}`)
        .then(r => r.json())
        .then(res => {
            if (res.error) {
                dropdown.innerHTML = '';
                return;
            }

            const sugerencias = res.sugerencias || [];
            if (sugerencias.length === 0) {
                dropdown.innerHTML = '<div class="text-sm text-muted p-2">Sin sugerencias para "' + marca + ' ' + modelo + '"</div>';
                return;
            }

            let html = '';
            sugerencias.forEach((s) => {
                const marcaDisplay = (s.marca || '').replace(/"/g, '&quot;');
                const modeloDisplay = (s.modelo || '').replace(/"/g, '&quot;');
                const fuenteIcon = s.verificado ? '✅' : '🌐';
                html += `<div class="sugerencia-item" onclick="seleccionarSugerencia('${marcaDisplay}', '${modeloDisplay}')">
                    <span class="sugerencia-texto">${fuenteIcon} ${marcaDisplay} ${modeloDisplay}</span>
                    <span class="sugerencia-badge">${s.verificado ? 'Verificado' : 'Web'}</span>
                </div>`;
            });
            dropdown.innerHTML = html;
        })
        .catch(err => {
            dropdown.innerHTML = '';
        });
}

function ocultarSugerenciasModelo() {
    const dropdown = document.getElementById('sugerencias-modelo');
    if (dropdown) dropdown.innerHTML = '';
}

function seleccionarSugerencia(marca, modelo) {
    document.getElementById('ft-marca').value = marca;
    document.getElementById('ft-modelo').value = modelo;
    ocultarSugerenciasModelo();
}

// ============================================================
// Panel derecho: Especificaciones de la web (Firecrawl)
// ============================================================

let webSpecsCache = [];

function buscarCaracteristicasWeb() {
    const marca = (document.getElementById('ft-marca').value || '').trim();
    const modelo = (document.getElementById('ft-modelo').value || '').trim();
    const panel = document.getElementById('ft-caracteristicas-web');
    if (!panel) return;

    if (!marca && !modelo) {
        panel.innerHTML = '<p class="form-error">Ingrese la marca y/o modelo para buscar en la web.</p>';
        return;
    }

    panel.innerHTML = `<div class="loading-indicator">
        <p class="text-sm">⏳ Buscando especificaciones en la web…</p>
        <button type="button" class="btn btn-sm btn-secondary" onclick="cancelarBusquedaWeb()">✕ Cancelar</button>
    </div>`;

    webSearchController = new AbortController();

    const q = new URLSearchParams({ marca, modelo });
    fetch(`/api/catalogos/caracteristicas-web?${q.toString()}`, { signal: webSearchController.signal })
        .then(r => {
            if (!r.ok) {
                return r.text().then(t => { throw new Error(`HTTP ${r.status}: ${t || r.statusText}`); });
            }
            return r.json();
        })
        .then(res => {
            if (res.error) {
                panel.innerHTML = `<p class="form-error">${res.error}</p>`;
                return;
            }
            const specs = res.caracteristicas || [];
            webSpecsCache = specs;

            if (specs.length === 0) {
                panel.innerHTML = `<p class="text-muted text-sm mt-2">No se encontraron especificaciones en la web para este modelo.</p>
                    ${esFirecrawl ? '' : '<p class="text-sm mt-2">💡 Configura FIRECRAWL_API_KEY en .env para obtener specs reales del fabricante.</p>'}`;
                return;
            }

            let html = '';
            html += `<button type="button" class="btn btn-sm btn-success mb-2" onclick="copiarTodasWeb()">➕ Copiar todas al panel izquierdo</button>`;
            html += '<div class="char-web-list">';
            specs.forEach((c, idx) => {
                const nombre = (c.nombre || '').replace(/"/g, '&quot;');
                const valor = (c.valor || '').replace(/"/g, '&quot;');
                html += `
                    <div class="char-web-row">
                        <div class="char-web-info">
                            <span class="char-name">${nombre}:</span>
                            <span class="char-value">${valor}</span>
                        </div>
                        <button type="button" class="btn btn-sm btn-secondary" onclick="copiarWeb(${idx})" title="Copiar al panel izquierdo">➕</button>
                    </div>`;
            });
            html += '</div>';
            panel.innerHTML = html;
        })
        .catch(err => {
            if (err.name === 'AbortError') {
                panel.innerHTML = '<p class="text-muted text-sm">Búsqueda cancelada.</p>';
                return;
            }
            panel.innerHTML = '<p class="form-error">No se pudo consultar la web. Verifique conexión e inicio de sesión, o revise la consola del servidor.</p>';
        });
}

function cancelarBusquedaWeb() {
    if (webSearchController) {
        webSearchController.abort();
        webSearchController = null;
    }
}

function copiarWeb(idx) {
    const c = webSpecsCache[idx];
    if (c) agregarFilaCaracteristica(c.nombre || '', c.valor || '');
}

function copiarTodasWeb() {
    webSpecsCache.forEach(c => agregarFilaCaracteristica(c.nombre || '', c.valor || ''));
}

// ============================================================
// Características editables en FT
// ============================================================

function renderCaracteristicasEditables(chars, origenInfo) {
    const container = document.getElementById('ft-caracteristicas-list');
    if (!container) return;

    let badgeHtml = '';
    if (origenInfo) {
        if (origenInfo.origen === 'DATABASE' && origenInfo.verificado) {
            badgeHtml = `<div class="alert alert-success mb-2">✅ ${origenInfo.mensaje}</div>`;
        } else if (origenInfo.origen === 'WEB') {
            badgeHtml = `<div class="alert alert-warning mb-2">🌐 ${origenInfo.mensaje}</div>`;
        } else {
            badgeHtml = `<div class="alert alert-info mb-2">ℹ️ ${origenInfo.mensaje}</div>`;
        }
    }

    if (!chars || chars.length === 0) {
        container.innerHTML = badgeHtml + `
            <p class="text-muted text-sm">No hay características asociadas.
            Use "➕ Agregar característica" o 🔍 para buscar en la web.</p>`;
        return;
    }

    const isFromWeb = origenInfo && origenInfo.origen === 'WEB';

    if (isFromWeb) {
        let html = badgeHtml + '<div class="char-edit-grid">';
        chars.forEach((c, idx) => {
            const nombre = c.nombre || '';
            const valor = c.valor || c.valor_sugerido || '';
            html += `
                <div class="char-edit-row char-edit-row-web" id="char-row-${idx}">
                    <div class="char-edit-content">
                        <span class="char-name-display">${nombre}: ${valor}</span>
                    </div>
                    <div class="char-edit-actions">
                        <button type="button" class="btn btn-sm btn-success" onclick="aprobarCaracteristicaFT(${idx}, '${nombre.replace(/'/g, "\\'")}', '${valor.replace(/'/g, "\\'")}')" title="Aprobar">✓</button>
                        <button type="button" class="btn btn-sm btn-danger" onclick="quitarCaracteristicaFT(${idx})" title="Eliminar">✖</button>
                    </div>
                </div>`;
        });
        html += '</div>';
        container.innerHTML = html;
    } else {
        let html = badgeHtml + '<div class="char-edit-grid">';
        chars.forEach((c, idx) => {
            const nombre = c.nombre || '';
            const valor = c.valor || c.valor_sugerido || '';
            html += `
                <div class="char-edit-row char-edit-row-et" id="char-row-${idx}">
                    <input type="text" class="form-control char-edit-nombre"
                           value="${nombre.replace(/"/g, '&quot;')}" placeholder="Nombre">
                    <input type="text" class="form-control char-edit-valor"
                           value="${valor.replace(/"/g, '&quot;')}" placeholder="Valor">
                    <div class="char-edit-actions">
                        <button type="button" class="btn btn-sm btn-success" onclick="aprobarCaracteristicaFT(${idx}, '${nombre.replace(/'/g, "\\'")}', '${valor.replace(/'/g, "\\'")}')" title="Aprobar">✓</button>
                        <button type="button" class="btn btn-sm btn-danger" onclick="quitarCaracteristicaFT(${idx})" title="Eliminar">✖</button>
                    </div>
                </div>`;
        });
        html += '</div>';
        container.innerHTML = html;
    }
}
function agregarCaracteristicaFT() {
    agregarFilaCaracteristica('', '');
}

function agregarFilaCaracteristica(nombre = '', valor = '') {
    const container = document.getElementById('ft-caracteristicas-list');
    if (!container) return;

    let grid = container.querySelector('.char-edit-grid');
    if (!grid) {
        grid = document.createElement('div');
        grid.className = 'char-edit-grid';
        container.innerHTML = '';
        container.appendChild(grid);
    }

    const idx = grid.children.length;
    const row = document.createElement('div');
    row.className = 'char-edit-row';
    row.id = `char-row-${idx}`;
    row.innerHTML = `
        <input type="text" class="form-control char-edit-nombre"
               value="${nombre.replace(/"/g, '&quot;')}" placeholder="Nombre (ej: Procesador)">
        <input type="text" class="form-control char-edit-valor"
               value="${valor.replace(/"/g, '&quot;')}" placeholder="Valor verificado">
        <div class="char-edit-actions">
            <button type="button" class="btn btn-sm btn-success" onclick="aprobarCaracteristicaFTManual(this)" title="Aprobar">✓</button>
            <button type="button" class="btn btn-sm btn-danger" onclick="this.closest('.char-edit-row').remove()" title="Quitar">✖</button>
        </div>`;
    grid.appendChild(row);
    row.querySelector('.char-edit-nombre').focus();
}

function quitarCaracteristicaFT(idx) {
    const row = document.getElementById(`char-row-${idx}`);
    if (row) row.remove();
}

function aprobarCaracteristicaFT(idx, nombre, valor) {
    const row = document.getElementById(`char-row-${idx}`);
    if (row) {
        row.classList.remove('char-edit-row-web');
        row.classList.add('char-edit-row-aprobada');
        const actions = row.querySelector('.char-edit-actions');
        if (actions) {
            actions.innerHTML = '<span style="color:green;font-size:0.8rem;">✓ Aprobado</span>';
        }
    }
}

function aprobarCaracteristicaFTManual(btn) {
    const row = btn.closest('.char-edit-row');
    if (row) {
        row.classList.add('char-edit-row-aprobada');
        const actions = row.querySelector('.char-edit-actions');
        if (actions) {
            actions.innerHTML = '<span style="color:green;font-size:0.8rem;">✓ Aprobado</span>';
        }
    }
}

function quitarMarcadas() {
    const checkboxes = Array.from(document.querySelectorAll('.char-checkbox:checked'));
    checkboxes.forEach(cb => {
        const idx = parseInt(cb.id.replace('char-check-', ''));
        const row = document.getElementById(`char-row-${idx}`);
        if (row) row.remove();
    });
}

function agregarCaracteristicaFT() {
    agregarFilaCaracteristica('', '');
}

function recopilarCaracteristicasFT() {
    const rows = document.querySelectorAll('.char-edit-row');
    const chars = [];
    rows.forEach(row => {
        const nombre = row.querySelector('.char-edit-nombre').value.trim();
        const valor = row.querySelector('.char-edit-valor').value.trim();
        if (nombre) {
            chars.push({ nombre, valor });
        }
    });
    return chars;
}

function guardarComoPlantilla() {
    const marca = (document.getElementById('ft-marca').value || '').trim();
    const modelo = (document.getElementById('ft-modelo').value || '').trim();
    const chars = recopilarCaracteristicasFT();

    if (!marca || !modelo) {
        alert('Ingrese marca y modelo antes de guardar como plantilla');
        return;
    }
    if (chars.length === 0) {
        alert('Agregue al menos una característica antes de guardar como plantilla');
        return;
    }

    if (!confirm(`¿Guardar ${chars.length} características como plantilla para "${marca} ${modelo}"?\n\nEsta plantilla se sugerirá automáticamente en futuras fichas con el mismo modelo.`)) {
        return;
    }

    fetch('/api/plantillas-caracteristicas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ marca, modelo, caracteristicas: chars }),
    })
    .then(r => r.json().then(data => ({ status: r.status, data })))
    .then(({ status, data }) => {
        if (status >= 400) {
            alert(data.error || 'Error al guardar plantilla');
            return;
        }
        alert(`✅ Plantilla guardada para ${marca} ${modelo}.\nSe sugerirá automáticamente en próximas fichas.`);
    })
    .catch(err => {
        alert('Error de conexión al guardar plantilla');
    });
}

function verificarPlantillaExistente(forzarNotificacion = false) {
    const marca = (document.getElementById('ft-marca').value || '').trim();
    const modelo = (document.getElementById('ft-modelo').value || '').trim();

    if (!marca || !modelo) return;

    fetch(`/api/catalogos/buscar-modelo?marca=${encodeURIComponent(marca)}&modelo=${encodeURIComponent(modelo)}`)
        .then(r => r.json())
        .then(res => {
            if (res && res.caracteristicas && res.caracteristicas.length > 0) {
                renderCaracteristicasEditables(res.caracteristicas, {
                    origen: res.origen,
                    verificado: res.verificado,
                    mensaje: res.mensaje
                });
            } else if (forzarNotificacion) {
                alert('No se encontraron especificaciones automáticas para este modelo. Puede ingresarlas manualmente o agregarlas.');
            }
        })
}


// ============================================================
// Renderizado dinámico de campos de Series según cantidad del ítem
// ============================================================

function renderizarCamposSeries(cant, requiereSerie = true) {
    const contenedor = document.getElementById('contenedor-series-dinamicas');
    const lbl = document.getElementById('lbl-serie');
    const btnFinalizar = document.getElementById('btn-finalizar-ft');

    if (!contenedor) return;

    if (cant > 1) {
        if (lbl) lbl.innerHTML = `Número(s) de Serie (${cant} Unidades) ${requiereSerie ? '<span class="req">*</span>' : ''}`;
        if (btnFinalizar) btnFinalizar.textContent = `🔒 Finalizar ${cant} Fichas Técnicas`;

        let html = '';
        for (let i = 1; i <= cant; i++) {
            html += `
                <div class="form-group" style="margin-bottom: 0;">
                    <label class="text-sm font-semibold" style="display:block; margin-bottom: 0.25rem; font-size: 0.825rem; color: var(--text-color, #374151);">Unidad #${i} ${requiereSerie ? '<span class="req">*</span>' : ''}</label>
                    <input type="text" class="form-control ft-serie-input" data-index="${i}"
                           placeholder="${requiereSerie ? 'Ej: ADV1253S20512603...' : 'Opcional / Cod. Patrimonial'}">
                </div>
            `;
        }
        contenedor.innerHTML = html;
    } else {
        if (lbl) lbl.innerHTML = `Número de Serie ${requiereSerie ? '<span class="req">*</span>' : ''}`;
        if (btnFinalizar) btnFinalizar.textContent = `🔒 Finalizar Ficha Técnica`;

        contenedor.innerHTML = `
            <input type="text" id="ft-serie" class="form-control ft-serie-input"
                   placeholder="${requiereSerie ? 'Ej: ADV1253S205126030423' : 'Opcional o Código Patrimonial'}"
                   oninput="validarSerieAjax()">
        `;
    }
}



