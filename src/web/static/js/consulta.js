// Pantalla "Consultar facturas": adjuntar reporte, consultar en Oracle y paginar resultados.
const FILAS_POR_PAGINA = 10;

// ---------- Elementos ----------
const fileInput = $('fileInput'), btnAdjuntar = $('btnAdjuntar'), btnImportar = $('btnImportar');
const btnLimpiar = $('btnLimpiar'), btnDescargar = $('btnDescargar'), tablaBody = $('tablaBody');
const textoAdjuntar = $('textoAdjuntar'), textoImportar = $('textoImportar');
const contenedorContador = $('contenedorContador'), labelContador = $('labelContador');
const textoContador = $('textoContador'), badgeContador = $('badgeContador');
const contadorResultados = $('contadorResultados'), paginacion = $('paginacion');
const contenedorProgreso = $('contenedorProgreso'), barraProgreso = $('barraProgreso');
const porcentajeProgreso = $('porcentajeProgreso'), textoProgreso = $('textoProgreso');

let intervaloProgreso = null;
let filas = [];          // [{folio, factura, rfc, resultado, validacion, tono}]
let paginaActual = 1;
let mensajeVacio = 'Adjunta un reporte para comenzar';

function confirmarLimpiar() {
    mostrarModal('Limpiar monitor', 'Se borrarán todos los datos que se muestran en pantalla.', 'Limpiar datos', 'error',
                 limpiarMonitor, 'warning');
}
function confirmarProcesar() {
    mostrarModal('Consultar en Oracle ' + AMBIENTE,
                 'Se consultarán en Oracle ' + AMBIENTE + ' todas las facturas detectadas en el reporte.',
                 'Iniciar consulta', 'primary', procesarArchivo, AMBIENTE === 'PROD' ? 'warning' : 'info');
}
// ---------- Tabla + paginación (10 filas por página) ----------
function renderTabla() {
    tablaBody.replaceChildren();
    const total = filas.length;

    if (total === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 6;
        td.className = 'text-center !py-16 text-ink-inactive';
        td.textContent = mensajeVacio;
        tr.appendChild(td);
        tablaBody.appendChild(tr);
        contadorResultados.textContent = '0 resultados';
        paginacion.replaceChildren();
        return;
    }

    const paginas = Math.ceil(total / FILAS_POR_PAGINA);
    paginaActual = Math.min(Math.max(1, paginaActual), paginas);
    const inicio = (paginaActual - 1) * FILAS_POR_PAGINA;
    const fin = Math.min(inicio + FILAS_POR_PAGINA, total);

    filas.slice(inicio, fin).forEach((f, i) => {
        const tr = document.createElement('tr');
        tr.appendChild(celda(inicio + i + 1, 'num text-ink-soft'));
        tr.appendChild(celda(f.folio, 'font-medium whitespace-nowrap'));
        tr.appendChild(celda(f.factura, 'whitespace-nowrap'));
        tr.appendChild(celda(f.rfc, 'font-mono text-xs'));
        const tdRes = document.createElement('td');
        tdRes.appendChild(badge(f.resultado, f.tono));
        tr.appendChild(tdRes);
        tr.appendChild(celda(f.validacion));
        tablaBody.appendChild(tr);
    });

    contadorResultados.textContent = total > FILAS_POR_PAGINA
        ? `${inicio + 1}-${fin} de ${total} resultados`
        : `${total} resultados`;
    renderPaginacion(paginas);
}

function renderPaginacion(paginas) {
    paginacion.replaceChildren();
    if (paginas <= 1) return;

    const boton = (contenido, pagina, { activo = false, deshabilitado = false, titulo = '' } = {}) => {
        const b = document.createElement('button');
        b.className = 'pag-btn' + (activo ? ' activo' : '');
        b.disabled = deshabilitado;
        if (titulo) b.title = titulo;
        if (typeof contenido === 'string') b.textContent = contenido; else b.appendChild(contenido);
        if (!deshabilitado && !activo) b.onclick = () => { paginaActual = pagina; renderTabla(); };
        paginacion.appendChild(b);
    };
    const chevron = (grados) => { const i = icono(ICONOS.chevron); i.style.transform = `rotate(${grados}deg)`; return i; };
    const puntos = () => { const s = document.createElement('span'); s.className = 'px-1 text-ink-inactive'; s.textContent = '...'; paginacion.appendChild(s); };

    boton(chevron(90), paginaActual - 1, { deshabilitado: paginaActual === 1, titulo: 'Anterior' });

    // Ventana: 1 ... (actual-1, actual, actual+1) ... última
    const visibles = new Set([1, paginas, paginaActual - 1, paginaActual, paginaActual + 1]);
    if (paginaActual <= 3) [2, 3, 4].forEach(p => visibles.add(p));
    if (paginaActual >= paginas - 2) [paginas - 3, paginas - 2, paginas - 1].forEach(p => visibles.add(p));
    const lista = [...visibles].filter(p => p >= 1 && p <= paginas).sort((a, b) => a - b);
    lista.forEach((p, idx) => {
        if (idx > 0 && p - lista[idx - 1] > 1) puntos();
        boton(String(p), p, { activo: p === paginaActual });
    });

    boton(chevron(-90), paginaActual + 1, { deshabilitado: paginaActual === paginas, titulo: 'Siguiente' });
}

// ---------- Estados de la pantalla ----------
function setContador(label, valor, tono) {
    labelContador.textContent = label;
    textoContador.textContent = valor;
    badgeContador.className = `badge badge-${tono}`;
    contenedorContador.classList.remove('hidden');
}

function setBotonCargando(btn, spanTexto, texto, cargando) {
    spanTexto.textContent = texto;
    const spinner = btn.querySelector('.spinner');
    if (cargando && !spinner) { const s = document.createElement('span'); s.className = 'spinner'; btn.prepend(s); }
    if (!cargando && spinner) spinner.remove();
}

function limpiarMonitor() {
    if (intervaloProgreso) clearInterval(intervaloProgreso);
    fileInput.value = '';
    filas = []; paginaActual = 1; mensajeVacio = 'Adjunta un reporte para comenzar';
    renderTabla();

    contenedorContador.classList.add('hidden');
    contenedorProgreso.classList.add('hidden');
    setBotonCargando(btnAdjuntar, textoAdjuntar, 'Adjuntar reporte', false);
    setBotonCargando(btnImportar, textoImportar, 'Consultar en Oracle', false);
    btnAdjuntar.disabled = false;
    btnImportar.disabled = true;
    btnLimpiar.disabled = true;
    btnDescargar.disabled = true;
}

// ---------- Adjuntar / previsualizar ----------
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setBotonCargando(btnAdjuntar, textoAdjuntar, 'Leyendo archivo...', true);
    btnAdjuntar.disabled = true;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/previsualizar', { method: 'POST', body: formData });
        if (!revisarSesion(response)) return;
        const data = await response.json();

        if (!response.ok) {
            mostrarError('No se pudo leer el reporte', data.error || 'Ocurrió un error al leer el archivo.');
            setBotonCargando(btnAdjuntar, textoAdjuntar, 'Adjuntar reporte', false);
            btnAdjuntar.disabled = false;
            fileInput.value = '';
            return;
        }

        const folios = data.folios || [];
        setContador('Facturas detectadas:', data.total || folios.length, 'info');
        filas = folios.map(folio => ({ folio, factura: '', rfc: '', resultado: 'Listo para procesar', validacion: '', tono: 'info' }));
        paginaActual = 1;
        renderTabla();

        setBotonCargando(btnAdjuntar, textoAdjuntar, file.name, false);
        btnAdjuntar.disabled = false;
        btnImportar.disabled = false;
        btnLimpiar.disabled = false;
    } catch (error) {
        console.error(error);
        mostrarError('Error de conexión', 'Ocurrió un error al conectar con el servidor.');
        setBotonCargando(btnAdjuntar, textoAdjuntar, 'Adjuntar reporte', false);
        btnAdjuntar.disabled = false;
        fileInput.value = '';
    }
});

// ---------- Procesar ----------
function tonoResultado(estatus) {
    if (estatus === 'Encontrada') return 'success';
    if (estatus === 'Monto diferente al del Excel') return 'warning';
    if (estatus === 'No encontrada') return 'error';
    return 'neutral';
}

function finalizarProgreso(exito, texto) {
    clearInterval(intervaloProgreso);
    barraProgreso.style.width = '100%';
    barraProgreso.style.backgroundColor = exito ? 'var(--color-text-success)' : 'var(--color-interactive-error)';
    porcentajeProgreso.textContent = exito ? '100%' : '';
    textoProgreso.textContent = texto;
    textoProgreso.style.color = exito ? 'var(--color-text-success)' : 'var(--color-text-error)';
}

async function procesarArchivo() {
    const totalFacturas = parseInt(textoContador.textContent) || 1;
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    btnImportar.disabled = true; btnAdjuntar.disabled = true; btnLimpiar.disabled = true; btnDescargar.disabled = true;
    setBotonCargando(btnImportar, textoImportar, 'Procesando...', true);

    contenedorProgreso.classList.remove('hidden');
    barraProgreso.style.width = '0%';
    barraProgreso.style.backgroundColor = '';
    porcentajeProgreso.textContent = '0%';
    textoProgreso.textContent = 'Consultando Oracle ' + AMBIENTE + '...';
    textoProgreso.style.color = '';

    let progreso = 0;
    const segundosEstimados = Math.max(5, totalFacturas * 0.15);
    intervaloProgreso = setInterval(() => {
        if (progreso < 95) {
            progreso += Math.max(0.1, (95 - progreso) / 30);
            barraProgreso.style.width = `${progreso}%`;
            porcentajeProgreso.textContent = `${Math.floor(progreso)}%`;
        }
    }, (segundosEstimados * 1000) / 95);

    try {
        const response = await fetch('/procesar', { method: 'POST', body: formData });
        if (!revisarSesion(response)) return;
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Error en el procesamiento.');

        finalizarProgreso(true, 'Proceso finalizado');
        const resultado = data.data || [];
        filas = resultado.map(row => ({
            folio: row['Folio C.F.D.I.'],
            factura: row['InvoiceNumber'],
            rfc: row['RFC'],
            resultado: row['EstatusBusqueda'] || 'Sin resultado',
            validacion: row['ValidationStatus'],
            tono: tonoResultado(row['EstatusBusqueda']),
        }));
        paginaActual = 1;
        mensajeVacio = 'No se encontraron datos';
        renderTabla();

        setContador('Procesadas:', filas.length, 'success');
        setBotonCargando(btnImportar, textoImportar, 'Completado', false);
        if (filas.length) btnDescargar.disabled = false;
        setTimeout(() => contenedorProgreso.classList.add('hidden'), 3000);
    } catch (error) {
        finalizarProgreso(false, 'Error en el procesamiento');
        mostrarError('No se pudo procesar', error.message);
        setBotonCargando(btnImportar, textoImportar, 'Reintentar', false);
        btnImportar.disabled = false;
    } finally {
        btnAdjuntar.disabled = false;
        btnLimpiar.disabled = false;
    }
}

renderTabla();
