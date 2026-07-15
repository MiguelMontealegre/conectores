"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_GCHAT_.

El conector soporta dos modos de autenticación (auth_modes del manifest):

- "webhook":          RUVIC_GCHAT_WEBHOOK_URL definida.
- "service_account":  RUVIC_GCHAT_SERVICE_ACCOUNT_JSON definida.

El modo se infiere de cuál variable está presente; si ambas existen,
prevalece la cuenta de servicio (modo más completo).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_GCHAT_"

MODE_WEBHOOK = "webhook"
MODE_SERVICE_ACCOUNT = "service_account"


@dataclass(frozen=True)
class GchatConfig:
    """Parámetros de conexión a Google Chat.

    Attributes:
        mode: "webhook" o "service_account".
        webhook_url: URL del webhook entrante (modo webhook).
        service_account_info: dict del JSON de la cuenta de servicio
            (modo service_account).
        default_space: espacio destino por defecto, formato "spaces/XXXX"
            (solo aplica en modo service_account).
        timeout: timeout en segundos para cada petición HTTP.
    """

    mode: str
    webhook_url: str | None = None
    service_account_info: dict | None = None
    default_space: str | None = None
    timeout: int = 15

    @classmethod
    def from_env(cls) -> "GchatConfig":
        """Construye la configuración desde las variables RUVIC_GCHAT_*.

        Raises:
            ValueError: si no hay credenciales de ningún modo, o si el JSON
                de la cuenta de servicio es inválido.

        Ejemplo:
            >>> config = GchatConfig.from_env()
            >>> config.mode
            'service_account'
        """
        webhook_url = os.environ.get(f"{ENV_PREFIX}WEBHOOK_URL") or None
        sa_json = os.environ.get(f"{ENV_PREFIX}SERVICE_ACCOUNT_JSON") or None
        default_space = os.environ.get(f"{ENV_PREFIX}DEFAULT_SPACE") or None
        timeout = int(os.environ.get(f"{ENV_PREFIX}TIMEOUT", "15"))

        if sa_json:
            try:
                info = json.loads(sa_json)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"La variable {ENV_PREFIX}SERVICE_ACCOUNT_JSON no contiene "
                    "un JSON válido. Pega el contenido completo del archivo de "
                    "credenciales de la cuenta de servicio en Settings → "
                    "Conectores."
                ) from exc
            if info.get("type") != "service_account" or "private_key" not in info:
                raise ValueError(
                    f"El JSON de {ENV_PREFIX}SERVICE_ACCOUNT_JSON no es un "
                    "archivo de credenciales de cuenta de servicio de Google "
                    "(falta type=service_account o private_key)."
                )
            if default_space and not default_space.startswith("spaces/"):
                default_space = f"spaces/{default_space}"
            return cls(
                mode=MODE_SERVICE_ACCOUNT,
                service_account_info=info,
                default_space=default_space,
                timeout=timeout,
            )

        if webhook_url:
            if not webhook_url.startswith("https://chat.googleapis.com/"):
                raise ValueError(
                    f"La variable {ENV_PREFIX}WEBHOOK_URL no parece un webhook "
                    "de Google Chat (debe empezar por "
                    "https://chat.googleapis.com/). Cópiala completa desde "
                    "Apps e integraciones → Webhooks del espacio."
                )
            return cls(mode=MODE_WEBHOOK, webhook_url=webhook_url, timeout=timeout)

        raise ValueError(
            "Faltan credenciales del conector gchat: define "
            f"{ENV_PREFIX}WEBHOOK_URL (modo webhook) o "
            f"{ENV_PREFIX}SERVICE_ACCOUNT_JSON (modo cuenta de servicio). "
            "Configura el conector en Settings → Conectores."
        )
