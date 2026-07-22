---
name: aranda
description: >
  Usa la librería ruvic_aranda_connector para gestionar casos del service
  desk de Aranda ASMS - crear casos (incidentes, requerimientos, problemas,
  cambios) con create_item, consultar un caso por su id con get_item_by_id,
  y todo el descubrimiento previo necesario: proyectos, servicios,
  categorías, modelos, estados, compañías, clientes, campos adicionales,
  grupos y responsables, más catálogos (urgencia, impacto, tipos de caso) y
  búsqueda de elementos de configuración (CIs) en la CMDB. Úsala cuando el
  usuario pida abrir/crear un caso o ticket en Aranda, consultar un caso, o
  resolver los IDs necesarios para crearlo.
triggers:
- aranda
- asms
- mesa de servicio
- service desk
- crear caso
- abrir ticket
- incidente
- requerimiento
- problema
- cambio
- itsm
- ci
- cmdb
---

# Conector Aranda ASMS (ruvic_aranda_connector)

Librería Python para la API v9 de Aranda ASMS. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-aranda.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea el token**. Siempre se lee de variables de entorno, disponibles cuando el conector `aranda` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_ARANDA_TOKEN` | Token de integración (secreto — jamás imprimirlo) |
| `RUVIC_ARANDA_BASE_URL` | (opcional) URL base de la API v9 |
| `RUVIC_ARANDA_VERIFY_SSL` | (opcional) validar TLS; default `false` |
| `RUVIC_ARANDA_TIMEOUT` | (opcional) timeout en segundos, default 30 |

Si `RUVIC_ARANDA_TOKEN` NO existe, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Conexión (siempre igual)

```python
from ruvic_aranda_connector import ArandaClient

client = ArandaClient()  # lee RUVIC_ARANDA_* del entorno automáticamente
```

## Cómo crear un caso (flujo completo de IDs)

Aranda necesita muchos IDs relacionados. **Resuélvelos en este orden** usando las skills de descubrimiento; no inventes IDs:

```python
project_id = 1
item_type  = 1   # 1=Incidente, 2=Problema, 3=Cambio, 4=Requerimiento (según instalación)

# 1) servicio del proyecto para ese tipo de caso
services   = client.get_services(project_id, item_type)
service_id = services[0]["id"]

# 2) categoría del servicio
categories  = client.get_categories_by_service(item_type, service_id)
category_id = categories[0]["id"]

# 3) modelo de flujo de trabajo
model    = client.get_model(item_type, category_id, service_id)
model_id = model["id"]

# 4) estado inicial del modelo
states   = client.get_states(model_id, item_type)
state_id = states[0]["id"]

# 5) compañía y cliente (usuario final)
company_id  = client.get_companies(project_id, item_type)[0]["id"]
customer_id = client.get_customers(project_id, item_type, company_id, service_id)[0]["id"]

# 6) (opcional) campos adicionales obligatorios
fields = client.get_additional_fields(category_id, item_type, model_id, state_id)

# 7) crear el caso
caso = client.create_item(
    author_id=customer_id,
    category_id=category_id,
    company_id=company_id,
    customer_id=customer_id,
    description="El servidor de correo no responde desde las 9:00.",
    item_type=item_type,
    model_id=model_id,
    project_id=project_id,
    service_id=service_id,
    state_id=state_id,
    subject="Caída del servidor de correo",
    urgency_id=None,           # ver client.get_urgency()
    additional_fields=None,    # completar según get_additional_fields
)
print(caso["idByProject"], "→ id interno:", caso["id"])
```

## Consultar un caso

```python
detalle = client.get_item_by_id(caso["id"])   # id INTERNO, no 'IM-10658'
print(detalle["subject"], "|", detalle.get("stateName"))
```

## Catálogos globales (sin parámetros)

```python
client.get_item_types()      # tipos de caso según licencia
client.get_urgency()         # niveles de urgencia
client.get_impact()          # niveles de impacto
client.get_registry_types()  # tipos de registro/nota
```

## Flujo de trabajo, transiciones y asignación

```python
# transiciones válidas DESDE un estado (pasa state_id):
client.get_states(model_id, item_type, state_id=state_id)
# grupos disponibles en un estado del servicio:
client.get_groups_by_state(service_id, state_id)
# motivos asociados a un estado:
client.get_reasons_for_state(state_id)
# especialistas (responsables) de un grupo en un proyecto:
client.get_responsible(group_id, project_id)
```

## CMDB — Elementos de configuración

```python
cis = client.search_cis(project_id, item_type, service_id, ci_item_types=[21])
```

## Manejo de errores

```python
from ruvic_aranda_connector import (
    ArandaAuthError,
    ArandaDataError,
    ArandaNetworkError,
    ArandaRateLimitError,
)

try:
    client.create_item(...)
except ArandaAuthError:
    print("Token inválido o sin permisos — revisa la configuración del conector")
except ArandaRateLimitError as e:
    print(f"Límite de peticiones; reintentar en {e.retry_after}s")
except ArandaNetworkError:
    print("No se pudo alcanzar Aranda — revisa la URL base y la red")
except ArandaDataError as e:
    print(f"Error de datos: {e}")  # IDs inexistentes, combinación inválida, campos faltantes…
```

## Buenas prácticas al generar código

1. Lee el token SOLO de `RUVIC_ARANDA_TOKEN` (el constructor de `ArandaClient` ya lo hace); nunca lo imprimas.
2. **Resuelve los IDs con las skills de descubrimiento antes de crear un caso**; no inventes IDs ni los copies de ejemplos.
3. Los IDs de `item_type` y de estados/servicios dependen de la instalación: obténlos en tiempo de ejecución.
4. Para consultar un caso usa el `id` interno (devuelto por `create_item`), no el código visible `idByProject`.
5. Muchas instalaciones usan certificado interno: si aparece un error TLS, el conector ya viene con `verify_ssl=false` por defecto; no lo fuerces a true salvo que el sitio tenga cert público.
6. Ante `ArandaDataError`, revisa que la combinación proyecto/servicio/categoría/modelo/estado sea coherente (los endpoints de descubrimiento la validan).
