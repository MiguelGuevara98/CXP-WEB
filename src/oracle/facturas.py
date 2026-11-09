"""
Consulta de existencia de facturas en Oracle (solo lectura).
"""
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.auth import HTTPBasicAuth

from src.config import url_facturas

HEADERS = {"Accept": "application/json", "User-Agent": "CXP-WEB/1.0"}


def buscar_existentes(ambiente, usuario, password, numeros, workers=10):
    """
    Solo lectura. Devuelve {numero: InvoiceId | 'sí' | None | 'ERROR: ...'} indicando si cada número
    ya existe como InvoiceNumber en Oracle.
    """
    base = url_facturas(ambiente)
    auth = HTTPBasicAuth(usuario, password)

    def una(numero):
        try:
            r = requests.get(f"{base}?q=InvoiceNumber={numero}", params={"onlyData": "true", "fields": "InvoiceId"},
                             auth=auth, headers=HEADERS, timeout=60)
            if not r.ok:
                return numero, f"ERROR: HTTP {r.status_code}"
            items = r.json().get("items", [])
            return numero, ((items[0].get("InvoiceId") or "sí") if items else None)
        except Exception as e:  # noqa: BLE001
            return numero, f"ERROR: {type(e).__name__}"

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(una, numeros))
