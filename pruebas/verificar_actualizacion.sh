#!/usr/bin/env bash
# Revisa si el proyecto en Cloud Shell ya tiene la última actualización de la rama actual-cloudshell-2026-11-08.
# No modifica nada y no se conecta a internet.
#
# Uso:  bash verificar_actualizacion.sh [carpeta del proyecto]     (por defecto ~/cxp-web)
set -uo pipefail

PROYECTO="${1:-$HOME/cxp-web}"
OK=0; FALLA=0
bien() { echo "  [OK]    $1"; OK=$((OK+1)); }
mal()  { echo "  [FALTA] $1"; FALLA=$((FALLA+1)); }

echo "Proyecto: $PROYECTO"
if [ ! -d "$PROYECTO/src" ]; then
  echo "No encuentro $PROYECTO/src. Indica la carpeta: bash $0 /ruta/al/proyecto" >&2
  exit 1
fi

if [ -f "$HOME/actualizar_cxp_web.sh" ]; then
  echo "Script de actualización en ~: $(sed -n 2p "$HOME/actualizar_cxp_web.sh" | grep -o 'commit [0-9a-f]*' || echo 'versión desconocida')"
fi
echo

echo "Cambios de esta versión:"
grep -q "def limpiar_descripcion" "$PROYECTO/src/dominio/cfdi.py" 2>/dev/null \
  && bien "Descripción del concepto sin hash del emisor" || mal "Descripción del concepto sin hash del emisor"
grep -q '("Cantidad", 10)' "$PROYECTO/src/dominio/plantilla.py" 2>/dev/null \
  && bien "Columna Cantidad en la plantilla de Excel" || mal "Columna Cantidad en la plantilla de Excel"
grep -q '"1_xml_recibidos"' "$PROYECTO/src/servicios/almacen.py" 2>/dev/null \
  && bien "Carpetas de Storage: 1_xml_recibidos, 2_plantillas_capturadas, 3_envios_oracle" \
  || mal "Carpetas de Storage: 1_xml_recibidos, 2_plantillas_capturadas, 3_envios_oracle"
grep -q "def sitio_oracle" "$PROYECTO/src/dominio/captura.py" 2>/dev/null && [ -f "$PROYECTO/src/oracle/proveedores.py" ] \
  && bien "Sitio en Oracle desde '# Colaborador' (X + colaborador o GT + RFC)" \
  || mal "Sitio en Oracle desde '# Colaborador' (X + colaborador o GT + RFC)"
echo

echo "App:"
PIDS="$(pgrep -f 'python.*run\.py' || true)"
if [ -z "$PIDS" ]; then
  echo "  La app no está corriendo. Iníciala con:"
  echo "    cd $PROYECTO && source venv/bin/activate && python run.py"
else
  ARCHIVO="$PROYECTO/src/servicios/almacen.py"
  INICIO=$(ps -o lstart= -p "$(echo "$PIDS" | head -1)" | xargs -I{} date -d "{}" +%s 2>/dev/null || echo 0)
  CAMBIO=$(stat -c %Y "$ARCHIVO" 2>/dev/null || echo 0)
  if [ "$INICIO" -gt 0 ] && [ "$CAMBIO" -gt "$INICIO" ]; then
    echo "  [REINICIAR] La app arrancó ANTES de la actualización y sigue con el código anterior."
    echo "              En su terminal presiona Ctrl+C y vuelve a iniciarla:"
    echo "              cd $PROYECTO && source venv/bin/activate && python run.py"
    FALLA=$((FALLA+1))
  else
    bien "La app está corriendo con el código actualizado"
  fi
fi
echo

if [ "$FALLA" -eq 0 ]; then
  echo "Todo listo. Las carpetas nuevas de Storage aparecen al procesar el siguiente lote."
else
  echo "Hay $FALLA punto(s) pendiente(s). Si falta algún cambio, vuelve a descargar actualizar_cxp_web.sh"
  echo "en tu PC desde GitHub, súbelo con ⋮ → Upload y ejecuta: bash ~/actualizar_cxp_web.sh $PROYECTO"
fi
