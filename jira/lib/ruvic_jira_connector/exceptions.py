"""Excepciones propias del conector Jira.

Separan los tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor, datos y rate limiting. Nunca exponemos
respuestas crípticas de la REST API ni de la librería HTTP subyacente.
"""


class JiraConnectorError(Exception):
    """Error base del conector."""


class JiraAuthError(JiraConnectorError):
    """Credenciales inválidas o sin permisos (HTTP 401/403).

    Email/API token incorrectos, token revocado, o la cuenta no tiene
    permiso para la operación (crear en el proyecto, transicionar, etc.).
    """


class JiraNetworkError(JiraConnectorError):
    """No se pudo alcanzar el sitio de Jira (red, DNS, timeout, 5xx)."""


class JiraDataError(JiraConnectorError):
    """La operación es válida pero los datos no: issue/proyecto inexistente,
    transición no permitida, JQL inválido, campos obligatorios faltantes."""


class JiraRateLimitError(JiraConnectorError):
    """Jira limitó las peticiones (HTTP 429). Incluye los segundos a esperar."""

    def __init__(self, message: str, retry_after: int = 0) -> None:
        super().__init__(message)
        self.retry_after = retry_after
