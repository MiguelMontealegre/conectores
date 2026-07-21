"""Excepciones propias del conector Slack.

Separan los tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor, datos y rate limiting. Nunca exponemos
respuestas crípticas de la Web API ni de la librería HTTP subyacente.
"""


class SlackConnectorError(Exception):
    """Error base del conector."""


class SlackAuthError(SlackConnectorError):
    """Token inválido, revocado o sin los scopes necesarios
    (invalid_auth, not_authed, account_inactive, token_revoked,
    missing_scope)."""


class SlackNetworkError(SlackConnectorError):
    """No se pudo alcanzar slack.com (red, DNS, timeout, respuesta no válida)."""


class SlackDataError(SlackConnectorError):
    """La operación es válida pero los datos no: canal inexistente, bot no
    invitado al canal, usuario desconocido, parámetros inválidos."""


class SlackRateLimitError(SlackConnectorError):
    """Slack limitó las peticiones (HTTP 429). Incluye los segundos a esperar."""

    def __init__(self, message: str, retry_after: int = 0) -> None:
        super().__init__(message)
        self.retry_after = retry_after
