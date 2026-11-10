"""
Datos que el colaborador captura a mano en la plantilla (columnas blancas) y su validación.
"""
import re

from src.dominio import catalogos as cat

# Columnas de captura manual (encabezados de la plantilla)
COL_INCLUIR = "Incluir"
COL_COLABORADOR = "# Colaborador"
COL_PROVEEDOR = "Número de proveedor"   # ya no se captura: se llena con el proveedor del sitio encontrado en Oracle
COL_DESCRIPCION = "Descripción"
COL_TIPO = "Tipo de factura"
COL_FORMA_PAGO = "Forma de pago"
COL_SUBIR_A = "Subir factura a"
COL_ACTIVO = "Activo fijo"
COL_ANTICIPO = "Anticipo"
COL_CUENTA = "Combinación contable"
COL_PREFIJO = "Prefijo de prueba"

COLUMNAS_MANUALES = [COL_INCLUIR, COL_COLABORADOR, COL_DESCRIPCION, COL_TIPO, COL_FORMA_PAGO,
                     COL_SUBIR_A, COL_ACTIVO, COL_ANTICIPO, COL_CUENTA, COL_PREFIJO]
OBLIGATORIAS = [COL_COLABORADOR, COL_DESCRIPCION, COL_TIPO, COL_FORMA_PAGO,
                COL_SUBIR_A, COL_ACTIVO, COL_CUENTA]

# RFC: persona moral (3 letras) o física (4 letras) + fecha AAMMDD + homoclave de 3
RFC = re.compile(r"[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}")


def a_quien(m):
    """
    Interpreta '# Colaborador'. Devuelve ("colaborador", número), ("proveedor", RFC) o (None, texto capturado).
    Acepta que escriban el prefijo por error: X90324086 -> 90324086, GTCES911213AU1 -> CES911213AU1.
    """
    v = "".join(str(m.get(COL_COLABORADOR) or "").split()).upper()
    if v.isdigit():
        return "colaborador", v
    if v.startswith("X") and v[1:].isdigit():
        return "colaborador", v[1:]
    if RFC.fullmatch(v):
        return "proveedor", v
    pre = cat.PREFIJO_SITIO_PROVEEDOR
    if v.startswith(pre) and RFC.fullmatch(v[len(pre):]):
        return "proveedor", v[len(pre):]
    return None, v


def sitio_oracle(m):
    """Sitio de proveedor en Oracle: X + número de colaborador, o GT + RFC del proveedor ('' si no es válido)."""
    tipo, valor = a_quien(m)
    if tipo == "colaborador":
        return f"{cat.SUBIR_FACTURA_A.get(str(m.get(COL_SUBIR_A) or '').strip(), '')}{valor}"
    if tipo == "proveedor":
        return f"{cat.PREFIJO_SITIO_PROVEEDOR}{valor}"
    return ""


def prefijo(m):
    """Prefijo de prueba en mayúsculas ('' si no hay)."""
    return str(m.get(COL_PREFIJO) or "").strip().upper()


def excluida(m):
    """True si el usuario marcó la fila con Incluir = No."""
    return cat.INCLUIR.get(str(m.get(COL_INCLUIR) or "Sí").strip(), True) is False


def validar_captura(m):
    """Errores en los datos de captura manual de una fila."""
    errores = [f"Falta '{col}'" for col in OBLIGATORIAS if not str(m.get(col) or "").strip()]
    for col, catalogo in ((COL_INCLUIR, cat.INCLUIR), (COL_TIPO, cat.TIPO_FACTURA), (COL_FORMA_PAGO, cat.FORMA_PAGO),
                          (COL_SUBIR_A, cat.SUBIR_FACTURA_A), (COL_ACTIVO, cat.ACTIVO_FIJO)):
        v = str(m.get(col) or "").strip()
        if v and v not in catalogo:
            errores.append(f"'{col}' = '{v}' no está en el catálogo")
    colab = str(m.get(COL_COLABORADOR) or "").strip()
    if colab and a_quien(m)[0] is None:
        errores.append(f"'# Colaborador' = '{colab}': debe ser un número de colaborador (ej. 90324086) "
                       f"o el RFC del proveedor (ej. CES911213AU1)")
    cuenta = str(m.get(COL_CUENTA) or "").strip()
    if cuenta and len(cuenta.split("-")) != 8:
        errores.append("'Combinación contable' debe tener 8 segmentos separados por '-'")
    if prefijo(m) and not re.fullmatch(r"[A-Z0-9]{1,10}", prefijo(m)):
        errores.append("'Prefijo de prueba' solo puede tener letras y números (máximo 10)")
    return errores
