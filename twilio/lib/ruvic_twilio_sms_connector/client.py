"""Cliente para Twilio Programmable Messaging (SMS).

Capacidades:
- send_sms():        enviar un SMS transaccional a un número.
- get_status():      consultar el estado de entrega de un mensaje por SID.
- list_messages():   listar mensajes recientes (con filtros opcionales).

Autenticación (se infiere de las env vars, ver config.py):
- auth_token: Account SID + Auth Token.
- api_key:    Account SID + API Key SID + API Key Secret (recomendado).

Las credenciales SIEMPRE provienen de variables de entorno
RUVIC_TWILIO_SMS_* (ver config.TwilioSmsConfig.from_env). Prohibido
hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from .config import TwilioSmsConfig
from .exceptions import (
    TwilioSmsAuthError,
    TwilioSmsDataError,
    TwilioSmsNetworkError,
    TwilioSmsRateLimitError,
)
from .logging_utils import get_logger

_API_BASE = "https://api.twilio.com/2010-04-01"

# Longitud típica de un segmento SMS (GSM-7). Informativo para el logging.
_SEGMENT_LEN = 160


def _mask(number: str | None) -> str:
    """Ofusca un número de teléfono para logs (deja país + últimos 2)."""
    if not number:
        return "(desconocido)"
    if len(number) <= 4:
        return "***"
    return f"{number[:3]}***{number[-2:]}"


class TwilioSmsClient:
    """Cliente de envío de SMS por Twilio.

    Args:
        config: configuración del conector. Si se omite, se lee de las
            variables de entorno RUVIC_TWILIO_SMS_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = TwilioSmsClient()   # lee RUVIC_TWILIO_SMS_* del entorno
        >>> client.send_sms("+573001234567", "Tu código es 4821")
        {'sid': 'SMxxxx', 'status': 'queued', 'to': '+57***67'}
    """

    def __init__(self, config: TwilioSmsConfig | None = None) -> None:
        self.config = config or TwilioSmsConfig.from_env()
        self._logger = get_logger()
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(self.config.username, self.config.password)

    # ------------------------------------------------------------------ #
    # Núcleo HTTP
    # ------------------------------------------------------------------ #

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una petición a la API de Twilio y traduce fallos.

        Nunca incluye credenciales en logs ni en mensajes de error.
        """
        url = f"{_API_BASE}/Accounts/{self.config.account_sid}{path}"
        try:
            response = self._session.request(
                method,
                url,
                data=data,
                params=params,
                timeout=self.config.timeout,
            )
        except requests.Timeout as exc:
            raise TwilioSmsNetworkError(
                f"Timeout de {self.config.timeout}s llamando a la API de "
                "Twilio. Verifica la conectividad de red."
            ) from exc
        except requests.RequestException as exc:
            raise TwilioSmsNetworkError(
                "No se pudo alcanzar api.twilio.com. Verifica la conexión de "
                "red y que el runtime tenga salida HTTPS."
            ) from exc

        if response.status_code < 300:
            try:
                return response.json()
            except ValueError:
                return {}

        # Error: la API de Twilio devuelve JSON con 'code' y 'message'.
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        code = payload.get("code")
        detail = payload.get("message", "")

        if response.status_code == 401:
            raise TwilioSmsAuthError(
                "Credenciales inválidas (HTTP 401). Verifica el Account SID y "
                + (
                    "el Auth Token"
                    if self.config.mode == "auth_token"
                    else "la API Key SID/Secret"
                )
                + " en Settings → Conectores."
            )
        if response.status_code == 429:
            raise TwilioSmsRateLimitError(
                "Twilio limitó las peticiones (HTTP 429). Espera unos "
                "segundos y reintenta."
            )
        # 400/404: casi siempre datos (número inválido, no verificado, etc.).
        raise TwilioSmsDataError(
            f"Twilio rechazó la operación (HTTP {response.status_code}"
            + (f", código {code}" if code else "")
            + ")."
            + (f" {detail}" if detail else "")
            + " Verifica los números y el contenido del mensaje.",
            code=code,
        )

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica credenciales SIN enviar SMS: consulta la cuenta.

        Returns:
            True si la conexión funciona.

        Raises:
            TwilioSmsAuthError / TwilioSmsNetworkError según el fallo.
        """
        self._request("GET", ".json")
        self._logger.info("Ping exitoso a la cuenta %s", self.config.account_sid)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: enviar SMS
    # ------------------------------------------------------------------ #

    def send_sms(
        self,
        to: str,
        body: str,
        status_callback: str | None = None,
    ) -> dict[str, Any]:
        """Envía un SMS a un número de teléfono.

        Args:
            to: número destino en formato E.164 (ej. "+573001234567").
            body: contenido del mensaje. Los SMS se dividen en segmentos de
                ~160 caracteres (GSM-7) o ~70 (Unicode); Twilio los une.
            status_callback: (opcional) URL a la que Twilio notificará los
                cambios de estado de entrega.

        Returns:
            Dict con sid (identificador del mensaje), status inicial, to y
            num_segments estimado.

        Ejemplo:
            >>> client.send_sms("+573001234567", "Tu código OTP es 4821")
            {'sid': 'SMxxxx', 'status': 'queued', 'to': '+57***67', ...}
        """
        if not to or not to.startswith("+"):
            raise TwilioSmsDataError(
                f"Número destino inválido: {to!r}. Usa formato E.164, "
                "empezando por '+' y el código de país (ej. +573001234567)."
            )
        if not body or not body.strip():
            raise TwilioSmsDataError("El cuerpo del SMS no puede estar vacío.")

        data: dict[str, Any] = {"To": to, "Body": body}
        # Remitente: Messaging Service tiene prioridad si ambos están definidos.
        if self.config.messaging_service_sid:
            data["MessagingServiceSid"] = self.config.messaging_service_sid
        else:
            data["From"] = self.config.from_number
        if status_callback:
            data["StatusCallback"] = status_callback

        result = self._request("POST", "/Messages.json", data=data)
        self._logger.info(
            "SMS %s encolado hacia %s (%s segmento(s) est.)",
            result.get("sid"),
            _mask(to),
            result.get("num_segments") or (len(body) // _SEGMENT_LEN + 1),
        )
        return {
            "sid": result.get("sid"),
            "status": result.get("status"),
            "to": _mask(result.get("to")),
            "num_segments": result.get("num_segments"),
            "date_created": result.get("date_created"),
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2: consultar estado de un mensaje
    # ------------------------------------------------------------------ #

    def get_status(self, message_sid: str) -> dict[str, Any]:
        """Consulta el estado de entrega de un mensaje por su SID.

        Estados posibles de Twilio: queued, sending, sent, delivered,
        undelivered, failed, received.

        Args:
            message_sid: SID del mensaje (empieza por "SM" o "MM").

        Returns:
            Dict con sid, status, to, error_code y error_message (estos dos
            últimos poblados si el envío falló).

        Ejemplo:
            >>> client.get_status("SMxxxx")
            {'sid': 'SMxxxx', 'status': 'delivered', 'error_code': None}
        """
        if not message_sid or not message_sid.startswith(("SM", "MM")):
            raise TwilioSmsDataError(
                f"SID de mensaje inválido: {message_sid!r}. Debe empezar por "
                "'SM' (o 'MM' para MMS)."
            )
        result = self._request("GET", f"/Messages/{message_sid}.json")
        return {
            "sid": result.get("sid"),
            "status": result.get("status"),
            "to": _mask(result.get("to")),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
            "date_sent": result.get("date_sent"),
            "price": result.get("price"),
        }

    # ------------------------------------------------------------------ #
    # Capacidad 3: listar mensajes recientes
    # ------------------------------------------------------------------ #

    def list_messages(
        self,
        to: str | None = None,
        date_sent: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista mensajes recientes de la cuenta, con filtros opcionales.

        Args:
            to: filtra por número destino (E.164).
            date_sent: filtra por fecha de envío (formato "YYYY-MM-DD").
            limit: máximo de mensajes a retornar (1-1000).

        Returns:
            Lista de dicts: {sid, status, to, from, date_sent}.

        Ejemplo:
            >>> client.list_messages(limit=10)
            [{'sid': 'SMxxxx', 'status': 'delivered', ...}, ...]
        """
        limit = max(1, min(int(limit), 1000))
        params: dict[str, Any] = {"PageSize": min(limit, 1000)}
        if to:
            params["To"] = to
        if date_sent:
            params["DateSent"] = date_sent

        result = self._request("GET", "/Messages.json", params=params)
        messages = []
        for m in result.get("messages", [])[:limit]:
            messages.append(
                {
                    "sid": m.get("sid"),
                    "status": m.get("status"),
                    "to": _mask(m.get("to")),
                    "from": _mask(m.get("from")),
                    "date_sent": m.get("date_sent"),
                }
            )
        self._logger.info("Listados %d mensajes", len(messages))
        return messages
