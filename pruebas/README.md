# CXP-WEB en Cloud Shell: un solo script

Todo está en **`cxp_web.sh`**: actualizar el proyecto, verificarlo, reiniciar la app y las pruebas.
**Cloud Shell nunca se conecta a GitHub**: el código del proyecto va dentro del script.

## 1. Descargarlo en la PC

Abre `pruebas/cxp_web.sh` en GitHub y usa el botón de descarga (⤓ *Download raw file*).
Si ya tenías uno anterior, bórralo antes de Descargas; si Windows lo guarda como `cxp_web (1).sh`,
renómbralo a `cxp_web.sh`.

## 2. Subirlo a Cloud Shell

**⋮ (tres puntos) → Upload** → elige `cxp_web.sh`. Queda en tu carpeta home (`~`).

## 3. Ejecutarlo

```bash
cd ~ && bash cxp_web.sh
```

Hace todo en orden:

1. Guarda un respaldo de la versión actual en `~/cxp-web-respaldo-<fecha>.tar.gz`.
2. Reemplaza `src/`, `run.py`, `requirements.txt` y `.gitignore` (no toca `venv/` ni `.secret_key`).
3. Verifica que estén todos los cambios (deben salir 4 `[OK]`).
4. Pregunta si quieres iniciar la app con la versión nueva. Si respondes **S**, detiene la app
   anterior de este proyecto (si estaba corriendo) y la inicia en esa terminal.

Si el script llegó incompleto, se detiene sin cambiar nada.

## Opciones

| Comando | Qué hace |
|---|---|
| `bash cxp_web.sh` | Actualiza, verifica y ofrece iniciar la app |
| `bash cxp_web.sh verificar` | Solo revisa si el proyecto tiene esta versión y si la app debe reiniciarse |
| `bash cxp_web.sh iniciar` | Detiene la app de este proyecto si está corriendo y la vuelve a iniciar |
| `bash cxp_web.sh probar-xml ~/FACTURA.xml` | Lee XML o zip, muestra descripción, cantidad y unidad, y genera `~/plantilla_prueba.xlsx` |
| `bash cxp_web.sh probar-sitio DEV 90324086 CES911213AU1` | Busca en Oracle los sitios `X90324086` y `GTCES911213AU1` y muestra su proveedor (pide usuario y contraseña; no se guardan) |
| `bash cxp_web.sh ayuda` | Muestra las opciones |

Si el proyecto no está en `~/cxp-web`: `PROYECTO=/ruta/al/proyecto bash cxp_web.sh`.

Para regresar a la versión anterior: `cd ~/cxp-web && tar xzf ~/cxp-web-respaldo-<fecha>.tar.gz`.

## Qué incluye esta versión

- **Descripción limpia:** se quita el código (hash) que algunos emisores pegan al final.
  `DESINSECTACION DE CHASIS a7ebf2a9f246...` queda como `DESINSECTACION DE CHASIS`. A Oracle va limpia.
- **Columna Cantidad** junto a *Primer concepto* en la hoja **Facturas**; columna **Unidad** en la hoja **Conceptos**.
- **Carpetas de Cloud Storage con nombres descriptivos** (aparecen solas con el primer lote nuevo; las
  anteriores no se renombran y conservan la evidencia de los lotes pasados):

  | Antes | Ahora | Qué contiene |
  |---|---|---|
  | `original/` | `1_xml_recibidos/` | Los XML o zip subidos (o traídos de Drive), tal cual llegaron |
  | `plantillas/` | `2_plantillas_capturadas/` | Cada versión del Excel llenado por el colaborador |
  | `fbdi/` | `3_envios_oracle/` | El zip enviado a Oracle y `resultado.json` con la respuesta |

- **Columna `# Colaborador`: a quién se carga la factura.** La app busca el sitio en Oracle y de ahí
  toma el número de proveedor:

  | Se captura | Ejemplo | Sitio que se busca en Oracle |
  |---|---|---|
  | Número de colaborador (sin la X) | `90324086` | `X90324086` |
  | RFC del proveedor (sin GT) | `CES911213AU1` | `GTCES911213AU1` |

  - Distingue sola si es colaborador (solo números) o proveedor (RFC); acepta el prefijo si lo escriben.
  - La columna **Número de proveedor** ya no está en la plantilla: se llena desde Oracle.
  - Si el sitio no existe o está inactivo, esa factura sale **con error** y no se carga; las demás sí.
  - Descarga una plantilla nueva después de actualizar (las anteriores todavía piden *Número de proveedor*).

## Si algo no sale bien

| Síntoma | Qué hacer |
|---|---|
| `verificar` marca `[FALTA]` | El script es una versión anterior: descárgalo de nuevo y corre `bash cxp_web.sh` |
| `verificar` marca `[REINICIAR]` | `bash cxp_web.sh iniciar` |
| No aparecen las carpetas nuevas de Storage | Se crean con el primer lote procesado después de reiniciar |
| "El sitio X... no existe o está inactivo" | Revisar con `probar-sitio`; si falta, darlo de alta en Oracle |
| `probar-sitio` da `NO ENCONTRADO` en un sitio que sí existe, o `HTTP 401/403` | Al usuario de Oracle puede faltarle permiso de consultar proveedores y sitios; mandar la captura |

## Seguridad

- `.secret_key` nunca se sube al repositorio. La clave anterior quedó expuesta en el historial de `main`;
  para generar una nueva: `rm ~/cxp-web/.secret_key` y `bash cxp_web.sh iniciar` (los usuarios vuelven a iniciar sesión).

## Para quien mantiene el repo

`cxp_web.sh` se genera; no se edita a mano. Después de hacer commit de cambios en `src/`:

```bash
python3 herramientas/generar_cxp_web_sh.py
```

La lógica del script está en `herramientas/cxp_web.plantilla.sh`.
