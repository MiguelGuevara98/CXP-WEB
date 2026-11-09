"""
Generación del FBDI de facturas de Payables (ApInvoicesInterface.csv + ApInvoiceLinesInterface.csv).

Replica el formato del archivo real del sistema actual (APInvoicesImport_<AAAAMMDDhhmmss>.zip):
- CSV UTF-8 con BOM, saltos CRLF, sin encabezado, comillas solo cuando hace falta.
- Cabecera: 132 campos, el último 'END'. Líneas: 158 campos, el último 'END'.
- Posiciones según los archivos de control de Oracle (ApInvoicesInterface.ctl / ApInvoiceLinesInterface.ctl);
  las columnas 'expression'/'constant' del .ctl (p. ej. INVOICE_LINE_ID) no ocupan posición.
"""
import csv
import io
import zipfile
from datetime import date, datetime
from decimal import Decimal

from src.config import ahora

N_CAMPOS_CABECERA = 132
N_CAMPOS_LINEA = 158
MARCA_FIN = "END"

# Posición (1-based) de cada columna en el CSV
CABECERA = {
    "INVOICE_ID": 1, "OPERATING_UNIT": 2, "SOURCE": 3, "INVOICE_NUM": 4, "INVOICE_AMOUNT": 5, "INVOICE_DATE": 6,
    "VENDOR_NAME": 7, "VENDOR_NUM": 8, "VENDOR_SITE_CODE": 9, "INVOICE_CURRENCY_CODE": 10,
    "PAYMENT_CURRENCY_CODE": 11, "DESCRIPTION": 12, "GROUP_ID": 13, "INVOICE_TYPE_LOOKUP_CODE": 14,
    "LEGAL_ENTITY_NAME": 15, "TERMS_NAME": 20, "TERMS_DATE": 21, "GL_DATE": 24, "PAYMENT_METHOD_CODE": 25,
    "PREPAY_NUM": 29, "PREPAY_LINE_NUM": 30, "PREPAY_APPLY_AMOUNT": 31, "PREPAY_GL_DATE": 32,
    "ACCTS_PAY_CODE_CONCATENATED": 37, "ATTRIBUTE15": 89,
    "GLOBAL_ATTRIBUTE_CATEGORY": 100, "GLOBAL_ATTRIBUTE1": 101,
}
LINEA = {
    "INVOICE_ID": 1, "LINE_NUMBER": 2, "LINE_TYPE_LOOKUP_CODE": 3, "AMOUNT": 4, "DESCRIPTION": 8,
    "DIST_CODE_CONCATENATED": 22, "ACCOUNTING_DATE": 24, "TAX_CLASSIFICATION_CODE": 28,
}
LARGO_DESCRIPCION = 240
GDF_MEXICO = "JLxMXPayablesInformation"


def _fecha(v):
    """'2026-08-05', date o datetime -> '2026/08/05'."""
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y/%m/%d")
    return str(v)[:10].replace("-", "/")


def _monto(v):
    return f"{Decimal(str(v)):.2f}"


def _fila(n_campos, posiciones, valores):
    fila = [""] * n_campos
    for col, v in valores.items():
        if v not in (None, ""):
            fila[posiciones[col] - 1] = str(v)
    fila[-1] = MARCA_FIN
    return fila


def _csv(filas):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL).writerows(filas)
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def generar_zip(facturas, fecha_contable, momento=None):
    """
    facturas: salida de src.dominio.factura.generar_factura (nombres del API REST); el número ya trae
    el prefijo de prueba, si se capturó en la plantilla.
    fecha_contable: GL_DATE / ACCOUNTING_DATE de todas las facturas (la app usa el día de la carga).
    No incluye la aplicación de anticipos (PREPAY_*).
    Devuelve (nombre_zip, bytes, resumen).
    """
    momento = momento or ahora()
    base_id = momento.strftime("%y%m%d%H%M%S")
    gl = _fecha(fecha_contable)
    cabeceras, lineas, resumen = [], [], []

    for i, f in enumerate(facturas, 1):
        invoice_id = f"{base_id}{i:03d}"
        uuid = f["invoiceGdf"][0]["CFDIUniqueIdentifier"]
        numero = f["InvoiceNumber"]
        descripcion = f["Description"]
        cabeceras.append(_fila(N_CAMPOS_CABECERA, CABECERA, {
            "INVOICE_ID": invoice_id,
            "OPERATING_UNIT": f["BusinessUnit"],
            "SOURCE": f["InvoiceSource"],
            "INVOICE_NUM": numero,
            "INVOICE_AMOUNT": _monto(f["InvoiceAmount"]),
            "INVOICE_DATE": _fecha(f["InvoiceDate"]),
            "VENDOR_NUM": f["SupplierNumber"],
            "VENDOR_SITE_CODE": f["SupplierSite"],
            "INVOICE_CURRENCY_CODE": f["InvoiceCurrency"],
            "PAYMENT_CURRENCY_CODE": f["PaymentCurrency"],
            "DESCRIPTION": descripcion[:LARGO_DESCRIPCION],
            "INVOICE_TYPE_LOOKUP_CODE": f["InvoiceType"].upper(),
            "TERMS_NAME": f["PaymentTerms"],
            "TERMS_DATE": _fecha(f["TermsDate"]),
            "GL_DATE": gl,
            "PAYMENT_METHOD_CODE": f.get("PaymentMethodCode"),
            "ACCTS_PAY_CODE_CONCATENATED": f.get("LiabilityDistribution"),
            "GLOBAL_ATTRIBUTE_CATEGORY": GDF_MEXICO,
            "GLOBAL_ATTRIBUTE1": uuid,
        }))
        for l in f["invoiceLines"]:
            es_tax = l["LineType"].upper() == "TAX"
            lineas.append(_fila(N_CAMPOS_LINEA, LINEA, {
                "INVOICE_ID": invoice_id,
                "LINE_NUMBER": l["LineNumber"],
                "LINE_TYPE_LOOKUP_CODE": l["LineType"].upper(),
                "AMOUNT": _monto(l["LineAmount"]),
                "DESCRIPTION": l["Description"][:LARGO_DESCRIPCION],
                "DIST_CODE_CONCATENATED": None if es_tax else l.get("DistributionCombination"),
                "ACCOUNTING_DATE": gl,
                "TAX_CLASSIFICATION_CODE": l.get("TaxClassification") if es_tax else None,
            }))
        resumen.append({"INVOICE_ID": invoice_id, "INVOICE_NUM": numero, "INVOICE_AMOUNT": _monto(f["InvoiceAmount"]),
                        "lineas": len(f["invoiceLines"])})

    nombre = f"APInvoicesImport_{momento:%Y%m%d%H%M%S}.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ApInvoicesInterface.csv", _csv(cabeceras))
        z.writestr("ApInvoiceLinesInterface.csv", _csv(lineas))
    return nombre, buf.getvalue(), resumen
