# Conector Telegram — `telegram`

Conector Ruvic para la **Bot API de Telegram**: envío de mensajes y archivos a
chats, grupos y canales, recepción de actualizaciones (mensajes entrantes) e
información de chats.

## Instalación

```bash
pip install git+https://github.com/tu-org/conector-telegram.git#subdirectory=lib
```

- Python ≥ 3.10 (probado en 3.12).
- Única dependencia: `requests>=2.31,<3.0`.
- Requiere salida HTTPS hacia `api.telegram.org` (puerto 443).

## Prerrequisitos en Telegram

1. **Crear el bot**: en Telegram, hablar con [@BotFather](https://t.me/BotFather)
   → `/newbot` → asignar nombre y username (termina en `bot`). BotFather
   entrega el **token** (formato `123456789:AAH8x...`). Ese token va en el
   campo *Token del bot* del formulario (se guarda como secreto).
2. **Permisos en el destino**:
   - Chat privado: el usuario debe iniciar la conversación con el bot primero
     (los bots no pueden escribirle a alguien que nunca les habló).
   - Grupo/supergrupo: agregar el bot como miembro.
   - Canal: agregar el bot como **administrador** con permiso de publicar.
3. **Obtener el chat_id**: agregar el bot al chat, escribir un mensaje ahí y
   ejecutar `client.get_updates()` (o `https://api.telegram.org/bot<TOKEN>/getUpdates`).
   El `chat.id` aparece en la respuesta. Supergrupos y canales empiezan por `-100`.
4. **(Opcional) leer todos los mensajes de un grupo**: por defecto el *privacy
   mode* hace que el bot solo vea comandos y menciones. Desactivarlo en
   BotFather: `/setprivacy` → seleccionar el bot → **Disable** (y re-agregar el
   bot al grupo para que aplique).
5. **Sin webhook**: `get_updates` (polling) entra en conflicto si el bot tiene
   un webhook configurado. Si se usó webhook antes, eliminarlo con
   `deleteWebhook`.

## Variables de entorno (generadas por la plataforma)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_TELEGRAM_BOT_TOKEN` | Sí | Token de BotFather (secreto) |
| `RUVIC_TELEGRAM_DEFAULT_CHAT_ID` | No | Chat/grupo/canal destino por defecto |
| `RUVIC_TELEGRAM_TIMEOUT` | No | Timeout HTTP en segundos (default 15) |

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_TELEGRAM_BOT_TOKEN="123456789:AAH8x..."
export RUVIC_TELEGRAM_DEFAULT_CHAT_ID="-1001234567890"   # opcional

python test_connection.py        # prueba de conexión estándar
python validate_local.py         # ejercita las 4 capacidades
```

Casos de fallo a verificar:

```bash
RUVIC_TELEGRAM_BOT_TOKEN="123:tokeninvalido00000000000000000000" python test_connection.py
# FALLO: Autenticación fallida: Token de bot inválido o revocado...

RUVIC_TELEGRAM_DEFAULT_CHAT_ID="999999999999" python test_connection.py
# FALLO: El token es válido..., pero el bot no tiene acceso al chat por defecto...
```

## Limitaciones y notas de integración

- **Rate limits de Telegram**: ~30 mensajes/segundo global y ~20 mensajes/minuto
  al mismo grupo. Ante HTTP 429 la librería lanza `TelegramRateLimitError` con
  `retry_after` (segundos a esperar).
- **Tamaño de archivos**: la Bot API permite subir máximo **50 MB** por archivo
  (validado por la librería antes de subir).
- **Mensajes**: máximo 4096 caracteres (validado por la librería).
- **`get_updates`**: Telegram retiene actualizaciones máximo 24 h; el modelo de
  consumo es por `offset` (ver SKILL.md). No compatible con webhook activo.
- El token nunca se loguea ni se incluye en mensajes de excepción.
