# Conector Jira — `jira`

Conector Ruvic para la **REST API de Jira Cloud (v3)**: crear tickets, actualizar
sus campos, cambiar su estado (transiciones del flujo de trabajo), comentar,
buscar con JQL y obtener tickets por su clave.

## Instalación

```bash
pip install git+https://github.com/tu-org/conector-jira.git#subdirectory=lib
```

- Python ≥ 3.10 (probado en 3.12).
- Única dependencia: `requests>=2.31,<3.0`.
- Requiere salida HTTPS hacia tu sitio `*.atlassian.net` (puerto 443).

## Prerrequisitos en Jira / Atlassian

1. **Sitio de Jira Cloud**: tu URL base, con el formato
   `https://miempresa.atlassian.net`.
2. **Cuenta de Atlassian** que operará Jira (la que crea/comenta tickets). Todo
   ocurre con **sus** permisos.
3. **API token**: entra a <https://id.atlassian.com/manage-profile/security/api-tokens>
   → **Create API token**, ponle un nombre y **copia el token** (solo se muestra una
   vez, formato `ATATT3xFfGF0...`). Es la credencial secreta.
4. **Permisos del proyecto** (la cuenta debe tenerlos en cada proyecto usado):
   *Browse projects* (leer/buscar), *Create issues*, *Edit issues*,
   *Transition issues* y *Add comments*.
5. **Clave del proyecto**: el prefijo de los tickets, ej. `OPS` en `OPS-123`.
   Aparece en la configuración del proyecto y en la URL de cualquier ticket.

> Nota: este conector es para **Jira Cloud** (autenticación email + API token).
> Jira Server/Data Center usa Personal Access Tokens y rutas distintas.

## Variables de entorno (generadas por la plataforma)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_JIRA_BASE_URL` | Sí | URL del sitio, ej. `https://miempresa.atlassian.net` |
| `RUVIC_JIRA_EMAIL` | Sí | Email de la cuenta Atlassian |
| `RUVIC_JIRA_API_TOKEN` | Sí | API token (secreto) |
| `RUVIC_JIRA_DEFAULT_PROJECT` | No | Clave de proyecto por defecto, ej. `OPS` |
| `RUVIC_JIRA_TIMEOUT` | No | Timeout HTTP en segundos (default 20) |

## Capacidades

| Operación | Método | Qué hace |
|-----------|--------|----------|
| `issue.create` | `create_issue(summary, …)` | Crea un ticket en un proyecto |
| `issue.update` | `update_issue(key, …)` | Actualiza campos (resumen, descripción, prioridad, etiquetas, asignado) |
| `issue.transition` | `transition_issue(key, status, …)` | Cambia el estado según el flujo de trabajo |
| `issue.add_comment` | `add_comment(key, body)` | Comenta un ticket |
| `issue.search` | `search_issues(jql, …)` | Busca tickets con JQL |
| `issue.get` | `get_issue(key)` | Obtiene un ticket por su clave |
| — | `list_transitions(key)` | Lista los estados alcanzables desde el estado actual |

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_JIRA_BASE_URL="https://miempresa.atlassian.net"
export RUVIC_JIRA_EMAIL="usuario@empresa.com"
export RUVIC_JIRA_API_TOKEN="ATATT3xFfGF0..."
export RUVIC_JIRA_DEFAULT_PROJECT="OPS"

python test_connection.py        # prueba de conexión estándar
python validate_local.py         # crea/comenta/transiciona/busca un ticket real
```

> `validate_local.py` **crea un ticket real** en el proyecto por defecto (con la
> etiqueta `ruvic-prueba`). Bórralo después si no lo necesitas.

Casos de fallo a verificar:

```bash
RUVIC_JIRA_API_TOKEN="tokeninvalido" python test_connection.py
# FALLO: Autenticación fallida: Autenticación o permisos insuficientes en Jira (HTTP 401)...

RUVIC_JIRA_DEFAULT_PROJECT="NOEXISTE" python test_connection.py
# FALLO: Las credenciales son válidas..., pero no se pudo acceder al proyecto por defecto...
```

## Limitaciones y notas de integración

- **ADF**: Jira Cloud v3 exige que descripción y comentarios estén en Atlassian
  Document Format. La librería convierte automáticamente el texto plano a ADF (y
  al leer un issue devuelve la descripción como texto plano).
- **Transiciones**: los estados a los que se puede pasar dependen del flujo de
  trabajo del proyecto y del estado actual. `transition_issue` resuelve el nombre
  del estado a la transición; si no es alcanzable, lanza `JiraDataError` con las
  opciones válidas.
- **Asignación**: se hace por `accountId` de Atlassian (no por email), por las
  políticas de privacidad de Atlassian.
- **Rate limits**: Jira aplica límites por cuenta/IP; ante HTTP 429 la librería
  lanza `JiraRateLimitError` con `retry_after` (segundos a esperar).
- **JQL**: `search_issues` usa el endpoint `POST /rest/api/3/search/jql`. Un JQL
  inválido produce `JiraDataError` con el detalle del error de Jira.
- El API token nunca se loguea ni se incluye en mensajes de excepción.
