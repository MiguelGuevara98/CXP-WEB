# ==========================================
# PLANTILLA DE INICIO DE SESIÓN (LOGIN)
# ==========================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Gestión de Facturas</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 flex h-screen items-center justify-center">
    <div class="bg-white p-8 rounded-xl shadow-md w-full max-w-md border border-gray-100">
        <div class="text-center mb-8">
            <h2 class="text-2xl font-bold text-gray-800 tracking-wider">CUENTAS POR PAGAR</h2>
            <p class="text-gray-500 text-sm mt-2">Inicia sesión con tus credenciales de Oracle</p>
        </div>
        
        <form method="POST" action="/login" class="space-y-6">
            <div>
                <label for="username" class="block text-sm font-medium text-gray-700 mb-1">Usuario Oracle</label>
                <input type="text" id="username" name="username" required 
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all">
            </div>
            
            <div>
                <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
                <div class="relative">
                    <input type="password" id="password" name="password" required 
                        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all pr-10">
                    
                    <button type="button" onclick="togglePassword()" class="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-blue-600 transition-colors">
                        
                        <svg id="eyeClosed" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
                        </svg>
                        
                        <svg id="eyeOpen" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 hidden">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                        </svg>
                        
                    </button>
                </div>
            </div>
            
            <button type="submit" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors shadow-sm">
                Ingresar
            </button>
        </form>
    </div>
    
    <script>
        function togglePassword() {
            const passwordInput = document.getElementById('password');
            const eyeClosed = document.getElementById('eyeClosed');
            const eyeOpen = document.getElementById('eyeOpen');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeClosed.classList.add('hidden');
                eyeOpen.classList.remove('hidden');
            } else {
                passwordInput.type = 'password';
                eyeClosed.classList.remove('hidden');
                eyeOpen.classList.add('hidden');
            }
        }
    </script>
</body>
</html>
"""

# ==========================================
# PLANTILLA PRINCIPAL (MONITOR DINÁMICO)
# ==========================================
INDEX_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gestión de Facturas</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <style>
        .sidebar-transition { transition: all 0.3s ease-in-out; }
        .sidebar-hidden { width: 0 !important; min-width: 0 !important; overflow: hidden; opacity: 0; }
        .progress-transition { transition: width 0.5s ease-out; }
        
        /* Animación suave para el Modal */
        .modal-enter { opacity: 0; transform: scale(0.95); }
        .modal-enter-active { opacity: 1; transform: scale(1); transition: all 0.2s ease-out; }
    </style>
</head>
<body class="bg-gray-50 flex h-screen overflow-hidden text-gray-800">

    <div id="customModal" class="hidden fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 transition-opacity">
        <div class="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 transform transition-all">
            <h3 id="modalTitle" class="text-xl font-bold text-gray-900 mb-2">Título</h3>
            <p id="modalMessage" class="text-sm text-gray-600 mb-6">Mensaje descriptivo</p>
            <div class="flex justify-end gap-3">
                <button onclick="cerrarModal()" class="px-4 py-2 text-sm font-bold text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">
                    Cancelar
                </button>
                <button id="modalConfirmBtn" class="px-4 py-2 text-sm font-bold text-white rounded-lg transition-colors shadow-sm">
                    Aceptar
                </button>
            </div>
        </div>
    </div>

    <aside id="sidebar" class="sidebar-transition w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 shadow-sm z-20">
        <div class="p-6 text-center mt-8">
            <h2 class="text-lg font-bold tracking-wider text-gray-800">CUENTAS<br>pxPOR PAGAR</h2>
        </div>
        <div class="mt-8 px-6 flex-1">
            <a href="#" class="block px-4 py-3 text-sm font-bold text-white bg-blue-600 rounded-lg shadow-md text-center hover:bg-blue-700 transition-colors">
                Gestionar Facturas
            </a>
        </div>
        <div class="p-4 mb-4 text-center">
            <button onclick="confirmarCerrarSesion()" 
               class="block w-full py-2 text-sm font-bold text-red-500 border border-red-500 rounded-full hover:bg-red-50 transition-colors">
                Cerrar Sesión
            </button>
        </div>
    </aside>

    <main class="flex-1 flex flex-col h-full min-w-0 bg-white">
        <header class="px-8 py-6 flex items-center border-b border-gray-100 bg-white z-10">
            <button onclick="toggleSidebar()" class="text-2xl mr-4 text-gray-600 hover:text-blue-600 focus:outline-none transition-colors">
                ☰
            </button>
            <h1 class="text-lg font-bold truncate">GESTIÓN DE FACTURAS</h1>
            <div class="ml-auto flex items-center text-sm text-gray-500 whitespace-nowrap">
                Usuario activo: <span class="font-bold ml-1 text-blue-600">{{ username }}</span>
            </div>
        </header>

        <div class="px-8 py-4 flex justify-between items-center bg-white border-b border-gray-50">
            
            <div id="contenedorContador" class="hidden opacity-0 transition-opacity duration-300">
                <span id="badgeContador" class="bg-blue-50 border border-blue-200 text-blue-800 text-sm font-bold px-4 py-2 rounded-full shadow-sm flex items-center gap-2">
                    <span id="labelContador">📄 Facturas detectadas:</span>
                    <span id="textoContador" class="text-blue-600 text-lg">0</span>
                </span>
            </div>

            <div class="flex gap-4 ml-auto">
                <input type="file" id="fileInput" accept=".xls,.xlsx,.htm,.html" class="hidden">
                
                <button id="btnLimpiar" onclick="confirmarLimpiar()" title="Limpiar Monitor" disabled
                    class="px-4 py-2 text-sm font-bold text-gray-500 bg-white border border-gray-300 rounded-lg shadow-sm flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-red-50 hover:text-red-600 hover:border-red-300 disabled:hover:bg-white disabled:hover:text-gray-500 disabled:hover:border-gray-300">
                    🗑️ Limpiar
                </button>

                <button id="btnAdjuntar" onclick="document.getElementById('fileInput').click()" 
                    class="px-4 py-2 text-sm font-bold text-blue-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm">
                    + Adjuntar Reporte
                </button>
                
                <button id="btnImportar" onclick="confirmarProcesar()" disabled
                    class="px-4 py-2 text-sm font-bold text-white bg-green-500 rounded-lg transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-green-600">
                    Consultar Oracle
                </button>
            </div>
        </div>

        <div id="contenedorProgreso" class="hidden px-8 py-2 bg-white">
            <div class="flex justify-between text-xs font-bold text-gray-500 mb-1">
                <span id="textoProgreso" class="animate-pulse">Consultando con la base de datos de Oracle...</span>
                <span id="porcentajeProgreso">0%</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden border border-gray-200">
                <div id="barraProgreso" class="bg-blue-500 h-2.5 rounded-full progress-transition relative" style="width: 0%">
                    <div class="absolute top-0 left-0 bottom-0 right-0 bg-white opacity-20" style="animation: shimmer 2s infinite;"></div>
                </div>
            </div>
        </div>

        <div class="flex-1 px-8 pb-4 overflow-auto">
            <table class="w-full text-left border-collapse min-w-[600px]">
                <thead>
                    <tr class="bg-gray-50 border-b border-gray-200 text-xs text-gray-500 uppercase sticky top-0 shadow-sm z-10">
                        <th class="px-4 py-3 font-bold text-blue-700">Reporte (CFDI)</th>
                        <th class="px-4 py-3 font-bold">Oracle</th>
                        <th class="px-4 py-3 font-bold">RFC</th>
                        <th class="px-4 py-3 font-bold">Resultado</th>
                        <th class="px-4 py-3 font-bold">Validada</th>
                    </tr>
                </thead>
                <tbody id="tablaBody" class="text-sm divide-y divide-gray-100">
                    <tr><td colspan="5" class="text-center py-12 text-gray-400 font-medium">Adjunta un reporte para comenzar</td></tr>
                </tbody>
            </table>
        </div>

        <footer class="p-8 flex justify-end bg-white border-t border-gray-50">
            <a href="/descargar" id="btnDescargar" 
                class="px-8 py-2 text-sm font-bold text-blue-600 border border-blue-600 rounded-full hover:bg-blue-50 transition-all pointer-events-none opacity-30 shadow-sm">
                Descargar datos
            </a>
        </footer>
    </main>

    <style>
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
    </style>

    <script>
        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('sidebar-hidden');
        }

        const fileInput = document.getElementById('fileInput');
        const btnAdjuntar = document.getElementById('btnAdjuntar');
        const btnImportar = document.getElementById('btnImportar');
        const btnLimpiar = document.getElementById('btnLimpiar');
        const btnDescargar = document.getElementById('btnDescargar');
        const tablaBody = document.getElementById('tablaBody');

        const contenedorContador = document.getElementById('contenedorContador');
        const labelContador = document.getElementById('labelContador');
        const textoContador = document.getElementById('textoContador');
        const badgeContador = document.getElementById('badgeContador');

        const contenedorProgreso = document.getElementById('contenedorProgreso');
        const barraProgreso = document.getElementById('barraProgreso');
        const porcentajeProgreso = document.getElementById('porcentajeProgreso');
        const textoProgreso = document.getElementById('textoProgreso');

        let intervaloProgreso;
        let accionPendiente = null;

        // --- SISTEMA DE MODAL ---
        function mostrarModal(titulo, mensaje, textoBtn, claseColorBtn, funcionCallback) {
            document.getElementById('modalTitle').textContent = titulo;
            document.getElementById('modalMessage').textContent = mensaje;
            
            const btnConfirm = document.getElementById('modalConfirmBtn');
            btnConfirm.textContent = textoBtn;
            btnConfirm.className = `px-4 py-2 text-sm font-bold text-white rounded-lg shadow-sm transition-colors ${claseColorBtn}`;
            
            accionPendiente = funcionCallback;
            document.getElementById('customModal').classList.remove('hidden');
        }

        function cerrarModal() {
            document.getElementById('customModal').classList.add('hidden');
            accionPendiente = null;
        }

        document.getElementById('modalConfirmBtn').addEventListener('click', () => {
            if (accionPendiente) accionPendiente();
            cerrarModal();
        });

        // --- FUNCIONES DE CONFIRMACIÓN ---
        function confirmarCerrarSesion() {
            mostrarModal('Cerrar Sesión', '¿Estás seguro de que deseas salir del sistema?', 'Salir', 'bg-red-500 hover:bg-red-600', () => {
                window.location.href = '/logout';
            });
        }

        function confirmarLimpiar() {
            mostrarModal('Limpiar Monitor', '¿Estás seguro de que deseas borrar todos los datos de la pantalla actual?', 'Borrar', 'bg-red-500 hover:bg-red-600', limpiarMonitor);
        }

        function confirmarProcesar() {
            mostrarModal('Consultar Oracle', '¿Iniciar la consulta? Esto procesará todas las facturas detectadas en el reporte.', 'Iniciar Consulta', 'bg-blue-600 hover:bg-blue-700', procesarArchivo);
        }

        // --- LÓGICA PRINCIPAL ---
        function limpiarMonitor() {
            if(intervaloProgreso) clearInterval(intervaloProgreso);
            fileInput.value = '';
            tablaBody.innerHTML = '<tr><td colspan="5" class="text-center py-12 text-gray-400 font-medium">Adjunta un reporte para comenzar</td></tr>';
            
            contenedorContador.classList.add('hidden', 'opacity-0');
            contenedorProgreso.classList.add('hidden');
            
            btnAdjuntar.innerHTML = '+ Adjuntar Reporte';
            btnAdjuntar.classList.remove('text-green-600', 'border-green-300');
            btnAdjuntar.classList.add('text-blue-600', 'border-gray-300');
            btnAdjuntar.disabled = false;
            
            
            btnImportar.disabled = true;
            btnLimpiar.disabled = true;
            btnDescargar.classList.add('pointer-events-none', 'opacity-30');
            btnImportar.innerHTML = 'Consultar Oracle';
            btnImportar.classList.replace('bg-blue-600', 'bg-green-500');
        }

        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            btnAdjuntar.textContent = 'Leyendo archivo...';
            
            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await fetch('/previsualizar', { method: 'POST', body: formData });
                const data = await response.json();

                if (!response.ok) {
                    mostrarModal('Error', data.error, 'Entendido', 'bg-gray-500 hover:bg-gray-600', null);
                    btnAdjuntar.textContent = '+ Adjuntar Reporte';
                    fileInput.value = ''; 
                    return;
                }

                labelContador.textContent = '📄 Facturas detectadas:';
                textoContador.textContent = data.total || data.folios.length; 
                textoContador.className = "text-blue-600 text-lg font-bold";
                badgeContador.className = "bg-blue-50 border border-blue-200 text-blue-800 text-sm font-bold px-4 py-2 rounded-full shadow-sm flex items-center gap-2";
                
                contenedorContador.classList.remove('hidden');
                setTimeout(() => contenedorContador.classList.remove('opacity-0'), 50);

                tablaBody.innerHTML = '';
                data.folios.forEach(folio => {
                    const tr = document.createElement('tr');
                    tr.className = "bg-blue-50/30 border-b border-white";
                    tr.innerHTML = `
                        <td class="px-4 py-3 font-bold text-blue-800">${folio}</td>
                        <td class="px-4 py-3 text-gray-400 italic">Pendiente...</td>
                        <td class="px-4 py-3 text-gray-400 italic">Pendiente...</td>
                        <td class="px-4 py-3"><span class="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-bold">Listo para Oracle</span></td>
                        <td class="px-4 py-3 text-gray-400 italic">-</td>
                    `;
                    tablaBody.appendChild(tr);
                });

                btnAdjuntar.innerHTML = 'Archivo Listo ✔️';
                btnAdjuntar.classList.replace('text-blue-600', 'text-green-600');
                btnAdjuntar.classList.replace('border-gray-300', 'border-green-300');
                
              
                btnImportar.disabled = false;
                btnLimpiar.disabled = false;

            } catch (error) {
                console.error(error);
                mostrarModal('Error de Conexión', 'Ocurrió un error al conectar con el servidor.', 'Cerrar', 'bg-red-500 hover:bg-red-600', null);
                btnAdjuntar.textContent = '+ Adjuntar Reporte';
                fileInput.value = '';
            }
        });

        async function procesarArchivo() {
            const totalFacturas = parseInt(textoContador.textContent) || 1;
            const formData = new FormData();
            formData.append("file", fileInput.files[0]);

            btnImportar.disabled = true;
            btnAdjuntar.disabled = true;
            btnLimpiar.disabled = true; 
            
            btnImportar.textContent = "Procesando...";
            tablaBody.innerHTML = '<tr><td colspan="5" class="text-center py-12 text-gray-400 font-medium">El proceso se está ejecutando...</td></tr>';
            
            contenedorProgreso.classList.remove('hidden');
            barraProgreso.style.width = '0%';
            barraProgreso.classList.remove('bg-green-500', 'bg-red-500');
            barraProgreso.classList.add('bg-blue-500');
            porcentajeProgreso.textContent = '0%';
            textoProgreso.textContent = 'Consultando con la base de datos de Oracle...';
            textoProgreso.classList.add('animate-pulse');
            textoProgreso.classList.remove('text-red-600', 'text-green-600');
            textoProgreso.classList.add('text-gray-500');

            let progresoActual = 0;
            const tiempoEstimadoSegundos = Math.max(5, (totalFacturas * 0.15)); 
            const tiempoIntervaloMs = (tiempoEstimadoSegundos * 1000) / 95; 

            intervaloProgreso = setInterval(() => {
                if (progresoActual < 95) {
                    const incremento = Math.max(0.1, (95 - progresoActual) / 30);
                    progresoActual += incremento;
                    barraProgreso.style.width = `${progresoActual}%`;
                    porcentajeProgreso.textContent = `${Math.floor(progresoActual)}%`;
                }
            }, tiempoIntervaloMs);

            try {
                const response = await fetch('/procesar', { method: 'POST', body: formData });
                const data = await response.json();
                
                clearInterval(intervaloProgreso);
                barraProgreso.style.width = '100%';
                barraProgreso.classList.replace('bg-blue-500', 'bg-green-500');
                porcentajeProgreso.textContent = '100%';
                textoProgreso.textContent = '¡Consulta finalizada exitosamente!';
                textoProgreso.classList.remove('animate-pulse', 'text-gray-500');
                textoProgreso.classList.add('text-green-600');

                if (!response.ok) throw new Error(data.error);

                tablaBody.innerHTML = '';
                if (data.data.length === 0) {
                    tablaBody.innerHTML = '<tr><td colspan="5" class="text-center py-12 text-red-400">No se encontraron datos.</td></tr>';
                    btnLimpiar.disabled = false;
                    return;
                }

                labelContador.textContent = '✅ Procesadas exitosamente:';
                textoContador.textContent = data.data.length;
                textoContador.className = "text-green-700 text-lg font-bold";
                badgeContador.className = "bg-green-50 border border-green-200 text-green-800 text-sm font-bold px-4 py-2 rounded-full shadow-sm flex items-center gap-2";

                data.data.forEach(row => {
                    let badgeClass = 'bg-gray-100 text-gray-700';
                    if (row['EstatusBusqueda'] === 'Encontrada') badgeClass = 'bg-green-100 text-green-700 border border-green-200';
                    else if (row['EstatusBusqueda'] === 'Monto diferente al del Excel') badgeClass = 'bg-yellow-100 text-yellow-700 border border-yellow-200';
                    else if (row['EstatusBusqueda'] === 'No encontrada') badgeClass = 'bg-red-50 text-red-600 border border-red-100';

                    const tr = document.createElement('tr');
                    tr.className = "hover:bg-gray-50 transition-colors border-b border-gray-100";
                    tr.innerHTML = `
                        <td class="px-4 py-4 font-medium text-gray-900 text-xs">${row['Folio C.F.D.I.'] || '-'}</td>
                        <td class="px-4 py-4 text-gray-600 text-xs">${row['InvoiceNumber'] || '-'}</td>
                        <td class="px-4 py-4 text-xs font-mono text-gray-500">${row['RFC'] || '-'}</td>
                        <td class="px-4 py-4">
                            <span class="px-2 py-1 rounded-md text-xs font-bold ${badgeClass}">
                                ${row['EstatusBusqueda'] || 'No encontrado'}
                            </span>
                        </td>
                        <td class="px-4 py-4 text-gray-600 text-xs">${row['ValidationStatus'] || '-'}</td>
                    `;
                    tablaBody.appendChild(tr);
                });

                btnImportar.textContent = "¡Completado! ✔️";
                btnImportar.classList.replace('bg-green-500', 'bg-blue-600');
                btnDescargar.classList.remove('pointer-events-none', 'opacity-30');
                
                setTimeout(() => {
                    contenedorProgreso.classList.add('hidden');
                }, 3000);

            } catch (error) {
                clearInterval(intervaloProgreso);
                barraProgreso.classList.replace('bg-blue-500', 'bg-red-500');
                textoProgreso.textContent = 'Error en el procesamiento.';
                textoProgreso.classList.remove('animate-pulse', 'text-gray-500');
                textoProgreso.classList.add('text-red-600');
                
                mostrarModal('Error', error.message, 'Cerrar', 'bg-red-500 hover:bg-red-600', null);
                btnImportar.textContent = "Reintentar Importar";
                btnImportar.disabled = false;
            } finally {
                btnAdjuntar.disabled = false;
                btnLimpiar.disabled = false;
            }
        }
    </script>
</body>
</html>
"""