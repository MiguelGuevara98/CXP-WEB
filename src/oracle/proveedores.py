"""
Búsqueda de sitios de proveedor en Oracle (solo lectura).

buscar_sitios(ambiente, usuario, password, {sitio: rfc_o_None})
    -> {sitio: {"SupplierNumber", "Supplier", "SupplierSite", "fuente"} | None | "ERROR: ..."}

Para cada sitio se intenta, en orden, hasta encontrarlo:
1. Proveedor por RFC (solo sitios GT + RFC): suppliers?q=TaxpayerId='<RFC>' con sus sitios.
2. Proveedor que tenga ese sitio: suppliers?q=sites.SupplierSite='<sitio>'. Si el ambiente no admite
   este filtro (HTTP 400) se ignora; si lo admite, se confirma que el sitio venga en los sitios del proveedor.
3. Facturas anteriores con ese sitio: invoices?q=SupplierSite='<sitio>' (toma su SupplierNumber).
Un sitio con InactiveDate vencida cuenta como no encontrado. None = no existe; "ERROR: ..." = no se pudo consultar.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import requests
from requests.auth import HTTPBasicAuth

from src.config import url_facturas, url_proveedores

HEADERS = {"Accept": "application/json", "User-Agent": "CXP-WEB/1.0"}
TIMEOUT = 60


class _ErrorConsulta(Exception):
    pass


def _get(url, auth, params, tolerar_400=False):
    try:
        r = requests.get(url, params={"onlyData": "true", **params}, auth=auth, headers=HEADERS, timeout=TIMEOUT)
    except Exception as e:  # noqa: BLE001
        raise _ErrorConsulta(type(e).__name__)
    if r.status_code == 400 and tolerar_400:
        return None
    if not r.ok:
        raise _ErrorConsulta(f"HTTP {r.status_code}")
    return r.json().get("items", [])


def _texto(v):
    return str(v or "").strip()


def _sitio_activo(s):
    fin = _texto(s.get("InactiveDate"))[:10]
    return not fin or fin > date.today().isoformat()


def _sitios_de(proveedor):
    sites = proveedor.get("sites") or []
    return sites.get("items", []) if isinstance(sites, dict) else sites


def _en_proveedores(items, sitio):
    """Busca el sitio dentro de los sitios de una lista de proveedores. Devuelve (encontrado, inactivo)."""
    inactivo = False
    for p in items or []:
        for s in _sitios_de(p):
            if _texto(s.get("SupplierSite")).upper() == sitio:
                if _sitio_activo(s):
                    return {"SupplierNumber": _texto(p.get("SupplierNumber")), "Supplier": _texto(p.get("Supplier")),
                            "SupplierSite": _texto(s.get("SupplierSite"))}, False
                inactivo = True
    return None, inactivo


def buscar_sitio(ambiente, auth, sitio, rfc=None):
    sitio = sitio.upper()
    proveedores = url_proveedores(ambiente)
    inactivo = False

    if rfc:
        items = _get(proveedores, auth, {"q": f"TaxpayerId='{rfc}'", "expand": "sites", "limit": "10"})
        hallado, inactivo = _en_proveedores(items, sitio)
        if hallado:
            return {**hallado, "fuente": "proveedor por RFC"}

    items = _get(proveedores, auth, {"q": f"sites.SupplierSite='{sitio}'", "expand": "sites", "limit": "5"},
                 tolerar_400=True)
    hallado, inact = _en_proveedores(items, sitio)
    inactivo = inactivo or inact
    if hallado:
        return {**hallado, "fuente": "proveedor por sitio"}
    if inactivo:
        return None   # el sitio existe pero está dado de baja

    items = _get(url_facturas(ambiente), auth, {"q": f"SupplierSite='{sitio}'", "limit": "1",
                                                "fields": "SupplierNumber,Supplier,SupplierSite"})
    for f in items:
        if _texto(f.get("SupplierSite")).upper() == sitio and _texto(f.get("SupplierNumber")):
            return {"SupplierNumber": _texto(f["SupplierNumber"]), "Supplier": _texto(f.get("Supplier")),
                    "SupplierSite": _texto(f["SupplierSite"]), "fuente": "factura anterior"}
    return None


def buscar_sitios(ambiente, usuario, password, consultas, workers=8):
    """consultas: {sitio: rfc o None}. Ver el docstring del módulo."""
    auth = HTTPBasicAuth(usuario, password)

    def una(par):
        sitio, rfc = par
        try:
            return sitio, buscar_sitio(ambiente, auth, sitio, rfc)
        except _ErrorConsulta as e:
            return sitio, f"ERROR: {e}"

    if not consultas:
        return {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(una, consultas.items()))
