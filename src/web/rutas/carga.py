"""
Pantalla "Cargar facturas" (proceso principal).

1) POST /carga/xml             sube zip/carpeta/XML -> lee y valida CFDI, busca duplicados en Oracle
   POST /carga/drive           lo mismo, con los XML/zip de la carpeta de Drive del área
2) GET  /carga/plantilla       descarga la plantilla Excel del lote
3) POST /carga/plantilla       sube la plantilla llena -> genera/actualiza las facturas (también recupera
                               el lote por el número que trae la plantilla)
   GET  /carga/lote            estado del lote para restaurar la pantalla al recargar
4) POST /carga/enviar          carga en Oracle por FBDI (solo DEV); avance en GET /carga/estado
"""
import io

from flask import Blueprint, jsonify, render_template, request, send_file

from src.oracle.permisos import AMBIENTES_CARGA
from src.servicios import ErrorServicio
from src.servicios import carga as srv_carga
from src.servicios import drive
from src.servicios import lote as srv_lote
from src.web import sesion
from src.web.sesion import requiere_api, requiere_pagina

bp = Blueprint("carga", __name__)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@bp.errorhandler(ErrorServicio)
def _error_servicio(e):
    return jsonify({"error": e.mensaje}), e.codigo


def _texto(e):
    """Para descargas (enlaces normales): el error va como texto."""
    return e.mensaje, e.codigo


@bp.route("/carga")
@bp.route("/")          # dirección principal (url_for da "/")
@requiere_pagina
def inicio(datos):
    return render_template("carga.html", username=datos["usuario"], ambiente=datos["ambiente"], pagina="carga",
                           ambientes_carga=sorted(AMBIENTES_CARGA), drive_activo=drive.activa())


@bp.route("/carga/xml", methods=["POST"])
@requiere_api
def subir_xml(datos):
    archivos = [(f.filename or "archivo", f.read()) for f in request.files.getlist("archivos")]
    lote, respuesta = srv_lote.procesar_xml(sesion.credenciales(datos), archivos)
    with sesion.LOCK:
        datos["lote"] = lote
    return jsonify(respuesta)


@bp.route("/carga/drive", methods=["POST"])
@requiere_api
def traer_drive(datos):
    lote, respuesta = srv_lote.procesar_drive(sesion.credenciales(datos))
    with sesion.LOCK:
        datos["lote"] = lote
    return jsonify(respuesta)


@bp.route("/carga/plantilla", methods=["GET"])
def descargar_plantilla():
    datos = sesion.actual()
    try:
        lote = datos and datos.get("lote")
        contenido = srv_lote.plantilla_del_lote(lote)
    except ErrorServicio as e:
        return _texto(e)
    return send_file(io.BytesIO(contenido), as_attachment=True, download_name=f"Plantilla_{lote['id']}.xlsx", mimetype=XLSX)


@bp.route("/carga/plantilla", methods=["POST"])
@requiere_api
def subir_plantilla(datos):
    if "plantilla" not in request.files:
        raise ErrorServicio("No se recibió la plantilla.")
    lote, respuesta = srv_lote.procesar_plantilla(
        datos.get("lote"), request.files["plantilla"].read(), datos["usuario"], sesion.credenciales(datos),
        request.files["plantilla"].filename or "plantilla.xlsx")
    with sesion.LOCK:
        datos["lote"] = lote   # puede ser un lote recuperado por el número de la plantilla
    return jsonify(respuesta)


@bp.route("/carga/lote")
@requiere_api
def lote_actual(datos):
    """Lo último que mostró la pantalla y el avance de la carga, para restaurarla al recargar la página."""
    lote = datos.get("lote")
    if not lote:
        return jsonify({"lote": None})
    return jsonify({**lote.get("vista", {}), "carga": srv_carga.estado_carga(lote)})


@bp.route("/carga/limpiar", methods=["POST"])
@requiere_api
def limpiar(datos):
    with sesion.LOCK:
        datos["lote"] = None
    return jsonify({"status": "ok"})


@bp.route("/carga/enviar", methods=["POST"])
@requiere_api
def enviar(datos):
    """Arranca la carga por FBDI en segundo plano (solo DEV)."""
    return jsonify(srv_carga.iniciar_carga(sesion.credenciales(datos), datos.get("lote")))


@bp.route("/carga/estado")
@requiere_api
def estado(datos):
    return jsonify(srv_carga.estado_carga(datos.get("lote")))
