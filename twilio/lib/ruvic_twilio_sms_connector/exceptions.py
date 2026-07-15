"""Excepciones propias del conector Twilio SMS.

Separan los tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor, datos y rate limiting. Nunca exponemos
respuestas crípticas de la API de Twilio ni de la librería HTTP.
"""


class TwilioSmsConnectorError(Exception):
    """Error base del conector."""


class TwilioSmsAuthError(TwilioSmsConnectorError):
    """Credenciales inválidas: Account SID / Auth Token o API key/secret
    incorrectos (HTTP 401)."""


class TwilioSmsNetworkError(TwilioSmsConnectorError):
    """No se pudo alcanzar api.twilio.com (red, DNS, timeout)."""


class TwilioSmsDataError(TwilioSmsConnectorError):
    """La operación es válida pero los datos no: número 'to'/'from' inválido,
    número no verificado (cuenta trial), mensaje vacío, SID inexistente.
    Incluye el código de error de Twilio cuando está disponible."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class TwilioSmsRateLimitError(TwilioSmsConnectorError):
    """Twilio limitó las peticiones (HTTP 429)."""
