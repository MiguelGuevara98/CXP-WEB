# run.py en la raíz
import os
import socket
import sys

from src.web.app import app

PUERTO = int(os.environ.get("PORT", "8080"))
# Solo este equipo por defecto. En Cloud Shell la Vista previa usa localhost; si no abre, usa HOST=0.0.0.0
HOST = os.environ.get("HOST", "127.0.0.1")

MSG_OCUPADO = """
ERROR: el puerto {p} ya lo está usando otra aplicación (por ejemplo, otro proyecto abierto).
Si CXP-WEB arrancara así, el navegador podría mostrar la otra aplicación.
Opciones:
  - Detén la otra aplicación, o
  - Usa otro puerto:  Windows PowerShell: $env:PORT=8200; python run.py
                      Linux/Cloud Shell:  PORT=8200 python run.py
"""

MSG_NO_ABRE = """
ERROR: no se pudo abrir el puerto {p} ({e}).
En Windows algunos rangos están reservados (ver: netsh interface ipv4 show excludedportrange protocol=tcp).
Prueba otro puerto, por ejemplo PORT=8200.
"""


def puerto_ocupado(puerto):
    """True si otra aplicación ya responde en el puerto (IPv4 o IPv6)."""
    for familia, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(familia, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((host, puerto)) == 0:
                    return True
        except OSError:
            pass
    return False


if __name__ == "__main__":
    # Con debug=True Werkzeug relanza este archivo; la verificación solo se hace en el primer arranque.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        if puerto_ocupado(PUERTO):
            sys.exit(MSG_OCUPADO.format(p=PUERTO))
        print(f"CXP-WEB en http://127.0.0.1:{PUERTO}")
    try:
        # Reinicio automático al guardar un archivo, SIN el depurador interactivo de Werkzeug
        # (ese depurador permite ejecutar código en el servidor desde el navegador).
        app.run(host=HOST, port=PUERTO, debug=True, use_debugger=False)
    except OSError as e:
        sys.exit(MSG_NO_ABRE.format(p=PUERTO, e=e))
