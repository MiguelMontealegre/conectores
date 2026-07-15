"""Cliente para la Bot API de Telegram.

Capacidades:
- send_message():   enviar mensajes de texto a chats, grupos o canales.
- send_file():      enviar archivos (documento, foto, video, audio).
- get_updates():    recibir actualizaciones (mensajes entrantes) del bot.
- get_chat():       obtener información de un chat/grupo/canal.
- get_me():         identidad del bot (usado por la prueba de conexión).

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_TELEGRAM_*
(ver config.TelegramConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests

from .config import TelegramConfig
from .exceptions import (
    TelegramAuthError,
    TelegramDataError,
    TelegramNetworkError,
    TelegramRateLimitError,
)
from .logging_utils import get_logger

_API_BASE = "https://api.telegram.org"

# Tipos de archivo soportados por send_file y su método de la Bot API.
_FILE_KINDS = {
    "document": ("sendDocument", "document"),
    "photo": ("sendPhoto", "photo"),
    "video": ("sendVideo", "video"),
    "audio": ("sendAudio", "audio"),
}

# Límite de subida de la Bot API para bots estándar (50 MB).
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class TelegramClient:
    """Cliente de la Bot API de Telegram.

    Args:
        config: configuración del conector. Si se omite, se lee de las
            variables de entorno RUVIC_TELEGRAM_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = TelegramClient()   # lee RUVIC_TELEGRAM_* del entorno
        >>> client.send_message("Hola equipo", chat_id="-1001234567890")
        {'message_id': 42, 'chat_id': -1001234567890, ...}
    """

    def __init__(self, config: TelegramConfig | None = None) -> None:
        self.config = config or TelegramConfig.from_env()
        self._logger = get_logger()
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    # Núcleo HTTP
    # ------------------------------------------------------------------ #

    def _call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> Any:
        """Invoca un método de la Bot API y retorna su campo `result`.

        Traduce todos los fallos a excepciones propias del conector.
        Nunca incluye el token en logs ni en mensajes de error.
        """
        url = f"{_API_BASE}/bot{self.config.bot_token}/{method}"
        try:
            response = self._session.post(
                url,
                data=params or {},
                files=files,
                timeout=timeout or self.config.timeout,
            )
        except requests.Timeout as exc:
            raise TelegramNetworkError(
                f"Timeout de {timeout or self.config.timeout}s llamando a la API "
                f"de Telegram ({method}). Verifica la conectividad de red."
            ) from exc
        except requests.RequestException as exc:
            raise TelegramNetworkError(
                "No se pudo alcanzar api.telegram.org. Verifica la conexión "
                "de red y que el runtime tenga salida HTTPS."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise TelegramNetworkError(
                f"Respuesta no válida de la API de Telegram (HTTP "
                f"{response.status_code}) en {method}."
            ) from exc

        if payload.get("ok"):
            return payload.get("result")

        code = payload.get("error_code", response.status_code)
        description = payload.get("description", "sin descripción")

        if code == 401 or (code == 404 and method != "getFile"):
            raise TelegramAuthError(
                "Token de bot inválido o revocado. Genera/copia el token "
                "correcto en @BotFather y actualízalo en Settings → Conectores."
            )
        if code == 429:
            retry_after = int(
                (payload.get("parameters") or {}).get("retry_after", 0)
            )
            raise TelegramRateLimitError(
                f"Telegram limitó las peticiones; reintenta en {retry_after}s.",
                retry_after=retry_after,
            )
        # 400 (bad request), 403 (bot bloqueado/expulsado), 409 (webhook activo)…
        raise TelegramDataError(
            f"Telegram rechazó la operación {method}: {description}. "
            "Verifica el chat_id, que el bot sea miembro del chat y los "
            "parámetros enviados."
        )

    def _resolve_chat_id(self, chat_id: str | int | None) -> str:
        """Retorna el chat_id efectivo (argumento o default del conector)."""
        effective = chat_id if chat_id is not None else self.config.default_chat_id
        if effective is None or str(effective).strip() == "":
            raise TelegramDataError(
                "No se indicó chat_id y el conector no tiene un chat por "
                "defecto configurado (RUVIC_TELEGRAM_DEFAULT_CHAT_ID). "
                "Pasa chat_id explícitamente o configura el valor por defecto."
            )
        return str(effective)

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def get_me(self) -> dict[str, Any]:
        """Retorna la identidad del bot (id, username, nombre).

        Ejemplo:
            >>> client.get_me()
            {'id': 123456, 'username': 'ruvic_bot', 'first_name': 'Ruvic'}
        """
        result = self._call("getMe")
        return {
            "id": result.get("id"),
            "username": result.get("username"),
            "first_name": result.get("first_name"),
            "can_join_groups": result.get("can_join_groups"),
        }

    def ping(self) -> bool:
        """Verifica token y conectividad llamando getMe.

        Returns:
            True si la conexión funciona.

        Raises:
            TelegramAuthError / TelegramNetworkError según el fallo.
        """
        me = self.get_me()
        self._logger.info("Ping exitoso como @%s", me.get("username"))
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: enviar mensajes
    # ------------------------------------------------------------------ #

    def send_message(
        self,
        text: str,
        chat_id: str | int | None = None,
        parse_mode: str | None = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
    ) -> dict[str, Any]:
        """Envía un mensaje de texto a un chat, grupo o canal.

        Args:
            text: contenido del mensaje (máx. 4096 caracteres).
            chat_id: destino. ID numérico ("123456", "-1001234567890" para
                supergrupos/canales) o "@nombre_canal" para canales públicos.
                Si se omite, usa el chat por defecto del conector.
            parse_mode: None (texto plano), "HTML" o "MarkdownV2".
            disable_notification: True = envío silencioso (sin sonido).
            reply_to_message_id: responder a un mensaje específico.

        Returns:
            Dict con message_id, chat_id y date del mensaje enviado.

        Ejemplo:
            >>> client.send_message("Backup completado ✅")
            {'message_id': 42, 'chat_id': -1001234567890, 'date': 1767225600}
        """
        if not text or not text.strip():
            raise TelegramDataError("El texto del mensaje no puede estar vacío.")
        if len(text) > 4096:
            raise TelegramDataError(
                f"El mensaje tiene {len(text)} caracteres; el máximo de "
                "Telegram es 4096. Divide el contenido en varios mensajes."
            )
        params: dict[str, Any] = {
            "chat_id": self._resolve_chat_id(chat_id),
            "text": text,
            "disable_notification": disable_notification,
        }
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_to_message_id:
            params["reply_to_message_id"] = reply_to_message_id
        result = self._call("sendMessage", params)
        self._logger.info(
            "Mensaje %s enviado al chat %s",
            result.get("message_id"),
            result.get("chat", {}).get("id"),
        )
        return {
            "message_id": result.get("message_id"),
            "chat_id": result.get("chat", {}).get("id"),
            "date": result.get("date"),
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2: enviar archivos
    # ------------------------------------------------------------------ #

    def send_file(
        self,
        file_path: str,
        chat_id: str | int | None = None,
        caption: str | None = None,
        kind: str = "document",
        disable_notification: bool = False,
    ) -> dict[str, Any]:
        """Envía un archivo local a un chat, grupo o canal.

        Args:
            file_path: ruta del archivo en el sistema local.
            chat_id: destino (ver send_message). Default: chat del conector.
            caption: texto que acompaña al archivo (máx. 1024 caracteres).
            kind: "document" (default, cualquier archivo), "photo",
                "video" o "audio".
            disable_notification: True = envío silencioso.

        Returns:
            Dict con message_id, chat_id y file_name enviado.

        Ejemplo:
            >>> client.send_file("/tmp/reporte.pdf", caption="Reporte mensual")
            {'message_id': 43, 'chat_id': -1001234567890, 'file_name': 'reporte.pdf'}
        """
        if kind not in _FILE_KINDS:
            raise TelegramDataError(
                f"Tipo de archivo inválido: {kind!r}. "
                f"Usa uno de: {', '.join(sorted(_FILE_KINDS))}."
            )
        path = Path(file_path)
        if not path.is_file():
            raise TelegramDataError(f"El archivo no existe: {file_path}")
        size = path.stat().st_size
        if size > _MAX_UPLOAD_BYTES:
            raise TelegramDataError(
                f"El archivo pesa {size / (1024 * 1024):.1f} MB; la Bot API "
                "permite máximo 50 MB por archivo."
            )
        method, field = _FILE_KINDS[kind]
        params: dict[str, Any] = {
            "chat_id": self._resolve_chat_id(chat_id),
            "disable_notification": disable_notification,
        }
        if caption:
            params["caption"] = caption[:1024]
        with path.open("rb") as handle:
            result = self._call(
                method,
                params,
                files={field: (path.name, handle)},
                timeout=max(self.config.timeout, 60),  # subidas tardan más
            )
        self._logger.info(
            "Archivo %s (%d bytes) enviado al chat %s",
            path.name,
            size,
            result.get("chat", {}).get("id"),
        )
        return {
            "message_id": result.get("message_id"),
            "chat_id": result.get("chat", {}).get("id"),
            "file_name": path.name,
        }

    # ------------------------------------------------------------------ #
    # Capacidad 3: recibir actualizaciones (mensajes entrantes)
    # ------------------------------------------------------------------ #

    def get_updates(
        self,
        offset: int | None = None,
        limit: int = 100,
        timeout: int = 0,
    ) -> list[dict[str, Any]]:
        """Obtiene actualizaciones pendientes del bot (mensajes recibidos).

        Telegram entrega cada actualización una sola vez por offset: para
        "consumir" las ya procesadas, vuelve a llamar con
        offset = último update_id + 1.

        Args:
            offset: primer update_id a retornar (None = las pendientes).
            limit: máximo de actualizaciones (1-100).
            timeout: segundos de long polling (0 = respuesta inmediata).

        Returns:
            Lista de dicts simplificados: {update_id, type, chat_id,
            chat_title, from_user, text, date}. El campo `raw` conserva la
            actualización completa por si se necesita más detalle.

        Ejemplo:
            >>> updates = client.get_updates()
            >>> for u in updates:
            ...     print(u["from_user"], ":", u["text"])
        """
        params: dict[str, Any] = {
            "limit": max(1, min(int(limit), 100)),
            "timeout": max(0, int(timeout)),
        }
        if offset is not None:
            params["offset"] = int(offset)
        results = self._call(
            "getUpdates", params, timeout=self.config.timeout + params["timeout"]
        )
        updates: list[dict[str, Any]] = []
        for item in results:
            message = (
                item.get("message")
                or item.get("edited_message")
                or item.get("channel_post")
                or {}
            )
            chat = message.get("chat", {})
            sender = message.get("from", {})
            updates.append(
                {
                    "update_id": item.get("update_id"),
                    "type": next(
                        (k for k in item if k != "update_id"), "unknown"
                    ),
                    "chat_id": chat.get("id"),
                    "chat_title": chat.get("title") or chat.get("username"),
                    "from_user": sender.get("username")
                    or sender.get("first_name"),
                    "text": message.get("text") or message.get("caption"),
                    "date": message.get("date"),
                    "raw": item,
                }
            )
        self._logger.info("Recibidas %d actualizaciones", len(updates))
        return updates

    # ------------------------------------------------------------------ #
    # Capacidad 4: información de un chat
    # ------------------------------------------------------------------ #

    def get_chat(self, chat_id: str | int | None = None) -> dict[str, Any]:
        """Obtiene información de un chat, grupo o canal.

        Args:
            chat_id: chat a consultar. Default: chat por defecto del conector.

        Returns:
            Dict con id, type ("private", "group", "supergroup", "channel"),
            title/username y description si aplica.

        Ejemplo:
            >>> client.get_chat("-1001234567890")
            {'id': -1001234567890, 'type': 'supergroup', 'title': 'Ops Ruvic'}
        """
        result = self._call(
            "getChat", {"chat_id": self._resolve_chat_id(chat_id)}
        )
        return {
            "id": result.get("id"),
            "type": result.get("type"),
            "title": result.get("title"),
            "username": result.get("username"),
            "description": result.get("description"),
        }
