"""Prueba de conexión estándar del conector twilio_sms.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_TWILIO_SMS_*.
- Nunca lanza excepciones; retorna (ok, mensaje).
- No envía SMS (solo consulta la cuenta; ver TwilioSmsClient.ping).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Valida las credenciales de Twilio consultando la cuenta (sin enviar SMS)."""
    try:
        from ruvic_twilio_sms_connector import (
            TwilioSmsAuthError,
            TwilioSmsClient,
            TwilioSmsDataError,
            TwilioSmsNetworkError,
            TwilioSmsRateLimitError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-twilio-sms-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-twilio-sms.git#subdirectory=lib",
        )

    try:
        client = TwilioSmsClient()  # valida env vars, modo y remitente
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except TwilioSmsAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except TwilioSmsNetworkError as exc:
        return False, f"Error de red: {exc}"
    except TwilioSmsRateLimitError as exc:
        return False, f"Límite de peticiones de Twilio: {exc}"
    except TwilioSmsDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    remitente = (
        f"Messaging Service {client.config.messaging_service_sid}"
        if client.config.messaging_service_sid
        else f"número {client.config.from_number}"
    )
    modo = "API Key" if client.config.mode == "api_key" else "Auth Token"
    return (
        True,
        f"Conexión exitosa a la cuenta Twilio {client.config.account_sid} "
        f"(modo {modo}, remitente: {remitente})",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
