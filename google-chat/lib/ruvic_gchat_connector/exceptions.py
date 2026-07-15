"""Excepciones propias del conector Google Chat.

Separan los tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor, datos y rate limiting. Nunca exponemos
respuestas crípticas de la API de Google ni de la librería HTTP.
"""


class GchatConnectorError(Exception):
    """Error base del conector."""


class GchatAuthError(GchatConnectorError):
    """Credenciales inválidas: webhook con key/token incorrecto, JSON de
    cuenta de servicio inválido, API no habilitada o permisos insuficientes."""


class GchatNetworkError(GchatConnectorError):
    """No se pudo alcanzar chat.googleapis.com (red, DNS, timeout)."""


class GchatDataError(GchatConnectorError):
    """La operación es válida pero los datos no: espacio inexistente,
    la app no es miembro del espacio, mensaje mal formado."""


class GchatRateLimitError(GchatConnectorError):
    """Google limitó las peticiones (HTTP 429)."""
