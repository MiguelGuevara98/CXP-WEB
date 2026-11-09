"""
Plantilla Excel para la captura manual.

crear_plantilla(cfdis, lote_id) -> bytes (.xlsx)
leer_plantilla(bytes)           -> (lote_id, {UUID: {columna_manual: valor}})

Hoja "Facturas": una fila por CFDI. Columnas del XML en gris y bloqueadas;
columnas de captura en blanco, con listas desplegables donde hay catálogo.
Hoja "Conceptos": detalle de conceptos (solo consulta). Hoja "Instrucciones".
Hoja oculta "_lote": identificador del lote para relacionar la plantilla con sus XML.
"""
import io

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from src.dominio import catalogos as cat
from src.dominio.captura import (COLUMNAS_MANUALES, OBLIGATORIAS, COL_TIPO, COL_FORMA_PAGO,
                                     COL_SUBIR_A, COL_ACTIVO, COL_INCLUIR)

HOJA = "Facturas"
COLUMNAS_XML = [
    ("UUID", 38), ("Archivo", 28), ("RFC emisor", 15), ("Emisor", 32), ("Serie", 12), ("Folio", 12),
    ("Fecha emisión", 13), ("Fecha timbrado", 13), ("Método pago", 10), ("Forma pago", 18), ("Moneda", 8),
    ("Subtotal", 12), ("IVA", 10), ("Total", 12), ("Conceptos", 10), ("Primer concepto", 45),
    ("Advertencias", 50),
]
COLUMNAS_IMPORTE = {"Subtotal", "IVA", "Total"}
COLUMNAS_TEXTO = {"UUID", "Serie", "Folio", "Forma pago"}
ANCHOS_MANUALES = {"Incluir": 9, "# Colaborador": 14, "Número de proveedor": 14, "Descripción": 55, "Tipo de factura": 16,
                   "Forma de pago": 20, "Subir factura a": 20, "Activo fijo": 16, "Anticipo": 40,
                   "Combinación contable": 52, "Prefijo de prueba": 14}
AYUDA = {
    "Incluir": "Sí = se carga. No = se excluye del lote (por ejemplo, por una advertencia).",
    "# Colaborador": "Número de colaborador dueño del gasto. Se usa para el sitio del proveedor (X + colaborador).",
    "Número de proveedor": "Número de proveedor del colaborador en Oracle.",
    "Descripción": "Información del ticket. Ej.: LIQ DE TICKET 13872999 PEAJES FACTURA EN TICKET 14095386",
    "Anticipo": "Número del anticipo a liquidar. Ej.: ANT-OPERACION TRANSPORTE TICKET 13872999 (opcional).",
    "Combinación contable": "Cuenta de Oracle de 8 segmentos. Ej.: 002-2500651001-073-5061701001-000000000-000-0000-0000",
    "Prefijo de prueba": "Solo para pruebas (opcional). Ej.: TEST1 -> la factura se carga como TEST1-<UUID>. Déjalo vacío en cargas reales.",
}
CATALOGOS = {COL_INCLUIR: cat.INCLUIR, COL_TIPO: cat.TIPO_FACTURA, COL_FORMA_PAGO: cat.FORMA_PAGO,
             COL_SUBIR_A: cat.SUBIR_FACTURA_A, COL_ACTIVO: cat.ACTIVO_FIJO}

GRIS = PatternFill("solid", fgColor="F3F3F3")
AZUL = PatternFill("solid", fgColor="1C42E8")
AMARILLO = PatternFill("solid", fgColor="FFF6CC")


def _fmt(v):
    return "" if v is None else (float(v) if not isinstance(v, str) else v)


def crear_plantilla(cfdis, lote_id, advertencias=None):
    """advertencias: {UUID: [textos]} para mostrarlas en la plantilla (opcional)."""
    advertencias = advertencias or {}
    wb = Workbook()
    ws = wb.active
    ws.title = HOJA

    encabezados = [c for c, _ in COLUMNAS_XML] + [
        f"{c} *" if c in OBLIGATORIAS else c for c in COLUMNAS_MANUALES]
    ws.append(encabezados)
    for i, h in enumerate(encabezados, 1):
        celda = ws.cell(row=1, column=i)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = AZUL
        celda.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 32

    n_xml = len(COLUMNAS_XML)
    validos = [c for c in cfdis if not c.get("_error")]
    for c in validos:
        iva = c["TotalImpuestosTrasladados"]
        fp = c["FormaPago"]
        fila = [c["UUID"], c["archivo"], c["EmisorRfc"], c["EmisorNombre"], c["Serie"], c["Folio"],
                c["Fecha"][:10], (c["FechaTimbrado"] or "")[:10], c["MetodoPago"],
                f"{fp} {cat.FORMAS_PAGO_SAT.get(fp, '')}".strip(), c["Moneda"],
                _fmt(c["SubTotal"]), _fmt(iva), _fmt(c["Total"]), len(c["Conceptos"]),
                (c["Conceptos"][0]["Descripcion"][:120] if c["Conceptos"] else ""),
                " · ".join(advertencias.get(c["UUID"], []))]
        fila += [cat.DEFAULTS.get(col, "") for col in COLUMNAS_MANUALES]
        ws.append(fila)

    ultima = max(ws.max_row, 2)
    # Estilos y protección: XML bloqueado, captura editable
    for fila in ws.iter_rows(min_row=2, max_row=ultima):
        for celda in fila:
            if celda.column <= n_xml:
                celda.fill = GRIS
                celda.protection = Protection(locked=True)
            else:
                celda.protection = Protection(locked=False)
                if COLUMNAS_MANUALES[celda.column - n_xml - 1] in OBLIGATORIAS and celda.value in (None, ""):
                    celda.fill = AMARILLO
            nombre_col = COLUMNAS_XML[celda.column - 1][0] if celda.column <= n_xml else ""
            if nombre_col in COLUMNAS_IMPORTE:
                celda.number_format = "#,##0.00"
            if nombre_col in COLUMNAS_TEXTO or celda.column > n_xml:
                celda.number_format = "@"  # texto: conserva ceros y guiones
            if nombre_col == "Advertencias" and celda.value:
                celda.fill = PatternFill("solid", fgColor="FFE3CC")
                celda.font = Font(color="CF4600")

    # Filas extra editables por si arrastran fórmulas (no se usan)
    for i, (col, ancho) in enumerate(COLUMNAS_XML, 1):
        ws.column_dimensions[get_column_letter(i)].width = ancho
    for j, col in enumerate(COLUMNAS_MANUALES, n_xml + 1):
        ws.column_dimensions[get_column_letter(j)].width = ANCHOS_MANUALES.get(col, 18)
        if col in CATALOGOS:
            lista = ",".join(CATALOGOS[col].keys())
            dv = DataValidation(type="list", formula1=f'"{lista}"', allow_blank=False,
                                showErrorMessage=True, errorTitle="Valor no válido",
                                error="Elige un valor de la lista.")
            ws.add_data_validation(dv)
            dv.add(f"{get_column_letter(j)}2:{get_column_letter(j)}{ultima}")
        if col in AYUDA:
            from openpyxl.comments import Comment
            ws.cell(row=1, column=j).comment = Comment(AYUDA[col], "CXP-WEB")

    ws.freeze_panes = ws.cell(row=2, column=2)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(encabezados))}{ultima}"
    ws.protection.sheet = True
    ws.protection.autoFilter = False
    ws.protection.sort = False
    ws.protection.formatColumns = False

    # Conceptos (consulta)
    wc = wb.create_sheet("Conceptos")
    wc.append(["UUID", "No.", "ClaveProdServ", "Descripción", "Cantidad", "Valor unitario", "Importe", "IVA"])
    for c in validos:
        for con in c["Conceptos"]:
            iva = sum((t["Importe"] or 0) for t in con["Traslados"])
            wc.append([c["UUID"], con["n"], con["ClaveProdServ"], con["Descripcion"],
                       _fmt(con["Cantidad"]), _fmt(con["ValorUnitario"]), _fmt(con["Importe"]), float(iva)])
    for i, w in enumerate([38, 6, 14, 70, 10, 14, 12, 10], 1):
        wc.column_dimensions[get_column_letter(i)].width = w
    for celda in wc[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = AZUL

    # Instrucciones
    wi = wb.create_sheet("Instrucciones")
    textos = [
        "Cómo llenar esta plantilla",
        "",
        "1. En la hoja 'Facturas', llena las columnas blancas (las de fondo amarillo son obligatorias).",
        "2. Las columnas grises vienen del XML y no se pueden editar.",
        "   Revisa la columna 'Advertencias' (en naranja) y las fechas de emisión y timbrado.",
        "   Para EXCLUIR una factura del lote, cambia la columna 'Incluir' a 'No'.",
        "3. Si todas las facturas son del mismo ticket, llena la primera fila y arrastra hacia abajo.",
        "4. No cambies el orden de las columnas ni el nombre de las hojas.",
        "5. Guarda el archivo como .xlsx y súbelo en la página para validarlo.",
        "",
        "Columnas de captura:",
    ] + [f"   - {c}: {AYUDA.get(c, 'Elige un valor de la lista.')}" for c in COLUMNAS_MANUALES]
    for t in textos:
        wi.append([t])
    wi["A1"].font = Font(bold=True, size=14)
    wi.column_dimensions["A"].width = 120

    # Lote (oculta)
    wl = wb.create_sheet("_lote")
    wl.append(["lote", lote_id])
    wl.sheet_state = "hidden"

    wb.active = 0
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def leer_plantilla(contenido):
    wb = load_workbook(io.BytesIO(contenido), data_only=True)
    if HOJA not in wb.sheetnames:
        raise ValueError(f"La plantilla no tiene la hoja '{HOJA}'.")
    lote_id = wb["_lote"]["B1"].value if "_lote" in wb.sheetnames else None

    ws = wb[HOJA]
    encabezados = [str(c.value or "").replace(" *", "").strip() for c in ws[1]]
    if "UUID" not in encabezados:
        raise ValueError("La hoja 'Facturas' no tiene la columna 'UUID'.")
    faltan = [c for c in COLUMNAS_MANUALES if c not in encabezados]
    if faltan:
        raise ValueError(f"Faltan columnas en la plantilla: {', '.join(faltan)}")

    idx = {h: i for i, h in enumerate(encabezados)}
    capturas = {}
    for fila in ws.iter_rows(min_row=2, values_only=True):
        uuid = str(fila[idx["UUID"]] or "").strip().upper()
        if not uuid:
            continue
        datos = {}
        for col in COLUMNAS_MANUALES:
            v = fila[idx[col]]
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            datos[col] = "" if v is None else str(v).strip()
        capturas[uuid] = datos
    return lote_id, capturas
