"""
Reglas sobre el contenido del XML (CFDI).

- validar_cfdi:       errores que impiden generar la factura.
- advertencias_cfdi:  reglas de negocio que NO bloquean; se muestran y el usuario decide.
"""
from decimal import Decimal

from src.dominio import catalogos as cat


def validar_cfdi(c):
    """Errores que impiden generar la factura sólo por el contenido del XML."""
    errores = []
    if c.get("_error"):
        return [c["_error"]]
    if not c["UUID"]:
        errores.append("Sin Timbre Fiscal (UUID)")
    if c["TipoDeComprobante"] != "I":
        errores.append(f"Tipo de comprobante '{c['TipoDeComprobante']}' aún no soportado (solo Ingreso)")
    if c["RetIVA"] or c["RetISR"]:
        errores.append("Retenciones aún no soportadas")
    if c["Descuento"]:
        errores.append("Descuentos aún no soportados")
    for t in c["Traslados"]:
        clave = (t["Impuesto"], f"{t['TasaOCuota']:.6f}" if t["TasaOCuota"] is not None else "")
        if (t["Importe"] or 0) and clave not in cat.IMPUESTOS_TRASLADO:
            errores.append(f"Impuesto trasladado {clave} aún no soportado")
    if not c["Conceptos"]:
        errores.append("Sin conceptos")
    return errores


def advertencias_cfdi(c, anio_actual):
    """
    Reglas de negocio que NO bloquean la factura: se muestran como advertencia y el usuario decide
    (para excluirla, marca 'Incluir = No' o borra su fila de la plantilla).
    """
    if c.get("_error"):
        return []
    adv = []
    # 1. Timbrada a Coppel
    if c["ReceptorRfc"] != cat.RFC_COPPEL:
        adv.append(f"Receptor {c['ReceptorRfc'] or '(vacío)'} no es Coppel ({cat.RFC_COPPEL})")
    # 2. Año vigente (se revisan fecha de emisión y de timbrado)
    for nombre, fecha in (("emisión", c["Fecha"]), ("timbrado", c["FechaTimbrado"])):
        if not fecha:
            adv.append(f"Sin fecha de {nombre}")
        elif fecha[:4] != str(anio_actual):
            adv.append(f"Fecha de {nombre} {fecha[:10]} no es del año {anio_actual}")
    # 3. Tipo de gasto: pendiente (aún no hay reglas de negocio)
    # 4. Método de pago
    if c["MetodoPago"] != cat.METODO_PAGO_PERMITIDO:
        adv.append(f"Método de pago {c['MetodoPago'] or '(vacío)'}; se esperaba {cat.METODO_PAGO_PERMITIDO}")
    # 5. Forma de pago
    fp = c["FormaPago"]
    nombre_fp = f"{fp} {cat.FORMAS_PAGO_SAT.get(fp, '')}".strip() or "(vacía)"
    if fp == cat.FORMA_PAGO_POR_DEFINIR:
        adv.append(f"Forma de pago {nombre_fp}")
    elif c["Total"] is not None and c["Total"] > Decimal(cat.LIMITE_EFECTIVO) and fp not in cat.FORMAS_PAGO_SOBRE_LIMITE:
        permitidas = ", ".join(f"{k} {v}" for k, v in cat.FORMAS_PAGO_SOBRE_LIMITE.items())
        adv.append(f"Total {c['Total']:,.2f} mayor a {Decimal(cat.LIMITE_EFECTIVO):,.2f} pagado con {nombre_fp}; "
                   f"debe ser {permitidas}")
    return adv
