"""
Lectura de CFDI (XML del SAT, versiones 3.3 y 4.0).

leer_archivos(lista de (nombre, bytes))  -> lista de dicts con el CFDI estructurado.
Acepta .xml sueltos y .zip (con XML dentro, en cualquier carpeta). Ignora PDF y otros.
"""
import io
import re
import zipfile
from xml.etree.ElementTree import ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath

# Límites al abrir zip (evitan que un zip pequeño se expanda a gigas y tumbe el servidor)
MAX_ARCHIVOS = 5000                  # archivos en total, contando los de zips anidados
MAX_DESCOMPRIMIDO = 300 * 1024 ** 2  # 300 MB descomprimidos en total
MAX_NIVELES_ZIP = 3                  # zip dentro de zip dentro de zip


class LimiteExcedido(ValueError):
    pass


def _local(tag):
    return tag.split("}")[-1]


def _dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v).strip())
    except InvalidOperation:
        return None


# Códigos de control que algunos emisores pegan a la descripción (hashes hexadecimales de 32+ caracteres).
# Se exige al menos una letra a-f y un dígito para no borrar números largos legítimos.
_HASH = re.compile(r"\b(?=[0-9a-fA-F]*[a-fA-F])(?=[0-9a-fA-F]*\d)[0-9a-fA-F]{32,}\b")


def limpiar_descripcion(texto):
    """Quita hashes hexadecimales y espacios de más de la descripción del concepto."""
    return " ".join(_HASH.sub(" ", texto or "").split())


def _hijos(elem, nombre):
    return [e for e in elem if _local(e.tag) == nombre]


def _uno(elem, nombre):
    for e in elem.iter():
        if _local(e.tag) == nombre:
            return e
    return None


def parsear_cfdi(contenido: bytes, nombre_archivo: str = ""):
    """Devuelve el CFDI estructurado o un dict con '_error'."""
    try:
        raiz = fromstring(contenido)
    except ParseError as e:
        return {"archivo": nombre_archivo, "_error": f"XML inválido ({e})"}
    except DefusedXmlException:
        return {"archivo": nombre_archivo, "_error": "XML con contenido no permitido (entidades o DTD)"}
    if _local(raiz.tag) != "Comprobante":
        return {"archivo": nombre_archivo, "_error": "No es un CFDI (falta el nodo Comprobante)"}

    a = raiz.attrib
    emisor = _uno(raiz, "Emisor")
    receptor = _uno(raiz, "Receptor")
    tfd = _uno(raiz, "TimbreFiscalDigital")

    conceptos = []
    nodo_conceptos = next((e for e in raiz if _local(e.tag) == "Conceptos"), None)
    for i, c in enumerate(_hijos(nodo_conceptos, "Concepto") if nodo_conceptos is not None else [], 1):
        traslados = [t for t in c.iter() if _local(t.tag) == "Traslado"]
        retenciones = [r for r in c.iter() if _local(r.tag) == "Retencion"]
        conceptos.append({
            "n": i,
            "ClaveProdServ": c.get("ClaveProdServ", ""),
            "Descripcion": limpiar_descripcion(c.get("Descripcion", "")),
            "DescripcionXml": c.get("Descripcion", ""),
            "Cantidad": _dec(c.get("Cantidad")),
            "Unidad": (c.get("Unidad") or "").strip(),
            "ClaveUnidad": (c.get("ClaveUnidad") or "").strip(),
            "ValorUnitario": _dec(c.get("ValorUnitario")),
            "Importe": _dec(c.get("Importe")),
            "Descuento": _dec(c.get("Descuento")),
            "Traslados": [{"Impuesto": t.get("Impuesto"), "TasaOCuota": _dec(t.get("TasaOCuota")),
                           "Importe": _dec(t.get("Importe"))} for t in traslados],
            "Retenciones": [{"Impuesto": r.get("Impuesto"), "Importe": _dec(r.get("Importe"))} for r in retenciones],
        })

    # Impuestos a nivel comprobante (hijo directo de Comprobante)
    imp = next((e for e in raiz if _local(e.tag) == "Impuestos"), None)
    traslados_tot, retenciones_tot = [], []
    if imp is not None:
        for t in imp.iter():
            if _local(t.tag) == "Traslado":
                traslados_tot.append({"Impuesto": t.get("Impuesto"), "TasaOCuota": _dec(t.get("TasaOCuota")),
                                      "TipoFactor": t.get("TipoFactor"), "Importe": _dec(t.get("Importe"))})
            elif _local(t.tag) == "Retencion":
                retenciones_tot.append({"Impuesto": t.get("Impuesto"), "Importe": _dec(t.get("Importe"))})

    def suma_ret(cod):
        v = sum((r["Importe"] or 0) for r in retenciones_tot if r["Impuesto"] == cod)
        return Decimal(v) if v else Decimal(0)

    return {
        "archivo": nombre_archivo,
        "UUID": (tfd.get("UUID") if tfd is not None else "").upper(),
        "Version": a.get("Version", ""),
        "TipoDeComprobante": a.get("TipoDeComprobante", ""),
        "Serie": a.get("Serie", ""),
        "Folio": a.get("Folio", ""),
        "Fecha": a.get("Fecha", ""),
        "Moneda": a.get("Moneda", ""),
        "TipoCambio": _dec(a.get("TipoCambio")),
        "MetodoPago": a.get("MetodoPago", ""),
        "FormaPago": a.get("FormaPago", ""),
        "SubTotal": _dec(a.get("SubTotal")),
        "Descuento": _dec(a.get("Descuento")),
        "Total": _dec(a.get("Total")),
        "EmisorRfc": emisor.get("Rfc", "") if emisor is not None else "",
        "EmisorNombre": emisor.get("Nombre", "") if emisor is not None else "",
        "ReceptorRfc": receptor.get("Rfc", "") if receptor is not None else "",
        "ReceptorNombre": receptor.get("Nombre", "") if receptor is not None else "",
        "TotalImpuestosTrasladados": _dec(imp.get("TotalImpuestosTrasladados")) if imp is not None else None,
        "TotalImpuestosRetenidos": _dec(imp.get("TotalImpuestosRetenidos")) if imp is not None else None,
        "Traslados": traslados_tot,
        "RetIVA": suma_ret("002"),
        "RetISR": suma_ret("001"),
        "Conceptos": conceptos,
        "FechaTimbrado": tfd.get("FechaTimbrado", "") if tfd is not None else "",
    }


def leer_archivos(archivos):
    """
    archivos: iterable de (nombre, bytes). Expande .zip (también anidados).
    Devuelve (cfdis, ignorados) donde ignorados es la lista de nombres no XML.
    Cada cfdi trae "_origen" (índice del archivo subido que lo contiene) y "_ruta_zip" (ruta dentro del zip, si aplica).
    """
    cfdis, ignorados = [], []
    cuenta = {"archivos": 0, "bytes": 0}

    def procesar(nombre, contenido, origen, nivel=0, ruta_zip=None):
        ext = PurePosixPath(nombre.replace("\\", "/")).suffix.lower()
        base = PurePosixPath(nombre.replace("\\", "/")).name
        cuenta["archivos"] += 1
        if cuenta["archivos"] > MAX_ARCHIVOS:
            raise LimiteExcedido(f"Son demasiados archivos (máximo {MAX_ARCHIVOS}). Divide la carga en varios lotes.")
        if ext == ".zip":
            if nivel >= MAX_NIVELES_ZIP:
                cfdis.append({"archivo": base, "_error": "Demasiados zip uno dentro de otro", "_origen": origen})
                return
            try:
                with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                    for info in z.infolist():
                        if info.is_dir():
                            continue
                        # Se revisa el tamaño declarado ANTES de descomprimir
                        cuenta["bytes"] += info.file_size
                        if cuenta["bytes"] > MAX_DESCOMPRIMIDO:
                            raise LimiteExcedido("Los archivos descomprimidos pasan de 300 MB. Divide la carga en varios lotes.")
                        procesar(info.filename, z.read(info), origen, nivel + 1,
                                 f"{ruta_zip}/{info.filename}" if ruta_zip else info.filename)
            except zipfile.BadZipFile:
                cfdis.append({"archivo": base, "_error": "ZIP dañado", "_origen": origen})
        elif ext == ".xml":
            cfdis.append({**parsear_cfdi(contenido, base), "_origen": origen, "_ruta_zip": ruta_zip})
        elif base and not base.startswith("."):
            ignorados.append(base)

    for i, (nombre, contenido) in enumerate(archivos):
        procesar(nombre, contenido, i)
    return cfdis, ignorados
