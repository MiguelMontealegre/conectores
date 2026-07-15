---
name: gchat
description: >
  Usa la librería ruvic_gchat_connector para enviar mensajes a espacios de
  Google Chat (send_message), listar los espacios disponibles (list_spaces)
  y consultar información de un espacio (get_space). Úsala cuando el usuario
  pida enviar un mensaje, notificación, alerta o reporte a Google Chat o a
  un espacio/sala de Google Workspace.
triggers:
- google chat
- gchat
- espacio de chat
- enviar mensaje
- notificacion
- notificación
- google workspace
---

# Conector Google Chat (ruvic_gchat_connector)

Librería Python de mensajería para espacios de Google Chat. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-gchat.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `gchat` está configurado. El conector tiene dos modos; las variables presentes dependen del modo elegido:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_GCHAT_WEBHOOK_URL` | (modo webhook) URL completa del webhook — secreta, jamás imprimirla |
| `RUVIC_GCHAT_SERVICE_ACCOUNT_JSON` | (modo cuenta de servicio) JSON de credenciales — secreto, jamás imprimirlo |
| `RUVIC_GCHAT_DEFAULT_SPACE` | (opcional, modo cuenta de servicio) espacio destino por defecto |
| `RUVIC_GCHAT_TIMEOUT` | (opcional) timeout en segundos, default 15 |

Si ninguna de las dos primeras existe, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

Diferencia entre modos (el cliente lo detecta solo):
- **webhook**: solo puede enviar mensajes, y siempre al espacio del webhook. `list_spaces`/`get_space` no están disponibles.
- **service_account**: puede enviar a cualquier espacio donde la app esté agregada, listar espacios y consultar información.

## Conexión (siempre igual)

```python
from ruvic_gchat_connector import GchatClient

client = GchatClient()  # lee RUVIC_GCHAT_* del entorno y detecta el modo
print(client.config.mode)  # "webhook" o "service_account"
```

## Capacidad 1 — Enviar un mensaje a un espacio

```python
# Al espacio del webhook o al espacio por defecto:
result = client.send_message("Backup completado ✅")
print(f"Mensaje creado: {result['message_name']}")

# A un espacio específico (solo modo service_account):
client.send_message("Reporte diario listo", space="spaces/AAAAAAAAAAA")

# Agrupar mensajes relacionados en un mismo hilo:
client.send_message("Inicio del despliegue…", thread_key="deploy-2026-07-12")
client.send_message("Despliegue finalizado ✅", thread_key="deploy-2026-07-12")
```

Notas:
- Máximo 4096 caracteres por mensaje; para textos largos, divide en varios `send_message`.
- Formato de texto de Google Chat: `*negrita*`, `_cursiva_`, `~tachado~`, `` `código` `` y `<https://url|texto del enlace>`.

## Capacidad 2 — Listar espacios (solo service_account)

```python
for s in client.list_spaces():
    print(f"{s['name']}: {s['display_name']} ({s['type']})")
```

Útil para descubrir el identificador `spaces/XXXX` de un espacio por su nombre visible.

## Capacidad 3 — Información de un espacio (solo service_account)

```python
info = client.get_space("spaces/AAAAAAAAAAA")
print(f"{info['display_name']} (type={info['type']})")
```

## Manejo de errores

```python
from ruvic_gchat_connector import (
    GchatAuthError,
    GchatDataError,
    GchatNetworkError,
    GchatRateLimitError,
)

try:
    client.send_message("Hola equipo")
except GchatAuthError:
    print("Credenciales inválidas — revisa la configuración del conector")
except GchatRateLimitError:
    print("Límite de peticiones de Google; espera y reintenta")
except GchatNetworkError:
    print("No se pudo alcanzar chat.googleapis.com — revisa la red")
except GchatDataError as e:
    print(f"Error de datos: {e}")  # espacio inexistente, app no agregada…
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_GCHAT_*` (el constructor de `GchatClient` ya lo hace).
2. Nunca imprimas `RUVIC_GCHAT_WEBHOOK_URL` ni `RUVIC_GCHAT_SERVICE_ACCOUNT_JSON` en logs ni en la salida (ambas contienen secretos).
3. Antes de usar `list_spaces`/`get_space` o el parámetro `space`, verifica el modo con `client.config.mode`: en modo webhook solo existe `send_message` al espacio fijo.
4. Si el usuario nombra un espacio por su título visible, usa `list_spaces()` para resolver el identificador `spaces/XXXX`; no lo inventes.
5. Usa `thread_key` estable (ej. un id de tarea) para que las actualizaciones del mismo proceso queden en un solo hilo.
6. Ante `GchatRateLimitError`, espera unos segundos (`time.sleep`) y reintenta.
