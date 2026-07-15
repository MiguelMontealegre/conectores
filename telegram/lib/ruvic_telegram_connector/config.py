"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_TELEGRAM_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_TELEGRAM_"


@dataclass(frozen=True)
class TelegramConfig:
    """Parámetros de conexión a la Bot API de Telegram.

    Attributes:
        bot_token: token del bot emitido por @BotFather.
        default_chat_id: chat/grupo destino por defecto (opcional). Si está
            definido, los métodos de envío pueden omitir chat_id.
        timeout: timeout en segundos para cada petición HTTP.
    """

    bot_token: str
    default_chat_id: str | None = None
    timeout: int = 15

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        """Construye la configuración desde las variables RUVIC_TELEGRAM_*.

        Raises:
            ValueError: si falta alguna variable obligatoria.

        Ejemplo:
            >>> config = TelegramConfig.from_env()
            >>> config.timeout
            15
        """
        token = os.environ.get(f"{ENV_PREFIX}BOT_TOKEN")
        if not token:
            raise ValueError(
                f"Falta la variable de entorno {ENV_PREFIX}BOT_TOKEN del conector "
                "telegram. Configura el conector en Settings → Conectores."
            )
        default_chat = os.environ.get(f"{ENV_PREFIX}DEFAULT_CHAT_ID") or None
        return cls(
            bot_token=token,
            default_chat_id=default_chat,
            timeout=int(os.environ.get(f"{ENV_PREFIX}TIMEOUT", "15")),
        )
