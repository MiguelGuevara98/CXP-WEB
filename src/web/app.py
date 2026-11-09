"""
Aplicación web (Flask): configura la sesión y registra las pantallas.

    auth      /login, /logout
    carga     /  y /carga/...      (proceso principal: cargar facturas desde XML)
    consulta  /consulta, /previsualizar, /procesar, /descargar
"""
import os

from flask import Flask, jsonify, request

from src.web import sesion
from src.web.rutas.auth import bp as bp_auth
from src.web.rutas.carga import bp as bp_carga
from src.web.rutas.consulta import bp as bp_consulta


def crear_app():
    app = Flask(__name__)   # templates/ y static/ junto a este archivo
    sesion.configurar(app)
    # Tope por petición (evita que un archivo enorme agote la memoria). Ajustable con CXP_MAX_MB.
    max_mb = int(os.environ.get("CXP_MAX_MB", "100"))
    app.config["MAX_CONTENT_LENGTH"] = max_mb * 1024 * 1024

    @app.errorhandler(413)
    def _muy_grande(_e):
        mensaje = f"Los archivos pasan de {max_mb} MB. Divide la carga en varios lotes."
        return (jsonify({"error": mensaje}), 413) if request.method == "POST" else (mensaje, 413)

    @app.after_request
    def _cabeceras_seguridad(resp):
        resp.headers.setdefault("X-Frame-Options", "DENY")              # nadie puede meter la app en un marco
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")    # el navegador respeta el tipo de archivo
        resp.headers.setdefault("Referrer-Policy", "same-origin")       # no se filtran URLs a otros sitios
        if not request.path.startswith("/static/"):
            resp.headers.setdefault("Cache-Control", "no-store")        # datos de facturas y sesión: sin caché
        return resp

    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_carga)
    app.register_blueprint(bp_consulta)
    return app


app = crear_app()
