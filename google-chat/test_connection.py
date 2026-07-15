"""Prueba de conexión estándar del conector gchat.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_GCHAT_*.
- Nunca lanza excepciones; retorna (ok, mensaje).
- No publica mensajes en el espacio (ver GchatClient.ping).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Valida las credenciales de Google Chat según el modo configurado.

    - Modo service_account: obtiene un token y llama spaces.list.
    - Modo webhook: valida la URL sin publicar mensajes.
    """
    try:
        from ruvic_gchat_connector import (
            GchatAuthError,
            GchatClient,
            GchatDataError,
            GchatNetworkError,
            GchatRateLimitError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-gchat-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-gchat.git#subdirectory=lib",
        )

    try:
        client = GchatClient()  # valida env vars y modo
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except GchatAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except GchatNetworkError as exc:
        return False, f"Error de red: {exc}"
    except GchatRateLimitError as exc:
        return False, f"Límite de peticiones de Google: {exc}"
    except GchatDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    if client.config.mode == "webhook":
        return True, "Conexión exitosa: el webhook del espacio es válido"

    extra = ""
    if client.config.default_space:
        try:
            space = client.get_space()
            extra = f" con acceso al espacio {space.get('display_name') or space.get('name')}"
        except GchatDataError as exc:
            return (
                False,
                "Las credenciales son válidas, pero la app no tiene acceso "
                f"al espacio por defecto {client.config.default_space!r}: "
                f"{exc} Agrega la app de Chat al espacio o corrige el ID.",
            )
        except Exception as exc:
            return False, f"Error inesperado verificando el espacio: {exc}"
    return True, f"Conexión exitosa con la Chat API (cuenta de servicio){extra}"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
