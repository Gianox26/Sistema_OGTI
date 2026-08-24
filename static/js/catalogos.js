/**
 * catalogos.js
 * Lógica genérica para los catálogos de apoyo
 * Se usa con la variable global CATALOGO_TIPO definida en cada página
 */

function cargarCatalogo() {
    const apiMap = {
        'proveedores': '/api/proveedores',
        'responsables': '/api/responsables',
        'dependencias': '/api/dependencias',
        'tipos-bien': '/api/tipos-bien',
    };

    fetch(apiMap[CATALOGO_TIPO])
        .then(r => r.json())
        .then(data => renderTabla(data));
}

function renderTabla(data) {
    const container = document.getElementById('tabla-container');

    if (data.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="icon">📁</div><p>No hay registros</p></div>';
        return;
    }

    let html = '<div class="table-wrap" style="border:none;"><table class="table"><thead><tr>';

    if (CATALOGO_TIPO === 'proveedores') {
        html += '<th>RUC</th><th>Razón Social</th><th>Dirección</th><th>Teléfono</th><th>Correo</th>';
        html += '</tr></thead><tbody>';
        data.forEach(p => {
            html += `<tr>
                <td><code>${p.ruc}</code></td>
                <td><strong>${p.razon_social}</strong></td>
                <td class="text-sm">${p.direccion || '-'}</td>
                <td class="text-sm">${p.telefono || '-'}</td>
                <td class="text-sm">${p.correo || '-'}</td>
            </tr>`;
        });
    } else if (CATALOGO_TIPO === 'responsables') {
        html += '<th>Nombre</th><th>Cargo</th><th>Dependencia</th><th>Teléfono</th><th>Correo</th>';
        html += '</tr></thead><tbody>';
        data.forEach(r => {
            html += `<tr>
                <td><strong>${r.nombre}</strong></td>
                <td>${r.cargo || '-'}</td>
                <td>${r.dependencia_nombre || '-'}</td>
                <td class="text-sm">${r.telefono || '-'}</td>
                <td class="text-sm">${r.correo || '-'}</td>
            </tr>`;
        });
    } else if (CATALOGO_TIPO === 'dependencias') {
        html += '<th>Nombre</th><th>Edificio</th><th>Pabellón</th>';
        html += '</tr></thead><tbody>';
        data.forEach(d => {
            html += `<tr>
                <td><strong>${d.nombre}</strong></td>
                <td>${d.edificio || '-'}</td>
                <td>${d.pabellon || '-'}</td>
            </tr>`;
        });
    } else if (CATALOGO_TIPO === 'tipos-bien') {
        html += '<th>Tipo de Bien</th><th>Características Típicas</th>';
        html += '</tr></thead><tbody>';
        data.forEach(t => {
            const chars = t.caracteristicas_tipicas || [];
            const charsHtml = chars.map(c =>
                `<span class="text-sm"><strong>${c.nombre}:</strong> ${c.valor_sugerido || '-'}</span>`
            ).join('<br>');
            html += `<tr>
                <td><strong>${t.nombre}</strong></td>
                <td>${charsHtml || '<span class="text-muted">—</span>'}</td>
            </tr>`;
        });
    }

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function abrirModal() {
    document.getElementById('modal-form').classList.add('show');
}

function cerrarModal() {
    document.getElementById('modal-form').classList.remove('show');
}

function guardar() {
    let body = {};
    let url = '';

    if (CATALOGO_TIPO === 'proveedores') {
        url = '/api/proveedores';
        body = {
            ruc: document.getElementById('f-ruc').value.trim(),
            razon_social: document.getElementById('f-razon').value.trim(),
            direccion: document.getElementById('f-direccion').value.trim(),
            telefono: document.getElementById('f-telefono').value.trim(),
            correo: document.getElementById('f-correo').value.trim(),
        };
        if (!body.ruc || !body.razon_social) {
            alert('RUC y razón social son obligatorios');
            return;
        }
    } else if (CATALOGO_TIPO === 'responsables') {
        url = '/api/responsables';
        body = {
            nombre: document.getElementById('f-nombre').value.trim(),
            cargo: document.getElementById('f-cargo').value.trim(),
            telefono: document.getElementById('f-telefono').value.trim(),
            correo: document.getElementById('f-correo').value.trim(),
            dependencia_id: document.getElementById('f-dependencia').value || null,
        };
        if (!body.nombre) {
            alert('El nombre es obligatorio');
            return;
        }
    } else if (CATALOGO_TIPO === 'dependencias') {
        url = '/api/dependencias';
        body = {
            nombre: document.getElementById('f-nombre').value.trim(),
            edificio: document.getElementById('f-edificio').value.trim(),
            pabellon: document.getElementById('f-pabellon').value.trim(),
        };
        if (!body.nombre) {
            alert('El nombre es obligatorio');
            return;
        }
    } else if (CATALOGO_TIPO === 'tipos-bien') {
        url = '/api/tipos-bien';
        const nombre = document.getElementById('f-nombre').value.trim();
        if (!nombre) {
            alert('El nombre es obligatorio');
            return;
        }
        // Recopilar características
        const charRows = document.querySelectorAll('#chars-container .char-row');
        const chars = [];
        charRows.forEach(row => {
            const inputs = row.querySelectorAll('input');
            if (inputs[0] && inputs[0].value.trim()) {
                chars.push({
                    nombre: inputs[0].value.trim(),
                    valor_sugerido: inputs[1] ? inputs[1].value.trim() : '',
                });
            }
        });
        body = { nombre, caracteristicas_tipicas: chars };
    }

    fetch(url, {
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
            cerrarModal();
            cargarCatalogo();
        });
}

// Helper para tipos de bien: agregar fila de característica
function agregarChar() {
    const container = document.getElementById('chars-container');
    const row = document.createElement('div');
    row.className = 'char-row';
    row.style.marginBottom = '0.5rem';
    row.innerHTML = `
        <input type="text" class="form-control" style="max-width:160px;" placeholder="Nombre">
        <input type="text" class="form-control flex-1" placeholder="Valor sugerido">
        <button class="btn btn-danger btn-sm" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(row);
}
