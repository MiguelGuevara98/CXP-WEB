"""
Armado de la factura para Oracle Payables a partir de CFDI + datos de captura manual.

Reglas confirmadas contra 95 facturas reales en PROD:
- InvoiceNumber y GDF CFDIUniqueIdentifier = UUID del Timbre
- InvoiceAmount = Total; monedas = Moneda; InvoiceDate/TermsDate = Fecha (solo fecha)
- Description = "F-<UUID> <Folio|0> <Serie> | Empleado <capturista> | <descripción del ticket>"
- Una línea Item por Concepto: importe redondeado a 2 decimales, descripción recortada a 235
- Línea Tax con TotalImpuestosTrasladados (IVA 16%)
- Sitio del proveedor = prefijo ("X") + número de colaborador
- Anticipo aplicado por el total de la factura

El resultado usa los nombres de campo del API REST de Oracle (/invoices).
"""
from decimal import Decimal, ROUND_HALF_UP

from src.dominio import catalogos as cat
from src.dominio.captura import (COL_ACTIVO, COL_ANTICIPO, COL_COLABORADOR, COL_CUENTA, COL_DESCRIPCION,
                                     COL_FORMA_PAGO, COL_PROVEEDOR, COL_SUBIR_A, COL_TIPO, prefijo)

CENTAVO = Decimal("0.01")


def r2(v):
    return (v or Decimal(0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _num(v):
    """Decimal -> float/int para JSON (Oracle devuelve números)."""
    v = r2(v)
    return int(v) if v == v.to_integral_value() else float(v)


def generar_factura(c, m, capturista):
    """
    c: CFDI (src.dominio.cfdi.parsear_cfdi)
    m: dict con las columnas manuales
    capturista: usuario que captura (aparece como 'Empleado' en la descripción)
    """
    uuid = c["UUID"]
    fecha = c["Fecha"][:10]
    s = lambda col: str(m.get(col) or "").strip()

    descripcion = f"F-{uuid} {c['Folio'] or '0'} {c['Serie']} | Empleado {capturista} | {s(COL_DESCRIPCION)}"
    pre = prefijo(m)   # solo para pruebas: PREFIJO-<UUID> evita chocar con la factura real
    if pre:
        descripcion = f"{pre} | {descripcion}"
    sitio = f"{cat.SUBIR_FACTURA_A[s(COL_SUBIR_A)]}{s(COL_COLABORADOR)}"
    forma_pago = cat.FORMA_PAGO[s(COL_FORMA_PAGO)]

    lineas = []
    for con in c["Conceptos"]:
        lineas.append({
            "LineNumber": len(lineas) + 1,
            "LineType": "Item",
            "LineAmount": _num(con["Importe"]),
            "Description": con["Descripcion"][:cat.LARGO_DESCRIPCION_LINEA].rstrip(),
            "DistributionCombination": s(COL_CUENTA),
            "TrackAsAssetFlag": cat.ACTIVO_FIJO[s(COL_ACTIVO)],
        })
    if c["TotalImpuestosTrasladados"]:
        t = next(t for t in c["Traslados"] if (t["Importe"] or 0))
        datos = cat.IMPUESTOS_TRASLADO[(t["Impuesto"], f"{t['TasaOCuota']:.6f}")]
        lineas.append({"LineNumber": len(lineas) + 1, "LineType": "Tax",
                       "LineAmount": _num(c["TotalImpuestosTrasladados"]), **datos})

    factura = {
        "InvoiceNumber": f"{pre}-{uuid}" if pre else uuid,
        "InvoiceCurrency": c["Moneda"],
        "PaymentCurrency": c["Moneda"],
        "InvoiceAmount": _num(c["Total"]),
        "InvoiceDate": fecha,
        "BusinessUnit": cat.FIJOS["BusinessUnit"],
        "SupplierNumber": s(COL_PROVEEDOR),
        "SupplierSite": sitio,
        "Description": descripcion,
        "InvoiceType": cat.TIPO_FACTURA[s(COL_TIPO)],
        "InvoiceSource": cat.FIJOS["InvoiceSource"],
        "PaymentMethodCode": forma_pago,
        "PaymentTerms": cat.FIJOS["PaymentTerms"],
        "TermsDate": fecha,
        "LiabilityDistribution": cat.FIJOS["LiabilityDistribution"],
        "invoiceLines": lineas,
        "invoiceGdf": [{"__FLEX_Context": "JLxMXPayablesInformation", "CFDIUniqueIdentifier": uuid}],
    }
    anticipo = s(COL_ANTICIPO)
    if anticipo:
        factura["_anticipo"] = {"PrepaymentNumber": anticipo, "AppliedAmount": _num(c["Total"])}
    return factura
