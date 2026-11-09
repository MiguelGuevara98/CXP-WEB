#!/usr/bin/env bash
# Prueba la lectura de CFDI (XML) sin levantar la app ni conectarse a Oracle/Google.
# Muestra, por cada concepto: descripción limpia (sin hash del emisor), cantidad y unidad.
# También genera una plantilla de Excel de prueba para revisar la columna "Cantidad".
#
# Uso:  bash probar_lectura_xml.sh <archivo.xml | archivo.zip> [más archivos...]
#       Proyecto por defecto en ~/cxp-web (cámbialo con: PROYECTO=/ruta bash probar_lectura_xml.sh ...)
set -euo pipefail

PROYECTO="${PROYECTO:-$HOME/cxp-web}"
if [ "$#" -eq 0 ]; then
  echo "Uso: bash $0 <archivo.xml | archivo.zip> [más archivos...]" >&2
  exit 1
fi
if [ ! -d "$PROYECTO/src" ]; then
  echo "No encuentro el proyecto en $PROYECTO (falta src/). Usa: PROYECTO=/ruta bash $0 ..." >&2
  exit 1
fi

PY="$PROYECTO/venv/bin/python"
[ -x "$PY" ] || PY="python3"

SALIDA="$HOME/plantilla_prueba.xlsx"
cd "$PROYECTO"
"$PY" - "$SALIDA" "$@" <<'PYEOF'
import os, sys
from src.dominio import cfdi, plantilla

salida, rutas = sys.argv[1], sys.argv[2:]
archivos = [(r, open(r, "rb").read()) for r in rutas]
cfdis, ignorados = cfdi.leer_archivos(archivos)
for n in ignorados:
    print(f"(ignorado, no es XML) {n}")

validos = []
for c in cfdis:
    if c.get("_error"):
        print(f"\nERROR {c['archivo']}: {c['_error']}")
        continue
    validos.append(c)
    print(f"\n{os.path.basename(c['archivo'])}  UUID {c['UUID']}  Total {c['Total']}")
    for con in c["Conceptos"]:
        print(f"  {con['n']}. Descripción: {con['Descripcion']}")
        print(f"     Cantidad:    {'' if con['Cantidad'] is None else format(con['Cantidad'].normalize(), 'f')}   Unidad: {con['Unidad'] or con['ClaveUnidad']}")
        if con["DescripcionXml"] != con["Descripcion"]:
            print(f"     (en el XML venía: {con['DescripcionXml'][:60]}...)")

if validos:
    data = plantilla.crear_plantilla(validos, "PRUEBA")
    data = data if isinstance(data, bytes) else data.getvalue()
    open(salida, "wb").write(data)
    print(f"\nPlantilla de prueba: {salida}  (descárgala con: cloudshell download {salida})")
PYEOF
