"""Cliente para Google Chat: mensajería a espacios.

Capacidades:
- send_message():  enviar mensajes de texto a un espacio (ambos modos),
                   con soporte de hilos (thread_key).
- list_spaces():   listar los espacios donde la app está agregada
                   (solo modo service_account).
- get_space():     información de un espacio (solo modo service_account).

Modos de autenticación (se infieren de las env vars, ver config.py):
- webhook:          envía SOLO al espacio del webhook configurado.
- service_account:  Chat API con credenciales de app; envía a cualquier
                    espacio donde la app de Chat esté agregada.

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_GCHAT_*
(ver config.GchatConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import requests

from .config import MODE_SERVICE_ACCOUNT, MODE_WEBHOOK, GchatConfig
from .exceptions import (
    GchatAuthError,
    GchatDataError,
    GchatNetworkError,
    GchatRateLimitError,
)
from .logging_utils import get_logger

_API_BASE = "https://chat.googleapis.com/v1"
_SCOPE = "https://www.googleapis.com/auth/chat.bot"

# Límite de la API para el campo text de un mensaje.
_MAX_TEXT_CHARS = 4096


class GchatClient:
    """Cliente de mensajería para espacios de Google Chat.

    Args:
        config: configuración del conector. Si se omite, se lee de las
            variables de entorno RUVIC_GCHAT_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = GchatClient()   # lee RUVIC_GCHAT_* del entorno
        >>> client.send_message("Despliegue completado ✅")
        {'message_name': 'spaces/AAA/messages/BBB', 'space': 'spaces/AAA'}
    """

    def __init__(self, config: GchatConfig | None = None) -> None:
        self.config = config or GchatConfig.from_env()
        self._logger = get_logger()
        self._session = requests.Session()
        self._credentials = None  # lazy, solo modo service_account

    # ------------------------------------------------------------------ #
    # Autenticación (modo service_account)
    # ------------------------------------------------------------------ #

    def _access_token(self) -> str:
        """Obtiene (y refresca si es necesario) el access token de la app."""
        if self.config.mode != MODE_SERVICE_ACCOUNT:
            raise GchatAuthError(
                "Esta operación requiere el modo 'cuenta de servicio'. El "
                "conector está configurado en modo webhook, que solo permite "
                "enviar mensajes al espacio del webhook."
            )
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
        except ImportError as exc:  # pragma: no cover
            raise GchatAuthError(
                "Falta la dependencia google-auth. Reinstala la librería del "
                "conector (pip install ruvic-gchat-connector)."
            ) from exc

        if self._credentials is None:
            try:
                self._credentials = (
                    service_account.Credentials.from_service_account_info(
                        self.config.service_account_info, scopes=[_SCOPE]
                    )
                )
            except ValueError as exc:
                raise GchatAuthError(
                    "El JSON de la cuenta de servicio es inválido o está "
                    "incompleto (revisa que sea el archivo descargado de "
                    "Google Cloud Console sin modificar)."
                ) from exc
        try:
            if not self._credentials.valid:
                self._credentials.refresh(Request())
        except Exception as exc:
            raise GchatAuthError(
                "No se pudo obtener un token con la cuenta de servicio. "
                "Verifica que la clave no esté revocada y que la API de "
                "Google Chat esté habilitada en el proyecto."
            ) from exc
        return self._credentials.token

    # ------------------------------------------------------------------ #
    # Núcleo HTTP
    # ------------------------------------------------------------------ #

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una petición HTTP y traduce fallos a excepciones propias.

        Nunca incluye credenciales (token, key del webhook) en logs ni en
        mensajes de error.
        """
        try:
            response = self._session.request(
                method,
                url,
                json=json_body,
                params=params,
                headers=headers,
                timeout=self.config.timeout,
            )
        except requests.Timeout as exc:
            raise GchatNetworkError(
                f"Timeout de {self.config.timeout}s llamando a Google Chat. "
                "Verifica la conectividad de red."
            ) from exc
        except requests.RequestException as exc:
            raise GchatNetworkError(
                "No se pudo alcanzar chat.googleapis.com. Verifica la "
                "conexión de red y que el runtime tenga salida HTTPS."
            ) from exc

        if response.status_code < 300:
            try:
                return response.json() if response.content else {}
            except ValueError:
                return {}

        # Error: intentar extraer el mensaje de la API.
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = ""

        if response.status_code in (401, 403):
            raise GchatAuthError(
                "Google Chat rechazó las credenciales (HTTP "
                f"{response.status_code}). "
                + (
                    "Verifica que la URL del webhook esté completa (incluye "
                    "los parámetros key y token)."
                    if self.config.mode == MODE_WEBHOOK
                    else "Verifica que la API de Google Chat esté habilitada "
                    "en el proyecto, que la app de Chat esté configurada y "
                    "que la cuenta de servicio sea la del proyecto correcto."
                )
                + (f" Detalle: {detail}" if detail else "")
            )
        if response.status_code == 404:
            raise GchatDataError(
                "Recurso no encontrado en Google Chat. Verifica el nombre del "
                "espacio (formato spaces/XXXX) y que la app/webhook siga "
                "agregada al espacio."
                + (f" Detalle: {detail}" if detail else "")
            )
        if response.status_code == 429:
            raise GchatRateLimitError(
                "Google Chat limitó las peticiones (HTTP 429). Espera unos "
                "segundos y reintenta."
            )
        raise GchatDataError(
            f"Google Chat rechazó la operación (HTTP {response.status_code})."
            + (f" Detalle: {detail}" if detail else "")
            + " Verifica los parámetros del mensaje."
        )

    def _resolve_space(self, space: str | None) -> str:
        """Retorna el espacio efectivo (argumento o default del conector)."""
        effective = space or self.config.default_space
        if not effective:
            raise GchatDataError(
                "No se indicó el espacio y el conector no tiene un espacio "
                "por defecto configurado (RUVIC_GCHAT_DEFAULT_SPACE). Pasa "
                "space='spaces/XXXX' o configura el valor por defecto."
            )
        return effective if effective.startswith("spaces/") else f"spaces/{effective}"

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica credenciales y conectividad SIN publicar mensajes.

        - Modo service_account: obtiene un token y llama spaces.list.
        - Modo webhook: envía un POST vacío; un webhook válido responde
          400 (payload inválido) — credenciales incorrectas responden
          401/403/404. No se publica nada en el espacio.

        Returns:
            True si la conexión funciona.

        Raises:
            GchatAuthError / GchatNetworkError / GchatDataError según el fallo.
        """
        if self.config.mode == MODE_SERVICE_ACCOUNT:
            token = self._access_token()
            self._request(
                "GET",
                f"{_API_BASE}/spaces",
                params={"pageSize": 1},
                headers={"Authorization": f"Bearer {token}"},
            )
            self._logger.info("Ping exitoso (service_account)")
            return True

        # Modo webhook: POST vacío → 400 esperado si la URL es válida.
        try:
            self._request("POST", self.config.webhook_url, json_body={})
        except GchatDataError:
            pass  # 400/"text required": la URL y sus credenciales son válidas
        self._logger.info("Ping exitoso (webhook)")
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: enviar mensaje a un espacio
    # ------------------------------------------------------------------ #

    def send_message(
        self,
        text: str,
        space: str | None = None,
        thread_key: str | None = None,
    ) -> dict[str, Any]:
        """Envía un mensaje de texto a un espacio de Google Chat.

        Args:
            text: contenido del mensaje (máx. 4096 caracteres). Soporta el
                formato básico de Chat: *negrita*, _cursiva_, ~tachado~,
                `código` y <URL|texto>.
            space: espacio destino, formato "spaces/XXXX". Solo aplica en
                modo service_account; en modo webhook el destino es siempre
                el espacio del webhook. Si se omite, usa el espacio por
                defecto del conector.
            thread_key: clave arbitraria para agrupar mensajes en un mismo
                hilo (los mensajes con igual thread_key caen al mismo hilo).

        Returns:
            Dict con message_name (identificador del mensaje), space y
            thread del mensaje creado.

        Ejemplo:
            >>> client.send_message("Backup completado ✅")
            {'message_name': 'spaces/AAA/messages/BBB.CCC', 'space': 'spaces/AAA'}
        """
        if not text or not text.strip():
            raise GchatDataError("El texto del mensaje no puede estar vacío.")
        if len(text) > _MAX_TEXT_CHARS:
            raise GchatDataError(
                f"El mensaje tiene {len(text)} caracteres; el máximo de "
                f"Google Chat es {_MAX_TEXT_CHARS}. Divide el contenido en "
                "varios mensajes."
            )
        body: dict[str, Any] = {"text": text}

        if self.config.mode == MODE_WEBHOOK:
            params: dict[str, Any] = {}
            if thread_key:
                params["messageReplyOption"] = (
                    "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"
                )
                body["thread"] = {"threadKey": thread_key}
            result = self._request(
                "POST", self.config.webhook_url, json_body=body, params=params
            )
        else:
            target = self._resolve_space(space)
            token = self._access_token()
            params = {}
            if thread_key:
                params["messageReplyOption"] = (
                    "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"
                )
                body["thread"] = {"threadKey": thread_key}
            result = self._request(
                "POST",
                f"{_API_BASE}/{target}/messages",
                json_body=body,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )

        message_name = result.get("name", "")
        space_name = (result.get("space") or {}).get("name") or (
            message_name.rsplit("/messages/", 1)[0] if message_name else None
        )
        self._logger.info("Mensaje enviado a %s", space_name or "el espacio")
        return {
            "message_name": message_name,
            "space": space_name,
            "thread": (result.get("thread") or {}).get("name"),
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2: listar espacios (solo service_account)
    # ------------------------------------------------------------------ #

    def list_spaces(self, page_size: int = 100) -> list[dict[str, Any]]:
        """Lista los espacios donde la app de Chat está agregada.

        Solo disponible en modo service_account.

        Args:
            page_size: máximo de espacios a retornar (1-1000).

        Returns:
            Lista de dicts: {"name", "display_name", "type"}.

        Ejemplo:
            >>> client.list_spaces()
            [{'name': 'spaces/AAA', 'display_name': 'Operaciones', 'type': 'SPACE'}]
        """
        token = self._access_token()
        spaces: list[dict[str, Any]] = []
        page_token: str | None = None
        page_size = max(1, min(int(page_size), 1000))
        while True:
            params: dict[str, Any] = {"pageSize": min(page_size, 100)}
            if page_token:
                params["pageToken"] = page_token
            result = self._request(
                "GET",
                f"{_API_BASE}/spaces",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            for item in result.get("spaces", []):
                spaces.append(
                    {
                        "name": item.get("name"),
                        "display_name": item.get("displayName"),
                        "type": item.get("spaceType") or item.get("type"),
                    }
                )
            page_token = result.get("nextPageToken")
            if not page_token or len(spaces) >= page_size:
                break
        self._logger.info("Listados %d espacios", len(spaces))
        return spaces[:page_size]

    # ------------------------------------------------------------------ #
    # Capacidad 3: información de un espacio (solo service_account)
    # ------------------------------------------------------------------ #

    def get_space(self, space: str | None = None) -> dict[str, Any]:
        """Obtiene información de un espacio.

        Solo disponible en modo service_account.

        Args:
            space: espacio a consultar, formato "spaces/XXXX". Default:
                espacio por defecto del conector.

        Returns:
            Dict con name, display_name, type y threaded.

        Ejemplo:
            >>> client.get_space("spaces/AAAAAAAAAAA")
            {'name': 'spaces/AAAAAAAAAAA', 'display_name': 'Operaciones', ...}
        """
        target = self._resolve_space(space)
        token = self._access_token()
        result = self._request(
            "GET",
            f"{_API_BASE}/{target}",
            headers={"Authorization": f"Bearer {token}"},
        )
        return {
            "name": result.get("name"),
            "display_name": result.get("displayName"),
            "type": result.get("spaceType") or result.get("type"),
            "threaded": result.get("spaceThreadingState"),
        }
