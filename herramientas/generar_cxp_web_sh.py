"""
Genera pruebas/cxp_web.sh: un solo script para Cloud Shell con el código de src/, run.py,
requirements.txt y .gitignore de este commit (tar.gz en base64) más los comandos de
actualizar, verificar, iniciar y probar.

Uso (desde la raíz del repo, con los cambios ya en commit):
    python3 herramientas/generar_cxp_web_sh.py
"""
import base64
import hashlib
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / "herramientas" / "cxp_web.plantilla.sh"
SALIDA = RAIZ / "pruebas" / "cxp_web.sh"


def main():
    paquete = subprocess.run(["git", "archive", "--format=tar.gz", "HEAD", "src", "run.py", "requirements.txt",
                              ".gitignore"], cwd=RAIZ, capture_output=True, check=True).stdout
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                            check=True, text=True).stdout.strip()
    b64 = base64.b64encode(paquete).decode()
    texto = (PLANTILLA.read_text(encoding="utf-8")
             .replace("__SHA__", hashlib.sha256(paquete).hexdigest())
             .replace("__COMMIT__", commit))
    texto += "\n".join(b64[i:i + 76] for i in range(0, len(b64), 76)) + "\n"
    SALIDA.write_text(texto, encoding="utf-8")
    SALIDA.chmod(0o755)
    print(f"{SALIDA.relative_to(RAIZ)} generado (commit {commit}, {len(texto) // 1024} KB)")


if __name__ == "__main__":
    main()
