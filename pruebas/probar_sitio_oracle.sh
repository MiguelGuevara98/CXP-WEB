#!/usr/bin/env bash
# Busca sitios de proveedor en Oracle tal como lo hace la app al subir la plantilla (solo lectura).
# Sirve para confirmar que X + colaborador y GT + RFC se encuentran y qué número de proveedor devuelven.
#
# Uso:  bash probar_sitio_oracle.sh <ambiente DEV|PROD> <colaborador o RFC> [más...]
#   Ej: bash probar_sitio_oracle.sh DEV 90324086 CES911213AU1
# Pide usuario y contraseña de Oracle (la contraseña no se muestra ni se guarda).
set -euo pipefail

PROYECTO="${PROYECTO:-$HOME/cxp-web}"
if [ "$#" -lt 2 ]; then
  echo "Uso: bash $0 <DEV|PROD> <colaborador o RFC> [más...]" >&2
  exit 1
fi
if [ ! -f "$PROYECTO/src/oracle/proveedores.py" ]; then
  echo "El proyecto en $PROYECTO no tiene la búsqueda de sitios. Corre primero actualizar_cxp_web.sh" >&2
  exit 1
fi
AMBIENTE="$1"; shift
read -rp "Usuario de Oracle: " ORA_USUARIO
read -rsp "Contraseña de Oracle: " ORA_PASSWORD; echo
export ORA_USUARIO ORA_PASSWORD

PY="$PROYECTO/venv/bin/python"
[ -x "$PY" ] || PY="python3"
cd "$PROYECTO"
"$PY" - "$AMBIENTE" "$@" <<'PYEOF'
import os, sys
from src.dominio import captura as cp
from src.oracle.proveedores import buscar_sitios

ambiente, valores = sys.argv[1].upper(), sys.argv[2:]
consultas, filas = {}, []
for v in valores:
    m = {cp.COL_COLABORADOR: v, cp.COL_SUBIR_A: "Cuentas por Pagar X"}
    tipo, valor = cp.a_quien(m)
    if tipo is None:
        filas.append((v, None, "No es número de colaborador ni RFC"))
        continue
    sitio = cp.sitio_oracle(m)
    consultas[sitio] = valor if tipo == "proveedor" else None
    filas.append((v, sitio, tipo))

res = buscar_sitios(ambiente, os.environ["ORA_USUARIO"], os.environ["ORA_PASSWORD"], consultas)
print(f"\nAmbiente {ambiente}")
for v, sitio, info in filas:
    if sitio is None:
        print(f"  {v:<16} ERROR: {info}")
        continue
    r = res.get(sitio)
    if r is None:
        print(f"  {v:<16} sitio {sitio:<18} NO ENCONTRADO (o inactivo)")
    elif isinstance(r, str):
        print(f"  {v:<16} sitio {sitio:<18} {r}")
    else:
        print(f"  {v:<16} sitio {sitio:<18} proveedor {r['SupplierNumber']} {r['Supplier']}  (encontrado por: {r['fuente']})")
PYEOF
