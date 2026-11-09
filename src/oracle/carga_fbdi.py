"""
Carga de facturas en Oracle Payables por FBDI con el servicio REST erpintegrations.
Adaptado del proceso del robot (Proceso_Carga_Oracle.md):

  ZIP -> Base64 -> uploadFileToUCM                     -> DocumentId
      -> submitESSJobRequest InterfaceLoaderController  -> ReqstId -> esperar estado final
      -> submitESSJobRequest APXIIMPT                   -> ReqstId -> esperar estado final
      -> GET invoices por cada factura (registrada / rechazada)
      -> evidencia local: cargas/<lote>/ (zip enviado + resultado.json)

REGLA: solo se permite en los ambientes de cargador.AMBIENTES_CARGA (DEV). PROD queda bloqueado aquí.
"""
import base64
import json
import time
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

from src import config
from src.oracle.facturas import buscar_existentes
from src.oracle.permisos import verificar_ambiente_carga

HEADERS = {"Content-Type": "application/json; charset=utf-8", "Accept": "application/json",
           "User-Agent": "CXP-WEB/1.0"}
REINTENTOS = 3
CODIGOS_REINTENTO = {429, 503}


class ErrorCarga(Exception):
    pass


class CargaFBDI:
    """
    Ejecuta la carga paso a paso e informa el avance con `aviso(paso, mensaje, datos)`.
    `aviso` se llama desde el hilo de la carga (la app lo usa para mostrar el avance en pantalla).
    """

    def __init__(self, ambiente, usuario, password, aviso=None, dormir=time.sleep):
        verificar_ambiente_carga(ambiente)
        self.ambiente = ambiente
        self.usuario, self.password = usuario, password
        self.url = config.url_erp_integrations(ambiente)
        self.auth = HTTPBasicAuth(usuario, password)
        self.aviso = aviso or (lambda *a, **k: None)
        self.dormir = dormir

    # ---------- HTTP con reintentos (solo 429/503, como el robot) ----------
    def _llamar(self, metodo, url, **kw):
        ultimo = None
        for intento in range(1, REINTENTOS + 1):
            try:
                r = requests.request(metodo, url, auth=self.auth, headers=HEADERS, timeout=180, **kw)
            except requests.RequestException as e:
                raise ErrorCarga(f"Sin respuesta de Oracle ({type(e).__name__}).")
            if r.status_code not in CODIGOS_REINTENTO:
                return r
            ultimo = r
            self.dormir(5 * intento)
        return ultimo

    @staticmethod
    def _error_http(paso, r):
        if r.status_code == 401:
            return ErrorCarga(f"{paso}: Oracle respondió 401 (usuario o contraseña).")
        if r.status_code == 403:
            return ErrorCarga(f"{paso}: Oracle respondió 403 (sin permiso para esta operación).")
        return ErrorCarga(f"{paso}: HTTP {r.status_code} {(r.text or '').strip()[:500]}")

    # ---------- Pasos ----------
    def subir_ucm(self, nombre_zip, contenido):
        r = self._llamar("POST", self.url, json={
            "OperationName": "uploadFileToUCM",   # 'UCM' en mayúsculas (con 'Ucm' Oracle responde 400)
            "DocumentContent": base64.b64encode(contenido).decode("ascii"),
            "DocumentAccount": config.UCM_CUENTA,
            "ContentType": "zip",
            "FileName": nombre_zip,
            "DocumentId": None,
        })
        if not r.ok:
            raise self._error_http("Subida a UCM", r)
        doc_id = (r.json() or {}).get("DocumentId")
        if not doc_id:
            raise ErrorCarga("Subida a UCM: Oracle no devolvió DocumentId.")
        return str(doc_id)

    def lanzar_job(self, paso, paquete, nombre, parametros):
        r = self._llamar("POST", self.url, json={
            "OperationName": "submitESSJobRequest",
            "JobPackageName": paquete,
            "JobDefName": nombre,
            "ESSParameters": parametros,
        })
        if not r.ok:
            raise self._error_http(paso, r)
        req = str((r.json() or {}).get("ReqstId") or "")
        if not req or req == "-1":
            raise ErrorCarga(f"{paso}: Oracle no devolvió el número de job (ReqstId).")
        return req

    def esperar_job(self, paso, req_id):
        limite = time.monotonic() + config.ESS_TIMEOUT_MIN * 60
        while True:
            r = self._llamar("GET", self.url, params={"finder": f"ESSJobStatusRF;requestId={req_id}"})
            if not r.ok:
                raise self._error_http(f"{paso} (estado del job {req_id})", r)
            items = (r.json() or {}).get("items") or []
            estado = (items[0].get("RequestStatus") if items else "") or "DESCONOCIDO"
            self.aviso(paso, f"Job {req_id}: {estado}", {"job": req_id, "estado": estado})
            if estado in config.ESS_ESTADOS_FINALES:
                return estado
            if time.monotonic() > limite:
                raise ErrorCarga(f"{paso}: el job {req_id} no terminó en {config.ESS_TIMEOUT_MIN} minutos.")
            self.dormir(config.ESS_INTERVALO_SEG)

    # ---------- Proceso completo ----------
    def ejecutar(self, nombre_zip, contenido, numeros_factura, fecha_contable, origen, carpeta_evidencia):
        """
        numeros_factura: INVOICE_NUM de cada factura del zip (ya con prefijo si lo hay).
        Devuelve el resultado (también se guarda en carpeta_evidencia/resultado.json).
        """
        res = {"ambiente": self.ambiente, "archivo": nombre_zip, "inicio": config.ahora().isoformat(timespec="seconds"),
               "usuario": self.usuario, "fecha_contable": str(fecha_contable), "origen": origen,
               "document_id": None, "job_loader": None, "estado_loader": None,
               "job_import": None, "estado_import": None, "facturas": [], "error": None}
        carpeta = Path(carpeta_evidencia)
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre_zip).write_bytes(contenido)
        try:
            self.aviso("ucm", "Subiendo el archivo a Oracle (UCM)...", {})
            res["document_id"] = self.subir_ucm(nombre_zip, contenido)
            self.aviso("ucm", f"Archivo en UCM: DocumentId {res['document_id']}", {"document_id": res["document_id"]})

            self.aviso("loader", "Cargando el archivo a las tablas de interfaz...", {})
            res["job_loader"] = self.lanzar_job(
                "Carga a interfaz", config.JOB_LOADER_PAQUETE, config.JOB_LOADER_NOMBRE,
                config.JOB_LOADER_PARAMS.format(document_id=res["document_id"], archivo=nombre_zip))
            res["estado_loader"] = self.esperar_job("loader", res["job_loader"])
            if res["estado_loader"] != "SUCCEEDED":
                raise ErrorCarga(f"La carga a interfaz (job {res['job_loader']}) terminó en {res['estado_loader']}. "
                                 f"Revisa su log en Oracle > Procesos programados.")

            self.aviso("import", "Importando facturas en Payables...", {})
            res["job_import"] = self.lanzar_job(
                "Importación de facturas", config.JOB_IMPORT_PAQUETE, config.JOB_IMPORT_NOMBRE,
                config.JOB_IMPORT_PARAMS.format(bu_id=config.BU_ID, ledger_id=config.LEDGER_ID, origen=origen,
                                                fecha_contable=fecha_contable.strftime("%Y-%m-%d")))
            res["estado_import"] = self.esperar_job("import", res["job_import"])

            # Aunque APXIIMPT termine bien, Oracle puede rechazar facturas sueltas: confirmar una por una
            self.aviso("confirmar", "Confirmando cada factura en Oracle...", {})
            existentes = buscar_existentes(self.ambiente, self.usuario, self.password, numeros_factura)
            for num in numeros_factura:
                ex = existentes.get(num)
                if isinstance(ex, str) and ex.startswith("ERROR"):
                    res["facturas"].append({"numero": num, "resultado": "SIN_CONFIRMAR", "detalle": ex[7:]})
                elif ex:
                    res["facturas"].append({"numero": num, "resultado": "FACTURA_REGISTRADA",
                                            "InvoiceId": ex if ex != "sí" else None})
                else:
                    res["facturas"].append({"numero": num, "resultado": "RECHAZO_ORACLE",
                                            "detalle": f"Ver 'Manage Payables Invoice Import Rejections' del job {res['job_import']}"})
        except ErrorCarga as e:
            res["error"] = str(e)
        finally:
            res["fin"] = config.ahora().isoformat(timespec="seconds")
            (carpeta / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        return res
