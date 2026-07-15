"""Prueba de conexión estándar del conector telegram.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_TELEGRAM_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Valida el token del bot llamando getMe con las env vars RUVIC_TELEGRAM_*.

    Si hay un chat por defecto configurado, verifica además que el bot
    tenga acceso a ese chat.
    """
    try:
        from ruvic_telegram_connector import (
            TelegramAuthError,
            TelegramClient,
            TelegramDataError,
            TelegramNetworkError,
            TelegramRateLimitError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-telegram-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-telegram.git#subdirectory=lib",
        )

    try:
        client = TelegramClient()  # valida que exista el token en el entorno
    except ValueError as exc:
        return False, str(exc)

    try:
        me = client.get_me()
    except TelegramAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except TelegramNetworkError as exc:
        return False, f"Error de red: {exc}"
    except TelegramRateLimitError as exc:
        return False, f"Límite de peticiones de Telegram: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    # Verificación adicional: acceso al chat por defecto, si está configurado.
    if client.config.default_chat_id:
        try:
            chat = client.get_chat()
        except TelegramDataError as exc:
            return (
                False,
                f"El token es válido (bot @{me['username']}), pero el bot no "
                f"tiene acceso al chat por defecto "
                f"{client.config.default_chat_id!r}: {exc} "
                "Agrega el bot al chat/grupo o corrige el ID.",
            )
        except Exception as exc:
            return False, f"Error inesperado verificando el chat: {exc}"
        return (
            True,
            f"Conexión exitosa como @{me['username']} con acceso al chat "
            f"{chat.get('title') or chat.get('id')}",
        )

    return True, f"Conexión exitosa como @{me['username']}"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
