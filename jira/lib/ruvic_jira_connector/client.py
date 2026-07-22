"""Cliente para la REST API de Jira Cloud (v3).

Capacidades:
- create_issue():      crear un ticket (issue) en un proyecto.
- update_issue():      actualizar campos de un ticket (resumen, descripción, asignado…).
- transition_issue():  cambiar el estado de un ticket (ej. "In Progress", "Done").
- add_comment():       comentar un ticket.
- search_issues():     buscar tickets con JQL.
- get_issue():         obtener un ticket por su clave.
- list_transitions():  ver las transiciones de estado disponibles para un ticket.
- myself():            identidad de la cuenta (usado por la prueba de conexión).

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_JIRA_*
(ver config.JiraConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from .config import JiraConfig
from .exceptions import (
    JiraAuthError,
    JiraDataError,
    JiraNetworkError,
    JiraRateLimitError,
)
from .logging_utils import get_logger


def _text_to_adf(text: str) -> dict[str, Any]:
    """Convierte texto plano a Atlassian Document Format (ADF).

    Jira Cloud v3 exige ADF en descripción y comentarios. Cada línea del
    texto se convierte en un párrafo; las líneas vacías se preservan como
    párrafos vacíos.
    """
    lines = text.split("\n")
    content: list[dict[str, Any]] = []
    for line in lines:
        if line:
            content.append(
                {"type": "paragraph", "content": [{"type": "text", "text": line}]}
            )
        else:
            content.append({"type": "paragraph", "content": []})
    if not content:
        content = [{"type": "paragraph", "content": []}]
    return {"type": "doc", "version": 1, "content": content}


def _adf_to_text(node: Any) -> str:
    """Extrae el texto plano de un nodo ADF (para mostrar descripciones/comentarios)."""
    if not isinstance(node, dict):
        return ""
    parts: list[str] = []
    if node.get("type") == "text":
        parts.append(node.get("text", ""))
    for child in node.get("content", []) or []:
        parts.append(_adf_to_text(child))
    text = "".join(parts)
    # Un salto de línea tras cada bloque de párrafo para legibilidad.
    if node.get("type") == "paragraph":
        text += "\n"
    return text


class JiraClient:
    """Cliente de la REST API de Jira Cloud (v3).

    Args:
        config: configuración del conector. Si se omite, se lee de las
            variables de entorno RUVIC_JIRA_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = JiraClient()   # lee RUVIC_JIRA_* del entorno
        >>> client.create_issue("Servidor caído", project="OPS", issue_type="Bug")
        {'key': 'OPS-123', 'id': '10001', 'url': 'https://.../browse/OPS-123'}
    """

    def __init__(self, config: JiraConfig | None = None) -> None:
        self.config = config or JiraConfig.from_env()
        self._logger = get_logger()
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(self.config.email, self.config.api_token)
        self._session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    # ------------------------------------------------------------------ #
    # Núcleo HTTP
    # ------------------------------------------------------------------ #

    def _call(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auth_context: bool = False,
    ) -> Any:
        """Invoca un endpoint de la REST API y retorna el cuerpo JSON (o None).

        Traduce todos los fallos a excepciones propias del conector.
        Nunca incluye credenciales en logs ni en mensajes de error.

        auth_context: si es True, un 404 se interpreta como problema de
            credenciales/URL del sitio (Jira Cloud responde 404 a /myself
            cuando la autenticación falla o el sitio no existe), no como un
            recurso concreto inexistente.
        """
        url = f"{self.config.base_url}/rest/api/3/{path.lstrip('/')}"
        try:
            response = self._session.request(
                method,
                url,
                json=json_body,
                params=params,
                timeout=self.config.timeout,
            )
        except requests.Timeout as exc:
            raise JiraNetworkError(
                f"Timeout de {self.config.timeout}s llamando a la API de Jira "
                f"({method} {path}). Verifica la conectividad de red."
            ) from exc
        except requests.RequestException as exc:
            raise JiraNetworkError(
                f"No se pudo alcanzar {self.config.base_url}. Verifica la URL "
                "del sitio, la conexión de red y que el runtime tenga salida HTTPS."
            ) from exc

        return self._handle_response(response, method, path, auth_context)

    def _handle_response(
        self,
        response: requests.Response,
        method: str,
        path: str,
        auth_context: bool = False,
    ) -> Any:
        status = response.status_code

        if status == 429:
            retry_after = int(response.headers.get("Retry-After", "0") or 0)
            raise JiraRateLimitError(
                f"Jira limitó las peticiones; reintenta en {retry_after}s.",
                retry_after=retry_after,
            )
        if status in (401, 403) or (status == 404 and auth_context):
            raise JiraAuthError(
                f"Autenticación o permisos insuficientes en Jira (HTTP {status}). "
                "Verifica la URL del sitio, el email y el API token del conector, "
                "y que la cuenta tenga permiso para esta operación."
            )
        if status == 404:
            raise JiraDataError(
                f"Recurso no encontrado en Jira ({method} {path}). Verifica "
                "que la clave del issue o proyecto exista y sea accesible."
            )
        if status >= 500:
            raise JiraNetworkError(
                f"Jira respondió con un error de servidor (HTTP {status}). "
                "Reintenta más tarde."
            )

        if status >= 400:
            raise JiraDataError(
                f"Jira rechazó la operación ({method} {path}, HTTP {status}): "
                f"{self._extract_error(response)}"
            )

        if status == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise JiraNetworkError(
                f"Respuesta no válida de la API de Jira (HTTP {status}) en {path}."
            ) from exc

    @staticmethod
    def _extract_error(response: requests.Response) -> str:
        """Extrae un mensaje legible del cuerpo de error de Jira."""
        try:
            body = response.json()
        except ValueError:
            return response.text[:300] or "sin detalle"
        messages: list[str] = []
        messages.extend(body.get("errorMessages", []) or [])
        for field, msg in (body.get("errors", {}) or {}).items():
            messages.append(f"{field}: {msg}")
        return "; ".join(messages) or "sin detalle"

    def _resolve_project(self, project: str | None) -> str:
        """Retorna la clave de proyecto efectiva (argumento o default)."""
        effective = project if project is not None else self.config.default_project
        if not effective or not str(effective).strip():
            raise JiraDataError(
                "No se indicó proyecto y el conector no tiene un proyecto por "
                "defecto configurado (RUVIC_JIRA_DEFAULT_PROJECT). Pasa el "
                "parámetro project o configura el valor por defecto."
            )
        return str(effective).strip()

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def myself(self) -> dict[str, Any]:
        """Retorna la identidad de la cuenta autenticada (GET /myself).

        Ejemplo:
            >>> client.myself()
            {'account_id': '5b10a...', 'display_name': 'Ana Ruiz',
             'email': 'ana@empresa.com'}
        """
        result = self._call("GET", "myself", auth_context=True)
        return {
            "account_id": result.get("accountId"),
            "display_name": result.get("displayName"),
            "email": result.get("emailAddress"),
        }

    def ping(self) -> bool:
        """Verifica credenciales y conectividad llamando /myself.

        Returns:
            True si la conexión funciona.

        Raises:
            JiraAuthError / JiraNetworkError según el fallo.
        """
        me = self.myself()
        self._logger.info("Ping exitoso como %s", me.get("display_name"))
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: crear ticket
    # ------------------------------------------------------------------ #

    def create_issue(
        self,
        summary: str,
        project: str | None = None,
        issue_type: str = "Task",
        description: str | None = None,
        priority: str | None = None,
        labels: list[str] | None = None,
        assignee_account_id: str | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Crea un ticket (issue) en un proyecto.

        Args:
            summary: título del ticket (obligatorio).
            project: clave del proyecto, ej. "OPS". Default: proyecto del conector.
            issue_type: tipo de issue por nombre ("Task", "Bug", "Story"…).
            description: descripción en texto plano (se convierte a ADF).
            priority: nombre de la prioridad ("High", "Medium"…), si el
                proyecto la usa.
            labels: lista de etiquetas.
            assignee_account_id: accountId del usuario asignado (no el email).
            extra_fields: campos adicionales del payload `fields` (custom fields,
                componentes, etc.), fusionados sobre los anteriores.

        Returns:
            Dict con key, id y url del ticket creado.

        Ejemplo:
            >>> client.create_issue("Servidor caído", issue_type="Bug",
            ...                      description="El nodo 3 no responde")
            {'key': 'OPS-123', 'id': '10001', 'url': 'https://.../browse/OPS-123'}
        """
        if not summary or not summary.strip():
            raise JiraDataError("El resumen (summary) del ticket es obligatorio.")

        fields: dict[str, Any] = {
            "project": {"key": self._resolve_project(project)},
            "summary": summary.strip(),
            "issuetype": {"name": issue_type},
        }
        if description:
            fields["description"] = _text_to_adf(description)
        if priority:
            fields["priority"] = {"name": priority}
        if labels:
            fields["labels"] = labels
        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}
        if extra_fields:
            fields.update(extra_fields)

        result = self._call("POST", "issue", json_body={"fields": fields})
        key = result.get("key")
        self._logger.info("Ticket %s creado", key)
        return {
            "key": key,
            "id": result.get("id"),
            "url": f"{self.config.base_url}/browse/{key}",
        }

    # ------------------------------------------------------------------ #
    # Capacidad 2: actualizar ticket
    # ------------------------------------------------------------------ #

    def update_issue(
        self,
        issue_key: str,
        summary: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        labels: list[str] | None = None,
        assignee_account_id: str | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Actualiza campos de un ticket existente.

        Solo se envían los campos indicados; el resto no se toca. Para cambiar
        el ESTADO usa transition_issue (el estado no es un campo editable así).

        Args:
            issue_key: clave del ticket, ej. "OPS-123".
            summary / description / priority / labels / assignee_account_id:
                nuevos valores (ver create_issue). Cualquiera puede omitirse.
            extra_fields: campos adicionales del payload `fields`.

        Returns:
            Dict con key y url del ticket.

        Ejemplo:
            >>> client.update_issue("OPS-123", priority="High",
            ...                     labels=["urgente"])
            {'key': 'OPS-123', 'url': 'https://.../browse/OPS-123'}
        """
        fields: dict[str, Any] = {}
        if summary is not None:
            fields["summary"] = summary
        if description is not None:
            fields["description"] = _text_to_adf(description)
        if priority is not None:
            fields["priority"] = {"name": priority}
        if labels is not None:
            fields["labels"] = labels
        if assignee_account_id is not None:
            fields["assignee"] = {"accountId": assignee_account_id}
        if extra_fields:
            fields.update(extra_fields)

        if not fields:
            raise JiraDataError(
                "No se indicó ningún campo para actualizar en "
                f"{issue_key!r}. Pasa al menos uno (summary, description, etc.)."
            )

        self._call("PUT", f"issue/{issue_key}", json_body={"fields": fields})
        self._logger.info("Ticket %s actualizado", issue_key)
        return {
            "key": issue_key,
            "url": f"{self.config.base_url}/browse/{issue_key}",
        }

    # ------------------------------------------------------------------ #
    # Capacidad 3: cambiar estado (transición)
    # ------------------------------------------------------------------ #

    def list_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Lista las transiciones de estado disponibles para un ticket.

        El flujo de trabajo de Jira determina a qué estados se puede pasar
        desde el estado actual. Cada transición tiene un id y un nombre
        (que suele coincidir con el estado destino).

        Args:
            issue_key: clave del ticket, ej. "OPS-123".

        Returns:
            Lista de dicts con id, name y to_status (estado destino).

        Ejemplo:
            >>> client.list_transitions("OPS-123")
            [{'id': '31', 'name': 'In Progress', 'to_status': 'In Progress'}, ...]
        """
        result = self._call("GET", f"issue/{issue_key}/transitions")
        transitions = []
        for tr in result.get("transitions", []):
            transitions.append(
                {
                    "id": tr.get("id"),
                    "name": tr.get("name"),
                    "to_status": (tr.get("to") or {}).get("name"),
                }
            )
        return transitions

    def transition_issue(
        self,
        issue_key: str,
        status: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Cambia el estado de un ticket a `status`.

        Resuelve el nombre del estado destino (ej. "In Progress", "Done") a la
        transición correspondiente entre las disponibles desde el estado actual.

        Args:
            issue_key: clave del ticket, ej. "OPS-123".
            status: nombre del estado o de la transición destino (sin distinguir
                mayúsculas), ej. "Done", "En progreso".
            comment: comentario opcional a añadir junto con la transición.

        Returns:
            Dict con key, status (aplicado) y url.

        Raises:
            JiraDataError: si no hay una transición hacia ese estado desde el
                estado actual (el mensaje lista las opciones válidas).

        Ejemplo:
            >>> client.transition_issue("OPS-123", "In Progress")
            {'key': 'OPS-123', 'status': 'In Progress', 'url': '...'}
        """
        transitions = self.list_transitions(issue_key)
        wanted = status.strip().lower()
        match = next(
            (
                tr
                for tr in transitions
                if (tr["name"] or "").lower() == wanted
                or (tr["to_status"] or "").lower() == wanted
            ),
            None,
        )
        if match is None:
            options = ", ".join(
                sorted({tr["to_status"] or tr["name"] for tr in transitions})
            )
            raise JiraDataError(
                f"No hay una transición hacia {status!r} desde el estado actual "
                f"de {issue_key}. Estados alcanzables ahora: {options or '(ninguno)'}."
            )

        body: dict[str, Any] = {"transition": {"id": match["id"]}}
        if comment:
            body["update"] = {
                "comment": [{"add": {"body": _text_to_adf(comment)}}]
            }
        self._call("POST", f"issue/{issue_key}/transitions", json_body=body)
        applied = match["to_status"] or match["name"]
        self._logger.info("Ticket %s → %s", issue_key, applied)
        return {
            "key": issue_key,
            "status": applied,
            "url": f"{self.config.base_url}/browse/{issue_key}",
        }

    # ------------------------------------------------------------------ #
    # Capacidad 4: comentar
    # ------------------------------------------------------------------ #

    def add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        """Añade un comentario a un ticket.

        Args:
            issue_key: clave del ticket, ej. "OPS-123".
            body: texto del comentario (se convierte a ADF).

        Returns:
            Dict con id del comentario, key del ticket y created (fecha).

        Ejemplo:
            >>> client.add_comment("OPS-123", "Desplegado el fix en producción")
            {'id': '10100', 'key': 'OPS-123', 'created': '2026-07-21T...'}
        """
        if not body or not body.strip():
            raise JiraDataError("El comentario no puede estar vacío.")
        result = self._call(
            "POST",
            f"issue/{issue_key}/comment",
            json_body={"body": _text_to_adf(body)},
        )
        self._logger.info("Comentario %s añadido a %s", result.get("id"), issue_key)
        return {
            "id": result.get("id"),
            "key": issue_key,
            "created": result.get("created"),
        }

    # ------------------------------------------------------------------ #
    # Capacidad 5: buscar tickets (JQL)
    # ------------------------------------------------------------------ #

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Busca tickets con una consulta JQL.

        Args:
            jql: consulta JQL, ej. 'project = OPS AND status = "In Progress"
                ORDER BY created DESC'.
            max_results: máximo de tickets a retornar (1-100).
            fields: campos a devolver por cada issue. Por defecto: summary,
                status, assignee, priority, created, updated.

        Returns:
            Lista de dicts simplificados: key, summary, status, assignee,
            priority, created, updated, url. El campo `raw` conserva los
            fields completos.

        Ejemplo:
            >>> client.search_issues('project = OPS AND status != Done')
            [{'key': 'OPS-123', 'summary': 'Servidor caído', 'status': 'To Do', ...}]
        """
        if not jql or not jql.strip():
            raise JiraDataError("La consulta JQL no puede estar vacía.")
        wanted_fields = fields or [
            "summary",
            "status",
            "assignee",
            "priority",
            "created",
            "updated",
        ]
        body = {
            "jql": jql,
            "maxResults": max(1, min(int(max_results), 100)),
            "fields": wanted_fields,
        }
        result = self._call("POST", "search/jql", json_body=body)
        issues = []
        for item in result.get("issues", []):
            f = item.get("fields", {})
            issues.append(
                {
                    "key": item.get("key"),
                    "summary": f.get("summary"),
                    "status": (f.get("status") or {}).get("name"),
                    "assignee": (f.get("assignee") or {}).get("displayName"),
                    "priority": (f.get("priority") or {}).get("name"),
                    "created": f.get("created"),
                    "updated": f.get("updated"),
                    "url": f"{self.config.base_url}/browse/{item.get('key')}",
                    "raw": f,
                }
            )
        self._logger.info("Búsqueda JQL retornó %d tickets", len(issues))
        return issues

    # ------------------------------------------------------------------ #
    # Capacidad 6: obtener un ticket
    # ------------------------------------------------------------------ #

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        """Obtiene un ticket por su clave.

        Args:
            issue_key: clave del ticket, ej. "OPS-123".

        Returns:
            Dict con key, summary, status, description (texto), assignee,
            reporter, priority, labels, created, updated y url.

        Ejemplo:
            >>> client.get_issue("OPS-123")
            {'key': 'OPS-123', 'summary': 'Servidor caído', 'status': 'To Do', ...}
        """
        result = self._call("GET", f"issue/{issue_key}")
        f = result.get("fields", {})
        description = f.get("description")
        return {
            "key": result.get("key"),
            "summary": f.get("summary"),
            "status": (f.get("status") or {}).get("name"),
            "description": _adf_to_text(description).strip() if description else None,
            "assignee": (f.get("assignee") or {}).get("displayName"),
            "reporter": (f.get("reporter") or {}).get("displayName"),
            "priority": (f.get("priority") or {}).get("name"),
            "labels": f.get("labels", []),
            "created": f.get("created"),
            "updated": f.get("updated"),
            "url": f"{self.config.base_url}/browse/{result.get('key')}",
        }
