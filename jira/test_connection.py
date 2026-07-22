"""Prueba de conexión estándar del conector jira.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_JIRA_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Valida las credenciales llamando /myself con las env vars RUVIC_JIRA_*.

    Si hay un proyecto por defecto configurado, verifica además que la cuenta
    pueda ver ese proyecto (una búsqueda JQL acotada).
    """
    try:
        from ruvic_jira_connector import (
            JiraAuthError,
            JiraClient,
            JiraDataError,
            JiraNetworkError,
            JiraRateLimitError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-jira-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-jira.git#subdirectory=lib",
        )

    try:
        client = JiraClient()  # valida que existan las credenciales en el entorno
    except ValueError as exc:
        return False, str(exc)

    try:
        me = client.myself()
    except JiraAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except JiraNetworkError as exc:
        return False, f"Error de red: {exc}"
    except JiraRateLimitError as exc:
        return False, f"Límite de peticiones de Jira: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    # Verificación adicional: acceso al proyecto por defecto, si está configurado.
    project = client.config.default_project
    if project:
        try:
            client.search_issues(f'project = "{project}"', max_results=1)
        except JiraDataError as exc:
            return (
                False,
                f"Las credenciales son válidas ({me['display_name']}), pero no se "
                f"pudo acceder al proyecto por defecto {project!r}: {exc} "
                "Verifica la clave del proyecto y los permisos de la cuenta.",
            )
        except Exception as exc:
            return False, f"Error inesperado verificando el proyecto: {exc}"
        return (
            True,
            f"Conexión exitosa como {me['display_name']} con acceso al "
            f"proyecto {project}",
        )

    return True, f"Conexión exitosa como {me['display_name']} ({me['email']})"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
