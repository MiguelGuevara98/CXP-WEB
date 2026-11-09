"""
Sesión de usuario.

- Los datos de trabajo (lote, resultados) viven en memoria, ligados a un token de la cookie.
- Las credenciales también van en la cookie, CIFRADAS (Fernet, clave derivada de SECRET_KEY), para
  rehacer la sesión si el servidor se reinició: no se pide usuario al recargar ni al reiniciar.
- Un solo proceso: Cloud Shell o Cloud Run con --workers 1.
"""
import base64
import functools
import hashlib
import json
import os
import secrets
import threading
import time
from datetime import timedelta
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from flask import jsonify, redirect, session, url_for

from src.config import ambientes_disponibles

SESION_HORAS = int(os.environ.get("SESION_HORAS", "12"))
# Intentos de login: tras 5 contraseñas rechazadas por Oracle en 15 min se pausa ese usuario, para que la app
# no sirva para adivinar contraseñas ni termine bloqueando la cuenta de Oracle.
MAX_INTENTOS_USUARIO = 5
MAX_INTENTOS_IP = 30
VENTANA_INTENTOS_SEG = 15 * 60
RAIZ = Path(__file__).resolve().parents[2]

_SESIONES = {}
LOCK = threading.Lock()
_FALLIDOS = {}   # ("u", usuario) | ("ip", ip) -> [momentos de intentos fallidos]
_FERNET = None

SESION_EXPIRADA = ({"error": "Tu sesión expiró. Vuelve a iniciar sesión."}, 401)


def clave_secreta():
    """
    SECRET_KEY del entorno o, si no hay, una clave guardada en .secret_key (se crea la primera vez,
    está en .gitignore). Así la sesión sobrevive a los reinicios del servidor.
    """
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    ruta = RAIZ / ".secret_key"
    try:
        clave = ruta.read_text(encoding="ascii").strip()
        if len(clave) >= 32:
            return clave
    except OSError:
        pass
    clave = secrets.token_hex(32)
    try:
        ruta.write_text(clave, encoding="ascii")
        os.chmod(ruta, 0o600)
    except OSError:
        pass   # sin disco escribible: clave solo de este arranque
    return clave


def configurar(app):
    """Configura la cookie de sesión de la app y la clave de cifrado de credenciales."""
    global _FERNET
    app.secret_key = clave_secreta()
    # Nombre propio de cookie: el navegador comparte cookies entre puertos del mismo host, y otros
    # proyectos locales suelen usar el nombre por defecto "session".
    app.config["SESSION_COOKIE_NAME"] = "cxp_web_sesion"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=SESION_HORAS)
    _FERNET = Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"cxp-web/credenciales/" + app.secret_key.encode()).digest()))


def _cifrar(usuario, password, ambiente):
    return _FERNET.encrypt(json.dumps({"u": usuario, "p": password, "a": ambiente}).encode()).decode("ascii")


def _descifrar(texto):
    try:
        d = json.loads(_FERNET.decrypt(texto.encode("ascii"), ttl=SESION_HORAS * 3600))
        return d["u"], d["p"], d["a"]
    except (InvalidToken, ValueError, KeyError, TypeError):
        return None


def actual():
    """Datos de la sesión activa ({usuario, password, ambiente, ...}) o None."""
    token = session.get("token")
    if not token:
        return None
    with LOCK:
        _purgar_vencidas()
        datos = _SESIONES.get(token)
    if datos:
        return datos
    # El servidor se reinició: rehacer la sesión con las credenciales cifradas de la cookie
    texto = session.get("cred") or ""
    cred = _descifrar(texto)
    if not cred or cred[2] not in ambientes_disponibles():
        return None
    creada = _FERNET.extract_timestamp(texto.encode("ascii"))   # la sesión dura SESION_HORAS desde el login
    with LOCK:
        return _SESIONES.setdefault(token, {"usuario": cred[0], "password": cred[1], "ambiente": cred[2],
                                            "resultado": None, "creada": creada})


def _purgar_vencidas():
    """Quita de memoria las sesiones de más de SESION_HORAS (llamar con LOCK tomado)."""
    limite = time.time() - SESION_HORAS * 3600
    for token in [t for t, d in _SESIONES.items() if d.get("creada", 0) < limite]:
        borrar_archivo(_SESIONES.pop(token).get("resultado"))


# ---------- Intentos de login ----------
def _recientes(clave, ahora):
    vigentes = [t for t in _FALLIDOS.get(clave, []) if ahora - t < VENTANA_INTENTOS_SEG]
    if vigentes:
        _FALLIDOS[clave] = vigentes
    else:
        _FALLIDOS.pop(clave, None)
    return vigentes


def login_bloqueado(usuario, ip):
    """Minutos que faltan para poder intentar de nuevo (0 = puede intentar)."""
    ahora = time.time()
    with LOCK:
        por_usuario = _recientes(("u", usuario.lower()), ahora)
        por_ip = _recientes(("ip", ip), ahora)
    bloqueos = [l for l, maximo in ((por_usuario, MAX_INTENTOS_USUARIO), (por_ip, MAX_INTENTOS_IP)) if len(l) >= maximo]
    if not bloqueos:
        return 0
    return max(1, int((min(min(l) for l in bloqueos) + VENTANA_INTENTOS_SEG - ahora) // 60) + 1)


def registrar_fallo(usuario, ip):
    ahora = time.time()
    with LOCK:
        for clave in (("u", usuario.lower()), ("ip", ip)):
            _FALLIDOS.setdefault(clave, []).append(ahora)


def limpiar_fallos(usuario):
    with LOCK:
        _FALLIDOS.pop(("u", usuario.lower()), None)


def credenciales(datos):
    return datos["ambiente"], datos["usuario"], datos["password"]


def iniciar(usuario, password, ambiente):
    cerrar()
    token = secrets.token_urlsafe(32)
    with LOCK:
        _purgar_vencidas()
        _SESIONES[token] = {"usuario": usuario, "password": password, "ambiente": ambiente, "resultado": None,
                            "creada": time.time()}
    session.permanent = True
    session["token"] = token
    session["cred"] = _cifrar(usuario, password, ambiente)


def borrar_archivo(ruta):
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass


def cerrar():
    token = session.pop("token", None)
    if token:
        with LOCK:
            datos = _SESIONES.pop(token, None)
        if datos:
            borrar_archivo(datos.get("resultado"))
    session.clear()


# ---------- Decoradores para las rutas ----------
def requiere_pagina(vista):
    """Página: sin sesión, manda al login. La vista recibe `datos`."""
    @functools.wraps(vista)
    def envoltura(*a, **k):
        datos = actual()
        if not datos:
            return redirect(url_for("auth.login"))
        return vista(datos, *a, **k)
    return envoltura


def requiere_api(vista):
    """Llamada de la pantalla (JSON): sin sesión, responde 401 y la pantalla regresa al login."""
    @functools.wraps(vista)
    def envoltura(*a, **k):
        datos = actual()
        if not datos:
            return jsonify(SESION_EXPIRADA[0]), SESION_EXPIRADA[1]
        return vista(datos, *a, **k)
    return envoltura
