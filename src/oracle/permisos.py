"""
REGLA: Oracle PROD es solo lectura.

Este es el único lugar que decide en qué ambientes se puede escribir (cargar facturas).
Cualquier escritura en Oracle pasa por verificar_ambiente_carga(), aunque la interfaz lo permitiera.
"""
AMBIENTES_CARGA = {"DEV"}


class CargaNoPermitida(Exception):
    pass


def verificar_ambiente_carga(ambiente):
    if ambiente not in AMBIENTES_CARGA:
        raise CargaNoPermitida(f"La carga de facturas está bloqueada en Oracle {ambiente}. Solo se permite en: "
                               f"{', '.join(sorted(AMBIENTES_CARGA))}.")
