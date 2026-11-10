# Pruebas y actualización de CXP-WEB en Cloud Shell

Esta carpeta trae dos scripts para actualizar y probar el proyecto en Cloud Shell.
**Cloud Shell nunca se conecta a GitHub.** Los archivos se descargan en la PC desde el
navegador y se suben a Cloud Shell con el menú **⋮ → Upload**.

| Archivo | Para qué sirve |
|---|---|
| `actualizar_cxp_web.sh` | Actualiza el proyecto en Cloud Shell a la versión de esta rama. Trae todo el código adentro, no descarga nada. |
| `verificar_actualizacion.sh` | Revisa si el proyecto ya tiene esta versión y si la app necesita reiniciarse. No modifica nada. |
| `probar_sitio_oracle.sh` | Busca en Oracle el sitio de un colaborador o proveedor, igual que la app, y muestra el número de proveedor que encuentra. Solo lectura. |
| `probar_lectura_xml.sh` | Lee uno o varios XML/zip y muestra descripción, cantidad y unidad de cada concepto. Genera una plantilla de Excel de prueba. No se conecta a Oracle ni a Google. |

## Qué incluye esta versión

- La descripción del concepto se limpia de los códigos (hash) que algunos emisores pegan al final.
  Ejemplo: `DESINSECTACION DE CHASIS a7ebf2a9f246...` queda como `DESINSECTACION DE CHASIS`.
- La plantilla de Excel (hoja **Facturas**) tiene la columna **Cantidad** junto a **Primer concepto**.
- La hoja **Conceptos** tiene la columna **Unidad**.
- A Oracle se envía la descripción limpia.
- Las carpetas de Cloud Storage tienen nombres que dicen qué contienen y en qué paso se generan:

  | Antes | Ahora | Qué contiene |
  |---|---|---|
  | `original/` | `1_xml_recibidos/` | Los XML, zip o carpeta que sube el usuario (o que se traen de Drive), tal cual llegaron. |
  | `plantillas/` | `2_plantillas_capturadas/` | Cada versión del Excel ya llenado que sube el colaborador (`plantilla_v1_...`, `plantilla_v2_...`). |
  | `fbdi/` | `3_envios_oracle/` | El zip FBDI enviado a Oracle y `resultado.json` con la respuesta. |

  Lo que ya estaba guardado con los nombres anteriores se queda donde está; los lotes nuevos usan los nombres nuevos.
- **Columna `# Colaborador`: a quién se carga la factura.** La app busca el sitio en Oracle y de ahí toma
  el número de proveedor:

  | Se captura | Ejemplo | Sitio que se busca en Oracle |
  |---|---|---|
  | Número de colaborador (sin la X) | `90324086` | `X90324086` |
  | RFC del proveedor (sin GT) | `CES911213AU1` | `GTCES911213AU1` |

  - La app distingue sola si es colaborador (solo números) o proveedor (RFC). Si escriben el prefijo por
    error (`X90324086` o `GTCES911213AU1`) también lo acepta.
  - La columna **Número de proveedor** ya no está en la plantilla: se llena con el proveedor dueño del sitio.
  - Si el sitio no existe o está inactivo en Oracle, la factura sale **con error** y no se carga;
    las demás del lote sí.
  - En la pantalla, cada factura lista para Oracle muestra el sitio y el proveedor encontrado.

## Paso 1. Descargar los scripts en la PC

En el navegador, abre cada archivo de esta carpeta en GitHub y usa el botón de descarga
(⤓ *Download raw file*):

- `pruebas/actualizar_cxp_web.sh`
- `pruebas/verificar_actualizacion.sh`
- `pruebas/probar_sitio_oracle.sh`
- `pruebas/probar_lectura_xml.sh`

Si ya habías descargado una versión anterior, **bórrala primero de Descargas**. Si Windows guarda el
nuevo como `actualizar_cxp_web (1).sh`, renómbralo a `actualizar_cxp_web.sh` antes de subirlo.

## Paso 2. Subirlos a Cloud Shell

En Cloud Shell: **⋮ (tres puntos) → Upload**, elige los archivos y haz clic en **Upload**.
Quedan en la carpeta home (`~`).

## Paso 3. Actualizar el proyecto

Confirma que subiste la versión más reciente del script (la línea debe terminar con el commit
indicado en la primera línea de `actualizar_cxp_web.sh` en GitHub):

```bash
head -2 ~/actualizar_cxp_web.sh
```

Ejecútalo:

```bash
cd ~ && bash actualizar_cxp_web.sh ~/cxp-web
```

- Guarda antes un respaldo en `~/cxp-web-respaldo-<fecha>.tar.gz`.
- Reemplaza `src/`, `run.py`, `requirements.txt` y `.gitignore`.
- No toca `venv/` ni `.secret_key`.

Para regresar a la versión anterior (si hiciera falta):

```bash
cd ~/cxp-web && tar xzf ~/cxp-web-respaldo-<fecha>.tar.gz
```

## Paso 4. Verificar la actualización

```bash
cd ~ && bash verificar_actualizacion.sh ~/cxp-web
```

Salida esperada:

```
Cambios de esta versión:
  [OK]    Descripción del concepto sin hash del emisor
  [OK]    Columna Cantidad en la plantilla de Excel
  [OK]    Carpetas de Storage: 1_xml_recibidos, 2_plantillas_capturadas, 3_envios_oracle
```

Si aparece `[FALTA]`, el script que subiste era una versión anterior: vuelve al paso 1.
Si aparece `[REINICIAR]`, la app sigue con el código anterior: ve al paso 6.

## Paso 5. Probar la lectura de XML

Sube uno o varios XML (o un zip) a Cloud Shell con **⋮ → Upload** y ejecuta:

```bash
cd ~ && bash probar_lectura_xml.sh ~/MI_FACTURA.xml
```

Varios a la vez:

```bash
cd ~ && bash probar_lectura_xml.sh ~/*.xml
```

Salida esperada (ejemplo con la factura ED-61930):

```
CES911213AU1_FACTURA_CFDi-ED61930_COP920428Q20.xml  UUID 41ACD15B-8B61-44C4-97EC-CF8FDACCDDCA  Total 1600.00
  1. Descripción: DESINSECTACION DE CHASIS
     Cantidad:    16   Unidad: SERVICIO
     (en el XML venía: DESINSECTACION DE CHASIS a7ebf2a9f246eef13f71463faf1fc792617...)

Plantilla de prueba: /home/<usuario>/plantilla_prueba.xlsx
```

Para revisar la plantilla de prueba en Excel:

```bash
cloudshell download ~/plantilla_prueba.xlsx
```

## Paso 5b. Probar la búsqueda de sitios en Oracle

Con números de colaborador o RFC reales (pide usuario y contraseña de Oracle; no se guardan):

```bash
cd ~ && bash probar_sitio_oracle.sh DEV 90324086 CES911213AU1
```

Salida esperada:

```
Ambiente DEV
  90324086         sitio X90324086          proveedor 12345 NOMBRE DEL COLABORADOR  (encontrado por: ...)
  CES911213AU1     sitio GTCES911213AU1     proveedor 67890 NOMBRE DEL PROVEEDOR    (encontrado por: proveedor por RFC)
```

`encontrado por` indica cómo se encontró: `proveedor por RFC`, `proveedor por sitio` o `factura anterior`
(un colaborador que ya tuvo facturas con ese sitio). Si sale `NO ENCONTRADO` para un sitio que sí existe,
o `ERROR: HTTP 403`, avisa: puede faltar el permiso de consulta de proveedores (View Supplier Site) al usuario.

## Paso 6. Reiniciar la app

Si la app está corriendo, detenla con **Ctrl+C** y vuelve a iniciarla:

```bash
cd ~/cxp-web && source venv/bin/activate && python run.py
```

Después, genera una plantilla desde la app y confirma que aparezcan la columna **Cantidad**
y la descripción sin el código largo.

## Paso 7. Revisar Cloud Storage

Con la app reiniciada, procesa un lote nuevo. Las carpetas nuevas aparecen solas, no hay que crearlas
ni renombrar nada a mano:

| Acción en la app | Carpeta que aparece |
|---|---|
| Subir XML o traer de Drive | `cxp_facturas/1_xml_recibidos/AAAA/MM/DD/<lote>/` |
| Subir la plantilla llena | `cxp_facturas/2_plantillas_capturadas/AAAA/MM/DD/<lote>/` |
| Cargar a Oracle | `cxp_facturas/3_envios_oracle/AAAA/MM/DD/<lote>/` |

Las carpetas anteriores (`original/`, `plantillas/`, `fbdi/`) se siguen viendo porque **no se
renombran**: ahí queda la evidencia de los lotes anteriores y BigQuery guarda esas rutas. Ya no
reciben archivos nuevos.

## Si algo no cambió

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `verificar_actualizacion.sh` marca `[FALTA]` | Se subió un script anterior | Borrar el script de Descargas, descargarlo de nuevo, subirlo y repetir el paso 3 |
| Marca `[REINICIAR]` | La app arrancó antes de actualizar | Ctrl+C en la terminal de la app y paso 6 |
| Todo `[OK]` pero no aparecen las carpetas nuevas | Aún no se procesa un lote nuevo | Subir XML desde la app y revisar el bucket |
| La plantilla no trae la columna Cantidad | Es una plantilla generada antes de reiniciar | Generar una plantilla nueva |
| "El sitio X... no existe o está inactivo" | El colaborador o proveedor no tiene ese sitio activo en Oracle, o el número/RFC está mal | Revisar con `probar_sitio_oracle.sh` y, si falta, darlo de alta en Oracle |
| "No se pudo buscar el sitio ... (HTTP 401/403)" | El usuario de Oracle no tiene permiso de consultar proveedores | Pedir el permiso de consulta de proveedores y sitios |

## Seguridad

- Cloud Shell no se conecta a GitHub: todo pasa por la PC.
- `.secret_key` nunca se sube al repositorio. La clave anterior quedó expuesta en el historial de
  `main`; para generar una nueva: `rm ~/cxp-web/.secret_key` y reiniciar la app (los usuarios vuelven a iniciar sesión).
