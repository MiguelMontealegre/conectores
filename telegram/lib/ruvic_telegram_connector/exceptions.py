"""Excepciones propias del conector Telegram.

Separan los tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor, datos y rate limiting. Nunca exponemos
respuestas crípticas de la Bot API ni de la librería HTTP subyacente.
"""


class TelegramConnectorError(Exception):
    """Error base del conector."""


class TelegramAuthError(TelegramConnectorError):
    """Token de bot inválido o revocado (HTTP 401/404 sobre el token)."""


class TelegramNetworkError(TelegramConnectorError):
    """No se pudo alcanzar api.telegram.org (red, DNS, timeout)."""


class TelegramDataError(TelegramConnectorError):
    """La operación es válida pero los datos no: chat inexistente,
    bot expulsado del grupo, archivo demasiado grande, parámetros inválidos."""


class TelegramRateLimitError(TelegramConnectorError):
    """Telegram limitó las peticiones (HTTP 429). Incluye los segundos a esperar."""

    def __init__(self, message: str, retry_after: int = 0) -> None:
        super().__init__(message)
        self.retry_after = retry_after
