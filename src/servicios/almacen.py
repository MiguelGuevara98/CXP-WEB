"""
Cloud Storage del proyecto (gs://CXP_GCS_BUCKET/CXP_GCS_PREFIJO/):
- original/AAAA/MM/DD/<lote>/<archivo>: los archivos que sube el usuario (XML, zip o carpeta), en segundo plano.
- plantillas/AAAA/MM/DD/<lote>/plantilla_vN_HHMMSS.xlsx: cada plantilla llena que sube el colaborador.
- fbdi/AAAA/MM/DD/<lote>/: el zip FBDI enviado a Oracle y resultado.json de cada carga.
Si CXP_GCS_BUCKET no está definida no se respalda nada.
Si falla, el proceso sigue y el error queda en el log.
"""
import hashlib
import logging
import os
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import ZONA_HORARIA

log = logging.getLogger(__name__)

BUCKET = (os.environ.get("CXP_GCS_BUCKET") or "").strip()
PREFIJO = (os.environ.get("CXP_GCS_PREFIJO") or "cxp_facturas").strip().strip("/")

_cliente = None


def _gcs():
    global _cliente
    if _cliente is None:
        from google.cloud import storage
        _cliente = storage.Client()
    return _cliente


def _nombre_seguro(nombre):
    partes = [p for p in re.split(r"[\\/]+", nombre or "") if p and p not in (".", "..")]
    return "/".join(re.sub(r"[^\w.\- ]", "_", p) for p in partes) or "archivo"


def _consola(ruta):
    return f"https://console.cloud.google.com/storage/browser/{BUCKET}/{ruta}"


def _carpeta_dia(tipo, lote_id):
    hoy = datetime.now(ZoneInfo(ZONA_HORARIA))
    return f"{PREFIJO}/{tipo}/{hoy:%Y/%m/%d}/{lote_id}/"


def guardar_evidencia(lote_id, carpeta_local):
    """
    Sube a Storage los archivos de la carga (zip FBDI y resultado.json) y borra la copia local.
    Devuelve {nombre_archivo: gs://...}; vacío si no hay bucket o si falla (la copia local se conserva).
    """
    local = Path(carpeta_local)
    if not BUCKET or not local.is_dir():
        return {}
    ruta = _carpeta_dia("fbdi", lote_id)
    try:
        bucket = _gcs().bucket(BUCKET)
        subidos = {}
        for f in sorted(local.iterdir()):
            if f.is_file():
                bucket.blob(ruta + f.name).upload_from_filename(str(f))
                subidos[f.name] = f"gs://{BUCKET}/{ruta}{f.name}"
        shutil.rmtree(local, ignore_errors=True)
        return subidos
    except Exception:  # noqa: BLE001
        log.exception("No se pudo guardar la evidencia del lote %s en Cloud Storage", lote_id)
        return {}


def _entrada(objeto, nombre, contenido):
    n = objeto.rsplit("/", 1)[-1]
    return {
        "archivo": nombre, "objeto": objeto, "tipo": n.rpartition(".")[2].lower() if "." in n else "",
        "tamano_bytes": len(contenido), "sha256": hashlib.sha256(contenido).hexdigest(),
        "storage_uri": f"gs://{BUCKET}/{objeto}", "storage_url": _consola(objeto),
    }


def planear_plantilla(lote_id, numero, nombre, contenido):
    """Dónde queda la plantilla número `numero` del lote (mismo formato que planear); None si no hay bucket."""
    if not BUCKET:
        return None
    hora = datetime.now(ZoneInfo(ZONA_HORARIA))
    entrada = _entrada(f"{_carpeta_dia('plantillas', lote_id)}plantilla_v{numero}_{hora:%H%M%S}.xlsx", nombre, contenido)
    entrada["tipo"] = "plantilla"
    return entrada


def planear(lote_id, archivos):
    """
    Decide dónde queda cada archivo subido, en el mismo orden de archivos [(nombre, bytes)].
    Devuelve (carpeta, lista) con carpeta = {storage_uri, storage_url} del lote y, por archivo,
    {archivo, objeto, tipo, tamano_bytes, sha256, storage_uri, storage_url}. Sin bucket devuelve (None, []).
    """
    if not BUCKET:
        return None, []
    ruta = _carpeta_dia("original", lote_id)
    usados, plan = set(), []
    for nombre, contenido in archivos:
        n = base = _nombre_seguro(nombre)
        i = 1
        while n in usados:
            i += 1
            raiz, punto, ext = base.rpartition(".")
            n = f"{raiz}_{i}.{ext}" if punto else f"{base}_{i}"
        usados.add(n)
        plan.append(_entrada(ruta + n, nombre, contenido))
    return {"storage_uri": f"gs://{BUCKET}/{ruta}", "storage_url": _consola(ruta)}, plan


def respaldar(lote_id, plan, archivos, al_terminar=None):
    """Sube los archivos según el plan, en segundo plano; luego llama al_terminar(subidos: bool)."""
    if not plan:
        return

    def trabajo():
        ok = False
        try:
            bucket = _gcs().bucket(BUCKET)
            for p, (_, contenido) in zip(plan, archivos):
                bucket.blob(p["objeto"]).upload_from_string(contenido)
            ok = True
            log.info("Lote %s respaldado en Cloud Storage (%d archivos)", lote_id, len(plan))
        except Exception:  # noqa: BLE001
            log.exception("No se pudo respaldar el lote %s en Cloud Storage", lote_id)
        if al_terminar:
            al_terminar(ok)

    threading.Thread(target=trabajo, daemon=True).start()
