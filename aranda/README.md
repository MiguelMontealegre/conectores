# Conector Aranda ASMS — `aranda`

Conector Ruvic para la **API v9 de Aranda ASMS** (service desk / ITSM): crear y
consultar casos, catálogos, descubrimiento de metadatos para armar un caso
(proyectos, servicios, categorías, modelos, estados, compañías, clientes, campos
adicionales), flujo de trabajo/asignación y búsqueda de elementos de
configuración (CMDB).

Empaqueta las 18 skills del service desk de Aranda como métodos de una sola clase
`ArandaClient`, **sin token hardcodeado**: el token se lee de las variables de
entorno del conector.

## Instalación

```bash
pip install git+https://github.com/tu-org/conector-aranda.git#subdirectory=lib
```

- Python ≥ 3.10 (probado en 3.12).
- Única dependencia: `requests>=2.31,<3.0`.
- Requiere salida HTTPS hacia tu servidor de Aranda.

## Prerrequisitos en Aranda

1. **URL base de la API v9**: por defecto la nube de Arandasoft
   (`https://proyectos.arandasoft.com/asmsapi/api/v9`). Para una instalación
   on-premise, la URL de tu servidor con la ruta `/asmsapi/api/v9`.
2. **Token de integración**: generado en la consola de administración de Aranda
   ASMS (sección de integraciones / API). Es un JWT que se envía en la cabecera
   `X-Authorization`. El token debe tener permisos sobre los proyectos y tipos de
   caso que vayas a gestionar.
3. **Certificado TLS**: muchas instalaciones on-premise usan certificados
   internos; por eso el conector trae `verify_ssl=false` por defecto (igual que
   las skills originales). Actívalo solo si tu servidor tiene un certificado de
   confianza pública.

## Variables de entorno (generadas por la plataforma)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_ARANDA_TOKEN` | Sí | Token de integración (con o sin prefijo `Bearer `) |
| `RUVIC_ARANDA_BASE_URL` | No | URL base de la API v9 (default nube Arandasoft) |
| `RUVIC_ARANDA_VERIFY_SSL` | No | Validar TLS (`false` por defecto) |
| `RUVIC_ARANDA_TIMEOUT` | No | Timeout HTTP en segundos (default 30) |

## Capacidades

| Grupo | Métodos |
|-------|---------|
| **Casos** | `create_item(...)`, `get_item_by_id(item_id)` |
| **Catálogos** | `get_item_types()`, `get_urgency()`, `get_impact()`, `get_registry_types()` |
| **Descubrimiento** | `get_projects()`, `get_services()`, `get_categories_by_service()`, `get_model()`, `get_states()`, `get_companies()`, `get_customers()`, `get_additional_fields()` |
| **Flujo / asignación** | `get_groups_by_state()`, `get_reasons_for_state()`, `get_responsible()` |
| **CMDB** | `search_cis()` |

El orden para resolver los IDs y crear un caso está en `SKILL.md`.

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_ARANDA_TOKEN="Bearer eyJ0..."
# export RUVIC_ARANDA_BASE_URL="https://tu-servidor/asmsapi/api/v9"   # opcional

python test_connection.py        # valida el token (lista tipos de caso)
python validate_local.py         # recorre catálogos y proyectos (no crea casos)
```

Casos de fallo a verificar:

```bash
RUVIC_ARANDA_TOKEN="Bearer token-invalido" python test_connection.py
# FALLO: Autenticación fallida: ... (HTTP 401) ...
```

## Notas sobre el diseño

- **Sin credenciales en el código**: las skills originales incluían el token JWT
  incrustado en cada archivo. Este conector lo elimina por completo y lo lee de
  `RUVIC_ARANDA_TOKEN`; el prefijo `Bearer ` se normaliza automáticamente.
- **Errores traducidos**: en vez de imprimir y devolver `None` ante un fallo, el
  conector lanza excepciones tipadas (`ArandaAuthError`, `ArandaDataError`,
  `ArandaNetworkError`, `ArandaRateLimitError`) con mensajes accionables.
- **Fidelidad de la API**: cada método replica exactamente el método HTTP, la
  ruta, los `params`, el `payload` y las cabeceras (`dataType: all`) de la skill
  original correspondiente.
- **TLS**: al desactivar la verificación se silencian las advertencias de urllib3
  (como hacían las skills originales), pero de forma controlada.
- El token nunca se loguea ni se incluye en mensajes de excepción.
