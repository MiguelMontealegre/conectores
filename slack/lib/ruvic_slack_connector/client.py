"""Cliente para la Web API de Slack.

Capacidades:
- send_message():        enviar mensajes a un canal o a un usuario (DM).
- send_direct_message(): enviar un mensaje directo a un usuario por su ID.
- get_channel_info():    obtener información de un canal.
- list_channels():       listar los canales visibles para el bot.
- auth_test():           identidad del bot (usado por la prueba de conexión).

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_SLACK_*
(ver config.SlackConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import requests

from .config import SlackConfig
from .exceptions import (
    SlackAuthError,
    SlackDataError,
    SlackNetworkError,
    SlackRateLimitError,
)
from .logging_utils import get_logger

_API_BASE = "https://slack.com/api"

# Códigos de error de Slack que significan "problema de credenciales/scopes".
_AUTH_ERRORS = {
    "invalid_auth",
    "not_authed",
    "account_inactive",
    "token_revoked",
    "token_expired",
    "no_permission",
    "missing_scope",
    "not_allowed_token_type",
}


class SlackClient:
    """Cliente de la Web API de Slack.

    Args:
        config: configuración del conector. Si se omite, se lee de las
            variables de entorno RUVIC_SLACK_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = SlackClient()   # lee RUVIC_SLACK_* del entorno
        >>> client.send_message("Hola equipo", channel="#general")
        {'ok': True, 'channel': 'C0123ABCD', 'ts': '1767225600.000100'}
    """

    def __init__(self, config: SlackConfig | None = None) -> None:
        self.config = config or SlackConfig.from_env()
        self._logger = get_logger()
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    # Núcleo HTTP
    # ------------------------------------------------------------------ #

    def _call(
        self,
        method: str,
        payload: dict[str, Any] | None = None,
        http_method: str = "POST",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Invoca un método de la Web API y retorna el cuerpo JSON completo.

        Traduce todos los fallos a excepciones propias del conector.
        Nunca incluye el token en logs ni en mensajes de error.
        """
        url = f"{_API_BASE}/{method}"
        headers = {"Authorization": f"Bearer {self.config.bot_token}"}
        effective_timeout = timeout or self.config.timeout
        try:
            if http_method == "GET":
                response = self._session.get(
                    url,
                    headers=headers,
                    params=payload or {},
                    timeout=effective_timeout,
                )
            else:
                # chat.postMessage y familia aceptan JSON con Bearer token.
                response = self._session.post(
                    url,
                    headers={**headers, "Content-Type": "application/json; charset=utf-8"},
                    json=payload or {},
                    timeout=effective_timeout,
                )
        except requests.Timeout as exc:
            raise SlackNetworkError(
                f"Timeout de {effective_timeout}s llamando a la Web API de "
                f"Slack ({method}). Verifica la conectividad de red."
            ) from exc
        except requests.RequestException as exc:
            raise SlackNetworkError(
                "No se pudo alcanzar slack.com. Verifica la conexión de red "
                "y que el runtime tenga salida HTTPS."
            ) from exc

        # Slack usa HTTP 429 para rate limiting con cabecera Retry-After.
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1") or 1)
            raise SlackRateLimitError(
                f"Slack limitó las peticiones; reintenta en {retry_after}s.",
                retry_after=retry_after,
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise SlackNetworkError(
                f"Respuesta no válida de la Web API de Slack (HTTP "
                f"{response.status_code}) en {method}."
            ) from exc

        if body.get("ok"):
            return body

        error = body.get("error", "unknown_error")

        if error in _AUTH_ERRORS:
            raise SlackAuthError(
                f"Fallo de autenticación de Slack ({error}). El token es "
                "inválido/revocado o le falta un scope. Revisa el Bot Token "
                "(xoxb-…) y los scopes de la app en Settings → Conectores."
            )
        # channel_not_found, not_in_channel, is_archived, user_not_found,
        # invalid_arguments, msg_too_long, restricted_action…
        raise SlackDataError(
            f"Slack rechazó la operación {method}: {error}. "
            "Verifica el destino (canal/usuario), que el bot esté invitado "
            "al canal y los parámetros enviados."
        )

    def _resolve_channel(self, channel: str | None) -> str:
        """Retorna el destino efectivo (argumento o default del conector)."""
        effective = channel if channel is not None else self.config.default_channel
        if effective is None or str(effective).strip() == "":
            raise SlackDataError(
                "No se indicó destino y el conector no tiene un canal por "
                "defecto configurado (RUVIC_SLACK_DEFAULT_CHANNEL). Pasa "
                "channel explícitamente o configura el valor por defecto."
            )
        return str(effective).strip()

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def auth_test(self) -> dict[str, Any]:
        """Retorna la identidad del bot y del workspace (auth.test).

        Ejemplo:
            >>> client.auth_test()
            {'user': 'ruvic_bot', 'user_id': 'U0123', 'team': 'Ruvic',
             'team_id': 'T0123', 'url': 'https://ruvic.slack.com/'}
        """
        result = self._call("auth.test")
        return {
            "user": result.get("user"),
            "user_id": result.get("user_id"),
            "bot_id": result.get("bot_id"),
            "team": result.get("team"),
            "team_id": result.get("team_id"),
            "url": result.get("url"),
        }

    def ping(self) -> bool:
        """Verifica token y conectividad llamando auth.test.

        Returns:
            True si la conexión funciona.

        Raises:
            SlackAuthError / SlackNetworkError según el fallo.
        """
        me = self.auth_test()
        self._logger.info(
            "Ping exitoso como %s en el workspace %s",
            me.get("user"),
            me.get("team"),
        )
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: enviar mensajes a canales y usuarios
    # ------------------------------------------------------------------ #

    def send_message(
        self,
        text: str,
        channel: str | None = None,
        thread_ts: str | None = None,
        blocks: list[dict[str, Any]] | None = None,
        unfurl_links: bool = True,
    ) -> dict[str, Any]:
        """Envía un mensaje a un canal o a un usuario (DM).

        Args:
            text: contenido del mensaje. Admite formato mrkdwn de Slack
                (*negrita*, _cursiva_, `código`, <url|texto>).
            channel: destino. Puede ser:
                - ID de canal ("C0123ABCD"),
                - nombre de canal con "#" ("#general"),
                - ID de usuario ("U0123ABCD") → se abre un DM automáticamente.
                Si se omite, usa el destino por defecto del conector.
            thread_ts: `ts` de un mensaje para responder en su hilo.
            blocks: bloques Block Kit para mensajes enriquecidos. Cuando se
                usan, `text` funciona como texto de respaldo/notificación.
            unfurl_links: True (default) expande vistas previas de enlaces.

        Returns:
            Dict con ok, channel (ID) y ts (timestamp/ID del mensaje).

        Ejemplo:
            >>> client.send_message("Backup completado ✅", channel="#ops")
            {'ok': True, 'channel': 'C0123', 'ts': '1767225600.000100'}
        """
        if (not text or not text.strip()) and not blocks:
            raise SlackDataError(
                "El mensaje no puede estar vacío: indica `text` o `blocks`."
            )

        destination = self._resolve_channel(channel)
        # Si el destino es un ID de usuario, abrimos un DM y usamos su canal.
        if destination.startswith(("U", "W")):
            destination = self._open_dm(destination)

        payload: dict[str, Any] = {
            "channel": destination,
            "text": text,
            "unfurl_links": unfurl_links,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if blocks:
            payload["blocks"] = blocks

        result = self._call("chat.postMessage", payload)
        self._logger.info(
            "Mensaje %s enviado al canal %s",
            result.get("ts"),
            result.get("channel"),
        )
        return {
            "ok": True,
            "channel": result.get("channel"),
            "ts": result.get("ts"),
        }

    def send_direct_message(
        self,
        text: str,
        user_id: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Envía un mensaje directo (DM) a un usuario por su ID.

        Atajo explícito de send_message para el caso de mensajería a
        personas: abre (o reutiliza) el canal de DM con el usuario y publica.

        Args:
            text: contenido del mensaje (formato mrkdwn de Slack).
            user_id: ID del usuario destino ("U0123ABCD"). Se obtiene del
                perfil del usuario en Slack o con users.list.
            blocks: bloques Block Kit opcionales.

        Returns:
            Dict con ok, channel (el DM) y ts.

        Ejemplo:
            >>> client.send_direct_message("¿Revisas el PR?", user_id="U0123")
            {'ok': True, 'channel': 'D0123', 'ts': '1767225600.000100'}
        """
        if not user_id or not user_id.strip():
            raise SlackDataError("Debes indicar el user_id del destinatario.")
        return self.send_message(text, channel=user_id.strip(), blocks=blocks)

    def _open_dm(self, user_id: str) -> str:
        """Abre (o reutiliza) el canal de DM con un usuario y retorna su ID."""
        result = self._call("conversations.open", {"users": user_id})
        channel_id = (result.get("channel") or {}).get("id")
        if not channel_id:
            raise SlackDataError(
                f"No se pudo abrir un mensaje directo con el usuario {user_id!r}. "
                "Verifica el ID de usuario y el scope im:write."
            )
        return channel_id

    # ------------------------------------------------------------------ #
    # Capacidad 2: información y descubrimiento de canales
    # ------------------------------------------------------------------ #

    def get_channel_info(self, channel: str | None = None) -> dict[str, Any]:
        """Obtiene información de un canal (conversations.info).

        Args:
            channel: ID del canal a consultar ("C0123ABCD"). Default: destino
                por defecto del conector. (No aplica a IDs de usuario.)

        Returns:
            Dict con id, name, is_private, is_member, num_members y topic.

        Ejemplo:
            >>> client.get_channel_info("C0123ABCD")
            {'id': 'C0123ABCD', 'name': 'general', 'is_member': True, ...}
        """
        target = self._resolve_channel(channel)
        result = self._call(
            "conversations.info", {"channel": target}, http_method="GET"
        )
        ch = result.get("channel", {})
        return {
            "id": ch.get("id"),
            "name": ch.get("name"),
            "is_private": ch.get("is_private"),
            "is_member": ch.get("is_member"),
            "num_members": ch.get("num_members"),
            "topic": (ch.get("topic") or {}).get("value"),
        }

    def list_channels(
        self,
        limit: int = 200,
        types: str = "public_channel,private_channel",
    ) -> list[dict[str, Any]]:
        """Lista los canales del workspace visibles para el bot.

        Útil para resolver un nombre de canal a su ID.

        Args:
            limit: máximo de canales a retornar (1-1000).
            types: tipos de conversación separados por coma
                ("public_channel", "private_channel", "mpim", "im").

        Returns:
            Lista de dicts con id, name, is_private e is_member.

        Ejemplo:
            >>> for c in client.list_channels():
            ...     print(c["name"], c["id"])
        """
        result = self._call(
            "conversations.list",
            {"limit": max(1, min(int(limit), 1000)), "types": types},
            http_method="GET",
        )
        channels = []
        for ch in result.get("channels", []):
            channels.append(
                {
                    "id": ch.get("id"),
                    "name": ch.get("name"),
                    "is_private": ch.get("is_private"),
                    "is_member": ch.get("is_member"),
                }
            )
        self._logger.info("Listados %d canales", len(channels))
        return channels
