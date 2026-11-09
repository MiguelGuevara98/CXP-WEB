"""
Catálogos de los campos que hoy se capturan a mano en la pantalla de captura,
y valores fijos observados en las cargas reales (análisis de 95 facturas en PROD).

Para agregar opciones a una lista desplegable, añade una entrada al diccionario
correspondiente: "texto que ve el usuario": "valor que se envía a Oracle".
"""

# --- Listas desplegables de la plantilla ---
INCLUIR = {"Sí": True, "No": False}   # "No" excluye la factura del lote
TIPO_FACTURA = {
    "Estándar": "Standard",
}
FORMA_PAGO = {
    "Liquidación Anticipo": "Liquidacion Anticipo",
}
# El valor es el prefijo del sitio de proveedor del colaborador (X + número de colaborador)
SUBIR_FACTURA_A = {
    "Cuentas por Pagar X": "X",
}
ACTIVO_FIJO = {
    "Captura normal": False,   # TrackAsAssetFlag
}

# Valores por defecto con los que se prellena la plantilla (el usuario los puede cambiar)
DEFAULTS = {
    "Incluir": "Sí",
    "Tipo de factura": "Estándar",
    "Forma de pago": "Liquidación Anticipo",
    "Subir factura a": "Cuentas por Pagar X",
    "Activo fijo": "Captura normal",
}

# --- Valores fijos observados en las 95 facturas analizadas ---
FIJOS = {
    "BusinessUnit": "BU_CSACV",
    "LiabilityDistribution": "002-2500653002-167-2010301001-000000000-000-0000-0000",
    "PaymentTerms": "Immediate",
    "InvoiceSource": "LECTOR XML",
    "LegalEntityIdentifier": "COP920428Q20",   # RFC de Coppel como receptor
}

# Impuestos trasladados soportados: (Impuesto SAT, tasa) -> datos de la línea Tax en Oracle
IMPUESTOS_TRASLADO = {
    ("002", "0.160000"): {"TaxRateCode": "MX_IVA", "TaxRate": 16, "TaxRateName": "002",
                          "TaxClassification": "MX_IVA", "Description": "IVA"},
}

# Largo máximo observado de la descripción de línea en Oracle
LARGO_DESCRIPCION_LINEA = 235

# --- Reglas de negocio (generan ADVERTENCIAS, no bloquean; el usuario decide) ---
RFC_COPPEL = "COP920428Q20"
METODO_PAGO_PERMITIDO = "PUE"
LIMITE_EFECTIVO = "2000.00"                 # hasta este total se acepta cualquier forma de pago
FORMAS_PAGO_SOBRE_LIMITE = {"03": "Transferencia", "04": "Tarjeta de crédito", "28": "Tarjeta de débito"}
FORMA_PAGO_POR_DEFINIR = "99"
FORMAS_PAGO_SAT = {"01": "Efectivo", "02": "Cheque nominativo", "03": "Transferencia", "04": "Tarjeta de crédito",
                   "28": "Tarjeta de débito", "99": "Por definir"}
# Pendiente: reglas de "tipo de gasto" (aún no definidas por negocio)
