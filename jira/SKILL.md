---
name: jira
description: >
  Usa la librería ruvic_jira_connector para gestionar tickets en Jira Cloud -
  crear tickets/incidencias (create_issue), actualizar sus campos
  (update_issue), cambiar su estado con el flujo de trabajo
  (transition_issue), comentar (add_comment), buscar con JQL
  (search_issues) y obtener un ticket por su clave (get_issue). Úsala
  cuando el usuario pida crear una tarea/bug/incidencia en Jira, mover un
  ticket de estado, comentar en un ticket, o consultar/listar tickets.
triggers:
- jira
- ticket
- incidencia
- crear tarea
- bug
- issue
- mover a
- cambiar estado
- comentar ticket
- buscar tickets
- jql
- atlassian
---

# Conector Jira (ruvic_jira_connector)

Librería Python para la REST API de Jira Cloud (v3). Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-jira.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `jira` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_JIRA_BASE_URL` | URL del sitio, ej. `https://miempresa.atlassian.net` |
| `RUVIC_JIRA_EMAIL` | Email de la cuenta Atlassian |
| `RUVIC_JIRA_API_TOKEN` | API token (secreto — jamás imprimirlo) |
| `RUVIC_JIRA_DEFAULT_PROJECT` | (opcional) clave de proyecto por defecto, ej. `OPS` |
| `RUVIC_JIRA_TIMEOUT` | (opcional) timeout en segundos, default 20 |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Conexión (siempre igual)

```python
from ruvic_jira_connector import JiraClient

client = JiraClient()  # lee RUVIC_JIRA_* del entorno automáticamente
```

## Capacidad 1 — Crear un ticket

```python
issue = client.create_issue(
    summary="El nodo 3 no responde",
    project="OPS",            # opcional si hay proyecto por defecto
    issue_type="Bug",         # "Task" | "Bug" | "Story" | ...
    description="Detectado a las 10:32. Reinicio no soluciona.",
    priority="High",          # opcional (si el proyecto usa prioridades)
    labels=["infra", "urgente"],
)
print(issue["key"], issue["url"])   # OPS-123 https://.../browse/OPS-123
```

La `description` se pasa como texto plano; la librería la convierte al formato ADF que exige Jira Cloud v3.

## Capacidad 2 — Actualizar campos de un ticket

```python
client.update_issue("OPS-123", priority="Highest", labels=["infra", "sev1"])
```

Solo se modifican los campos indicados. **El estado NO se cambia aquí** — usa `transition_issue`.

## Capacidad 3 — Cambiar el estado (transición)

```python
# Basta el nombre del estado destino; la librería resuelve la transición:
client.transition_issue("OPS-123", "In Progress")
client.transition_issue("OPS-123", "Done", comment="Resuelto con el fix #42")

# Si dudas de los estados alcanzables desde el estado actual:
for tr in client.list_transitions("OPS-123"):
    print(tr["name"], "→", tr["to_status"])
```

Los estados disponibles dependen del **flujo de trabajo** del proyecto y del estado actual del ticket. Si el estado pedido no es alcanzable, se lanza `JiraDataError` listando las opciones válidas.

## Capacidad 4 — Comentar un ticket

```python
client.add_comment("OPS-123", "Desplegado el fix en producción a las 14:05.")
```

## Capacidad 5 — Buscar tickets con JQL

```python
issues = client.search_issues(
    'project = OPS AND status != Done ORDER BY created DESC',
    max_results=20,
)
for i in issues:
    print(f"[{i['status']}] {i['key']}: {i['summary']} ({i['assignee']})")
```

JQL de ejemplo útiles:
- `assignee = currentUser() AND status = "In Progress"`
- `project = OPS AND priority = High AND created >= -7d`
- `text ~ "servidor caído" ORDER BY updated DESC`

## Capacidad 6 — Obtener un ticket por su clave

```python
t = client.get_issue("OPS-123")
print(t["summary"], "|", t["status"], "|", t["assignee"])
print(t["description"])   # descripción como texto plano
```

## Manejo de errores

```python
from ruvic_jira_connector import (
    JiraAuthError,
    JiraDataError,
    JiraNetworkError,
    JiraRateLimitError,
)

try:
    client.create_issue("Nueva tarea", project="OPS")
except JiraAuthError:
    print("Credenciales inválidas o sin permisos — revisa el conector")
except JiraRateLimitError as e:
    print(f"Límite de peticiones; reintentar en {e.retry_after}s")
except JiraNetworkError:
    print("No se pudo alcanzar el sitio de Jira — revisa la URL y la red")
except JiraDataError as e:
    print(f"Error de datos: {e}")  # proyecto/issue inexistente, transición inválida, JQL malo…
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_JIRA_*` (el constructor de `JiraClient` ya lo hace).
2. Nunca imprimas `RUVIC_JIRA_API_TOKEN` en logs ni en la salida.
3. Si el usuario no indica proyecto, usa el proyecto por defecto (omite `project`); si no hay default, pídele la clave del proyecto en lugar de inventarla.
4. Para asignar un ticket usa `assignee_account_id` (el **accountId** de Atlassian, no el email); resuélvelo antes si solo tienes el nombre.
5. Para cambiar estado usa `transition_issue` (no `update_issue`); ante `JiraDataError` de transición, muestra los estados alcanzables que trae el mensaje.
6. En búsquedas, entrega siempre el `key` y la `url` para que el usuario abra el ticket; acota con `max_results` para no traer listas enormes.
