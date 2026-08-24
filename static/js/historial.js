/**
 * historial.js
 * Búsqueda multicriterio en Fichas y Especificaciones Técnicas
 */

let tabActual = 'fichas';
let buscarTimeout = null;

function cambiarTab(tab) {
    tabActual = tab;
    document.getElementById('tab-fichas').classList.toggle('active', tab === 'fichas');
    document.getElementById('tab-ets').classList.toggle('active', tab === 'ets');

    // Mostrar/ocultar filtros específicos
    const filtroFicha = document.getElementById('filtro-numero-ficha');
    const filtroSerie = document.getElementById('filtro-serie');
    const filtroTipoBien = document.getElementById('filtro-tipo-bien');

    if (tab === 'fichas') {
        if (filtroFicha) filtroFicha.style.display = '';
        if (filtroSerie) filtroSerie.style.display = '';
        if (filtroTipoBien) filtroTipoBien.style.display = '';
    } else {
        if (filtroFicha) filtroFicha.style.display = 'none';
        if (filtroSerie) filtroSerie.style.display = 'none';
        if (filtroTipoBien) filtroTipoBien.style.display = 'none';
    }

    buscar();
}

function buscar() {
    clearTimeout(buscarTimeout);
    buscarTimeout = setTimeout(ejecutarBusqueda, 350);
}

function ejecutarBusqueda() {
    const params = new URLSearchParams();

    const pedido = document.getElementById('f-numero-pedido').value.trim();
    const proveedor = document.getElementById('f-proveedor').value.trim();
    const anio = document.getElementById('f-anio').value.trim();
    const estado = document.getElementById('f-estado').value;

    if (pedido) params.set('numero_pedido', pedido);
    if (proveedor) params.set('proveedor', proveedor);
    if (anio) params.set('anio', anio);
    if (estado) params.set('estado', estado);

    let url;
    if (tabActual === 'fichas') {
        url = '/api/historial/fichas';
        const numFicha = document.getElementById('f-numero-ficha').value.trim();
        const serie = document.getElementById('f-serie').value.trim();
        const tipoBien = document.getElementById('f-tipo-bien').value.trim();
        if (numFicha) params.set('numero_ficha', numFicha);
        if (serie) params.set('numero_serie', serie);
        if (tipoBien) params.set('tipo_bien', tipoBien);
    } else {
        url = '/api/historial/especificaciones';
    }

    // Solo buscar si hay al menos un filtro activo
    if (params.toString() === '') {
        document.getElementById('resultados-container').innerHTML =
            '<div class="empty-state"><div class="icon">🔍</div><p>Ingrese criterios de búsqueda</p></div>';
        document.getElementById('resultados-count').textContent = '';
        return;
    }

    fetch(`${url}?${params.toString()}`)
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('resultados-container');
            document.getElementById('resultados-count').textContent = `${data.length} resultado(s)`;

            if (data.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="icon">📭</div><p>No se encontraron resultados</p></div>';
                return;
            }

            if (tabActual === 'fichas') {
                renderTablaFichas(data, container);
            } else {
                renderTablaETs(data, container);
            }
        });
}

function renderTablaFichas(data, container) {
    let html = '<div class="table-wrap" style="border:none;"><table class="table"><thead><tr>';
    html += '<th>N° Ficha</th><th>Bien</th><th>Marca/Modelo</th><th>Serie</th>';
    html += '<th>Proveedor</th><th>Pedido</th><th>Creado por</th><th>Estado</th><th></th>';
    html += '</tr></thead><tbody>';

    data.forEach(ft => {
        const corr = ft.numero_correlativo ? `${ft.numero_correlativo}-${ft.anio}` : '—';
        const badge = ft.estado === 'FINALIZADA' ? 'badge-success' :
                      ft.estado === 'ANULADA' ? 'badge-danger' : 'badge-draft';
        html += `<tr>
            <td><strong>${corr}</strong></td>
            <td>${ft.bien_descripcion || ''}</td>
            <td>${ft.marca || ''} ${ft.modelo || ''}</td>
            <td><code>${ft.numero_serie}</code></td>
            <td class="text-sm">${ft.proveedor_razon || ''}</td>
            <td class="text-sm">${ft.numero_pedido}</td>
            <td class="text-sm text-muted">${ft.creado_por_nombre || ''}</td>
            <td><span class="badge ${badge}">${ft.estado}</span></td>
            <td><a href="/fichas/${ft.id}" class="btn btn-secondary btn-sm">Ver</a></td>
        </tr>`;
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function renderTablaETs(data, container) {
    let html = '<div class="table-wrap" style="border:none;"><table class="table"><thead><tr>';
    html += '<th>N° Pedido</th><th>Proveedor</th><th>Año</th>';
    html += '<th>Ítems</th><th>Fichas</th><th>Creado por</th><th>Estado</th><th></th>';
    html += '</tr></thead><tbody>';

    data.forEach(et => {
        const badge = et.estado === 'FINALIZADA' ? 'badge-success' :
                      et.estado === 'ANULADA' ? 'badge-danger' : 'badge-draft';
        html += `<tr>
            <td><strong>${et.numero_pedido}</strong></td>
            <td>${et.proveedor_nombre || ''}</td>
            <td>${et.anio_fiscal}</td>
            <td>${et.total_items}</td>
            <td>${et.total_fichas}</td>
            <td class="text-sm text-muted">${et.creado_por_nombre || ''}</td>
            <td><span class="badge ${badge}">${et.estado}</span></td>
            <td><a href="/especificaciones/${et.id}" class="btn btn-secondary btn-sm">Ver</a></td>
        </tr>`;
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function limpiarFiltros() {
    document.querySelectorAll('.form-grid .form-control').forEach(el => {
        if (el.tagName === 'SELECT') el.selectedIndex = 0;
        else el.value = '';
    });
    document.getElementById('resultados-container').innerHTML =
        '<div class="empty-state"><div class="icon">🔍</div><p>Ingrese criterios de búsqueda</p></div>';
    document.getElementById('resultados-count').textContent = '';
}
