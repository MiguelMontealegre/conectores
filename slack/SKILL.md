---
name: slack
description: >
  Usa la librería ruvic_slack_connector para enviar mensajes por Slack -
  a canales públicos o privados y a usuarios por mensaje directo
  (send_message / send_direct_message), consultar la información de un
  canal (get_channel_info) y listar los canales del workspace
  (list_channels). Úsala cuando el usuario pida enviar una notificación,
  aviso, alerta, reporte o mensaje por Slack, ya sea a un canal o a una
  persona.
triggers:
- slack
- enviar mensaje
- notificacion
- notificación
- avisar por slack
- canal de slack
- mensaje directo
- dm
- mensaje a usuario
---

# Conector Slack (ruvic_slack_connector)

Librería Python para la Web API de Slack. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-slack.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `slack` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_SLACK_BOT_TOKEN` | Bot User OAuth Token (xoxb-…, secreto — jamás imprimirlo) |
| `RUVIC_SLACK_DEFAULT_CHANNEL` | (opcional) destino por defecto: #canal, ID de canal (C…) o ID de usuario (U…) |
| `RUVIC_SLACK_TIMEOUT` | (opcional) timeout en segundos, default 15 |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Conexión (siempre igual)

```python
from ruvic_slack_connector import SlackClient

client = SlackClient()  # lee RUVIC_SLACK_* del entorno automáticamente
```

## Capacidad 1 — Enviar un mensaje a un canal

```python
# Al destino por defecto del conector:
result = client.send_message("Backup completado ✅")
print(f"Mensaje {result['ts']} enviado al canal {result['channel']}")

# A un canal específico (por nombre o por ID):
client.send_message("Reporte diario listo", channel="#operaciones")
client.send_message("Reporte diario listo", channel="C0123ABCD")
```

Notas:
- El bot debe estar **invitado al canal** (`/invite @tu-bot`) para publicar ahí; si no, Slack responde `not_in_channel`.
- El texto admite **mrkdwn** de Slack: `*negrita*`, `_cursiva_`, `` `código` ``, `<https://ruvic.io|enlace>`.
- Para mensajes enriquecidos usa `blocks=[...]` (Block Kit); `text` queda como respaldo de notificación.

## Capacidad 2 — Enviar un mensaje directo a un usuario

```python
# Por ID de usuario (recomendado, "U…"):
dm = client.send_direct_message("¿Puedes revisar el PR?", user_id="U0123ABCD")
print(f"DM enviado ({dm['ts']}) en el canal {dm['channel']}")

# send_message también acepta un ID de usuario como destino y abre el DM solo:
client.send_message("Aviso personal", channel="U0123ABCD")
```

El conector abre (o reutiliza) el canal de DM automáticamente con `conversations.open`. Requiere el scope `im:write`.

## Capacidad 3 — Información de un canal

```python
info = client.get_channel_info("C0123ABCD")
print(f"#{info['name']} — miembro: {info['is_member']}, privados: {info['is_private']}")
```

## Capacidad 4 — Listar / resolver canales

```python
# Útil para encontrar el ID de un canal a partir de su nombre:
for c in client.list_channels():
    print(c["name"], c["id"], "miembro" if c["is_member"] else "")
```

## Manejo de errores

```python
from ruvic_slack_connector import (
    SlackAuthError,
    SlackDataError,
    SlackNetworkError,
    SlackRateLimitError,
)

try:
    client.send_message("Hola", channel="#general")
except SlackAuthError:
    print("Token inválido o falta un scope — revisa la configuración del conector")
except SlackRateLimitError as e:
    print(f"Límite de peticiones; reintentar en {e.retry_after}s")
except SlackNetworkError:
    print("No se pudo alcanzar slack.com — revisa la red")
except SlackDataError as e:
    print(f"Error de datos: {e}")  # canal inexistente, bot no invitado, usuario desconocido…
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_SLACK_*` (el constructor de `SlackClient` ya lo hace).
2. Nunca imprimas `RUVIC_SLACK_BOT_TOKEN` en logs ni en la salida.
3. Si el usuario no indica destino, usa el destino por defecto (omite `channel`); si no hay default, pídele el canal o el usuario en lugar de inventarlo.
4. Para mensajería a personas usa `send_direct_message(user_id=...)`; para canales usa `send_message(channel="#…")`.
5. Recuerda que el bot debe estar invitado al canal para publicar; ante `not_in_channel` indica al usuario que ejecute `/invite @tu-bot`.
6. Al enviar muchos mensajes seguidos, captura `SlackRateLimitError` y espera `retry_after` segundos antes de reintentar (`time.sleep`).
