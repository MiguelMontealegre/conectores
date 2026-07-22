"""Prueba de conexión estándar del conector aranda.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_ARANDA_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Valida el token llamando a get_item_types (sin parámetros) con las
    env vars RUVIC_ARANDA_*.
    """
    try:
        from ruvic_aranda_connector import (
            ArandaAuthError,
            ArandaClient,
            ArandaDataError,
            ArandaNetworkError,
            ArandaRateLimitError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-aranda-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-aranda.git#subdirectory=lib",
        )

    try:
        client = ArandaClient()  # valida que exista el token en el entorno
    except ValueError as exc:
        return False, str(exc)

    try:
        item_types = client.get_item_types()
    except ArandaAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except ArandaNetworkError as exc:
        return False, f"Error de red: {exc}"
    except ArandaRateLimitError as exc:
        return False, f"Límite de peticiones de Aranda: {exc}"
    except ArandaDataError as exc:
        return False, f"Respuesta inesperada de Aranda: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    # get_item_types puede devolver una lista o un objeto {"content": [...]}.
    if isinstance(item_types, list):
        count: object = len(item_types)
    elif isinstance(item_types, dict) and isinstance(item_types.get("content"), list):
        count = item_types.get("totalItems", len(item_types["content"]))
    else:
        count = "?"
    return (
        True,
        f"Conexión exitosa con Aranda ASMS ({client.config.base_url}); "
        f"{count} tipos de caso disponibles.",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
