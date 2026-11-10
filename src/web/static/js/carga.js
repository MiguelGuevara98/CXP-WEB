// Pantalla "Cargar facturas": XML -> plantilla -> facturas -> carga en Oracle (pestañas con avance automático).
const AMBIENTES_CARGA = CXP.ambientesCarga;
const TONOS = { 'Lista para capturar': 'info', 'Lista con advertencias': 'warning', 'Lista para Oracle': 'success',
                'Lista para Oracle (con advertencias)': 'warning', 'Excluida': 'neutral', 'Con error': 'error',
                'Registrada en Oracle': 'success', 'Rechazada por Oracle': 'error', 'Sin confirmar': 'error' };
const ANIO = new Date().getFullYear().toString();

// ---- Pestañas: pasoMax = paso al que ya se llegó (5 = carga terminada) ----
let pasoMax = 1;
function mostrarPestana(n) {
    if (n > Math.min(pasoMax, 4)) return;
    for (let i = 1; i <= 4; i++) {
        const p = $('paso' + i);
        p.classList.toggle('hecho', i < pasoMax);
        p.classList.toggle('activo', i === n);
        p.disabled = i > pasoMax;
        p.setAttribute('aria-selected', i === n);
        $('tab' + i).classList.toggle('hidden', i !== n);
    }
}
function marcarPaso(n) { pasoMax = n; mostrarPestana(Math.min(n, 4)); }

function dinero(v) {
    return (v === null || v === undefined) ? '-' : v.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Detalle de cada factura: campos faltantes como etiquetas, otros errores y advertencias con ícono
function celdaDetalle(f) {
    const td = document.createElement('td');
    const caja = document.createElement('div');
    caja.className = 'detalle';
    td.appendChild(caja);

    const faltan = [], errores = [];
    (f.motivos || []).forEach(m => {
        const x = /^Falta '(.+)'$/.exec(m);
        x ? faltan.push(x[1]) : errores.push(m);
    });
    if (faltan.length) {
        const g = document.createElement('div');
        const t = document.createElement('p');
        t.className = 'det-titulo';
        t.append(icono(ICONOS.error), document.createTextNode(faltan.length === 1 ? 'Falta en la plantilla' : `Faltan ${faltan.length} datos en la plantilla`));
        const chips = document.createElement('div');
        chips.className = 'det-chips';
        faltan.forEach(c => { const s = document.createElement('span'); s.className = 'det-chip'; s.textContent = c; chips.appendChild(s); });
        g.append(t, chips);
        caja.appendChild(g);
    }
    const linea = (texto, clase, src) => {
        const p = document.createElement('p');
        p.className = 'det-linea ' + clase;
        if (src) p.appendChild(icono(src));
        const s = document.createElement('span'); s.textContent = texto; p.appendChild(s);
        caja.appendChild(p);
    };
    errores.forEach(m => linea(m, 'det-error', ICONOS.error));
    (f.advertencias || []).forEach(a => linea(a, 'det-aviso', ICONOS.alerta));
    if (f.descripcion) linea(`${f.lineas} línea(s) · sitio ${f.sitio || f.colaborador}` + (f.proveedor ? ` · proveedor ${f.proveedor}` : '') + (f.anticipo ? ` · anticipo ${f.anticipo}` : ''), 'det-info');
    if (!caja.childNodes.length) linea('-', 'det-info');
    return td;
}

function renderLote(filas, titulo) {
    $('tituloTabla').textContent = titulo;
    const cuerpo = $('tablaLote');
    cuerpo.replaceChildren();
    filas.forEach((f, i) => {
        const tr = document.createElement('tr');
        tr.appendChild(celda(i + 1, 'num text-ink-soft'));
        const tdU = celda(f.uuid || f.archivo, 'font-medium whitespace-nowrap text-xs');
        tdU.title = [f.emisor, f.rfc, f.archivo].filter(Boolean).join(' · ');
        tr.appendChild(tdU);
        tr.appendChild(celda(f.unidad_negocio, 'whitespace-nowrap'));
        const tdT = celda(f.fecha_timbrado, 'whitespace-nowrap');
        if (f.fecha_timbrado && !f.fecha_timbrado.startsWith(ANIO)) { tdT.style.color = 'var(--color-text-warning)'; tdT.style.fontWeight = '600'; }
        tr.appendChild(tdT);
        tr.appendChild(celda(dinero(f.total), 'num whitespace-nowrap'));
        const tdB = document.createElement('td');
        tdB.appendChild(badge(f.estado, TONOS[f.estado] || 'neutral'));
        tr.appendChild(tdB);
        tr.appendChild(celdaDetalle(f));
        cuerpo.appendChild(tr);
    });
    $('contadorLote').textContent = `${filas.length} resultados`;
}

function renderResumen(resumen, extra) {
    const r = $('resumen');
    r.replaceChildren();
    Object.entries(resumen).forEach(([estado, n]) => r.appendChild(badge(`${estado}: ${n}`, TONOS[estado] || 'neutral')));
    if (extra) r.appendChild(badge(extra, 'neutral'));
}

async function enviar(url, formData) {
    const resp = await fetch(url, { method: 'POST', body: formData });
    if (!revisarSesion(resp)) return null;
    let data;
    try { data = await resp.json(); }
    catch { throw new Error(`El servidor respondió con un error inesperado (HTTP ${resp.status}). Recarga la página e intenta de nuevo.`); }
    if (!resp.ok) throw new Error(data.error || 'Error del servidor');
    return data;
}

function cargando(boton, activo, texto) {
    if (!boton) return;
    if (activo) { boton.dataset.html = boton.innerHTML; boton.disabled = true; boton.innerHTML = `<span class="spinner"></span> ${texto}`; }
    else if (boton.dataset.html) { boton.innerHTML = boton.dataset.html; boton.disabled = false; }
}

// ---- Pintar lo que devuelve el servidor (también al restaurar la página) ----
function mostrarXml(data) {
    renderLote(data.filas, 'Facturas del lote');
    renderResumen(data.resumen, data.ignorados ? `Ignorados: ${data.ignorados}` : '');
    $('textoLote').textContent = data.lote;
    $('panelCarga').classList.add('hidden');
    marcarPaso(data.listos ? 2 : 1);
}

function mostrarPlantilla(data) {
    renderLote(data.filas, 'Facturas generadas');
    renderResumen(data.resumen, data.ignoradas_plantilla ? `Filas ajenas al lote: ${data.ignoradas_plantilla}` : '');
    $('textoLote').textContent = data.lote;
    const listas = data.listas;
    facturasListas = listas;
    const permitido = AMBIENTES_CARGA.includes(AMBIENTE);
    cargando($('btnCargar'), false);
    $('btnCargar').disabled = !permitido || !listas;
    $('btnCargar').textContent = permitido ? `Cargar ${listas} factura(s) en Oracle ${AMBIENTE}` : 'Carga bloqueada';
    $('textoCarga').textContent = permitido
        ? `${listas} factura(s) listas.`
        : `Estás conectado a Oracle ${AMBIENTE}: la carga solo se permite en ${AMBIENTES_CARGA.join(', ')}.`;
    $('panelCarga').classList.add('hidden');   // datos nuevos: el resultado anterior ya no aplica
    marcarPaso(listas ? 4 : 3);
}

// ---- Aviso de "procesando": que siempre se note que la página está trabajando ----
function mostrarProceso(titulo, mensaje, avance = null) {
    $('procTitulo').textContent = titulo;
    $('procMensaje').textContent = mensaje || '';
    $('procBarra').classList.toggle('hidden', avance === null);
    if (avance !== null) $('procBarra').firstElementChild.style.width = Math.round(avance * 100) + '%';
    $('procesando').classList.remove('hidden');
}
function ocultarProceso() { $('procesando').classList.add('hidden'); }

// Como enviar(), pero informa el avance de la subida (0 a 1)
function enviarConAvance(url, formData, alAvanzar) {
    return new Promise((ok, mal) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        xhr.upload.onprogress = (e) => { if (e.lengthComputable) alAvanzar(e.loaded / e.total); };
        xhr.upload.onload = () => alAvanzar(1);
        xhr.onerror = () => mal(new Error('No hubo conexión con el servidor. Revisa tu red e intenta de nuevo.'));
        xhr.onload = () => {
            if (xhr.status === 401) { window.location.href = '/login'; return ok(null); }
            let data;
            try { data = JSON.parse(xhr.responseText); }
            catch { return mal(new Error(`El servidor respondió con un error inesperado (HTTP ${xhr.status}). Recarga la página e intenta de nuevo.`)); }
            if (xhr.status >= 400) return mal(new Error(data.error || 'Error del servidor'));
            ok(data);
        };
        xhr.send(formData);
    });
}

// ---- Paso 1: subir XML (solo se envían .xml y .zip) ----
async function subirXml(lista, boton) {
    const archivos = [...lista].filter(f => /\.(xml|zip)$/i.test(f.name));
    if (!archivos.length) { ocultarProceso(); mostrarError('Sin XML', 'No se encontraron archivos .xml ni .zip en la selección.'); return; }
    const fd = new FormData();
    archivos.forEach(f => fd.append('archivos', f, f.webkitRelativePath || f.name));
    cargando(boton, true, `Leyendo ${archivos.length} archivo(s)...`);
    const cuantos = `${archivos.length} archivo(s)`;
    mostrarProceso('Subiendo facturas', cuantos, 0);
    try {
        const data = await enviarConAvance('/carga/xml', fd, (avance) => {
            if (avance < 1) mostrarProceso('Subiendo facturas', cuantos, avance);
            else mostrarProceso('Revisando facturas', 'Leyendo los XML y verificando en Oracle que no estén duplicadas…');
        });
        if (!data) return;
        ocultarProceso();
        mostrarXml(data);
        if (!data.listos) mostrarError('Sin facturas para capturar', 'Ninguna factura del lote pasó las validaciones. Revisa el detalle en la tabla.');
    } catch (e) {
        ocultarProceso();
        mostrarError('No se pudieron leer los XML', e.message);
    } finally {
        ocultarProceso();
        cargando(boton, false);
    }
}
// ---- Paso 1 desde la carpeta de Drive del área ----
async function traerDrive(boton) {
    cargando(boton, true, 'Trayendo...');
    mostrarProceso('Trayendo facturas de Drive', 'Leyendo la carpeta y verificando en Oracle que no estén duplicadas…');
    try {
        const data = await enviar('/carga/drive', new FormData());
        if (!data) return;
        ocultarProceso();
        mostrarXml(data);
        if (!data.listos) mostrarError('Sin facturas para capturar', 'Ninguna factura del lote pasó las validaciones. Revisa el detalle en la tabla.');
        else if (data.pendientes_drive) mostrarModal('Quedan facturas en Drive', `Se tomaron ${data.drive} archivo(s). Quedan ${data.pendientes_drive} en la carpeta para el siguiente lote.`, '', 'primary', null, 'info');
    } catch (e) {
        ocultarProceso();
        mostrarError('No se pudieron traer las facturas', e.message);
    } finally {
        ocultarProceso();
        cargando(boton, false);
    }
}

// ---- Arrastrar y soltar (carpetas incluidas, sin la confirmación de Chrome) ----
const zona = $('zonaArrastre');
['dragenter', 'dragover'].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.add('arrastrando'); }));
['dragleave', 'dragend'].forEach(ev => zona.addEventListener(ev, e => { if (!zona.contains(e.relatedTarget)) zona.classList.remove('arrastrando'); }));
// Evita que soltar fuera de la zona abra el archivo en el navegador
['dragover', 'drop'].forEach(ev => window.addEventListener(ev, e => e.preventDefault()));

async function recorrerEntrada(entrada, salida) {
    if (entrada.isFile) {
        if (/\.(xml|zip)$/i.test(entrada.name)) {
            salida.push(await new Promise((ok, err) => entrada.file(ok, err)));
            $('procMensaje').textContent = `${salida.length} archivo(s) XML o zip encontrados`;
        }
    } else if (entrada.isDirectory) {
        const lector = entrada.createReader();
        let bloque;
        do {
            bloque = await new Promise((ok, err) => lector.readEntries(ok, err));
            for (const e of bloque) await recorrerEntrada(e, salida);
        } while (bloque.length);
    }
}

zona.addEventListener('drop', async (e) => {
    e.preventDefault();
    zona.classList.remove('arrastrando');
    // Las entradas se leen antes de cualquier await (después ya no están disponibles)
    const entradas = [...e.dataTransfer.items].map(i => i.webkitGetAsEntry && i.webkitGetAsEntry()).filter(Boolean);
    mostrarProceso('Buscando facturas', 'Revisando la carpeta…');
    const archivos = [];
    try {
        if (entradas.length) { for (const en of entradas) await recorrerEntrada(en, archivos); }
        else archivos.push(...e.dataTransfer.files);
    } catch (err) {
        ocultarProceso();
        mostrarError('No se pudo leer la carpeta', err.message || String(err));
        return;
    }
    subirXml(archivos, null);
});

$('inputArchivos').addEventListener('change', e => { subirXml(e.target.files, null); e.target.value = ''; });
$('inputCarpeta').addEventListener('change', e => { subirXml(e.target.files, null); e.target.value = ''; });
// Al descargar la plantilla se pasa solo a la pestaña 3
$('btnPlantilla').addEventListener('click', () => setTimeout(() => marcarPaso(Math.max(pasoMax, 3)), 400));

// ---- Paso 3: subir plantilla llena ----
$('inputPlantilla').addEventListener('change', async (e) => {
    const archivo = e.target.files[0];
    e.target.value = '';
    if (!archivo) return;
    const fd = new FormData();
    fd.append('plantilla', archivo);
    const boton = $('btnSubirPlantilla');
    cargando(boton, true, 'Validando...');
    mostrarProceso('Validando plantilla', 'Revisando los datos capturados y generando las facturas…');
    try {
        const data = await enviar('/carga/plantilla', fd);
        if (!data) return;
        ocultarProceso();
        mostrarPlantilla(data);
    } catch (err) {
        ocultarProceso();
        mostrarError('No se pudo procesar la plantilla', err.message);
    } finally {
        ocultarProceso();
        cargando(boton, false);
    }
});

// ---- Paso 4: cargar (número y fecha contable de cada factura vienen de la plantilla) ----
let facturasListas = 0;
function confirmarCarga() {
    mostrarModal('Cargar en Oracle ' + AMBIENTE,
                 'Se cargarán ' + facturasListas + ' factura(s) en Oracle ' + AMBIENTE + '.',
                 'Cargar facturas', 'primary', cargarOracle, 'warning');
}

const PASOS_CARGA = ['ucm', 'loader', 'import', 'confirmar'];
let sondeo = null;

const TEXTO_PASO = { ucm: 'Subiendo el archivo a Oracle...', loader: 'Cargando a las tablas de interfaz...',
                     import: 'Importando las facturas en Payables...', confirmar: 'Confirmando cada factura...' };
let inicioCarga = null;

function pintarPasosCarga(paso, estado) {
    const idx = PASOS_CARGA.indexOf(paso);
    PASOS_CARGA.forEach((p, i) => {
        const li = $('pc-' + p);
        li.classList.toggle('hecho', i < idx);
        li.classList.toggle('activo', estado === 'en_proceso' && i === idx);
        li.classList.toggle('fallo', estado === 'error' && i === idx);
    });
}

function duracion(seg) {
    seg = Math.max(0, Math.round(seg));
    if (seg < 1) return 'menos de 1 s';
    return seg < 60 ? seg + ' s' : Math.floor(seg / 60) + ' min ' + (seg % 60) + ' s';
}

function pintarCarga(c) {
    $('panelCarga').classList.remove('hidden');
    if (c.estado === 'en_proceso') {
        $('cargaProgreso').classList.remove('hidden');
        $('cargaResultado').classList.add('hidden');
        pintarPasosCarga(c.paso, c.estado);
        $('cargaActual').textContent = TEXTO_PASO[c.paso] || 'Procesando...';
        if (!inicioCarga) inicioCarga = Date.now();
        $('cargaTiempo').textContent = 'Tiempo transcurrido: ' + duracion((Date.now() - inicioCarga) / 1000);
    }
}

function mostrarResultadoCarga(c) {
    const r = c.resultado || {};
    const facturas = r.facturas || [];
    const reg = facturas.filter(f => f.resultado === 'FACTURA_REGISTRADA').length;
    const total = facturas.length;

    // Tabla del lote
    const porUuid = {};
    facturas.forEach(f => { porUuid[f.numero.slice(-36)] = f; });
    [...$('tablaLote').rows].forEach(tr => {
        const f = porUuid[tr.cells[1] ? tr.cells[1].textContent.trim().slice(-36) : ''];   // la celda puede traer PREFIJO-UUID
        if (!f) return;
        const ok = f.resultado === 'FACTURA_REGISTRADA';
        const texto = ok ? 'Registrada en Oracle' : (f.resultado === 'RECHAZO_ORACLE' ? 'Rechazada por Oracle' : 'Sin confirmar');
        tr.cells[5].replaceChildren(badge(texto, ok ? 'success' : 'error'));
    });
    const conteo = {};
    [...$('tablaLote').rows].forEach(tr => { if (tr.cells[5]) { const e = tr.cells[5].textContent.trim(); conteo[e] = (conteo[e] || 0) + 1; } });
    renderResumen(conteo);

    // Tarjeta de resultado
    let tono, icono, titulo;
    if (r.error)             { tono = 'mal';   icono = ICONOS.error;  titulo = 'La carga no se completó'; }
    else if (reg === total)  { tono = 'ok';    icono = ICONOS.check;  titulo = 'Carga completada'; }
    else if (reg > 0)        { tono = 'aviso'; icono = ICONOS.alerta; titulo = 'Carga completada con rechazos'; }
    else                     { tono = 'mal';   icono = ICONOS.error;  titulo = 'Oracle no registró las facturas'; }
    $('resIcono').className = 'res-icono ' + tono;
    $('resIcono').firstElementChild.style.setProperty('--src', icono);
    $('resTitulo').textContent = titulo;
    // Solo lo que le importa al usuario: si su factura quedó registrada.
    // El detalle técnico (jobs, UCM, mensajes de Oracle) queda en cargas/<lote>/resultado.json.
    $('resSubtitulo').textContent = r.error
        ? 'Las facturas no se registraron en Oracle ' + AMBIENTE + '. Intenta de nuevo; si vuelve a fallar, avisa a soporte.'
        : reg + ' de ' + total + ' factura' + (total === 1 ? '' : 's') + ' registrada' + (reg === 1 ? '' : 's') + ' en Oracle ' + AMBIENTE + '.';
    $('resError').classList.add('hidden');

    $('cargaProgreso').classList.add('hidden');
    $('cargaActual').replaceChildren();
    $('cargaTiempo').textContent = '';
    $('cargaResultado').classList.remove('hidden');
    if (r.error) $('btnCargar').disabled = false;
    inicioCarga = null;
    $('panelCarga').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function consultarCarga() {
    try {
        const resp = await fetch('/carga/estado');
        if (!revisarSesion(resp)) return;
        const c = await resp.json();
        if (c.estado === 'sin_carga') return;
        pintarCarga(c);
        if (c.estado !== 'en_proceso') {
            clearInterval(sondeo); sondeo = null;
            cargando($('btnCargar'), false);
            $('btnCargar').disabled = c.estado === 'terminado';
            if (c.estado === 'terminado') marcarPaso(5);
            mostrarResultadoCarga(c);
        }
    } catch (e) { /* se reintenta en el siguiente ciclo */ }
}

async function cargarOracle() {
    const boton = $('btnCargar');
    cargando(boton, true, 'Cargando...');
    const fd = new FormData();
    try {
        const data = await enviar('/carga/enviar', fd);
        if (!data) return;
        inicioCarga = Date.now();
        pintarCarga({ estado: 'en_proceso', paso: 'ucm', archivo: data.archivo, mensajes: [], omitidas_existentes: data.omitidas_existentes });
        $('panelCarga').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        sondeo = setInterval(consultarCarga, 2000);
    } catch (e) {
        cargando(boton, false);
        mostrarError('Carga no realizada', e.message);
    }
}

// ---- Limpiar lote ----
function pantallaInicial() {
    $('tablaLote').innerHTML = '<tr><td colspan="7" class="text-center !py-16 text-ink-inactive">Sube las facturas para comenzar</td></tr>';
    $('tituloTabla').textContent = 'Facturas del lote';
    $('contadorLote').textContent = '0 resultados';
    $('resumen').replaceChildren();
    $('textoLote').textContent = '-';
    $('btnLimpiarLote').disabled = true;
    $('panelCarga').classList.add('hidden');
    if (sondeo) { clearInterval(sondeo); sondeo = null; }
    marcarPaso(1);
}
function confirmarLimpiarLote() {
    mostrarModal('Limpiar lote', 'Se borrarán los XML cargados, la plantilla y las facturas generadas de este lote. Tendrás que volver a subir los XML.',
                 'Limpiar lote', 'error', limpiarLote, 'warning');
}
async function limpiarLote() {
    try {
        await enviar('/carga/limpiar', new FormData());
        pantallaInicial();
    } catch (e) {
        mostrarError('No se pudo limpiar', e.message);
    }
}
// Habilitar "Limpiar" cada vez que hay un lote en pantalla
new MutationObserver(() => { $('btnLimpiarLote').disabled = $('textoLote').textContent === '-'; })
    .observe($('textoLote'), { childList: true, characterData: true, subtree: true });

// ---- Al abrir o recargar la página: restaurar el lote que tenga la sesión ----
async function restaurarLote() {
    try {
        const resp = await fetch('/carga/lote');
        if (!revisarSesion(resp)) return;
        const d = await resp.json();
        if (!d.lote) return;
        if (d.etapa === 'plantilla') mostrarPlantilla(d); else mostrarXml(d);
        const c = d.carga || {};
        if (c.estado === 'en_proceso') {
            cargando($('btnCargar'), true, 'Cargando...');
            pintarCarga(c);
            sondeo = setInterval(consultarCarga, 2000);
        } else if (c.estado === 'terminado' || c.estado === 'error') {
            pintarCarga(c);
            $('btnCargar').disabled = c.estado === 'terminado';
            if (c.estado === 'terminado') marcarPaso(5);
            mostrarResultadoCarga(c);
        }
    } catch (e) { /* sin lote que restaurar */ }
}

pantallaInicial();
restaurarLote();
