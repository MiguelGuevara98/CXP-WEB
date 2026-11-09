"""
Casos de uso de la app: orquestan dominio + Oracle. No dependen de Flask.
Los errores para el usuario se lanzan como ErrorServicio(mensaje, codigo_http).
"""


class ErrorServicio(Exception):
    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
