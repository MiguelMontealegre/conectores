"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_JIRA_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_JIRA_"


@dataclass(frozen=True)
class JiraConfig:
    """Parámetros de conexión a la REST API de Jira Cloud.

    Attributes:
        base_url: URL del sitio de Jira, ej. "https://miempresa.atlassian.net".
        email: correo de la cuenta de Atlassian dueña del API token.
        api_token: API token generado en id.atlassian.com (secreto).
        default_project: clave de proyecto por defecto (opcional), ej. "OPS".
            Si está definida, create_issue puede omitir el proyecto.
        timeout: timeout en segundos para cada petición HTTP.
    """

    base_url: str
    email: str
    api_token: str
    default_project: str | None = None
    timeout: int = 20

    @classmethod
    def from_env(cls) -> "JiraConfig":
        """Construye la configuración desde las variables RUVIC_JIRA_*.

        Raises:
            ValueError: si falta alguna variable obligatoria.

        Ejemplo:
            >>> config = JiraConfig.from_env()
            >>> config.timeout
            20
        """
        base_url = os.environ.get(f"{ENV_PREFIX}BASE_URL")
        email = os.environ.get(f"{ENV_PREFIX}EMAIL")
        api_token = os.environ.get(f"{ENV_PREFIX}API_TOKEN")

        missing = [
            name
            for name, value in (
                (f"{ENV_PREFIX}BASE_URL", base_url),
                (f"{ENV_PREFIX}EMAIL", email),
                (f"{ENV_PREFIX}API_TOKEN", api_token),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno obligatorias del conector jira: "
                f"{', '.join(missing)}. Configura el conector en "
                "Settings → Conectores."
            )

        assert base_url is not None and email is not None and api_token is not None
        return cls(
            base_url=base_url.rstrip("/"),
            email=email,
            api_token=api_token,
            default_project=os.environ.get(f"{ENV_PREFIX}DEFAULT_PROJECT") or None,
            timeout=int(os.environ.get(f"{ENV_PREFIX}TIMEOUT", "20")),
        )
