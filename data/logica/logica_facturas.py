import os
import json 
import math
import tempfile
import time
import traceback
from decimal import Decimal, InvalidOperation
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "https://fa-eqwz-saasfaprod1.fa.ocs.oraclecloud.com/fscmRestApi/resources/11.13.18.05/invoices"
MAX_WORKERS = 10
TIMEOUT = 60

# ==============================================================
#  🔧 CONFIGURACIÓN DE REINTENTOS (para errores de conexión)
#  MAX_REINTENTOS : cuántas veces reintenta antes de marcar error
#  ESPERA_REINTENTO: segundos base entre intentos (backoff lineal)
#                    intento 1 → 2s, intento 2 → 4s, intento 3 → 6s
# ==============================================================
MAX_REINTENTOS   = 3
ESPERA_REINTENTO = 2  # segundos base

COL_FOLIO = "Folio C.F.D.I."
COL_TOTAL = "Total"
SERVICE_FIELDS = ["InvoiceDate", "InvoiceCurrency", "BusinessUnit", "ValidationStatus", "Supplier", "SupplierNumber", "SupplierSite", "Party", "CreationDate", "AccountingDate", "Description", "InvoiceSource", "InvoiceType", "PaymentTerms", "TermsDate", "PaymentMethod", "LiabilityDistribution", "PaidStatus"]


EXCEL_FIELDS_FOR_SECOND_SHEET = ["Folio C.F.D.I.", "Modelo de dominio de proveedor", "Sistema", "Nombre del Beneficiario", "RFC", "Total"]

class ProcesadorOracle:
    def __init__(self, ruta_entrada, username, password):
        self.ruta_entrada = ruta_entrada
        self.username = username
        self.password = password
        self.fd, self.ruta_salida = tempfile.mkstemp(suffix=".xlsx")
        os.close(self.fd)

    def safe_str(self, value):
        return "" if pd.isna(value) else str(value).strip()

    def to_decimal(self, value):
        if value is None or (isinstance(value, float) and math.isnan(value)): return None
        text = str(value).strip().replace(",", "")
        try: return Decimal(text)
        except (InvalidOperation, ValueError): return None

    def decimals_equal(self, a, b, tolerance=Decimal("0.01")):
        if a is None or b is None: return False
        return abs(a - b) <= tolerance

    def normalize_for_excel(self, value):
        if isinstance(value, (list, dict)): return json.dumps(value, ensure_ascii=False)
        return value

    
    def normalize_invoice_source(self, value):
        return self.safe_str(value).upper()

    def read_input_file(self):
        ext = os.path.splitext(self.ruta_entrada)[1].lower()
        if ext == ".xlsx": return pd.read_excel(self.ruta_entrada, dtype=object)
        if ext == ".xls":
            try:
                tables = pd.read_html(self.ruta_entrada, encoding='utf-8')
            except Exception:
                tables = pd.read_html(self.ruta_entrada, encoding='latin1')
            if tables:
                for t in tables:
                    df = t.copy()
                    if "Folio C.F.D.I." in df.columns: return df
                    df.columns = [str(c).strip() for c in df.iloc[0]]
                    if "Folio C.F.D.I." in df.columns: return df.iloc[1:].reset_index(drop=True)
            try: return pd.read_excel(self.ruta_entrada, dtype=object, engine="xlrd")
            except: raise ValueError("Formato no soportado.")
        return pd.read_excel(self.ruta_entrada, dtype=object)

    def build_session(self):
        session = requests.Session()
        usuario_limpio = str(self.username).strip()
        password_limpia = str(self.password).strip()
        
        session.auth = HTTPBasicAuth(usuario_limpio, password_limpia)
        
        
        session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PostmanRuntime/7.36.1", 
            "Connection": "keep-alive"
        })
        return session

    def _get_con_reintento(self, session, url):
        """
        Ejecuta un GET con reintentos automáticos ante errores de conexión.
        Aplica backoff lineal entre intentos: 2s, 4s, 6s...
        Lanza la excepción original si agota todos los intentos.
        """
        ultimo_error = None
        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                response = session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
                return response
            except Exception as e:
                ultimo_error = e
                if intento < MAX_REINTENTOS:
                    espera = ESPERA_REINTENTO * intento
                    print(f"[REINTENTO {intento}/{MAX_REINTENTOS}] GET {url} → {type(e).__name__} | esperando {espera}s")
                    time.sleep(espera)
        raise ultimo_error

    def query_invoice_by_folio(self, session, folio):
        url_cruda = f"{BASE_URL}?q=InvoiceNumber={folio}"
        response = self._get_con_reintento(session, url_cruda)
        return response.json()

    def process_row(self, row_dict):
        session = self.build_session()
        folio = self.safe_str(row_dict.get(COL_FOLIO))
        total_excel = row_dict.get(COL_TOTAL)
        
        
        result = {"_folio": folio, "_found": "No", "_message": "", "Amount": ""}
        for f in SERVICE_FIELDS: result[f] = ""
        
        if not folio: return result
        
        try:
            payload = self.query_invoice_by_folio(session, folio)
            items = payload.get("items", [])
            
            if not items:
                result["_message"] = "No encontrada"
                return result

            excel_total_dec = self.to_decimal(total_excel)
            correct_invoice = next((i for i in items if self.decimals_equal(self.to_decimal(i.get("InvoiceAmount")), excel_total_dec)), None)
            
            if correct_invoice:
                result.update({"_found": "Sí", "_message": "Encontrada"})
                for f in SERVICE_FIELDS: result[f] = self.normalize_for_excel(correct_invoice.get(f, ""))
                result["Amount"] = self.normalize_for_excel(correct_invoice.get("InvoiceAmount", ""))
                return result
            
            
            first_invoice = items[0]
            for f in SERVICE_FIELDS: result[f] = self.normalize_for_excel(first_invoice.get(f, ""))
            result["Amount"] = self.normalize_for_excel(first_invoice.get("InvoiceAmount", ""))
            result["_message"] = "Monto diferente al del Excel"
            return result
            
        except Exception as e:
            tipo_err = type(e).__name__   # ej: "ConnectionError", "Timeout", "HTTPError"
            result["_message"] = f"Error tras {MAX_REINTENTOS} reintentos: {tipo_err}"
            return result

    def ejecutar_cruce(self):
        df = self.read_input_file()
        df_original = df.copy()
        df.columns = [self.safe_str(c) for c in df.columns]
        rows = df.to_dict(orient="records")
        results = []
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_index = {executor.submit(self.process_row, row): idx for idx, row in enumerate(rows)}
            for future in as_completed(future_to_index):
                results.append((future_to_index[future], future.result()))
                
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
        
        source_normalized = df_second["InvoiceSource"].apply(self.normalize_invoice_source)
        df_liquidacion_anticipo = df_second[source_normalized == "LECTOR XML"].copy()
        df_pago_proveedor = df_second[source_normalized == "LECTOR XML PAGO"].copy()
        df_otros_invoice_source = df_second[
            (source_normalized != "LECTOR XML") &
            (source_normalized != "LECTOR XML PAGO")
        ].copy()
        
        df_original["Encontrada"] = [p.get("_found", "No") for p in processed]
        df_original["EstatusBusqueda"] = [p.get("_message", "") for p in processed]
        
        
        with pd.ExcelWriter(self.ruta_salida, engine="openpyxl") as writer:
            df_original.to_excel(writer, sheet_name="Excel_Original", index=False)
            df_second.to_excel(writer, sheet_name="Conciliacion", index=False)
            df_not_found.to_excel(writer, sheet_name="No_Encontradas", index=False)
            df_liquidacion_anticipo.to_excel(writer, sheet_name="Liquidacion de anticipo", index=False)
            df_pago_proveedor.to_excel(writer, sheet_name="Pago Proveedor", index=False)
            df_otros_invoice_source.to_excel(writer, sheet_name="Otros InvoiceSource", index=False)
            
        return df_second.to_dict(orient="records"), self.ruta_salida