"""
Registro en BigQuery, dataset CXP_BQ_DATASET (proyecto.dataset). Todas las tablas se unen por id_ejecucion (= lote).

- control_ejecuciones: control estándar de ejecuciones. Cada cambio de una ejecución es una fila nueva
  (version 1 = subida de archivos; después, una por cada plantilla subida y cada carga a Oracle),
  ligada a la anterior por id_registro_anterior.
- archivos_subidos: una fila por archivo original (xml/zip) y por cada plantilla subida, con su ruta en Cloud Storage.
- xml_recibidos: una fila por XML leído, con su resultado de validación y el archivo de Storage que lo contiene.
- historial_cargas: una fila por factura enviada a Oracle (se une con xml_recibidos por lote + uuid).

Si CXP_BQ_DATASET no está definida no se registra nada.
Si falla, el proceso no se afecta: el error queda en el log.
"""
import hashlib
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger(__name__)

DATASET = (os.environ.get("CXP_BQ_DATASET") or "").strip()
TABLA_CONTROL = f"{DATASET}.control_ejecuciones"
TABLA_HISTORIAL = f"{DATASET}.historial_cargas"
TABLA_ARCHIVOS = f"{DATASET}.archivos_subidos"
TABLA_XML = f"{DATASET}.xml_recibidos"

PROCESO = "CXP_CARGA_FACTURAS"
FUENTE = "PORTAL_CXP"
EXITOSO, ERROR = "EXITOSO", "ERROR"
ETAPAS_ORACLE = {"inicio": "UCM", "ucm": "UCM", "loader": "INTERFAZ", "import": "IMPORTACION",
                 "confirmar": "CONFIRMACION"}

_cliente = None


def _bq():
    global _cliente
    if _cliente is None:
        from google.cloud import bigquery
        _cliente = bigquery.Client(project=DATASET.split(".")[0])
    return _cliente


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _utc(texto):
    """Hora local del servidor (isoformat sin zona) a UTC."""
    try:
        return datetime.fromisoformat(texto).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def _insertar(tabla, filas, lote_id):
    if not filas:
        return
    errores = _bq().insert_rows_json(tabla, filas)
    if errores:
        log.error("BigQuery rechazó filas de %s (lote %s): %s", tabla, lote_id, errores)


def resumen_archivos(archivos, carpeta, plan):
    """
    Datos de los archivos subidos para control_ejecuciones (un solo archivo o la carpeta del lote).
    archivos: [(nombre, bytes)]; carpeta/plan: salida de almacen.planear.
    """
    if len(archivos) == 1:
        return {"nombre_archivo": archivos[0][0], "sha256": hashlib.sha256(archivos[0][1]).hexdigest(),
                "ruta_archivo_gcs": plan[0]["storage_uri"] if plan else None}
    huellas = sorted(hashlib.sha256(c).hexdigest() for _, c in archivos)
    return {"nombre_archivo": f"{len(archivos)} archivos",
            "sha256": hashlib.sha256("".join(huellas).encode()).hexdigest(),
            "ruta_archivo_gcs": (carpeta or {}).get("storage_uri")}


def _control(lote_id, version, etapa, datos, inicio, fin, estatus, leidos, validos, rechazados, duplicados,
             mensaje_error=None, etapa_error=None, **extra):
    return {
        "id_ejecucion": lote_id, "proceso": PROCESO, "fuente": datos.get("fuente") or FUENTE,
        "nombre_archivo": datos.get("nombre_archivo"),
        "fecha_inicio": inicio, "fecha_fin": fin,
        "fecha_actualizacion_fuente": datos.get("fecha_subida"),
        "estatus": estatus, "registros_leidos": leidos, "registros_validos": validos,
        "registros_rechazados": rechazados, "registros_duplicados": duplicados,
        "mensaje_error": mensaje_error, "fecha_registro": _ahora(),
        "sha256": datos.get("sha256"), "ruta_archivo_gcs": datos.get("ruta_archivo_gcs"),
        "etapa_error": etapa_error,
        "id_registro": f"{lote_id}-v{version}", "version": version, "etapa": etapa,
        "id_registro_anterior": f"{lote_id}-v{version - 1}" if version > 1 else None,
        **extra,
    }


def _es_duplicado(motivos):
    return any(m.startswith(("Ya existe en Oracle", "UUID repetido")) for m in motivos)


def registrar_subida(lote_id, ambiente, usuario, datos, inicio, plan, recibidos, respaldado):
    """
    Versión 1 de la ejecución: archivos subidos y validados.
    datos: resumen_archivos + fecha_subida; plan: almacen.planear; recibidos: [(cfdi, fila_de_pantalla)];
    respaldado: si Storage quedó bien (None si no hay bucket).
    """
    if not DATASET:
        return
    try:
        ahora = _ahora()
        motivos = [r.get("motivos") or [] for _, r in recibidos]
        duplicados = sum(1 for m in motivos if _es_duplicado(m))
        con_error = sum(1 for m in motivos if m)
        fila = _control(lote_id, 1, "SUBIDA", datos, inicio, ahora,
                        ERROR if respaldado is False else EXITOSO,
                        len(recibidos), len(recibidos) - con_error, con_error - duplicados, duplicados,
                        "No se pudieron guardar los archivos en Cloud Storage" if respaldado is False else None,
                        "STORAGE" if respaldado is False else None, usuario=usuario, ambiente=ambiente)
        _insertar(TABLA_CONTROL, [fila], lote_id)
        _insertar(TABLA_ARCHIVOS, [_fila_archivo(ahora, lote_id, ambiente, usuario, p, respaldado) for p in plan],
                  lote_id)
        _insertar(TABLA_XML, [{
            "fecha_subida": ahora, "lote": lote_id, "ambiente": ambiente, "usuario": usuario,
            "uuid": c.get("UUID"), "archivo_xml": c.get("archivo"), "ruta_en_zip": c.get("_ruta_zip"),
            "storage_uri": c.get("_storage_uri"), "emisor_rfc": c.get("EmisorRfc"), "emisor_nombre": c.get("EmisorNombre"),
            "fecha_factura": (c.get("Fecha") or "")[:10] or None, "total": r.get("total"), "moneda": c.get("Moneda"),
            "estado": r.get("estado"), "motivos": "; ".join(r.get("motivos") or []) or None,
        } for c, r in recibidos], lote_id)
    except Exception:  # noqa: BLE001
        log.exception("No se pudo registrar la subida del lote %s en BigQuery", lote_id)


def _fila_archivo(fecha, lote_id, ambiente, usuario, p, respaldado):
    return {"fecha_subida": fecha, "lote": lote_id, "ambiente": ambiente, "usuario": usuario,
            "archivo": p["archivo"], "tipo": p["tipo"], "tamano_bytes": p["tamano_bytes"], "sha256": p["sha256"],
            "storage_uri": p["storage_uri"], "storage_url": p["storage_url"], "respaldado": bool(respaldado)}


def registrar_plantilla(lote, ambiente, usuario, version, inicio, entrada, nombre, contenido, conteo, respaldado):
    """
    Nueva versión de la ejecución al subir una plantilla llena.
    entrada: almacen.planear_plantilla (None sin bucket); conteo: {leidos, validos, rechazados};
    respaldado: si Storage quedó bien (None si no hay bucket).
    """
    if not DATASET:
        return
    try:
        ahora = _ahora()
        datos = {**(lote.get("control_datos") or {}), "nombre_archivo": nombre,
                 "sha256": hashlib.sha256(contenido).hexdigest(),
                 "ruta_archivo_gcs": (entrada or {}).get("storage_uri")}
        fila = _control(lote["id"], version, "PLANTILLA", datos, inicio, ahora,
                        ERROR if respaldado is False else EXITOSO,
                        conteo["leidos"], conteo["validos"], conteo["rechazados"], 0,
                        "No se pudo guardar la plantilla en Cloud Storage" if respaldado is False else None,
                        "STORAGE" if respaldado is False else None, usuario=usuario, ambiente=ambiente)
        _insertar(TABLA_CONTROL, [fila], lote["id"])
        if entrada:
            _insertar(TABLA_ARCHIVOS, [_fila_archivo(ahora, lote["id"], ambiente, usuario, entrada, respaldado)],
                      lote["id"])
    except Exception:  # noqa: BLE001
        log.exception("No se pudo registrar la plantilla del lote %s en BigQuery", lote.get("id"))


def registrar(lote, ambiente, usuario, archivo, facturas, omitidas, resultado, paso):
    """
    Nueva versión de la ejecución al terminar una carga a Oracle (éxito o error).
    facturas: las que se enviaron (formato de dominio.factura); omitidas: números que ya existían en Oracle;
    resultado: salida de CargaFBDI.ejecutar; paso: último paso alcanzado (para etapa_error).
    Devuelve la versión registrada (se guarda en el lote para encadenar la siguiente).
    """
    version = (lote.get("control_version") or 1) + 1
    if not DATASET:
        return version
    try:
        fin = _ahora()
        por_numero = {r["numero"]: r for r in resultado.get("facturas") or []}
        conteo = [r.get("resultado") for r in por_numero.values()]
        error = resultado.get("error")
        fila = _control(
            lote["id"], version, "CARGA_ORACLE", lote.get("control_datos") or {},
            _utc(resultado.get("inicio")), fin, ERROR if error else EXITOSO,
            len(facturas) + len(omitidas), conteo.count("FACTURA_REGISTRADA"),
            conteo.count("RECHAZO_ORACLE") + conteo.count("SIN_CONFIRMAR"), len(omitidas),
            error, ETAPAS_ORACLE.get(paso, (paso or "").upper() or None) if error else None,
            usuario=usuario, ambiente=ambiente, archivo_fbdi=archivo,
            fecha_contable=resultado.get("fecha_contable"),
            document_id=str(resultado["document_id"]) if resultado.get("document_id") else None,
            job_loader=str(resultado["job_loader"]) if resultado.get("job_loader") else None,
            estado_loader=resultado.get("estado_loader"),
            job_import=str(resultado["job_import"]) if resultado.get("job_import") else None,
            estado_import=resultado.get("estado_import"),
        )
        _insertar(TABLA_CONTROL, [fila], lote["id"])

        filas = []
        for f in facturas:
            r = por_numero.get(f["InvoiceNumber"], {})
            uuid = (f.get("invoiceGdf") or [{}])[0].get("CFDIUniqueIdentifier")
            c = lote["cfdis"].get(uuid) or {}
            filas.append({
                "fecha_carga": fin, "lote": lote["id"], "archivo": archivo, "ambiente": ambiente, "usuario": usuario,
                "numero_factura": f["InvoiceNumber"], "uuid": uuid,
                "archivo_xml": c.get("archivo"), "storage_uri": c.get("_storage_uri"),
                "proveedor": f.get("SupplierNumber"), "importe": f.get("InvoiceAmount"),
                "moneda": f.get("InvoiceCurrency"),
                "resultado": r.get("resultado") or (ERROR if error else None),
                "invoice_id": str(r["InvoiceId"]) if r.get("InvoiceId") else None,
                "detalle": r.get("detalle") or error,
                "job_import": str(resultado["job_import"]) if resultado.get("job_import") else None,
            })
        _insertar(TABLA_HISTORIAL, filas, lote["id"])
    except Exception:  # noqa: BLE001
        log.exception("No se pudo registrar el lote %s en BigQuery", lote.get("id"))
    return version
