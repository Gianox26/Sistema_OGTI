/**
 * util.js — Funciones reutilizables del Sistema OGTI
 */

/**
 * Sugiere el cargo de un responsable a partir del nombre de la dependencia.
 * Regla: se toma la PRIMERA palabra (o las palabras clave) del nombre:
 *   - SUBGERENCIA (o "Sub" + "Gerencia") → SUBGERENTE
 *   - GERENCIA                            → GERENTE
 *   - OFICINA                             → JEFE DE OFICINA
 *   - OBRA                                → JEFE DE OBRA
 *   - otro                                → '' (se deja en blanco para llenado manual)
 * Es reutilizable: basta llamarla desde cualquier formulario.
 */
function sugerirCargo(nombreDependencia) {
    if (!nombreDependencia) return '';
    const n = nombreDependencia.toUpperCase();
    if (n.includes('SUB') && n.includes('GERENCIA')) return 'SUBGERENTE';
    if (n.includes('GERENCIA')) return 'GERENTE';
    if (n.includes('OFICINA')) return 'JEFE DE OFICINA';
    if (n.includes('OBRA')) return 'JEFE DE OBRA';
    return '';
}

/**
 * Aplica el cargo sugerido al campo de cargo cuando se selecciona una dependencia.
 * selectId: id del <select> de dependencia
 * cargoId:  id del <input> de cargo
 */
function aplicarCargoSegunDependencia(selectId, cargoId) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const opt = sel.options[sel.selectedIndex];
    const nombre = opt ? opt.textContent.trim() : '';
    const cargo = document.getElementById(cargoId);
    if (cargo) cargo.value = sugerirCargo(nombre);
}
