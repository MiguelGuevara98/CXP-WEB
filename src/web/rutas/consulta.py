"""
Pantalla "Consultar facturas": cruza un reporte de facturas contra Oracle (solo lectura).
"""
import io
import logging
import os
import re
import tempfile

import pandas as pd
from flask import Blueprint, jsonify, render_template, request, send_file

from src.oracle.consulta import ProcesadorOracle
from src.web import sesion
from src.web.sesion import requiere_api, requiere_pagina

bp = Blueprint("consulta", __name__)
log = logging.getLogger(__name__)

PATRON_CFDI = r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"


@bp.route("/consulta")
@requiere_pagina
def inicio(datos):
    return render_template("consulta.html", username=datos["usuario"], ambiente=datos["ambiente"], pagina="consulta")


@bp.route("/previsualizar", methods=["POST"])
@requiere_api
def previsualizar(_datos):
    if "file" not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    raw_bytes = request.files["file"].read()
    texto_crudo = raw_bytes.replace(b"\x00", b"").decode("iso-8859-1", errors="ignore")
    folios = re.findall(PATRON_CFDI, texto_crudo)

    if not folios:
        try:
            df = pd.read_excel(io.BytesIO(raw_bytes))
            for col in df.columns:
                if "c.f.d.i" in str(col).lower() or "folio" in str(col).lower():
                    folios = df[col].dropna().astype(str).tolist()
                    break
        except Exception:  # noqa: BLE001
            pass

    if folios:
        finales = list(dict.fromkeys(f.upper().strip() for f in folios))
        return jsonify({"folios": finales[:50], "total": len(finales)})

    if "<frameset" in texto_crudo.lower():
        return jsonify({"error": 'Este archivo es un "cascarón". Sube el .xlsx que guardaste o el "sheet001.htm".'}), 400
    return jsonify({"error": "No se encontraron folios CFDI en este archivo."}), 400


@bp.route("/procesar", methods=["POST"])
@requiere_api
def procesar(datos):
    if "file" not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400

    file = request.files["file"]
    fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename or "")[1])
    os.close(fd)
    file.save(temp_path)
    try:
        procesador = ProcesadorOracle(temp_path, datos["ambiente"], datos["usuario"], datos["password"])
        filas, ruta = procesador.ejecutar_cruce()
        with sesion.LOCK:
            sesion.borrar_archivo(datos.get("resultado"))
            datos["resultado"] = ruta
        return jsonify({"status": "success", "data": filas})
    except ValueError as e:   # mensajes escritos para el usuario (p. ej. falta una columna)
        return jsonify({"error": str(e)}), 400
    except Exception:  # noqa: BLE001
        log.exception("Error al consultar el reporte en Oracle")
        return jsonify({"error": "No se pudo completar la consulta en Oracle. Intenta de nuevo; si persiste, avisa a soporte."}), 500
    finally:
        sesion.borrar_archivo(temp_path)


@bp.route("/descargar")
def descargar():
    datos = sesion.actual()
    ruta = datos and datos.get("resultado")
    if ruta and os.path.exists(ruta):
        return send_file(ruta, as_attachment=True, download_name=f"Reporte_Oracle_{datos['ambiente']}.xlsx")
    return "No hay archivo para descargar", 404
