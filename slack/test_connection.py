"""Prueba de conexión estándar del conector slack.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_SLACK_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Valida el token del bot llamando auth.test con las env vars RUVIC_SLACK_*.

    Si hay un canal por defecto configurado (por ID de canal), verifica
    además que el bot pueda consultar ese canal.
    """
    try:
        from ruvic_slack_connector import (
            SlackAuthError,
            SlackClient,
            SlackDataError,
            SlackNetworkError,
            SlackRateLimitError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-slack-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-slack.git#subdirectory=lib",
        )

    try:
        client = SlackClient()  # valida que exista el token en el entorno
    except ValueError as exc:
        return False, str(exc)

    try:
        me = client.auth_test()
    except SlackAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except SlackNetworkError as exc:
        return False, f"Error de red: {exc}"
    except SlackRateLimitError as exc:
        return False, f"Límite de peticiones de Slack: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    # Verificación adicional: acceso a un canal por defecto, si es un ID de canal.
    default = client.config.default_channel
    if default and default.startswith(("C", "G")):
        try:
            info = client.get_channel_info()
        except SlackDataError as exc:
            return (
                False,
                f"El token es válido (bot {me['user']} en {me['team']}), pero no "
                f"se pudo consultar el canal por defecto {default!r}: {exc} "
                "Invita el bot al canal (/invite @tu-bot) o corrige el ID.",
            )
        except Exception as exc:
            return False, f"Error inesperado verificando el canal: {exc}"
        return (
            True,
            f"Conexión exitosa como {me['user']} en {me['team']} con acceso al "
            f"canal #{info.get('name') or info.get('id')}",
        )

    return True, f"Conexión exitosa como {me['user']} en el workspace {me['team']}"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
