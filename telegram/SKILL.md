---
name: telegram
description: >
  Usa la librería ruvic_telegram_connector para interactuar con Telegram vía
  bot - enviar mensajes de texto a chats, grupos y canales (send_message),
  enviar archivos como documentos, fotos, videos o audios (send_file),
  recibir mensajes y actualizaciones entrantes (get_updates) y consultar
  información de un chat (get_chat). Úsala cuando el usuario pida enviar una
  notificación, mensaje, alerta, reporte o archivo por Telegram, o leer los
  mensajes que ha recibido el bot.
triggers:
- telegram
- enviar mensaje
- notificacion
- notificación
- avisar por telegram
- grupo de telegram
- canal de telegram
- bot
---

# Conector Telegram (ruvic_telegram_connector)

Librería Python para la Bot API de Telegram. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-telegram.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `telegram` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_TELEGRAM_BOT_TOKEN` | Token del bot (secreto — jamás imprimirlo) |
| `RUVIC_TELEGRAM_DEFAULT_CHAT_ID` | (opcional) chat/grupo destino por defecto |
| `RUVIC_TELEGRAM_TIMEOUT` | (opcional) timeout en segundos, default 15 |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Conexión (siempre igual)

```python
from ruvic_telegram_connector import TelegramClient

client = TelegramClient()  # lee RUVIC_TELEGRAM_* del entorno automáticamente
```

## Capacidad 1 — Enviar un mensaje / notificación

```python
# Al chat por defecto del conector:
result = client.send_message("Backup completado ✅")
print(f"Mensaje {result['message_id']} enviado al chat {result['chat_id']}")

# A un chat/grupo/canal específico:
client.send_message(
    "Reporte diario listo",
    chat_id="-1001234567890",       # o "@mi_canal" para canales públicos
    disable_notification=True,       # envío silencioso
)
```

Notas:
- Máximo 4096 caracteres por mensaje; para textos largos, divide en varios `send_message`.
- `parse_mode="HTML"` permite formato: `client.send_message("<b>Alerta</b>: disco al 90%", parse_mode="HTML")`.
- Una "notificación" en Telegram es simplemente un mensaje; usa `disable_notification=True` solo si debe llegar sin sonido.

## Capacidad 2 — Enviar un archivo

```python
result = client.send_file(
    "/tmp/reporte_mensual.pdf",
    caption="Reporte mensual de ventas",
    kind="document",                 # "document" | "photo" | "video" | "audio"
)
print(f"Archivo {result['file_name']} enviado (mensaje {result['message_id']})")
```

Límite de la Bot API: 50 MB por archivo.

## Capacidad 3 — Recibir actualizaciones (mensajes entrantes)

```python
updates = client.get_updates()
for u in updates:
    print(f"[{u['chat_title']}] {u['from_user']}: {u['text']}")

# Para no volver a recibir las mismas actualizaciones en la próxima llamada,
# confirma con offset = último update_id + 1:
if updates:
    client.get_updates(offset=updates[-1]["update_id"] + 1, limit=1, timeout=0)
```

`getUpdates` solo funciona si el bot NO tiene un webhook configurado; si Telegram responde con conflicto, el bot tiene un webhook activo que debe eliminarse.

## Capacidad 4 — Información de un chat

```python
info = client.get_chat("-1001234567890")
print(f"{info['type']}: {info['title']} (id={info['id']})")
```

## Manejo de errores

```python
from ruvic_telegram_connector import (
    TelegramAuthError,
    TelegramDataError,
    TelegramNetworkError,
    TelegramRateLimitError,
)

try:
    client.send_message("Hola")
except TelegramAuthError:
    print("Token inválido — revisa la configuración del conector")
except TelegramRateLimitError as e:
    print(f"Límite de peticiones; reintentar en {e.retry_after}s")
except TelegramNetworkError:
    print("No se pudo alcanzar api.telegram.org — revisa la red")
except TelegramDataError as e:
    print(f"Error de datos: {e}")  # chat inexistente, bot expulsado, archivo muy grande…
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_TELEGRAM_*` (el constructor de `TelegramClient` ya lo hace).
2. Nunca imprimas `RUVIC_TELEGRAM_BOT_TOKEN` en logs ni en la salida.
3. Si el usuario no indica destino, usa el chat por defecto (omite `chat_id`); si no hay default configurado, pídele el chat_id en lugar de inventarlo.
4. Al enviar muchos mensajes seguidos, captura `TelegramRateLimitError` y espera `retry_after` segundos antes de reintentar (`time.sleep`).
5. Los mensajes tienen máximo 4096 caracteres y los archivos 50 MB: valida o divide antes de enviar.
6. Tras procesar actualizaciones con `get_updates`, confirma con `offset` para no reprocesarlas.
