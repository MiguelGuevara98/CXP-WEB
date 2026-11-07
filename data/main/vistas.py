# ==========================================================
# VISTAS - Sistema de diseño Coltrane [Bubble] (Coppel)
# Referencia: carpeta "Ui Kit GCD Argentina" (tokens CSS, componentes y pantallas)
# ==========================================================

# ----------------------------------------------------------
# HEAD COMPARTIDO: tipografía, tokens y componentes base
# ----------------------------------------------------------
HEAD_COMUN = """
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Poppins', 'sans-serif'] },
                    colors: {
                        primary:   { DEFAULT: '#1C42E8', hover: '#081754', press: '#05297A' },
                        ink:       { DEFAULT: '#081754', soft: '#4A4A4A', inactive: '#8C8C8C' },
                        line:      '#C9C9C9',
                        bg0:       '#F3F3F3',
                        coppel:    '#F0D224',
                    },
                    borderRadius: { sm: '8px', md: '16px' },
                }
            }
        }
    </script>
    <style>
        /* ===== Tokens Coltrane (8. Tokens - CSS) ===== */
        :root {
            --color-interactive-primary: #1C42E8;
            --color-interactive-primary-hover: #081754;
            --color-interactive-primary-press: #05297A;
            --color-interactive-secondary: #F3F3F3;
            --color-interactive-secondary-hover: #C9C9C9;
            --color-interactive-secondary-press: #DEDEDE;
            --color-interactive-error: #FF594D;
            --color-interactive-error-hover: #7A2627;
            --color-interactive-error-press: #C8180D;

            --color-text: #081754;
            --color-text-soft: #4A4A4A;
            --color-text-inactive: #8C8C8C;
            --color-text-invert: #FFFFFF;
            --color-text-error: #C8180D;
            --color-text-warning: #CF4600;
            --color-text-success: #2E8A41;
            --color-text-info: #0062A5;

            --color-bg-0: #F3F3F3;
            --color-bg-body: #FFFFFF;
            --color-bg-inactive: #DEDEDE;
            --color-border: #C9C9C9;
            --color-brand-coppel: #F0D224;

            --rounded-sm: 8px;
            --rounded-md: 16px;
            --rounded-full: 999px;

            /* Profundidad: default / hover / float */
            --shadow-default: 0 1px 4px rgba(8, 23, 84, 0.08);
            --shadow-hover:   0 4px 12px rgba(8, 23, 84, 0.14);
            --shadow-float:   0 12px 32px rgba(8, 23, 84, 0.20);
        }

        html, body { font-family: 'Poppins', sans-serif; color: var(--color-text); }

        /* ===== Iconos Coltrane (SVG como máscara para heredar color) ===== */
        .icon {
            display: inline-block; width: 24px; height: 24px; flex-shrink: 0;
            background-color: currentColor;
            -webkit-mask: var(--src) center / contain no-repeat;
                    mask: var(--src) center / contain no-repeat;
        }
        .icon-sm { width: 20px; height: 20px; }
        .icon-xs { width: 16px; height: 16px; }

        /* ===== Button (semicircular, padding 12/24, Body 16) ===== */
        .btn {
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
            padding: 12px 24px; border-radius: var(--rounded-full);
            font-size: 16px; font-weight: 500; line-height: 24px;
            transition: background-color .15s, color .15s, box-shadow .15s;
            white-space: nowrap;
        }
        .btn:focus-visible { outline: 2px solid var(--color-interactive-primary); outline-offset: 2px; }
        .btn:disabled { background: var(--color-bg-inactive); color: var(--color-text-inactive); cursor: not-allowed; box-shadow: none; }

        .btn-primary { background: var(--color-interactive-primary); color: var(--color-text-invert); }
        .btn-primary:not(:disabled):hover  { background: var(--color-interactive-primary-hover); }
        .btn-primary:not(:disabled):active { background: var(--color-interactive-primary-press); }

        .btn-secondary { background: var(--color-interactive-secondary); color: var(--color-text); }
        .btn-secondary:not(:disabled):hover  { background: var(--color-interactive-secondary-hover); }
        .btn-secondary:not(:disabled):active { background: var(--color-interactive-secondary-press); }

        .btn-tertiary { background: transparent; color: var(--color-interactive-primary); padding-left: 12px; padding-right: 12px; }
        .btn-tertiary:not(:disabled):hover { color: var(--color-interactive-primary-hover); text-decoration: underline; }
        .btn-tertiary:disabled { background: transparent; }

        .btn-error { background: var(--color-interactive-error); color: var(--color-text-invert); }
        .btn-error:not(:disabled):hover  { background: var(--color-interactive-error-hover); }
        .btn-error:not(:disabled):active { background: var(--color-interactive-error-press); }

        .btn-icon {
            display: inline-flex; align-items: center; justify-content: center;
            width: 40px; height: 40px; border-radius: var(--rounded-full); color: var(--color-text);
            transition: background-color .15s;
        }
        .btn-icon:hover { background: var(--color-interactive-secondary); }

        /* ===== Input (rounded-sm) ===== */
        .input {
            width: 100%; height: 48px; padding: 0 16px;
            border: 1px solid var(--color-border); border-radius: var(--rounded-sm);
            font-size: 16px; color: var(--color-text); background: var(--color-bg-body);
            outline: none; transition: border-color .15s, box-shadow .15s;
        }
        .input::placeholder { color: var(--color-text-inactive); }
        .input:focus { border-color: var(--color-interactive-primary); box-shadow: 0 0 0 3px rgba(28, 66, 232, .15); }

        /* ===== Card (rounded-md) ===== */
        .card { background: var(--color-bg-body); border-radius: var(--rounded-md); box-shadow: var(--shadow-default); }

        @keyframes spin { to { transform: rotate(360deg); } }
        .spinner { width: 18px; height: 18px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; }
    </style>
"""

# ==========================================
# PLANTILLA DE INICIO DE SESIÓN (LOGIN)
# Referencia: "Inicio de sesión - IDC"
# ==========================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <title>Iniciar sesión · Cuentas por Pagar</title>
""" + HEAD_COMUN + """
</head>
<body class="bg-white min-h-screen grid lg:grid-cols-2">

    <section class="flex items-center justify-center px-6 py-12">
        <div class="w-full max-w-sm">
            <img src="{{ url_for('static', filename='img/coppel-blue.svg') }}" alt="Coppel" class="h-14 -ml-4">

            <h1 class="mt-8 text-[28px] leading-9 font-semibold text-ink">Cuentas por Pagar</h1>
            <p class="mt-2 text-sm text-ink-soft">Inicia sesión con tus credenciales para continuar</p>

            <form method="POST" action="/login" class="mt-8 space-y-5">
                <div>
                    <label for="username" class="block text-sm font-medium text-ink mb-2">Usuario</label>
                    <input type="text" id="username" name="username" required autocomplete="username"
                           placeholder="Ingresa tu usuario" class="input">
                </div>

                <div>
                    <label for="password" class="block text-sm font-medium text-ink mb-2">Contraseña</label>
                    <div class="relative">
                        <input type="password" id="password" name="password" required autocomplete="current-password"
                               placeholder="Ingresa tu contraseña" class="input pr-12">
                        <button type="button" onclick="togglePassword()" title="Mostrar contraseña"
                                class="absolute inset-y-0 right-1 my-auto btn-icon text-ink-soft">
                            <span id="iconoPassword" class="icon icon-sm"
                                  style="--src: url('{{ url_for('static', filename='icons/visibility.svg') }}')"></span>
                        </button>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary w-full !mt-8">Iniciar sesión</button>
            </form>
        </div>
    </section>

    <!-- Panel de marca: círculos amarillos Coppel sobre azul primario -->
    <aside class="hidden lg:block relative overflow-hidden bg-primary">
        <div class="absolute rounded-full bg-coppel" style="width: 38%; aspect-ratio: 1; left: 18%; top: 50%; transform: translateY(-50%);"></div>
        <div class="absolute rounded-full bg-coppel" style="width: 17%; aspect-ratio: 1; left: 60%; top: 50%; transform: translateY(-50%);"></div>
        <div class="absolute rounded-full bg-coppel" style="width: 17%; aspect-ratio: 1; left: 80%; top: 50%; transform: translateY(-50%);"></div>
    </aside>

    <script>
        const ICON_VER = "url('{{ url_for('static', filename='icons/visibility.svg') }}')";
        const ICON_OCULTAR = "url('{{ url_for('static', filename='icons/visibility-off.svg') }}')";
        function togglePassword() {
            const input = document.getElementById('password');
            const icono = document.getElementById('iconoPassword');
            const mostrar = input.type === 'password';
            input.type = mostrar ? 'text' : 'password';
            icono.style.setProperty('--src', mostrar ? ICON_OCULTAR : ICON_VER);
        }
    </script>
</body>
</html>
"""

# ==========================================
# PLANTILLA PRINCIPAL (MONITOR)
# Referencia: Navbar, Menú lateral, Table, Pagination y Modal
# ==========================================
INDEX_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <title>Gestión de facturas · Cuentas por Pagar</title>
""" + HEAD_COMUN + """
    <style>
        .sidebar { transition: width .25s ease, opacity .2s ease; }
        .sidebar-hidden { width: 0 !important; min-width: 0 !important; opacity: 0; overflow: hidden; border: 0 !important; }

        .nav-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: var(--rounded-sm);
                    font-size: 14px; font-weight: 500; color: var(--color-text); transition: background-color .15s; }
        .nav-item:hover { background: var(--color-interactive-secondary); }
        .nav-item.activo { background: var(--color-interactive-primary); color: var(--color-text-invert); box-shadow: var(--shadow-hover); }

        /* Table */
        .tabla th { font-size: 14px; font-weight: 600; color: var(--color-text); text-align: left; padding: 12px 16px;
                    border-bottom: 1px solid var(--color-border); background: var(--color-bg-body); position: sticky; top: 0; z-index: 1; }
        .tabla td { font-size: 14px; color: var(--color-text); padding: 14px 16px; border-bottom: 1px solid var(--color-bg-0); }
        .tabla tbody tr:hover td { background: #F8F9FE; }
        .tabla .num { text-align: right; }

        /* Badge de estatus (píldora) */
        .badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: var(--rounded-full);
                 font-size: 12px; font-weight: 500; white-space: nowrap; }
        .badge-success { background: #E6F6EC; color: var(--color-text-success); }
        .badge-warning { background: #FFF1E3; color: var(--color-text-warning); }
        .badge-error   { background: #FFECEA; color: var(--color-text-error); }
        .badge-info    { background: #E6F2FB; color: var(--color-text-info); }
        .badge-neutral { background: var(--color-bg-0); color: var(--color-text-soft); }

        /* Pagination */
        .pag-btn { min-width: 32px; height: 32px; padding: 0 6px; border-radius: var(--rounded-full); font-size: 14px; font-weight: 500;
                   display: inline-flex; align-items: center; justify-content: center; color: var(--color-text); transition: background-color .15s; }
        .pag-btn:hover:not(:disabled) { background: var(--color-interactive-secondary); }
        .pag-btn.activo { background: var(--color-interactive-primary); color: var(--color-text-invert); }
        .pag-btn:disabled { color: var(--color-text-inactive); cursor: not-allowed; }

        /* Progress */
        .barra { transition: width .5s ease-out, background-color .2s; }

        /* Modal */
        .modal-panel { animation: modalIn .18s ease-out; }
        @keyframes modalIn { from { opacity: 0; transform: scale(.96); } to { opacity: 1; transform: scale(1); } }
    </style>
</head>
<body class="bg-bg0 h-screen flex flex-col overflow-hidden">

    <!-- ================= MODAL ================= -->
    <div id="customModal" class="hidden fixed inset-0 z-50 flex items-center justify-center px-4" style="background: rgba(8, 23, 84, .45);">
        <div class="modal-panel card w-full max-w-md px-6 pt-6 pb-10 relative" style="box-shadow: var(--shadow-float);" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
            <button onclick="cerrarModal()" class="btn-icon absolute top-4 right-4" title="Cerrar">
                <span class="icon icon-sm" style="--src: url('{{ url_for('static', filename='icons/close.svg') }}')"></span>
            </button>
            <div class="flex flex-col items-center text-center pt-4 px-4">
                <span id="modalIcono" class="icon mb-4" style="width: 40px; height: 40px;"></span>
                <h3 id="modalTitle" class="text-2xl font-semibold text-ink">Título</h3>
                <p id="modalMessage" class="mt-3 text-base text-ink-soft">Mensaje</p>
                <button id="modalConfirmBtn" class="btn btn-primary mt-8">Aceptar</button>
            </div>
        </div>
    </div>

    <!-- ================= NAVBAR ================= -->
    <header class="bg-white flex items-center gap-4 px-4 lg:px-8 py-3 z-30" style="box-shadow: var(--shadow-default);">
        <button onclick="toggleSidebar()" class="btn-icon" title="Menú">
            <span class="icon" style="--src: url('{{ url_for('static', filename='icons/hamburguer-menu.svg') }}')"></span>
        </button>
        <img src="{{ url_for('static', filename='img/coppel-blue.svg') }}" alt="Coppel" class="h-10 hidden sm:block -mx-2">
        <span class="hidden sm:block w-px h-6 bg-line"></span>
        <h1 class="text-xl font-semibold text-ink truncate">Cuentas por Pagar</h1>

        <div class="ml-auto flex items-center gap-3 min-w-0">
            <span class="hidden md:block text-base text-ink truncate">{{ username }}</span>
            <span class="w-10 h-10 rounded-full bg-bg0 flex items-center justify-center text-ink shrink-0" title="{{ username }}">
                <span class="icon icon-sm" style="--src: url('{{ url_for('static', filename='icons/user-profile.svg') }}')"></span>
            </span>
        </div>
    </header>

    <div class="flex flex-1 min-h-0">

        <!-- ================= MENÚ LATERAL ================= -->
        <aside id="sidebar" class="sidebar w-64 bg-white border-r border-bg0 flex flex-col shrink-0 z-20">
            <nav class="flex-1 p-4 space-y-1">
                <a href="#" class="nav-item activo">
                    <span class="icon icon-sm" style="--src: url('{{ url_for('static', filename='icons/list-view.svg') }}')"></span>
                    Gestionar facturas
                </a>
            </nav>
            <div class="p-4 border-t border-bg0">
                <button onclick="confirmarCerrarSesion()" class="nav-item w-full" style="color: var(--color-text-error);">
                    <span class="icon icon-sm" style="--src: url('{{ url_for('static', filename='icons/cancel.svg') }}')"></span>
                    Cerrar sesión
                </button>
            </div>
        </aside>

        <!-- ================= CONTENIDO ================= -->
        <main class="flex-1 min-w-0 overflow-auto p-4 lg:p-8 space-y-6">

            <!-- Encabezado de sección -->
            <section class="card p-6 flex items-start gap-4">
                <img src="{{ url_for('static', filename='img/spot-documentos.svg') }}" alt="" class="w-12 h-12 shrink-0">
                <div class="min-w-0">
                    <h2 class="text-2xl font-semibold text-ink">Gestión de facturas</h2>
                    <p class="mt-1 text-sm text-ink-soft">Adjunta el reporte de facturas para revisarlo y procesarlo. Al terminar podrás descargar los resultados.</p>
                </div>
            </section>

            <!-- Tabla -->
            <section class="card flex flex-col min-h-[420px]">
                <div class="px-6 pt-6 pb-4 flex flex-wrap items-center gap-4">
                    <div class="min-w-0">
                        <h3 class="text-xl font-semibold text-ink">Facturas del reporte</h3>
                        <p id="contadorResultados" class="text-xs text-ink-soft mt-1">0 resultados</p>
                    </div>

                    <div id="contenedorContador" class="hidden">
                        <span id="badgeContador" class="badge badge-info">
                            <span id="labelContador">Facturas detectadas:</span>
                            <span id="textoContador" class="font-semibold">0</span>
                        </span>
                    </div>

                    <div class="flex flex-wrap gap-3 ml-auto">
                        <input type="file" id="fileInput" accept=".xls,.xlsx,.htm,.html" class="hidden">

                        <button id="btnLimpiar" onclick="confirmarLimpiar()" disabled class="btn btn-secondary">
                            <span class="icon icon-sm" style="--src: url('{{ url_for('static', filename='icons/remove-circle.svg') }}')"></span>
                            Limpiar
                        </button>
                        <button id="btnAdjuntar" onclick="document.getElementById('fileInput').click()" class="btn btn-secondary">
                            <span class="icon icon-sm" style="--src: url('{{ url_for('static', filename='icons/add-circle.svg') }}')"></span>
                            <span id="textoAdjuntar">Adjuntar reporte</span>
                        </button>
                        <button id="btnImportar" onclick="confirmarProcesar()" disabled class="btn btn-primary">
                            <span id="textoImportar">Procesar reporte</span>
                        </button>
                    </div>
                </div>

                <!-- Progreso -->
                <div id="contenedorProgreso" class="hidden px-6 pb-4">
                    <div class="flex justify-between text-xs font-medium text-ink-soft mb-2">
                        <span id="textoProgreso">Procesando reporte...</span>
                        <span id="porcentajeProgreso">0%</span>
                    </div>
                    <div class="w-full h-2 rounded-full bg-bg0 overflow-hidden">
                        <div id="barraProgreso" class="barra h-2 rounded-full bg-primary" style="width: 0%"></div>
                    </div>
                </div>

                <div class="flex-1 overflow-auto px-2">
                    <table class="tabla w-full border-collapse min-w-[640px]">
                        <thead>
                            <tr>
                                <th class="num w-16">No.</th>
                                <th>Folio CFDI</th>
                                <th>Factura</th>
                                <th>RFC</th>
                                <th>Resultado</th>
                                <th>Validación</th>
                            </tr>
                        </thead>
                        <tbody id="tablaBody"></tbody>
                    </table>
                </div>

                <!-- Pie: paginación + descarga -->
                <div class="px-6 py-4 flex flex-wrap items-center gap-4 border-t border-bg0">
                    <nav id="paginacion" class="flex items-center gap-1" aria-label="Paginación"></nav>
                    <button id="btnDescargar" onclick="window.location.href='/descargar'" disabled class="btn btn-primary ml-auto">
                        <span class="icon icon-sm" style="--src: url('{{ url_for('static', filename='icons/download.svg') }}')"></span>
                        Descargar resultados
                    </button>
                </div>
            </section>
        </main>
    </div>

    <script>
        // ---------- Recursos ----------
        const ICONOS = {
            check:   "url('{{ url_for('static', filename='icons/check-mark.svg') }}')",
            alerta:  "url('{{ url_for('static', filename='icons/alert-warning.svg') }}')",
            error:   "url('{{ url_for('static', filename='icons/cancel.svg') }}')",
            info:    "url('{{ url_for('static', filename='icons/info.svg') }}')",
            chevron: "url('{{ url_for('static', filename='icons/chevron-down.svg') }}')",
        };
        const FILAS_POR_PAGINA = 10;

        // ---------- Elementos ----------
        const $ = (id) => document.getElementById(id);
        const fileInput = $('fileInput'), btnAdjuntar = $('btnAdjuntar'), btnImportar = $('btnImportar');
        const btnLimpiar = $('btnLimpiar'), btnDescargar = $('btnDescargar'), tablaBody = $('tablaBody');
        const textoAdjuntar = $('textoAdjuntar'), textoImportar = $('textoImportar');
        const contenedorContador = $('contenedorContador'), labelContador = $('labelContador');
        const textoContador = $('textoContador'), badgeContador = $('badgeContador');
        const contadorResultados = $('contadorResultados'), paginacion = $('paginacion');
        const contenedorProgreso = $('contenedorProgreso'), barraProgreso = $('barraProgreso');
        const porcentajeProgreso = $('porcentajeProgreso'), textoProgreso = $('textoProgreso');

        let intervaloProgreso = null;
        let accionPendiente = null;
        let filas = [];          // [{folio, factura, rfc, resultado, validacion, tono}]
        let paginaActual = 1;
        let mensajeVacio = 'Adjunta un reporte para comenzar';

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
        function toggleSidebar() { $('sidebar').classList.toggle('sidebar-hidden'); }
        if (window.innerWidth < 1024) $('sidebar').classList.add('sidebar-hidden');

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
                         () => { window.location.href = '/logout'; }, 'warning');
        }
        function confirmarLimpiar() {
            mostrarModal('Limpiar monitor', 'Se borrarán todos los datos que se muestran en pantalla.', 'Limpiar datos', 'error',
                         limpiarMonitor, 'warning');
        }
        function confirmarProcesar() {
            mostrarModal('Procesar reporte', 'Se procesarán todas las facturas detectadas en el reporte.', 'Iniciar proceso', 'primary',
                         procesarArchivo, 'info');
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
                tr.appendChild(celda(f.folio, 'font-medium'));
                tr.appendChild(celda(f.factura));
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
            setBotonCargando(btnImportar, textoImportar, 'Procesar reporte', false);
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
            textoProgreso.textContent = 'Procesando reporte...';
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
    </script>
</body>
</html>
"""
