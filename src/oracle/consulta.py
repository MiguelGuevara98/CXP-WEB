"""
Consulta de facturas en Oracle Fusion (Payables REST API).

Recuperado del proyecto original (commit c4aa1bf) con estos cambios:
- La URL depende del ambiente elegido (DEV / PROD), ver config.py.
- Se agrega InvoiceNumber a los campos consultados (la UI lo muestra).
- Los archivos .htm/.html (exportaciones web de Excel) se leen igual que .xls HTML.
- validar_credenciales() permite comprobar usuario/contraseña al iniciar sesión.
"""
import json
import math
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, InvalidOperation

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

from src.config import url_facturas

MAX_WORKERS = 10
TIMEOUT = 60

# ==============================================================
#  Reintentos ante errores de conexión
#  MAX_REINTENTOS  : intentos antes de marcar error
#  ESPERA_REINTENTO: segundos base entre intentos (backoff lineal: 2s, 4s...)
# ==============================================================
MAX_REINTENTOS = 3
ESPERA_REINTENTO = 2

COL_FOLIO = "Folio C.F.D.I."
COL_TOTAL = "Total"
SERVICE_FIELDS = [
    "InvoiceNumber", "InvoiceDate", "InvoiceCurrency", "BusinessUnit", "ValidationStatus",
    "Supplier", "SupplierNumber", "SupplierSite", "Party", "CreationDate", "AccountingDate",
    "Description", "InvoiceSource", "InvoiceType", "PaymentTerms", "TermsDate", "PaymentMethod",
    "LiabilityDistribution", "PaidStatus",
]
EXCEL_FIELDS_FOR_SECOND_SHEET = [
    "Folio C.F.D.I.", "Modelo de dominio de proveedor", "Sistema", "Nombre del Beneficiario", "RFC", "Total",
]
HEADERS = {"Accept": "application/json", "User-Agent": "CXP-WEB/1.0", "Connection": "keep-alive"}


class CredencialesInvalidas(Exception):
    def __init__(self, mensaje, rechazo=False):
        super().__init__(mensaje)
        self.rechazo = rechazo   # True: Oracle rechazó el usuario/contraseña (cuenta como intento fallido)


def validar_credenciales(ambiente, username, password):
    """
    Hace una consulta mínima a Oracle para comprobar acceso.
    Lanza CredencialesInvalidas con un mensaje para el usuario si falla.
    """
    url = url_facturas(ambiente)
    try:
        r = requests.get(
            url, params={"limit": 1, "onlyData": "true", "fields": "InvoiceId"},
            auth=HTTPBasicAuth(username.strip(), password.strip()), headers=HEADERS, timeout=30,
        )
    except requests.RequestException as e:
        raise CredencialesInvalidas(f"No se pudo conectar con Oracle {ambiente} ({type(e).__name__}).")
    if r.status_code == 401:
        raise CredencialesInvalidas("Usuario o contraseña incorrectos.", rechazo=True)
    if r.status_code == 403:
        raise CredencialesInvalidas(f"Tu usuario no tiene permiso para consultar facturas en Oracle {ambiente}.")
    if not r.ok:
        raise CredencialesInvalidas(f"Oracle {ambiente} respondió con error {r.status_code}.")


class ProcesadorOracle:
    def __init__(self, ruta_entrada, ambiente, username, password):
        self.ruta_entrada = ruta_entrada
        self.base_url = url_facturas(ambiente)
        self.username = username
        self.password = password
        fd, self.ruta_salida = tempfile.mkstemp(suffix=".xlsx", prefix="cxp_resultado_")
        os.close(fd)

    # ---------- utilidades ----------
    def safe_str(self, value):
        return "" if pd.isna(value) else str(value).strip()

    def to_decimal(self, value):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        text = str(value).strip().replace(",", "").replace("$", "")
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None

    def decimals_equal(self, a, b, tolerance=Decimal("0.01")):
        if a is None or b is None:
            return False
        return abs(a - b) <= tolerance

    def normalize_for_excel(self, value):
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return value

    def normalize_invoice_source(self, value):
        return self.safe_str(value).upper()

    # ---------- lectura del archivo ----------
    def read_input_file(self):
        ext = os.path.splitext(self.ruta_entrada)[1].lower()
        if ext == ".xlsx":
            return pd.read_excel(self.ruta_entrada, dtype=object)
        if ext in (".xls", ".htm", ".html"):
            # Los .xls que exporta el sistema suelen ser HTML disfrazado
            try:
                try:
                    tables = pd.read_html(self.ruta_entrada, encoding="utf-8")
                except Exception:
                    tables = pd.read_html(self.ruta_entrada, encoding="latin1")
            except Exception:
                tables = []
            for t in tables:
                df = t.copy()
                if COL_FOLIO in df.columns:
                    return df
                df.columns = [str(c).strip() for c in df.iloc[0]]
                if COL_FOLIO in df.columns:
                    return df.iloc[1:].reset_index(drop=True)
            if ext == ".xls":
                try:
                    return pd.read_excel(self.ruta_entrada, dtype=object, engine="xlrd")
                except Exception:
                    pass
            raise ValueError(f"No se encontró la columna '{COL_FOLIO}' en el archivo.")
        return pd.read_excel(self.ruta_entrada, dtype=object)

    # ---------- Oracle ----------
    def build_session(self):
        session = requests.Session()
        session.auth = HTTPBasicAuth(str(self.username).strip(), str(self.password).strip())
        session.headers.update(HEADERS)
        return session

    def _get_con_reintento(self, session, url):
        ultimo_error = None
        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                response = session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
                return response
            except Exception as e:
                ultimo_error = e
                # Un 401/403 no se arregla reintentando
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status in (401, 403):
                    break
                if intento < MAX_REINTENTOS:
                    espera = ESPERA_REINTENTO * intento
                    print(f"[REINTENTO {intento}/{MAX_REINTENTOS}] GET {url} -> {type(e).__name__} | esperando {espera}s")
                    time.sleep(espera)
        raise ultimo_error

    def query_invoice_by_folio(self, session, folio):
        url = f"{self.base_url}?q=InvoiceNumber={folio}"
        return self._get_con_reintento(session, url).json()

    def process_row(self, row_dict):
        session = self.build_session()
        folio = self.safe_str(row_dict.get(COL_FOLIO))
        total_excel = row_dict.get(COL_TOTAL)

        result = {"_folio": folio, "_found": "No", "_message": "", "Amount": ""}
        for f in SERVICE_FIELDS:
            result[f] = ""
        if not folio:
            result["_message"] = "Sin folio"
            return result

        try:
            items = self.query_invoice_by_folio(session, folio).get("items", [])
            if not items:
                result["_message"] = "No encontrada"
                return result

            excel_total_dec = self.to_decimal(total_excel)
            correcta = next(
                (i for i in items if self.decimals_equal(self.to_decimal(i.get("InvoiceAmount")), excel_total_dec)),
                None,
            )
            factura = correcta or items[0]
            for f in SERVICE_FIELDS:
                result[f] = self.normalize_for_excel(factura.get(f, ""))
            result["Amount"] = self.normalize_for_excel(factura.get("InvoiceAmount", ""))

            if correcta:
                result.update({"_found": "Sí", "_message": "Encontrada"})
            else:
                result["_message"] = "Monto diferente al del Excel"
            return result
        except Exception as e:
            result["_message"] = f"Error tras {MAX_REINTENTOS} reintentos: {type(e).__name__}"
            return result

    def ejecutar_cruce(self):
        df = self.read_input_file()
        df_original = df.copy()
        df.columns = [self.safe_str(c) for c in df.columns]
        if COL_FOLIO not in df.columns:
            raise ValueError(f"El archivo no tiene la columna '{COL_FOLIO}'.")
        rows = df.to_dict(orient="records")

        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futuros = {executor.submit(self.process_row, row): idx for idx, row in enumerate(rows)}
            for futuro in as_completed(futuros):
                results.append((futuros[futuro], futuro.result()))
        results.sort(key=lambda x: x[0])
        processed = [r[1] for r in results]

        second_sheet_rows = []
        for orig, proc in zip(rows, processed):
            row_out = {col: orig.get(col, "") for col in EXCEL_FIELDS_FOR_SECOND_SHEET}
            row_out["Amount"] = proc.get("Amount", "")
            row_out.update({f: proc.get(f, "") for f in SERVICE_FIELDS})
            row_out.update({"Encontrada": proc["_found"], "EstatusBusqueda": proc["_message"]})
            second_sheet_rows.append(row_out)

        df_second = pd.DataFrame(second_sheet_rows)
        df_not_found = df_second[df_second["Encontrada"] == "No"].copy()

        source = df_second["InvoiceSource"].apply(self.normalize_invoice_source)
        df_liquidacion_anticipo = df_second[source == "LECTOR XML"].copy()
        df_pago_proveedor = df_second[source == "LECTOR XML PAGO"].copy()
        df_otros = df_second[(source != "LECTOR XML") & (source != "LECTOR XML PAGO")].copy()

        df_original["Encontrada"] = [p.get("_found", "No") for p in processed]
        df_original["EstatusBusqueda"] = [p.get("_message", "") for p in processed]

        with pd.ExcelWriter(self.ruta_salida, engine="openpyxl") as writer:
            df_original.to_excel(writer, sheet_name="Excel_Original", index=False)
            df_second.to_excel(writer, sheet_name="Conciliacion", index=False)
            df_not_found.to_excel(writer, sheet_name="No_Encontradas", index=False)
            df_liquidacion_anticipo.to_excel(writer, sheet_name="Liquidacion de anticipo", index=False)
            df_pago_proveedor.to_excel(writer, sheet_name="Pago Proveedor", index=False)
            df_otros.to_excel(writer, sheet_name="Otros InvoiceSource", index=False)

        datos = json.loads(df_second.to_json(orient="records", force_ascii=False))
        return datos, self.ruta_salida
