#!/usr/bin/env bash
# CXP-WEB: todo en un solo script para Cloud Shell (rama actual-cloudshell-2026-11-08, commit __COMMIT__).
# No se conecta a GitHub: el código del proyecto viene dentro de este archivo.
#
# Uso:
#   bash cxp_web.sh                         Actualiza el proyecto, verifica y ofrece reiniciar la app
#   bash cxp_web.sh verificar               Solo revisa si el proyecto ya tiene esta versión
#   bash cxp_web.sh iniciar                 Detiene la app si está corriendo y la vuelve a iniciar
#   bash cxp_web.sh probar-xml  ARCHIVO...  Lee XML/zip y muestra descripción, cantidad y unidad (+ plantilla de prueba)
#   bash cxp_web.sh probar-sitio DEV|PROD COLABORADOR_O_RFC...
#                                           Busca el sitio en Oracle (X + colaborador o GT + RFC) y su proveedor
#
# Carpeta del proyecto: ~/cxp-web (cámbiala con: PROYECTO=/ruta bash cxp_web.sh ...)
#
# Qué incluye esta versión:
#   - Descripción del concepto sin el código (hash) que algunos emisores pegan al final.
#   - Columna "Cantidad" en la plantilla de Excel y "Unidad" en la hoja Conceptos.
#   - Carpetas de Cloud Storage: 1_xml_recibidos, 2_plantillas_capturadas, 3_envios_oracle.
#   - '# Colaborador': número de colaborador (sitio X + número) o RFC del proveedor (sitio GT + RFC);
#     el sitio se busca en Oracle y de ahí sale el número de proveedor.
set -uo pipefail

PROYECTO="${PROYECTO:-$HOME/cxp-web}"
SHA_ESPERADO="__SHA__"
VERSION="__COMMIT__"

die() { echo "ERROR: $*" >&2; exit 1; }
python_proyecto() { if [ -x "$PROYECTO/venv/bin/python" ]; then echo "$PROYECTO/venv/bin/python"; else echo python3; fi; }
# PIDs de la app de ESTE proyecto (python ... run.py con la carpeta del proyecto como directorio de trabajo)
pids_app() {
  local pid real; real="$(realpath "$PROYECTO" 2>/dev/null)"
  for pid in $(pgrep -f 'python[0-9.]* .*run\.py' 2>/dev/null); do
    [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$real" ] && echo "$pid"
  done
}
requiere_proyecto() { [ -d "$PROYECTO/src" ] || die "No encuentro el proyecto en $PROYECTO (falta src/). Usa: PROYECTO=/ruta bash $0 ..."; }

# ---------------------------------------------------------------- actualizar
actualizar() {
  [ -d "$PROYECTO" ] || die "No existe la carpeta $PROYECTO. Usa: PROYECTO=/ruta bash $0"
  local tmp; tmp="$(mktemp -d)"
  sed -n '/^__PAQUETE__$/,$p' "$0" | sed '1d' | base64 -d > "$tmp/paquete.tgz" 2>/dev/null
  echo "$SHA_ESPERADO  $tmp/paquete.tgz" | sha256sum -c --quiet - 2>/dev/null \
    || { rm -rf "$tmp"; die "El script está dañado o incompleto; vuelve a descargarlo."; }

  local respaldo="$HOME/cxp-web-respaldo-$(date +%Y%m%d-%H%M%S).tar.gz"
  ( cd "$PROYECTO" && tar czf "$respaldo" $(ls -d src run.py requirements.txt .gitignore 2>/dev/null) ) \
    || { rm -rf "$tmp"; die "No se pudo crear el respaldo; no se cambió nada."; }
  echo "Respaldo de la versión anterior: $respaldo"

  tar xzf "$tmp/paquete.tgz" -C "$PROYECTO" || { rm -rf "$tmp"; die "No se pudo descomprimir el código."; }
  find "$PROYECTO/src" -name __pycache__ -type d -prune -exec rm -rf {} +
  rm -rf "$tmp"
  echo "Proyecto actualizado a la versión $VERSION en $PROYECTO (venv/ y .secret_key no se tocaron)."
  echo "Para regresar a la anterior: cd $PROYECTO && tar xzf $respaldo"
}

# ---------------------------------------------------------------- verificar
APP_DESACTUALIZADA=0
verificar() {
  requiere_proyecto
  local falla=0
  bien() { echo "  [OK]    $1"; }
  mal()  { echo "  [FALTA] $1"; falla=$((falla+1)); }
  echo; echo "Versión del proyecto en $PROYECTO:"
  grep -q "def limpiar_descripcion" "$PROYECTO/src/dominio/cfdi.py" 2>/dev/null \
    && bien "Descripción del concepto sin hash del emisor" || mal "Descripción del concepto sin hash del emisor"
  grep -q '("Cantidad", 10)' "$PROYECTO/src/dominio/plantilla.py" 2>/dev/null \
    && bien "Columna Cantidad en la plantilla de Excel" || mal "Columna Cantidad en la plantilla de Excel"
  grep -q '"1_xml_recibidos"' "$PROYECTO/src/servicios/almacen.py" 2>/dev/null \
    && bien "Carpetas de Storage: 1_xml_recibidos, 2_plantillas_capturadas, 3_envios_oracle" \
    || mal "Carpetas de Storage: 1_xml_recibidos, 2_plantillas_capturadas, 3_envios_oracle"
  { grep -q "def sitio_oracle" "$PROYECTO/src/dominio/captura.py" 2>/dev/null && [ -f "$PROYECTO/src/oracle/proveedores.py" ]; } \
    && bien "Sitio en Oracle desde '# Colaborador' (X + colaborador o GT + RFC)" \
    || mal "Sitio en Oracle desde '# Colaborador' (X + colaborador o GT + RFC)"

  echo; echo "App:"
  local pid; pid="$(pids_app | head -1)"
  if [ -z "$pid" ]; then
    echo "  No está corriendo."
    APP_DESACTUALIZADA=1
  else
    local inicio cambio
    inicio=$(date -d "$(ps -o lstart= -p "$pid")" +%s 2>/dev/null || echo 0)
    cambio=$(find "$PROYECTO/src" -name '*.py' -printf '%T@\n' 2>/dev/null | sort -n | tail -1 | cut -d. -f1)
    if [ "$inicio" -gt 0 ] && [ "${cambio:-0}" -gt "$inicio" ]; then
      echo "  [REINICIAR] Arrancó antes de la actualización y sigue con el código anterior."
      APP_DESACTUALIZADA=1
    else
      bien "Corriendo con el código actualizado"
    fi
  fi
  echo
  if [ "$falla" -gt 0 ]; then
    echo "Faltan $falla cambio(s): corre  bash $0  para actualizar."
    return 1
  fi
  return 0
}

# ---------------------------------------------------------------- iniciar
iniciar() {
  requiere_proyecto
  local pids; pids="$(pids_app)"
  if [ -n "$pids" ]; then
    echo "Deteniendo la app anterior..."
    kill $pids 2>/dev/null; sleep 2; kill -9 $pids 2>/dev/null || true
  fi
  cd "$PROYECTO" || die "No se pudo entrar a $PROYECTO"
  [ -f venv/bin/activate ] && . venv/bin/activate
  echo "Iniciando la app (Ctrl+C para detenerla)..."
  exec python run.py
}

# ---------------------------------------------------------------- probar-xml
probar_xml() {
  requiere_proyecto
  [ "$#" -gt 0 ] || die "Uso: bash $0 probar-xml ARCHIVO.xml|ARCHIVO.zip [más...]"
  local rutas=() r
  for r in "$@"; do [ -f "$r" ] || die "No existe el archivo $r"; rutas+=("$(realpath "$r")"); done
  ( cd "$PROYECTO" && "$(python_proyecto)" - "$HOME/plantilla_prueba.xlsx" "${rutas[@]}" <<'PYEOF'
import os, sys
from src.dominio import cfdi, plantilla
salida, rutas = sys.argv[1], sys.argv[2:]
cfdis, ignorados = cfdi.leer_archivos([(r, open(r, "rb").read()) for r in rutas])
for n in ignorados:
    print(f"(ignorado, no es XML) {n}")
validos = []
for c in cfdis:
    if c.get("_error"):
        print(f"\nERROR {os.path.basename(c['archivo'])}: {c['_error']}")
        continue
    validos.append(c)
    print(f"\n{os.path.basename(c['archivo'])}  UUID {c['UUID']}  Total {c['Total']}")
    for con in c["Conceptos"]:
        cant = "" if con["Cantidad"] is None else format(con["Cantidad"].normalize(), "f")
        print(f"  {con['n']}. Descripción: {con['Descripcion']}")
        print(f"     Cantidad:    {cant}   Unidad: {con['Unidad'] or con['ClaveUnidad']}")
        if con["DescripcionXml"] != con["Descripcion"]:
            print(f"     (en el XML venía: {con['DescripcionXml'][:60]}...)")
if validos:
    data = plantilla.crear_plantilla(validos, "PRUEBA")
    open(salida, "wb").write(data if isinstance(data, bytes) else data.getvalue())
    print(f"\nPlantilla de prueba: {salida}  (descárgala con: cloudshell download {salida})")
PYEOF
  )
}

# ---------------------------------------------------------------- probar-sitio
probar_sitio() {
  requiere_proyecto
  [ "$#" -ge 2 ] || die "Uso: bash $0 probar-sitio DEV|PROD COLABORADOR_O_RFC [más...]"
  [ -f "$PROYECTO/src/oracle/proveedores.py" ] || die "El proyecto no tiene la búsqueda de sitios; corre primero: bash $0"
  local ambiente="$1"; shift
  read -rp "Usuario de Oracle: " ORA_USUARIO
  read -rsp "Contraseña de Oracle: " ORA_PASSWORD; echo
  export ORA_USUARIO ORA_PASSWORD
  ( cd "$PROYECTO" && "$(python_proyecto)" - "$ambiente" "$@" <<'PYEOF'
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
  )
}

# ---------------------------------------------------------------- principal
case "${1:-actualizar}" in
  actualizar)
    actualizar
    verificar || exit 1
    if [ "$APP_DESACTUALIZADA" -eq 1 ]; then
      read -rp "¿Iniciar la app ahora con la versión nueva? [S/n] " r
      case "${r:-S}" in [nN]*) echo "Cuando quieras: bash $0 iniciar" ;; *) iniciar ;; esac
    fi
    ;;
  verificar)    verificar ;;
  iniciar)      iniciar ;;
  probar-xml)   shift; probar_xml "$@" ;;
  probar-sitio) shift; probar_sitio "$@" ;;
  -h|--help|ayuda) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "Opción desconocida '$1'. Usa: bash $0 ayuda" ;;
esac
exit $?

# Código del proyecto (tar.gz en base64). No editar debajo de esta línea.
__PAQUETE__
