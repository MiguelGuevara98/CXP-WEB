"""Inicio y cierre de sesión."""
from flask import Blueprint, redirect, render_template, request, url_for

from src.config import AMBIENTE_DEFECTO, ambientes_disponibles
from src.oracle.consulta import CredencialesInvalidas, validar_credenciales
from src.web import sesion

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    ambientes = ambientes_disponibles()
    defecto = AMBIENTE_DEFECTO if AMBIENTE_DEFECTO in ambientes else (ambientes[0] if ambientes else "")
    contexto = {"ambientes": ambientes, "ambiente_sel": defecto, "usuario": "", "error": ""}
    if request.method == "GET":
        if sesion.actual():
            return redirect(url_for("carga.inicio"))   # sesión recordada: directo a la app
        return render_template("login.html", **contexto)

    usuario = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    ambiente = request.form.get("ambiente", "")
    contexto.update(usuario=usuario, ambiente_sel=ambiente)
    if ambiente not in ambientes:
        contexto["error"] = "Selecciona un ambiente de Oracle válido."
        return render_template("login.html", **contexto), 400
    ip = request.remote_addr or "-"
    minutos = sesion.login_bloqueado(usuario, ip)
    if minutos:   # no se consulta a Oracle: así no se bloquea la cuenta de Oracle
        contexto["error"] = f"Demasiados intentos fallidos. Espera {minutos} minuto(s) e intenta de nuevo."
        return render_template("login.html", **contexto), 429
    try:
        validar_credenciales(ambiente, usuario, password)
    except CredencialesInvalidas as e:
        if e.rechazo:
            sesion.registrar_fallo(usuario, ip)
        contexto["error"] = str(e)
        return render_template("login.html", **contexto), 401
    sesion.limpiar_fallos(usuario)

    sesion.iniciar(usuario, password, ambiente)
    return redirect(url_for("carga.inicio"))   # la carga de facturas es el proceso principal


@bp.route("/logout", methods=["POST"])
def logout():
    sesion.cerrar()
    return redirect(url_for("auth.login"))
