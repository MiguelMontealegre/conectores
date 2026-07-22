"""Excepciones propias del conector Aranda ASMS.

Separan los tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor, datos y rate limiting. Nunca exponemos
respuestas crípticas de la API ni de la librería HTTP subyacente.
"""


class ArandaConnectorError(Exception):
    """Error base del conector."""


class ArandaAuthError(ArandaConnectorError):
    """Token inválido, expirado o sin permisos (HTTP 401/403)."""


class ArandaNetworkError(ArandaConnectorError):
    """No se pudo alcanzar el servidor de Aranda (red, DNS, timeout, TLS, 5xx)."""


class ArandaDataError(ArandaConnectorError):
    """La operación es válida pero los datos no: id inexistente, parámetros
    inválidos, combinación no permitida, campos obligatorios faltantes."""


class ArandaRateLimitError(ArandaConnectorError):
    """Aranda limitó las peticiones (HTTP 429). Incluye los segundos a esperar."""

    def __init__(self, message: str, retry_after: int = 0) -> None:
        super().__init__(message)
        self.retry_after = retry_after
