"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_TWILIO_SMS_.

El conector soporta dos modos de autenticación (auth_modes del manifest):

- "auth_token":  Account SID + Auth Token (Basic Auth simple).
- "api_key":     Account SID + API Key SID + API Key Secret (recomendado
                 por Twilio para producción).

En ambos casos hay que indicar el remitente: un número 'from' en formato
E.164, o un Messaging Service SID (empieza por "MG").
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_TWILIO_SMS_"

MODE_AUTH_TOKEN = "auth_token"
MODE_API_KEY = "api_key"


@dataclass(frozen=True)
class TwilioSmsConfig:
    """Parámetros de conexión a la API de Twilio (Programmable Messaging).

    Attributes:
        account_sid: Account SID de Twilio (empieza por "AC").
        username: usuario para HTTP Basic (Account SID o API Key SID).
        password: contraseña para HTTP Basic (Auth Token o API Key Secret).
        mode: "auth_token" o "api_key".
        from_number: número remitente en E.164 (ej. "+15017122661").
        messaging_service_sid: alternativa a from_number (empieza por "MG").
        timeout: timeout en segundos para cada petición HTTP.
    """

    account_sid: str
    username: str
    password: str
    mode: str
    from_number: str | None = None
    messaging_service_sid: str | None = None
    timeout: int = 15

    @classmethod
    def from_env(cls) -> "TwilioSmsConfig":
        """Construye la configuración desde las variables RUVIC_TWILIO_SMS_*.

        Raises:
            ValueError: si faltan credenciales o el remitente.

        Ejemplo:
            >>> config = TwilioSmsConfig.from_env()
            >>> config.mode
            'auth_token'
        """
        account_sid = os.environ.get(f"{ENV_PREFIX}ACCOUNT_SID") or None
        auth_token = os.environ.get(f"{ENV_PREFIX}AUTH_TOKEN") or None
        api_key_sid = os.environ.get(f"{ENV_PREFIX}API_KEY_SID") or None
        api_key_secret = os.environ.get(f"{ENV_PREFIX}API_KEY_SECRET") or None
        from_number = os.environ.get(f"{ENV_PREFIX}FROM_NUMBER") or None
        service_sid = os.environ.get(f"{ENV_PREFIX}MESSAGING_SERVICE_SID") or None
        timeout = int(os.environ.get(f"{ENV_PREFIX}TIMEOUT", "15"))

        if not account_sid:
            raise ValueError(
                f"Falta la variable {ENV_PREFIX}ACCOUNT_SID del conector "
                "twilio_sms. Configura el conector en Settings → Conectores."
            )
        if not account_sid.startswith("AC"):
            raise ValueError(
                f"{ENV_PREFIX}ACCOUNT_SID debe empezar por 'AC' (es el Account "
                "SID que aparece en el panel de Twilio)."
            )

        # Determinar el modo según las credenciales presentes.
        if api_key_sid and api_key_secret:
            mode = MODE_API_KEY
            username, password = api_key_sid, api_key_secret
        elif auth_token:
            mode = MODE_AUTH_TOKEN
            username, password = account_sid, auth_token
        else:
            raise ValueError(
                "Faltan credenciales del conector twilio_sms: define "
                f"{ENV_PREFIX}AUTH_TOKEN (modo Auth Token) o el par "
                f"{ENV_PREFIX}API_KEY_SID + {ENV_PREFIX}API_KEY_SECRET (modo "
                "API Key). Configura el conector en Settings → Conectores."
            )

        # Validar el remitente.
        if not from_number and not service_sid:
            raise ValueError(
                "Falta el remitente del conector twilio_sms: define "
                f"{ENV_PREFIX}FROM_NUMBER (número en formato E.164, ej. "
                f"+15017122661) o {ENV_PREFIX}MESSAGING_SERVICE_SID (empieza "
                "por MG). Configura el conector en Settings → Conectores."
            )
        if from_number and not from_number.startswith("+"):
            raise ValueError(
                f"{ENV_PREFIX}FROM_NUMBER debe estar en formato E.164, "
                "empezando por '+' y el código de país (ej. +573001234567)."
            )

        return cls(
            account_sid=account_sid,
            username=username,
            password=password,
            mode=mode,
            from_number=from_number,
            messaging_service_sid=service_sid,
            timeout=timeout,
        )
