"""Cliente para la API de Aranda ASMS (v9).

Empaqueta las skills del service desk de Aranda como métodos de una sola
clase. El token SIEMPRE proviene de variables de entorno RUVIC_ARANDA_*
(ver config.ArandaConfig.from_env); prohibido hardcodearlo.

Capacidades (agrupadas):

Catálogos globales (sin parámetros):
- get_item_types(), get_urgency(), get_impact(), get_registry_types()

Descubrimiento para armar un caso:
- get_projects(), get_services(), get_categories_by_service(), get_model(),
  get_states(), get_companies(), get_customers(), get_additional_fields()

Flujo de trabajo y asignación:
- get_groups_by_state(), get_reasons_for_state(), get_responsible()

Elementos de configuración (CMDB):
- search_cis()

Casos:
- create_item(), get_item_by_id()

El orden típico para crear un caso está documentado en SKILL.md.
"""

from __future__ import annotations

from typing import Any

import requests
import urllib3

from .config import ArandaConfig
from .exceptions import (
    ArandaAuthError,
    ArandaDataError,
    ArandaNetworkError,
    ArandaRateLimitError,
)
from .logging_utils import get_logger

# Muchas instalaciones de Aranda usan certificados internos; cuando
# verify_ssl=False evitamos el ruido de advertencias de urllib3.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ArandaClient:
    """Cliente de la API de Aranda ASMS (v9).

    Args:
        config: configuración del conector. Si se omite, se lee de las
            variables de entorno RUVIC_ARANDA_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = ArandaClient()   # lee RUVIC_ARANDA_* del entorno
        >>> proyectos = client.get_projects()
    """

    def __init__(self, config: ArandaConfig | None = None) -> None:
        self.config = config or ArandaConfig.from_env()
        self._logger = get_logger()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-Authorization": self.config.auth_header,
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------ #
    # Núcleo HTTP
    # ------------------------------------------------------------------ #

    def _call(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        """Invoca un endpoint de la API y retorna el cuerpo JSON (o None).

        Traduce todos los fallos a excepciones propias del conector.
        Nunca incluye el token en logs ni en mensajes de error.
        """
        url = f"{self.config.base_url}/{path.lstrip('/')}"
        headers = dict(extra_headers) if extra_headers else None
        try:
            response = self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
        except requests.Timeout as exc:
            raise ArandaNetworkError(
                f"Timeout de {self.config.timeout}s llamando a Aranda "
                f"({method} {path}). Verifica la conectividad de red."
            ) from exc
        except requests.exceptions.SSLError as exc:
            raise ArandaNetworkError(
                "Error de certificado TLS al conectar con Aranda. Si el sitio "
                "usa un certificado interno, configura RUVIC_ARANDA_VERIFY_SSL=false."
            ) from exc
        except requests.RequestException as exc:
            raise ArandaNetworkError(
                f"No se pudo alcanzar {self.config.base_url}. Verifica la URL "
                "base, la conexión de red y que el runtime tenga salida HTTPS."
            ) from exc

        return self._handle_response(response, method, path)

    def _handle_response(
        self, response: requests.Response, method: str, path: str
    ) -> Any:
        status = response.status_code

        if status == 429:
            retry_after = int(response.headers.get("Retry-After", "0") or 0)
            raise ArandaRateLimitError(
                f"Aranda limitó las peticiones; reintenta en {retry_after}s.",
                retry_after=retry_after,
            )
        if status in (401, 403):
            raise ArandaAuthError(
                f"Autenticación o permisos insuficientes en Aranda (HTTP {status}). "
                "El token es inválido/expiró o la cuenta no tiene permiso para "
                "esta operación. Revisa el token del conector en Settings → Conectores."
            )
        if status == 404:
            raise ArandaDataError(
                f"Recurso no encontrado en Aranda ({method} {path}). Verifica "
                "que los IDs (proyecto, servicio, caso, etc.) existan y sean válidos."
            )
        if status >= 500:
            raise ArandaNetworkError(
                f"Aranda respondió con un error de servidor (HTTP {status}). "
                "Reintenta más tarde."
            )
        if status >= 400:
            raise ArandaDataError(
                f"Aranda rechazó la operación ({method} {path}, HTTP {status}): "
                f"{self._extract_error(response)}"
            )

        if status == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise ArandaNetworkError(
                f"Respuesta no válida de Aranda (HTTP {status}) en {path}."
            ) from exc

    @staticmethod
    def _extract_error(response: requests.Response) -> str:
        """Extrae un mensaje legible del cuerpo de error de Aranda."""
        try:
            body = response.json()
        except ValueError:
            return (response.text or "").strip()[:300] or "sin detalle"
        if isinstance(body, dict):
            for key in ("message", "Message", "error", "Error", "detail"):
                if body.get(key):
                    return str(body[key])
        return str(body)[:300] or "sin detalle"

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica token y conectividad listando los tipos de caso.

        get_item_types no requiere parámetros, por lo que es la sonda ideal
        para validar el token contra Aranda.

        Returns:
            True si la conexión funciona.

        Raises:
            ArandaAuthError / ArandaNetworkError según el fallo.
        """
        self.get_item_types()
        self._logger.info("Ping a Aranda exitoso")
        return True

    # ------------------------------------------------------------------ #
    # Catálogos globales (sin parámetros)
    # ------------------------------------------------------------------ #

    def get_item_types(self) -> Any:
        """Lista los tipos de caso disponibles según licencia.

        Típicamente: 1=Incidente, 2=Problema, 3=Cambio, 4=Requerimiento de
        Servicio (los IDs dependen de la instalación).
        """
        return self._call("GET", "item/types/licenses")

    def get_urgency(self) -> Any:
        """Lista los niveles de urgencia del catálogo global."""
        return self._call("GET", "catalog/urgency", extra_headers={"dataType": "all"})

    def get_impact(self) -> Any:
        """Lista los niveles de impacto del catálogo global."""
        return self._call("GET", "catalog/impact", extra_headers={"dataType": "all"})

    def get_registry_types(self) -> Any:
        """Lista los tipos de registro (notas/seguimientos) del catálogo global."""
        return self._call(
            "GET", "catalog/registry_type", extra_headers={"dataType": "all"}
        )

    # ------------------------------------------------------------------ #
    # Descubrimiento para armar un caso
    # ------------------------------------------------------------------ #

    def get_projects(self, console_type: str = "specialist") -> Any:
        """Obtiene los proyectos accesibles para el usuario autenticado.

        Args:
            console_type: 'specialist' o 'customer'.
        """
        return self._call(
            "POST",
            "user/projects",
            json_body={"consoleType": console_type},
            extra_headers={"dataType": "all"},
        )

    def get_services(
        self,
        project_id: int,
        item_type: int,
        console: str = "Specialist",
        application: str = "ASDK",
    ) -> Any:
        """Busca los servicios de un proyecto para un tipo de caso.

        Args:
            project_id: ID del proyecto.
            item_type: ID del tipo de caso (ej. 1 = Incidente).
            console: tipo de consola, ej. 'Specialist'.
            application: identificador de aplicación, típicamente 'ASDK'.
        """
        return self._call(
            "GET",
            f"project/{project_id}/{item_type}/services/search",
            params={"console": console, "application": application},
            extra_headers={"dataType": "all"},
        )

    def get_categories_by_service(self, item_type: int, service_id: int) -> Any:
        """Obtiene las categorías de un servicio para un tipo de caso.

        Args:
            item_type: ID del tipo de caso.
            service_id: ID del servicio.
        """
        return self._call(
            "GET",
            f"item/{item_type}/services/{service_id}/categories",
            params={"dataType": "all"},
            extra_headers={"dataType": "all"},
        )

    def get_model(self, item_type: int, category_id: int, service_id: int) -> Any:
        """Obtiene el modelo de flujo de trabajo para una combinación
        tipo de caso + categoría + servicio.

        Args:
            item_type: ID del tipo de caso.
            category_id: ID de la categoría.
            service_id: ID del servicio.
        """
        return self._call(
            "GET",
            f"item/{item_type}/categories/{category_id}/service/{service_id}/model",
            extra_headers={"dataType": "all"},
        )

    def get_states(
        self,
        model_id: int,
        item_type: int,
        state_id: int | None = None,
        item_id: int | None = None,
    ) -> Any:
        """Obtiene los estados de un modelo de flujo de trabajo.

        Si se pasa state_id, retorna las transiciones válidas DESDE ese estado.

        Args:
            model_id: ID del modelo de flujo de trabajo.
            item_type: ID del tipo de caso.
            state_id: ID del estado actual (opcional) → transiciones válidas.
            item_id: ID de un caso existente (opcional) → transiciones contextuales.
        """
        params: dict[str, Any] = {}
        if state_id is not None:
            params["stateId"] = state_id
        if item_id is not None:
            params["itemId"] = item_id
        return self._call(
            "GET",
            f"model/{model_id}/{item_type}/states",
            params=params or None,
            extra_headers={"dataType": "all"},
        )

    def get_companies(self, project_id: int, item_type: int) -> Any:
        """Busca las compañías de un proyecto para un tipo de caso.

        Args:
            project_id: ID del proyecto.
            item_type: ID del tipo de caso.
        """
        return self._call(
            "GET", f"project/{project_id}/{item_type}/companies/search"
        )

    def get_customers(
        self,
        project_id: int,
        item_type: int,
        company_id: int,
        service_id: int,
        application: str = "ASDK",
    ) -> Any:
        """Busca los clientes (usuarios finales) de una compañía.

        Args:
            project_id: ID del proyecto.
            item_type: ID del tipo de caso.
            company_id: ID de la compañía para filtrar clientes.
            service_id: ID del servicio.
            application: identificador de aplicación, típicamente 'ASDK'.
        """
        return self._call(
            "GET",
            f"project/{project_id}/{item_type}/clients/search",
            params={
                "companyId": company_id,
                "serviceId": service_id,
                "application": application,
            },
        )

    def get_additional_fields(
        self,
        category_id: int,
        item_type: int,
        model_id: int,
        state_id: int,
        console_type: str = "specialist",
    ) -> Any:
        """Obtiene los campos adicionales (personalizados) para una combinación
        categoría + tipo de caso + modelo + estado.

        Úsalo antes de crear un caso para saber qué campos custom son requeridos.

        Args:
            category_id: ID de la categoría.
            item_type: ID del tipo de caso.
            model_id: ID del modelo de flujo de trabajo.
            state_id: ID del estado.
            console_type: tipo de consola, por defecto 'specialist'.
        """
        return self._call(
            "POST",
            "item/additionalfields",
            json_body={
                "consoleType": console_type,
                "categoryId": category_id,
                "itemType": item_type,
                "modelId": model_id,
                "stateId": state_id,
            },
        )

    # ------------------------------------------------------------------ #
    # Flujo de trabajo y asignación
    # ------------------------------------------------------------------ #

    def get_groups_by_state(self, service_id: int, state_id: int) -> Any:
        """Lista los grupos de especialistas disponibles en un estado del servicio.

        Args:
            service_id: ID del servicio.
            state_id: ID del estado.
        """
        return self._call(
            "GET",
            f"service/{service_id}/state/{state_id}/group/list",
            extra_headers={"dataType": "all"},
        )

    def get_reasons_for_state(self, state_id: int) -> Any:
        """Lista los motivos/razones asociados a un estado.

        Args:
            state_id: ID del estado.
        """
        return self._call(
            "GET", f"state/{state_id}/reasons", extra_headers={"dataType": "all"}
        )

    def get_responsible(self, group_id: int, project_id: int) -> Any:
        """Lista los especialistas (responsables) de un grupo en un proyecto.

        Args:
            group_id: ID del grupo.
            project_id: ID del proyecto.
        """
        return self._call(
            "GET",
            f"group/{group_id}/project/{project_id}/specialists",
            extra_headers={"dataType": "all"},
        )

    # ------------------------------------------------------------------ #
    # Elementos de configuración (CMDB)
    # ------------------------------------------------------------------ #

    def search_cis(
        self,
        project_id: int,
        item_type: int,
        service_id: int,
        ci_item_types: list[int] | None = None,
        page_size: int = 10,
        page_index: int = 1,
        view_id: int = -6,
        repository: int = 1,
        categories: list[dict[str, Any]] | None = None,
        projects: list[dict[str, Any]] | None = None,
        console_type: str = "specialist",
    ) -> Any:
        """Busca Elementos de Configuración (CIs) en un proyecto.

        Los CIs representan activos, componentes de infraestructura u otros
        elementos gestionados en la CMDB.

        Args:
            project_id: ID del proyecto donde buscar.
            item_type: ID del tipo de caso.
            service_id: ID del servicio para filtrar.
            ci_item_types: lista de IDs de tipos de CI a filtrar (ej. [21]).
            page_size: resultados por página (por defecto 10).
            page_index: número de página, base 1 (por defecto 1).
            view_id: ID de vista (por defecto -6).
            repository: ID del repositorio (por defecto 1).
            categories: lista de categorías para filtrar (ej. [{"id": 18}]).
            projects: lista de proyectos para filtrar (ej. [{"id": 2}]).
            console_type: tipo de consola, por defecto 'specialist'.
        """
        return self._call(
            "GET",
            f"project/{project_id}/{item_type}/Cis/search",
            params={"serviceId": service_id, "application": "ASDK"},
            json_body={
                "consoleType": console_type,
                "itemTypes": ci_item_types or [item_type],
                "PageSize": page_size,
                "PageIndex": page_index,
                "ViewId": view_id,
                "Repository": repository,
                "Categories": categories or [],
                "Projects": projects or [],
            },
            extra_headers={"dataType": "all"},
        )

    # ------------------------------------------------------------------ #
    # Casos
    # ------------------------------------------------------------------ #

    def create_item(
        self,
        author_id: int,
        category_id: int,
        company_id: int,
        customer_id: int,
        description: str,
        item_type: int,
        model_id: int,
        project_id: int,
        service_id: int,
        state_id: int,
        subject: str,
        urgency_id: int | None = None,
        additional_fields: list[dict[str, Any]] | None = None,
        console_type: str = "specialist",
    ) -> Any:
        """Crea un caso (incidente, requerimiento, problema o cambio) en Aranda.

        Antes de llamarla resuelve los IDs requeridos con las skills de
        descubrimiento (get_projects, get_services, get_categories_by_service,
        get_model, get_states, get_companies, get_customers, etc.).

        Args:
            author_id: ID del usuario que crea el caso.
            category_id: ID de la categoría.
            company_id: ID de la compañía.
            customer_id: ID del cliente (usuario final).
            description: descripción detallada (puede contener HTML).
            item_type: ID del tipo de caso (1=Incidente, 2=Problema, 3=Cambio,
                4=Requerimiento de Servicio).
            model_id: ID del modelo de flujo de trabajo.
            project_id: ID del proyecto.
            service_id: ID del servicio.
            state_id: ID del estado inicial.
            subject: título/asunto del caso.
            urgency_id: ID del nivel de urgencia (opcional).
            additional_fields: lista de campos adicionales (ver
                get_additional_fields para su estructura).
            console_type: tipo de consola, por defecto 'specialist'.

        Returns:
            El caso creado (incluye 'id' interno e 'idByProject' visible).
        """
        if not subject or not subject.strip():
            raise ArandaDataError("El asunto (subject) del caso es obligatorio.")

        payload: dict[str, Any] = {
            "authorId": author_id,
            "categoryId": category_id,
            "companyId": company_id,
            "consoleType": console_type,
            "customerId": customer_id,
            "description": description,
            "instance": 1663974898489,
            "isFeeAvailable": True,
            "itemType": item_type,
            "listAdditionalField": additional_fields or [],
            "modelId": model_id,
            "projectId": project_id,
            "serviceId": service_id,
            "stateId": state_id,
            "subject": subject,
            "tempItemId": -1,
            "transformed": False,
            "validate": True,
        }
        if urgency_id is not None:
            payload["urgencyId"] = urgency_id

        result = self._call("POST", "item/", json_body=payload)
        if isinstance(result, dict):
            self._logger.info(
                "Caso creado id=%s (%s)",
                result.get("id"),
                result.get("idByProject"),
            )
        return result

    def get_item_by_id(self, item_id: int) -> Any:
        """Obtiene el detalle completo de un caso por su ID interno.

        El ID interno es el 'id' que devuelve create_item (p. ej. 10658),
        NO el código visible 'idByProject' (p. ej. 'IM-10658').

        Args:
            item_id: ID interno del caso.
        """
        return self._call(
            "GET", f"item/{item_id}", extra_headers={"dataType": "all"}
        )
