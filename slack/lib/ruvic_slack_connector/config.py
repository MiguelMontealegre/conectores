"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_SLACK_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_SLACK_"


@dataclass(frozen=True)
class SlackConfig:
    """Parámetros de conexión a la Web API de Slack.

    Attributes:
        bot_token: token de bot de la app de Slack (empieza por xoxb-).
        default_channel: canal/usuario destino por defecto (opcional). Si
            está definido, los métodos de envío pueden omitir el destino.
            Puede ser un ID de canal (C…), un ID de usuario (U…) o un
            nombre de canal con "#" (ej. "#general").
        timeout: timeout en segundos para cada petición HTTP.
    """

    bot_token: str
    default_channel: str | None = None
    timeout: int = 15

    @classmethod
    def from_env(cls) -> "SlackConfig":
        """Construye la configuración desde las variables RUVIC_SLACK_*.

        Raises:
            ValueError: si falta alguna variable obligatoria.

        Ejemplo:
            >>> config = SlackConfig.from_env()
            >>> config.timeout
            15
        """
        token = os.environ.get(f"{ENV_PREFIX}BOT_TOKEN")
        if not token:
            raise ValueError(
                f"Falta la variable de entorno {ENV_PREFIX}BOT_TOKEN del conector "
                "slack. Configura el conector en Settings → Conectores."
            )
        default_channel = os.environ.get(f"{ENV_PREFIX}DEFAULT_CHANNEL") or None
        return cls(
            bot_token=token,
            default_channel=default_channel,
            timeout=int(os.environ.get(f"{ENV_PREFIX}TIMEOUT", "15")),
        )
