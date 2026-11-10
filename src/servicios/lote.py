"""
Lote de carga: XML -> validación -> plantilla -> facturas listas para Oracle.

Un lote vive en la sesión del usuario (memoria) con esta forma:
    {"id", "usuario", "cfdis": {uuid: cfdi}, "advertencias": {uuid: [...]}, "facturas": [...] | None,
     "vista": {...},            # lo último que mostró la pantalla (para restaurarla al recargar)
     "carga": {...} | None}     # avance de la carga en Oracle (servicios.carga)

Además se guarda en disco (cargas/<lote>/lote.pkl). La plantilla trae el número de lote: si coincide con un
lote guardado, se recupera aunque el servidor se haya reiniciado o se haya recargado la página, y la
plantilla actualiza lo que se enviará a Oracle sin volver a empezar.
"""
import os
import pickle
import re
import secrets
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from src.config import CARPETA_EVIDENCIAS, ZONA_HORARIA, ahora
from src.dominio import catalogos
from src.dominio.captura import COL_PROVEEDOR, a_quien, excluida, prefijo, sitio_oracle, validar_captura
from src.dominio.cfdi import MAX_ARCHIVOS, LimiteExcedido, leer_archivos
from src.dominio.factura import generar_factura
from src.dominio.plantilla import crear_plantilla, leer_plantilla
from src.dominio.validaciones import advertencias_cfdi, validar_cfdi
from src.oracle.facturas import buscar_existentes
from src.oracle.proveedores import buscar_sitios
from src.servicios import ErrorServicio, almacen, drive, historial

ESTADO_LISTA = "Lista para capturar"
ESTADO_LISTA_ADV = "Lista con advertencias"
ESTADO_ERROR = "Con error"
ESTADO_EXCLUIDA = "Excluida"
ESTADO_ORACLE = "Lista para Oracle"
ESTADO_ORACLE_ADV = "Lista para Oracle (con advertencias)"

PATRON_LOTE = re.compile(r"LOTE-\d{8}-\d{6}-[0-9A-F]{4}")


# ---------- Lote guardado en disco ----------
def _ruta(lote_id):
    return Path(CARPETA_EVIDENCIAS) / lote_id / "lote.pkl"


def guardar(lote):
    """Guarda el lote (sin el avance de la carga, que vive solo mientras corre)."""
    ruta = _ruta(lote["id"])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(pickle.dumps({k: v for k, v in lote.items() if k != "carga"}))


def recuperar(lote_id, usuario):
    """Lote guardado con ese número y del mismo usuario, o None."""
    if not lote_id or not PATRON_LOTE.fullmatch(str(lote_id)):   # el número viene del Excel: se valida antes de usarlo
        return None
    try:
        lote = pickle.loads(_ruta(lote_id).read_bytes())
    except (OSError, pickle.UnpicklingError, EOFError):
        return None
    return lote if lote.get("usuario") == usuario else None


def fila_cfdi(c, estado, motivos, advertencias=None):
    """Fila que muestra la tabla de la pantalla."""
    return {
        "uuid": c.get("UUID", ""), "archivo": c.get("archivo", ""), "emisor": c.get("EmisorNombre", ""),
        "rfc": c.get("EmisorRfc", ""), "fecha": (c.get("Fecha") or "")[:10],
        "fecha_timbrado": (c.get("FechaTimbrado") or "")[:10],
        "unidad_negocio": catalogos.FIJOS["BusinessUnit"],
        "total": float(c["Total"]) if c.get("Total") is not None else None, "moneda": c.get("Moneda", ""),
        "conceptos": len(c.get("Conceptos", [])), "estado": estado, "motivos": motivos,
        "advertencias": advertencias or [],
    }


def resumen(filas):
    return dict(Counter(f["estado"] for f in filas))


def procesar_xml(credenciales, archivos, fuente=None):
    """
    credenciales: (ambiente, usuario, password) para revisar duplicados en Oracle (solo lectura).
    archivos: [(nombre, bytes)] (xml, zip o carpeta aplanada).
    fuente: de dónde vienen (control_ejecuciones.fuente); por defecto, subidos desde el portal.
    Devuelve (lote, respuesta_para_la_pantalla).
    """
    if not archivos:
        raise ErrorServicio("No se recibieron archivos.")
    inicio = datetime.now(timezone.utc).isoformat()
    try:
        cfdis, ignorados = leer_archivos(archivos)
    except LimiteExcedido as e:
        raise ErrorServicio(str(e), 413)
    if not cfdis:
        raise ErrorServicio("No se encontraron archivos XML (los PDF y otros archivos se ignoran).")

    vistos, filas, validos = {}, [], []
    for c in cfdis:
        motivos = validar_cfdi(c)
        u = c.get("UUID")
        if u and u in vistos:
            motivos.append(f"UUID repetido (también en {vistos[u]})")
        if u:
            vistos.setdefault(u, c.get("archivo"))
        filas.append((c, motivos))
        if not motivos:
            validos.append(c)

    ambiente, usuario, password = credenciales
    existentes = buscar_existentes(ambiente, usuario, password, [c["UUID"] for c in validos]) if validos else {}

    resultado = []
    for c, motivos in filas:
        ex = existentes.get(c.get("UUID"))
        if isinstance(ex, str) and ex.startswith("ERROR"):
            motivos = motivos + [f"No se pudo verificar en Oracle ({ex[7:]})"]
        elif ex:
            motivos = motivos + [f"Ya existe en Oracle {ambiente}" + (f" (InvoiceId {ex})" if ex != "sí" else "")]
        adv = advertencias_cfdi(c, ahora().year) if not motivos else []
        estado = ESTADO_ERROR if motivos else (ESTADO_LISTA_ADV if adv else ESTADO_LISTA)
        resultado.append(fila_cfdi(c, estado, motivos, adv))

    listos = [(c, r["advertencias"]) for (c, _), r in zip(filas, resultado) if r["estado"] in (ESTADO_LISTA, ESTADO_LISTA_ADV)]
    lote_id = f"LOTE-{ahora():%Y%m%d-%H%M%S}-{secrets.token_hex(2).upper()}"
    respuesta = {"lote": lote_id, "etapa": "xml", "filas": resultado, "resumen": resumen(resultado),
                 "ignorados": len(ignorados), "listos": len(listos)}
    carpeta, plan = almacen.planear(lote_id, archivos)
    for c in cfdis:
        c["_storage_uri"] = plan[c["_origen"]]["storage_uri"] if plan else None
    recibidos = [(c, r) for (c, _), r in zip(filas, resultado)]
    control = {**historial.resumen_archivos(archivos, carpeta, plan),
               "fecha_subida": datetime.now(ZoneInfo(ZONA_HORARIA)).date().isoformat()}
    if fuente:
        control["fuente"] = fuente
    if plan:
        almacen.respaldar(lote_id, plan, archivos, lambda ok: historial.registrar_subida(
            lote_id, ambiente, usuario, control, inicio, plan, recibidos, ok))
    else:
        historial.registrar_subida(lote_id, ambiente, usuario, control, inicio, plan, recibidos, None)
    lote = {"id": lote_id, "usuario": usuario, "ambiente": ambiente, "cfdis": {c["UUID"]: c for c, _ in listos},
            "advertencias": {c["UUID"]: a for c, a in listos}, "facturas": None, "vista": respuesta, "carga": None,
            "storage_uri": (carpeta or {}).get("storage_uri"), "storage_url": (carpeta or {}).get("storage_url"),
            "control_datos": control, "control_version": 1}
    guardar(lote)
    return lote, respuesta


def procesar_drive(credenciales):
    """
    Toma los XML/zip pendientes de la carpeta de Drive del área y los procesa como una subida normal.
    Al terminar se mueven a procesados/<lote>/ en Drive, junto con el PDF de cada factura. Si hay más de lo que cabe en un lote, el resto
    queda en Drive para la siguiente vez (respuesta["pendientes_drive"]).
    """
    if not drive.activa():
        raise ErrorServicio("La carpeta de Drive no está configurada.", 404)
    max_bytes = int(os.environ.get("CXP_MAX_MB", "100")) * 1024 * 1024
    tomados, pendientes, pdfs = drive.tomar(max_bytes, MAX_ARCHIVOS)
    if not tomados:
        raise ErrorServicio("No hay facturas nuevas en la carpeta de Drive.", 404)
    try:
        lote, respuesta = procesar_xml(credenciales, [(a["ruta"], a["contenido"]) for a in tomados], "DRIVE")
    except Exception:
        drive.liberar(tomados)
        raise
    pdfs = drive.pdfs_de(pdfs, tomados, [f["uuid"] for f in respuesta["filas"]])
    drive.mover_a_procesados(lote["id"], tomados + pdfs)
    respuesta.update(drive=len(tomados), pendientes_drive=pendientes)
    return lote, respuesta


def plantilla_del_lote(lote):
    """Bytes del Excel de captura para el lote."""
    if not lote or not lote["cfdis"]:
        raise ErrorServicio("No hay un lote con facturas listas. Sube primero los XML.", 404)
    return crear_plantilla(list(lote["cfdis"].values()), lote["id"], lote.get("advertencias"))


def procesar_plantilla(lote_actual, contenido, capturista, credenciales, nombre="plantilla.xlsx"):
    """
    Lee la plantilla llena y (re)genera las facturas de SU lote: se puede subir las veces que haga falta,
    también después de una carga o de recargar la página / reiniciar el servidor.
    Cada plantilla subida se guarda en Cloud Storage y queda como una versión nueva en control_ejecuciones.
    El sitio de cada fila (X + colaborador o GT + RFC) se busca en Oracle; de ahí sale el número de proveedor.
    Si el sitio no existe, la factura queda con error y no se carga.
    Devuelve (lote, respuesta_para_la_pantalla); quien llama deja ese lote como el activo de la sesión.
    """
    inicio = datetime.now(timezone.utc).isoformat()
    try:
        lote_plantilla, capturas = leer_plantilla(contenido)
    except ValueError as e:   # mensajes ya escritos para el usuario (hoja o columnas faltantes)
        raise ErrorServicio(f"No se pudo leer la plantilla: {e}")
    except Exception:  # noqa: BLE001  (archivo dañado o que no es Excel)
        raise ErrorServicio("El archivo no es una plantilla de Excel válida. Descarga la plantilla del lote, "
                            "llénala y guárdala como .xlsx.")
    if lote_actual and (lote_actual.get("carga") or {}).get("estado") == "en_proceso":
        raise ErrorServicio("Hay una carga en proceso. Espera a que termine para subir la plantilla.", 409)

    if lote_actual and lote_actual["id"] == lote_plantilla:
        lote = lote_actual
    else:
        lote = recuperar(lote_plantilla, capturista)
        if not lote:
            raise ErrorServicio(f'No se encontró el lote {lote_plantilla or "(desconocido)"} de esta plantilla. '
                                f'Sube los XML y descarga una plantilla nueva.')

    # Sitios a buscar en Oracle (una sola consulta por sitio, aunque se repita en varias filas)
    consultas = {}
    for uuid in lote["cfdis"]:
        m = capturas.get(uuid)
        if m is not None and not excluida(m) and not validar_captura(m):
            tipo, valor = a_quien(m)
            consultas[sitio_oracle(m)] = valor if tipo == "proveedor" else None
    ambiente_oracle, usuario, password = credenciales
    sitios = buscar_sitios(ambiente_oracle, usuario, password, consultas)

    resultado, facturas = [], []
    for uuid, c in lote["cfdis"].items():
        m = capturas.get(uuid)
        adv = lote.get("advertencias", {}).get(uuid, [])
        if m is None or excluida(m):
            nota = "Fila eliminada de la plantilla" if m is None else "Marcada 'Incluir = No'"
            resultado.append(fila_cfdi(c, ESTADO_EXCLUIDA, [], [nota] + adv))
            continue
        motivos = validar_captura(m)
        sitio = encontrado = None
        if not motivos:
            sitio = sitio_oracle(m)
            encontrado = sitios.get(sitio)
            if encontrado is None:
                quien = "del colaborador" if a_quien(m)[0] == "colaborador" else "del proveedor"
                motivos = [f"El sitio {sitio} no existe o está inactivo en Oracle {ambiente_oracle}; "
                           f"revisa '# Colaborador' o da de alta el sitio {quien}"]
            elif isinstance(encontrado, str):
                motivos = [f"No se pudo buscar el sitio {sitio} en Oracle ({encontrado[7:]}); intenta de nuevo"]
            else:
                m[COL_PROVEEDOR] = encontrado["SupplierNumber"]
        pre = prefijo(m)
        if motivos:
            fila = fila_cfdi(c, ESTADO_ERROR, motivos, adv)
            if pre:
                fila["uuid"] = f"{pre}-{uuid}"   # con prefijo de prueba se muestra el número con que se cargará
            resultado.append(fila)
            continue
        f = generar_factura(c, m, capturista)
        facturas.append(f)
        fila = fila_cfdi(c, ESTADO_ORACLE_ADV if adv else ESTADO_ORACLE, [], adv)
        fila["uuid"] = f["InvoiceNumber"]   # PREFIJO-UUID si se capturó prefijo de prueba
        fila.update({"colaborador": m["# Colaborador"], "sitio": sitio,
                     "proveedor": f'{encontrado["SupplierNumber"]} {encontrado["Supplier"]}'.strip(),
                     "descripcion": f["Description"],
                     "lineas": len(f["invoiceLines"]), "anticipo": m.get("Anticipo", "")})
        resultado.append(fila)
    extras = [u for u in capturas if u not in lote["cfdis"]]
    respuesta = {"lote": lote["id"], "etapa": "plantilla", "filas": resultado, "resumen": resumen(resultado),
                 "listas": len(facturas), "ignoradas_plantilla": len(extras)}
    numero = (lote.get("plantillas") or 0) + 1
    version = (lote.get("control_version") or 1) + 1
    lote.update(facturas=facturas, vista=respuesta, carga=None,   # datos nuevos: la carga anterior ya no aplica
                plantillas=numero, control_version=version)
    guardar(lote)

    conteo = {"leidos": len(lote["cfdis"]), "validos": len(facturas),
              "rechazados": sum(1 for r in resultado if r["estado"] == ESTADO_ERROR)}
    ambiente = lote.get("ambiente")
    entrada = almacen.planear_plantilla(lote["id"], numero, nombre, contenido)

    def registrar(ok):
        historial.registrar_plantilla(lote, ambiente, capturista, version, inicio, entrada, nombre, contenido,
                                      conteo, ok)

    if entrada:
        almacen.respaldar(lote["id"], [entrada], [(nombre, contenido)], registrar)
    else:
        registrar(None)
    return lote, respuesta
