"""
Configuración de ambientes de Oracle Fusion.

Cada ambiente apunta al host de Oracle. La URL se puede sobrescribir con
variables de entorno sin tocar el código:
    ORACLE_URL_PROD=https://...
    ORACLE_URL_DEV=https://...

Un ambiente sin URL no aparece en el login.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import tempfile

# Ruta del recurso REST de facturas de Payables
RUTA_FACTURAS = "/fscmRestApi/resources/11.13.18.05/invoices"

AMBIENTES = {
    # "or": si la variable existe pero está vacía, se usa la dirección por defecto (antes ocultaba el ambiente)
    "DEV":  (os.environ.get("ORACLE_URL_DEV") or "https://fa-eqwz-dev1-saasfaprod1.fa.ocs.oraclecloud.com").strip(),
    "PROD": (os.environ.get("ORACLE_URL_PROD") or "https://fa-eqwz-saasfaprod1.fa.ocs.oraclecloud.com").strip(),
}

# Ambiente preseleccionado en el login (si está configurado)
AMBIENTE_DEFECTO = os.environ.get("ORACLE_AMBIENTE_DEFECTO", "DEV")


def ambientes_disponibles():
    """Ambientes con URL configurada, en el orden de AMBIENTES."""
    return [nombre for nombre, url in AMBIENTES.items() if url]


def url_base(ambiente):
    base = AMBIENTES.get(ambiente, "")
    if not base:
        raise ValueError(f"El ambiente '{ambiente}' no tiene URL configurada.")
    return base.rstrip("/")


def url_facturas(ambiente):
    return url_base(ambiente) + RUTA_FACTURAS


# Ruta del recurso REST de proveedores (con sus sitios como hijo "sites")
RUTA_PROVEEDORES = "/fscmRestApi/resources/11.13.18.05/suppliers"


def url_proveedores(ambiente):
    return url_base(ambiente) + RUTA_PROVEEDORES


# ==========================================================
#  Carga por FBDI (servicio erpintegrations)
#  Valores tomados del proceso del robot (Proceso_Carga_Oracle.md / Config.xlsx).
# ==========================================================
RUTA_ERP_INTEGRATIONS = "/fscmRestApi/resources/11.13.18.05/erpintegrations"
UCM_CUENTA = os.environ.get("ORACLE_UCM_CUENTA", "fin$/payables$/import$")

JOB_LOADER_PAQUETE = "oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader"
JOB_LOADER_NOMBRE = "InterfaceLoaderController"
JOB_LOADER_PARAMS = "1,{document_id},N,N,{archivo}"

JOB_IMPORT_PAQUETE = "oracle/apps/ess/financials/payables/invoices/transactions"
JOB_IMPORT_NOMBRE = "APXIIMPT"   # Import Payables Invoices
# Posiciones fijas (N, 1000, Y, 1) tomadas tal cual del script de referencia del robot.
JOB_IMPORT_PARAMS = ",{bu_id},N,{fecha_contable},N,,1000,{origen},,N,Y,{ledger_id},,1"

# Ids internos de la unidad de negocio BU_CSACV y su libro contable (Config.xlsx del robot)
BU_ID = os.environ.get("ORACLE_BU_ID", "300000002907696")
LEDGER_ID = os.environ.get("ORACLE_LEDGER_ID", "300000003009972")

ESS_INTERVALO_SEG = int(os.environ.get("ORACLE_ESS_INTERVALO_SEG", "15"))
ESS_TIMEOUT_MIN = int(os.environ.get("ORACLE_ESS_TIMEOUT_MIN", "30"))
ESS_ESTADOS_FINALES = {"SUCCEEDED", "WARNING", "ERROR", "CANCELLED", "EXPIRED", "ERROR_MANUAL_RECOVERY",
                       "FINISHED", "VALIDATION_FAILED"}

# Zona horaria para "hoy" (fecha contable = día de la carga). Cloud Shell corre en UTC; sin esto, después
# de las 5 pm de Culiacán ya sería el día siguiente (y a fin de mes, el periodo siguiente).
ZONA_HORARIA = os.environ.get("CXP_ZONA_HORARIA", "America/Mazatlan")


def ahora():
    """Fecha y hora de México (número de lote, nombres de archivo, fechas), sin importar la zona del servidor."""
    return datetime.now(ZoneInfo(ZONA_HORARIA))

# Carpeta de trabajo temporal, fuera del proyecto: estado de cada lote (lote.pkl) y, mientras se suben a
# Cloud Storage, el zip enviado y resultado.json. La evidencia permanente queda en Storage.
CARPETA_EVIDENCIAS = os.environ.get("CXP_CARPETA_EVIDENCIAS") or os.path.join(tempfile.gettempdir(), "cxp_web")


def url_erp_integrations(ambiente):
    return url_base(ambiente) + RUTA_ERP_INTEGRATIONS
