"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_ARANDA_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_ARANDA_"

_DEFAULT_BASE_URL = "https://proyectos.arandasoft.com/asmsapi/api/v9"


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on", "si", "sí"}


@dataclass(frozen=True)
class ArandaConfig:
    """Parámetros de conexión a la API de Aranda ASMS (v9).

    Attributes:
        token: token de integración de Aranda. Va en la cabecera
            X-Authorization. Puede incluir o no el prefijo "Bearer "
            (se normaliza automáticamente).
        base_url: URL base de la API, ej.
            "https://proyectos.arandasoft.com/asmsapi/api/v9".
        verify_ssl: si se valida el certificado TLS. Muchas instalaciones
            de Aranda usan certificados internos; por defecto False para
            replicar el comportamiento de las skills originales.
        timeout: timeout en segundos para cada petición HTTP.
    """

    token: str
    base_url: str = _DEFAULT_BASE_URL
    verify_ssl: bool = False
    timeout: int = 30

    @property
    def auth_header(self) -> str:
        """Valor de la cabecera X-Authorization, con prefijo Bearer normalizado."""
        token = self.token.strip()
        if token.lower().startswith("bearer "):
            return token
        return f"Bearer {token}"

    @classmethod
    def from_env(cls) -> "ArandaConfig":
        """Construye la configuración desde las variables RUVIC_ARANDA_*.

        Raises:
            ValueError: si falta el token (única variable obligatoria).

        Ejemplo:
            >>> config = ArandaConfig.from_env()
            >>> config.timeout
            30
        """
        token = os.environ.get(f"{ENV_PREFIX}TOKEN")
        if not token:
            raise ValueError(
                f"Falta la variable de entorno {ENV_PREFIX}TOKEN del conector "
                "aranda. Configura el conector en Settings → Conectores."
            )
        return cls(
            token=token,
            base_url=(os.environ.get(f"{ENV_PREFIX}BASE_URL") or _DEFAULT_BASE_URL).rstrip("/"),
            verify_ssl=_as_bool(os.environ.get(f"{ENV_PREFIX}VERIFY_SSL"), False),
            timeout=int(os.environ.get(f"{ENV_PREFIX}TIMEOUT", "30")),
        )
