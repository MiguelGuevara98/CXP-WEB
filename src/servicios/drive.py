"""
Carpeta de Google Drive del área (CXP_DRIVE_CARPETA: enlace o id de la carpeta).

"Traer de Drive" toma los .xml y .zip que haya en la carpeta (también en subcarpetas), los procesa como una
subida normal y después los mueve a procesados/<lote>/ dentro de la misma carpeta para que no se vuelvan a tomar.
Con ellos se mueve el PDF de cada factura: el que se llama igual que su XML (en la misma carpeta) o el que
trae el UUID en el nombre. Los PDF no se leen ni se suben a Storage.
Usa la cuenta de Google con que corre la app (credenciales por defecto con permiso de Drive).
Los detalles de los errores quedan en el log; al usuario solo le llega un mensaje simple.
"""
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor

from src.servicios import ErrorServicio

log = logging.getLogger(__name__)

API = "https://www.googleapis.com/drive/v3/files"
TIPO_CARPETA = "application/vnd.google-apps.folder"
PROCESADOS = "procesados"
HILOS = 8


def _id_carpeta(valor):
    valor = (valor or "").strip()
    m = re.search(r"/folders/([\w-]+)", valor) or re.search(r"[?&]id=([\w-]+)", valor)
    return m.group(1) if m else valor


CARPETA = _id_carpeta(os.environ.get("CXP_DRIVE_CARPETA"))

_sesion = None
_lock = threading.Lock()
_tomados = set()   # archivos que se están procesando o moviendo: no se vuelven a tomar mientras tanto


def activa():
    return bool(CARPETA)


def _http():
    global _sesion
    if _sesion is None:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        credenciales, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
        _sesion = AuthorizedSession(credenciales)
    return _sesion


def _pedir(metodo, url, **kw):
    params = {"supportsAllDrives": "true", **kw.pop("params", {})}
    r = _http().request(metodo, url, params=params, timeout=120, **kw)
    r.raise_for_status()
    return r


def _hijos(carpeta):
    q = f"'{carpeta}' in parents and trashed = false"
    token = None
    while True:
        params = {"q": q, "pageSize": 1000, "includeItemsFromAllDrives": "true",
                  "fields": "nextPageToken, files(id, name, mimeType, size)"}
        if token:
            params["pageToken"] = token
        datos = _pedir("GET", API, params=params).json()
        yield from datos.get("files", [])
        token = datos.get("nextPageToken")
        if not token:
            return


def _listar(carpeta, ruta=""):
    """XML, zip y PDF de la carpeta y sus subcarpetas (sin entrar a procesados/ de la raíz)."""
    for f in _hijos(carpeta):
        if f["mimeType"] == TIPO_CARPETA:
            if not (ruta == "" and f["name"].lower() == PROCESADOS):
                yield from _listar(f["id"], f"{ruta}{f['name']}/")
        elif re.search(r"\.(xml|zip|pdf)$", f["name"], re.I):
            yield {"id": f["id"], "padre": carpeta, "ruta": ruta + f["name"], "tamano": int(f.get("size") or 0)}


def _es_pdf(a):
    return a["ruta"].lower().endswith(".pdf")


def _base(a):
    return a["padre"], a["ruta"].rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()


def _falla(accion):
    log.exception("Google Drive: no se pudo %s (carpeta %s)", accion, CARPETA)
    return ErrorServicio("No se pudo leer la carpeta de Drive. Intenta de nuevo en unos minutos; "
                         "si sigue pasando, avisa al administrador.", 502)


def tomar(max_bytes, max_archivos):
    """
    Aparta y descarga los archivos pendientes de la carpeta, hasta max_bytes / max_archivos por lote.
    Devuelve (tomados, pendientes, pdfs): tomados = [{"id", "padre", "ruta", "tamano", "contenido"}],
    pendientes = cuántos XML/zip quedaron en Drive para la siguiente vez y pdfs = los PDF de la carpeta
    (sin descargar), para elegir con pdfs_de() los que acompañan al lote.
    """
    with _lock:
        try:
            todos = [a for a in _listar(CARPETA) if a["id"] not in _tomados]
        except Exception:  # noqa: BLE001
            raise _falla("listar")
        pdfs = [a for a in todos if _es_pdf(a)]
        disponibles = [a for a in todos if not _es_pdf(a)]
        lote, total = [], 0
        for a in sorted(disponibles, key=lambda a: a["ruta"].lower()):
            if lote and (total + a["tamano"] > max_bytes or len(lote) >= max_archivos):
                break
            lote.append(a)
            total += a["tamano"]
        _tomados.update(a["id"] for a in lote)

    def bajar(a):
        a["contenido"] = _pedir("GET", f"{API}/{a['id']}", params={"alt": "media"}).content
        return a

    try:
        with ThreadPoolExecutor(HILOS) as pool:
            lote = list(pool.map(bajar, lote))
    except Exception:  # noqa: BLE001
        liberar(lote)
        raise _falla("descargar")
    return lote, len(disponibles) - len(lote), pdfs


def pdfs_de(pdfs, tomados, uuids):
    """PDF que acompañan a los archivos tomados: mismo nombre que un XML de la misma carpeta, o con un UUID en el nombre."""
    nombres = {_base(a) for a in tomados}
    uuids = [u.lower() for u in uuids if u]
    elegidos = [p for p in pdfs if _base(p) in nombres or any(u in p["ruta"].lower() for u in uuids)]
    with _lock:
        elegidos = [p for p in elegidos if p["id"] not in _tomados]
        _tomados.update(p["id"] for p in elegidos)
    return elegidos


def liberar(archivos):
    with _lock:
        _tomados.difference_update(a["id"] for a in archivos)


def _carpeta(nombre, padre):
    """Id de la subcarpeta `nombre` dentro de `padre`; la crea si no existe."""
    nombre_q = nombre.replace("\\", "\\\\").replace("'", "\\'")
    q = f"'{padre}' in parents and name = '{nombre_q}' and mimeType = '{TIPO_CARPETA}' and trashed = false"
    existentes = _pedir("GET", API, params={"q": q, "includeItemsFromAllDrives": "true", "fields": "files(id)"})
    archivos = existentes.json().get("files", [])
    if archivos:
        return archivos[0]["id"]
    return _pedir("POST", API, params={"fields": "id"},
                  json={"name": nombre, "mimeType": TIPO_CARPETA, "parents": [padre]}).json()["id"]


def mover_a_procesados(lote_id, archivos):
    """En segundo plano: mueve los archivos a procesados/<lote>/. Si falla, quedan donde estaban (y en el log)."""
    if not archivos:
        return

    def trabajo():
        try:
            with _lock:   # evita que dos lotes al mismo tiempo creen dos carpetas procesados/
                destino = _carpeta(lote_id, _carpeta(PROCESADOS, CARPETA))

            def mover(a):
                _pedir("PATCH", f"{API}/{a['id']}",
                       params={"addParents": destino, "removeParents": a["padre"], "fields": "id"})

            with ThreadPoolExecutor(HILOS) as pool:
                list(pool.map(mover, archivos))
            log.info("Google Drive: %d archivos del lote %s movidos a %s/", len(archivos), lote_id, PROCESADOS)
        except Exception:  # noqa: BLE001
            log.exception("Google Drive: no se pudieron mover a %s/ los archivos del lote %s", PROCESADOS, lote_id)
        finally:
            liberar(archivos)

    threading.Thread(target=trabajo, daemon=True).start()
