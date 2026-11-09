"""
Carga del lote en Oracle por FBDI, en segundo plano.

El avance queda en lote["carga"] = {estado: en_proceso|terminado|error, paso, mensajes, archivo,
omitidas_existentes, resultado}; la pantalla lo consulta con estado_carga().
Solo se permite en los ambientes de oracle.permisos (DEV).
"""
import json
import logging
import os
import threading

from src.config import CARPETA_EVIDENCIAS, ahora
from src.dominio.fbdi import generar_zip
from src.oracle.carga_fbdi import CargaFBDI
from src.oracle.facturas import buscar_existentes
from src.oracle.permisos import CargaNoPermitida, verificar_ambiente_carga
from src.servicios import ErrorServicio, almacen, historial
from src.servicios import lote as srv_lote

log = logging.getLogger(__name__)
_LOCK = threading.Lock()   # protege lote["carga"] entre el hilo de la carga y la pantalla


def hoy():
    """Fecha de hoy en México (fecha contable de la carga), sin importar la zona horaria del servidor."""
    return ahora().date()


def iniciar_carga(credenciales, lote):
    """
    Revisa duplicados en Oracle, genera el FBDI y arranca la carga en un hilo.
    La fecha contable es siempre el día de la carga (hora de México); el prefijo de prueba viene de la plantilla.
    credenciales: (ambiente, usuario, password). Devuelve la respuesta para la pantalla.
    """
    ambiente, usuario, password = credenciales
    if not lote or not lote.get("facturas"):
        raise ErrorServicio("No hay facturas listas para cargar.")
    try:
        verificar_ambiente_carga(ambiente)
    except CargaNoPermitida as e:
        raise ErrorServicio(str(e), 403)
    if (lote.get("carga") or {}).get("estado") == "en_proceso":
        raise ErrorServicio("Ya hay una carga en proceso para este lote.", 409)

    # Evitar duplicados: ¿ya existe en Oracle alguna factura con el mismo número (con prefijo)?
    numeros = [f["InvoiceNumber"] for f in lote["facturas"]]
    existentes = buscar_existentes(ambiente, usuario, password, numeros)
    errores = [n for n in numeros if isinstance(existentes.get(n), str) and existentes[n].startswith("ERROR")]
    if errores:
        raise ErrorServicio(f"No se pudo verificar en Oracle si ya existen ({existentes[errores[0]][7:]}).", 502)
    ya = [n for n in numeros if existentes.get(n)]
    facturas = [f for f, n in zip(lote["facturas"], numeros) if not existentes.get(n)]
    if not facturas:
        raise ErrorServicio(f"Todas las facturas ya existen en Oracle {ambiente} con ese número. "
                            f"Para probar de nuevo, usa otro prefijo de prueba en la plantilla.", 409)
    origenes = {f["InvoiceSource"] for f in facturas}
    if len(origenes) != 1:
        raise ErrorServicio("Todas las facturas del lote deben tener el mismo origen (SOURCE).")

    fecha = hoy()
    nombre_zip, contenido, _ = generar_zip(facturas, fecha)
    carpeta = os.path.join(CARPETA_EVIDENCIAS, lote["id"], nombre_zip[:-4])
    estado = {"estado": "en_proceso", "paso": "inicio", "mensajes": [], "archivo": nombre_zip,
              "omitidas_existentes": ya, "resultado": None}
    with _LOCK:
        lote["carga"] = estado

    def aviso(paso, mensaje, _datos):
        with _LOCK:
            estado["paso"] = paso
            if not estado["mensajes"] or estado["mensajes"][-1]["texto"] != mensaje:
                estado["mensajes"].append({"hora": ahora().strftime("%H:%M:%S"), "texto": mensaje})

    def trabajo():
        try:
            res = CargaFBDI(ambiente, usuario, password, aviso).ejecutar(
                nombre_zip, contenido, [f["InvoiceNumber"] for f in facturas], fecha, origenes.pop(), carpeta)
        except Exception:  # noqa: BLE001
            log.exception("Error inesperado en la carga del lote %s", lote["id"])
            res = {"error": "Error inesperado durante la carga. Revisa el log del servidor.", "facturas": []}
        with _LOCK:
            estado["resultado"] = res
            estado["estado"] = "error" if res.get("error") else "terminado"
            if not res.get("error"):
                estado["paso"] = "fin"   # con error se conserva el paso donde falló
        evidencia = almacen.guardar_evidencia(lote["id"], carpeta)
        version = historial.registrar(lote, ambiente, usuario, evidencia.get(nombre_zip, nombre_zip),
                                      facturas, ya, res, estado["paso"])
        with _LOCK:
            lote["control_version"] = version
        try:
            srv_lote.guardar(lote)
        except Exception:  # noqa: BLE001
            log.exception("No se pudo guardar el lote %s", lote["id"])

    threading.Thread(target=trabajo, daemon=True).start()
    return {"status": "iniciada", "archivo": nombre_zip, "facturas": len(facturas), "omitidas_existentes": ya}


def estado_carga(lote):
    """Copia del avance de la carga (para responder a la pantalla sin compartir el dict)."""
    with _LOCK:
        return json.loads(json.dumps((lote or {}).get("carga") or {"estado": "sin_carga"}))
