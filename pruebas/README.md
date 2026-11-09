# Pruebas y actualización de CXP-WEB en Cloud Shell

Esta carpeta trae dos scripts para actualizar y probar el proyecto en Cloud Shell.
**Cloud Shell nunca se conecta a GitHub.** Los archivos se descargan en la PC desde el
navegador y se suben a Cloud Shell con el menú **⋮ → Upload**.

| Archivo | Para qué sirve |
|---|---|
| `actualizar_cxp_web.sh` | Actualiza el proyecto en Cloud Shell a la versión de esta rama. Trae todo el código adentro, no descarga nada. |
| `probar_lectura_xml.sh` | Lee uno o varios XML/zip y muestra descripción, cantidad y unidad de cada concepto. Genera una plantilla de Excel de prueba. No se conecta a Oracle ni a Google. |

## Qué incluye esta versión

- La descripción del concepto se limpia de los códigos (hash) que algunos emisores pegan al final.
  Ejemplo: `DESINSECTACION DE CHASIS a7ebf2a9f246...` queda como `DESINSECTACION DE CHASIS`.
- La plantilla de Excel (hoja **Facturas**) tiene la columna **Cantidad** junto a **Primer concepto**.
- La hoja **Conceptos** tiene la columna **Unidad**.
- A Oracle se envía la descripción limpia.

## Paso 1. Descargar los scripts en la PC

En el navegador, abre cada archivo de esta carpeta en GitHub y usa el botón de descarga
(⤓ *Download raw file*):

- `pruebas/actualizar_cxp_web.sh`
- `pruebas/probar_lectura_xml.sh`

## Paso 2. Subirlos a Cloud Shell

En Cloud Shell: **⋮ (tres puntos) → Upload**, elige los dos archivos y haz clic en **Upload**.
Quedan en la carpeta home (`~`).

## Paso 3. Actualizar el proyecto

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

## Paso 4. Probar la lectura de XML

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

## Paso 5. Reiniciar la app

Si la app está corriendo, detenla con **Ctrl+C** y vuelve a iniciarla:

```bash
cd ~/cxp-web && source venv/bin/activate && python run.py
```

Después, genera una plantilla desde la app y confirma que aparezcan la columna **Cantidad**
y la descripción sin el código largo.
