// Funciones comunes de las pantallas: íconos, celdas, badges, menú lateral, modal y sesión.
// Lee la configuración de la página de window.CXP (ver base.html).
const AMBIENTE = CXP.ambiente;
const ICONO = (nombre) => `url('${CXP.static}icons/${nombre}.svg')`;
const ICONOS = {
    check: ICONO('check-mark'), alerta: ICONO('alert-warning'), error: ICONO('cancel'),
    info: ICONO('info'), chevron: ICONO('chevron-down'),
};
const $ = (id) => document.getElementById(id);
let accionPendiente = null;

// ---------- Utilidades ----------
function icono(src, clases = 'icon icon-xs') {
    const s = document.createElement('span');
    s.className = clases;
    s.style.setProperty('--src', src);
    return s;
}

function celda(texto, clase = '') {
    const td = document.createElement('td');
    if (clase) td.className = clase;
    td.textContent = (texto === undefined || texto === null || texto === '') ? '-' : texto;
    return td;
}

function badge(texto, tono) {
    const iconos = { success: ICONOS.check, warning: ICONOS.alerta, error: ICONOS.error, info: ICONOS.info };
    const b = document.createElement('span');
    b.className = `badge badge-${tono}`;
    if (iconos[tono]) b.appendChild(icono(iconos[tono]));
    b.appendChild(document.createTextNode(texto));
    return b;
}

// ---------- Sidebar ----------
// Menú lateral: abierto o en íconos; se recuerda en este navegador
function toggleSidebar() {
    const mini = $('sidebar').classList.toggle('sidebar-mini');
    try { localStorage.setItem('cxp_menu_mini', mini ? '1' : '0'); } catch (e) {}
}
(function () {
    let pref = null;
    try { pref = localStorage.getItem('cxp_menu_mini'); } catch (e) {}
    if (pref === '1' || (pref === null && window.innerWidth < 1024)) {
        const s = $('sidebar');
        s.style.transition = 'none';             // sin animación al abrir la página
        s.classList.add('sidebar-mini');
        requestAnimationFrame(() => requestAnimationFrame(() => { s.style.transition = ''; }));
    }
})();

// ---------- Modal (cierre con ícono X, según Coltrane) ----------
function mostrarModal(titulo, mensaje, textoBtn, variante, callback, tono = 'info') {
    const coloresIcono = { info: 'var(--color-interactive-primary)', error: 'var(--color-interactive-error)',
                           warning: 'var(--color-text-warning)', success: 'var(--color-text-success)' };
    const iconosTono = { info: ICONOS.info, error: ICONOS.error, warning: ICONOS.alerta, success: ICONOS.check };
    const ic = $('modalIcono');
    ic.style.setProperty('--src', iconosTono[tono]);
    ic.style.color = coloresIcono[tono];

    $('modalTitle').textContent = titulo;
    $('modalMessage').textContent = mensaje;
    const btn = $('modalConfirmBtn');
    btn.textContent = textoBtn;
    btn.className = `btn btn-${variante} mt-8`;
    btn.classList.toggle('hidden', !callback);

    accionPendiente = callback;
    $('customModal').classList.remove('hidden');
}

function cerrarModal() {
    $('customModal').classList.add('hidden');
    accionPendiente = null;
}

$('modalConfirmBtn').addEventListener('click', () => {
    const accion = accionPendiente;
    cerrarModal();
    if (accion) accion();
});
$('customModal').addEventListener('click', (e) => { if (e.target.id === 'customModal') cerrarModal(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') cerrarModal(); });

function mostrarError(titulo, mensaje) { mostrarModal(titulo, mensaje, '', 'primary', null, 'error'); }

// ---------- Confirmaciones ----------
function confirmarCerrarSesion() {
    mostrarModal('Cerrar sesión', '¿Seguro que deseas salir del sistema?', 'Cerrar sesión', 'error',
                 () => { const f = document.createElement('form'); f.method = 'POST'; f.action = '/logout'; document.body.appendChild(f); f.submit(); }, 'warning');
}
// Si el servidor perdió la sesión (reinicio), regresar al login
function revisarSesion(response) {
    if (response.status === 401) { window.location.href = '/login'; return false; }
    return true;
}
