# CXP-WEB — Cuentas por Pagar

Aplicación web interna del área de **Cuentas por Pagar (CxP)**.

> **Estado actual:** solo existe la **interfaz (UI)**. Se eliminó la lógica anterior de conciliación contra Oracle y queda pendiente implementar el nuevo procesamiento. Los endpoints que usa el frontend existen como esqueleto y responden `501`.

- **Stack:** Python 3.10 · Flask · Tailwind (CDN) · gunicorn
- **Despliegue:** Docker → Artifact Registry → Cloud Run (`cxp-web`, `us-central1`) mediante Cloud Build

---

## 1. Estructura del proyecto

```
CXP-WEB/
├── run.py                 # Punto de entrada (gunicorn usa run:app)
├── requirements.txt       # Flask, gunicorn
├── Dockerfile
├── cloudbuild.yaml        # Pipeline build → push → deploy a Cloud Run
└── data/
    └── main/
        ├── app.py         # Rutas Flask (vistas + endpoints pendientes)
        ├── vistas.py      # Plantillas HTML (HEAD_COMUN, LOGIN_HTML, INDEX_HTML)
        └── static/
            ├── icons/     # Íconos SVG de Coltrane
            └── img/       # Logos Coppel y spot de la sección
```

## 2. Interfaz y sistema de diseño

La UI sigue el sistema de diseño **Coltrane [Bubble]** de Coppel. La referencia completa está en la carpeta `Ui Kit GCD Argentina/` (foundations, componentes y pantallas de referencia). Esa carpeta **no se versiona** (está en `.gitignore`), así que hay que conseguirla aparte.

- **Tipografía:** Poppins (Google Fonts).
- **Tokens:** `HEAD_COMUN` en `vistas.py` declara las variables CSS de "8. Tokens - CSS" (colores interactive/text/bg/border/brand, `rounded-sm` de 8px, `rounded-md` de 16px y `rounded-full`) y tres niveles de profundidad (default, hover y float). Tailwind (CDN) está configurado con esos mismos colores para el layout.
- **Componentes CSS:** `.btn` (`-primary`, `-secondary`, `-tertiary`, `-error`), `.btn-icon`, `.input`, `.card`, `.badge-*` (success, warning, error, info, neutral), `.tabla`, `.pag-btn` y `.spinner`.
- **Íconos:** los SVG del kit se aplican como máscara (`<span class="icon" style="--src: url(...)">`), así toman el color del texto (`currentColor`). Para agregar uno, cópialo de `Ui Kit GCD Argentina/5. Icons-Spots/Svg/icons/` a `data/main/static/icons/`.
- **Logos:** en el kit los nombres están invertidos: el archivo "Blue" trae las letras en blanco y el "White" en azul. En `static/img/` ya están corregidos: `coppel-blue.svg` tiene letras azules (para fondo blanco) y `coppel-white.svg` letras blancas (para fondo azul).

Pantallas:

- **Login** (`/login`): pantalla dividida, inspirada en "Inicio de sesión - IDC". A la izquierda, el logo, el nombre del sistema y el formulario; a la derecha, un panel azul con los círculos de la marca. Por ahora el login **no valida nada**: solo guarda `username` en la sesión.
- **Monitor** (`/`):
  - navbar blanca (hamburguesa, logo, nombre del sistema y usuario)
  - menú lateral colapsable con el elemento activo en azul
  - tarjeta de encabezado de sección
  - tarjeta con la tabla: título, contador "1-10 de N resultados", botones **Limpiar**, **Adjuntar reporte** y **Procesar reporte**, barra de progreso, paginación de 10 filas y **Descargar resultados**
  - modales con ícono de estatus, cierre con X, Esc o clic fuera, y una sola acción principal (según la guía de Coltrane)

## 3. Contrato entre UI y backend

El JavaScript de `vistas.py` ya llama a estas rutas. La nueva lógica debe respetar este formato, o bien hay que ajustar el JS.

| Método | Ruta | Estado | Request | Respuesta esperada por la UI |
|---|---|---|---|---|
| GET | `/` | ✅ | — | HTML del monitor (redirige a `/login` sin sesión) |
| GET/POST | `/login` | ✅ | form `username`, `password` | Redirige a `/` |
| GET | `/logout` | ✅ | — | Limpia la sesión |
| POST | `/previsualizar` | ⏳ 501 | `multipart` campo `file` | `{"folios": [str, ...], "total": int}` o `{"error": str}` (4xx) |
| POST | `/procesar` | ⏳ 501 | `multipart` campo `file` | `{"status": "success", "data": [fila, ...]}` o `{"error": str}` (4xx/5xx) |
| GET | `/descargar` | ⏳ 404 | — | Archivo para descargar |

Claves de cada `fila` que lee hoy la tabla después de `/procesar` (las mapea `procesarArchivo()` en `vistas.py`): `Folio C.F.D.I.`, `InvoiceNumber`, `RFC`, `EstatusBusqueda` y `ValidationStatus`. El color del badge lo decide `tonoResultado()`: `Encontrada` → success, `Monto diferente al del Excel` → warning, `No encontrada` → error, cualquier otro valor → neutral. Todo esto viene del proceso anterior y seguramente habrá que cambiarlo.

## 4. Ejecución local

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
python run.py                  # http://localhost:8080  (debug=True, autoreload)
```

Con Docker:

```bash
docker build -t cxp-web .
docker run -p 8080:8080 -e PORT=8080 cxp-web
```

## 5. Despliegue

> **El despliegue automático está desactivado.** Un push ya no actualiza Cloud Run.

Con cada push, el trigger de Cloud Build (configurado en la consola de GCP, no versionado en el repo) ejecuta `cloudbuild.yaml`, que **solo** hace dos pasos:

1. `docker build` → `us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/cxp-web:$COMMIT_SHA`
2. `docker push` de esa imagen a Artifact Registry

Los logs van solo a Cloud Logging.

**Despliegue manual** de un commit ya construido (desde Cloud Shell o con `gcloud` autenticado):

```bash
gcloud run deploy cxp-web \
  --image us-central1-docker.pkg.dev/<PROJECT_ID>/cloud-run-source-deploy/cxp-web:<COMMIT_SHA_COMPLETO> \
  --region us-central1 --platform managed
```

Para volver al despliegue automático, agrega de nuevo ese paso `gcloud run deploy` al final de `cloudbuild.yaml`. Si en cambio quieres que un push no construya nada, desactiva el trigger en *Cloud Build → Activadores*.

---

## 6. Pendientes

### Nuevo procesamiento
- [ ] Definir la nueva lógica y crear su módulo (por ejemplo `data/logica/`).
- [ ] Implementar `/previsualizar`, `/procesar` y `/descargar` en `app.py`.
- [ ] Ajustar en `vistas.py` las columnas de la tabla (Folio CFDI, Factura, RFC, Resultado, Validación) y el mapeo de `procesarArchivo()` a los datos del nuevo proceso.
- [ ] Agregar a `requirements.txt` las dependencias nuevas, con versión fija.

### UI
- [x] Rediseño con Coltrane [Bubble]: login, navbar, menú lateral, tabla, paginación, badges y modales.
- [x] La tabla se construye con `textContent` (ya no con `innerHTML`), lo que evita inyectar HTML desde los datos del archivo.
- [x] La barra de progreso revisa `response.ok` antes de marcar el proceso como exitoso.
- [ ] La barra de progreso sigue siendo una simulación por tiempo, no refleja el avance real.
- [x] `Ui Kit GCD Argentina/` (57 MB) queda fuera del repo vía `.gitignore`; los recursos que usa la app están copiados en `static/`. Quien necesite el kit lo debe pedir aparte.

### Seguridad / infraestructura
- [ ] El login no autentica. Definir el mecanismo real (IAP, OAuth de Google u otro).
- [ ] La `secret_key` está fija en `app.py`. Moverla a una variable de entorno o a Secret Manager.
- [ ] Agregar `.dockerignore` (hoy `COPY . .` incluye `.git`, `__pycache__`, etc.).
- [ ] Si el nuevo proceso genera archivos, guardarlos en Cloud Storage y no en disco local: Cloud Run usa varias instancias y su filesystem vive en memoria.
- [ ] Si el proceso tarda, considerar el timeout de las peticiones en Cloud Run o usar un job en segundo plano.
