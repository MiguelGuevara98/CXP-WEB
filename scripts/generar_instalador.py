"""
Genera dist/instalar_cxp_web.sh: un único script de bash que recrea este proyecto
completo (carpetas y archivos) en Cloud Shell o en cualquier Linux.

Uso (desde la raíz del repo):
    python scripts/generar_instalador.py

Incluye todos los archivos versionados o pendientes de versionar que no estén en
.gitignore (git ls-files -co --exclude-standard). Los archivos de texto van
legibles en heredocs; los binarios, en base64. Al final verifica cada archivo con sha256.
"""
import base64
import hashlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "dist" / "instalar_cxp_web.sh"
EXCLUIR_PREFIJOS = ("dist/",)
NOMBRE_DEFECTO = "cxp-web"


def listar_archivos():
    salida = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=RAIZ, capture_output=True, check=True,
    ).stdout.decode("utf-8")
    rutas = sorted(p for p in salida.split("\0") if p and not p.startswith(EXCLUIR_PREFIJOS))
    return [p for p in rutas if (RAIZ / p).is_file()]


def comillas_bash(texto):
    return "'" + texto.replace("'", "'\"'\"'") + "'"


def bloque_archivo(ruta, contenido):
    destino = comillas_bash(ruta)
    try:
        texto = contenido.decode("utf-8")
        es_texto = "\0" not in texto
    except UnicodeDecodeError:
        es_texto = False

    if es_texto:
        texto = texto.replace("\r\n", "\n")
        delimitador = "__CXP_FIN__"
        n = 0
        while delimitador in texto:
            n += 1
            delimitador = f"__CXP_FIN_{n}__"
        # printf '%s' conserva exactamente el contenido (incluido si no termina en \n)
        sin_salto_final = not texto.endswith("\n")
        cuerpo = texto if not sin_salto_final else texto + "\n"
        datos = cuerpo.encode("utf-8")
        cmd = f"escribir_texto {destino} {'1' if sin_salto_final else '0'} <<'{delimitador}'\n{cuerpo}{delimitador}\n"
        final = texto.encode("utf-8")
    else:
        b64 = base64.encodebytes(contenido).decode("ascii")
        cmd = f"escribir_binario {destino} <<'__CXP_B64__'\n{b64}__CXP_B64__\n"
        final = contenido
    return cmd, hashlib.sha256(final).hexdigest()


def main():
    archivos = listar_archivos()
    if not archivos:
        sys.exit("No se encontraron archivos.")

    bloques, sumas = [], []
    for ruta in archivos:
        cmd, sha = bloque_archivo(ruta, (RAIZ / ruta).read_bytes())
        bloques.append(f"# ---- {ruta}\n{cmd}")
        sumas.append(f"{sha}  {ruta}")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
                            capture_output=True, text=True).stdout.strip() or "sin-commit"
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    script = f"""#!/usr/bin/env bash
# =====================================================================
#  Instalador de CXP-WEB  (generado {fecha}, base commit {commit})
#  Recrea el proyecto completo: {len(archivos)} archivos.
#
#  Uso en Cloud Shell:
#    bash instalar_cxp_web.sh [carpeta_destino]
#  Por defecto crea ./{NOMBRE_DEFECTO}
# =====================================================================
set -euo pipefail

DESTINO="${{1:-{NOMBRE_DEFECTO}}}"
if [ -e "$DESTINO" ]; then
  echo "ERROR: '$DESTINO' ya existe. Bórrala o indica otra carpeta: bash $0 otra_carpeta" >&2
  exit 1
fi
mkdir -p "$DESTINO"
cd "$DESTINO"

escribir_texto() {{  # $1 ruta, $2 = 1 si el archivo original no termina en salto de línea
  mkdir -p "$(dirname "$1")"
  if [ "$2" = "1" ]; then
    local c; c="$(cat; printf x)"; c="${{c%x}}"; printf '%s' "${{c%$'\\n'}}" > "$1"
  else
    cat > "$1"
  fi
}}
escribir_binario() {{
  mkdir -p "$(dirname "$1")"
  base64 -d > "$1"
}}

echo "Creando proyecto en: $(pwd)"

{chr(10).join(bloques)}
# ---- Verificación de integridad
echo "Verificando archivos..."
sha256sum --quiet -c <<'__CXP_SHA__'
{chr(10).join(sumas)}
__CXP_SHA__

echo ""
echo "Listo: {len(archivos)} archivos creados en $(pwd)"
echo ""
echo "Siguientes pasos sugeridos:"
echo "  cd $DESTINO"
echo "  # Probar localmente en Cloud Shell:"
echo "  python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt && python run.py"
echo "  # Desplegar en Cloud Run (proyecto activo de gcloud):"
echo "  gcloud run deploy cxp-web --source . --region us-central1 --allow-unauthenticated"
"""
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_bytes(script.encode("utf-8"))  # siempre LF
    print(f"Generado: {SALIDA}  ({len(archivos)} archivos, {SALIDA.stat().st_size / 1024:.1f} KB)")
    for ruta in archivos:
        print(f"  - {ruta}")


if __name__ == "__main__":
    main()
