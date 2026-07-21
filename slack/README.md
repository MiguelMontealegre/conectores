# Conector Slack — `slack`

Conector Ruvic para la **Web API de Slack**: mensajería a canales (públicos y
privados) y a usuarios por mensaje directo, más consulta y listado de canales.

## Instalación

```bash
pip install git+https://github.com/tu-org/conector-slack.git#subdirectory=lib
```

- Python ≥ 3.10 (probado en 3.12).
- Única dependencia: `requests>=2.31,<3.0`.
- Requiere salida HTTPS hacia `slack.com` (puerto 443).

## Prerrequisitos en Slack

1. **Crear una app de Slack**: entra a <https://api.slack.com/apps> → **Create New
   App** → **From scratch**. Dale un nombre y elige el workspace.
2. **Añadir scopes de bot**: en **OAuth & Permissions → Scopes → Bot Token
   Scopes**, agrega como mínimo:
   - `chat:write` — enviar mensajes.
   - `im:write` — abrir mensajes directos a usuarios.
   - `channels:read` y `groups:read` — resolver/consultar canales (públicos y
     privados).
   - (opcional) `chat:write.public` — publicar en canales públicos sin necesidad
     de invitar el bot.
3. **Instalar la app en el workspace**: en **OAuth & Permissions** pulsa
   **Install to Workspace** y autoriza. Slack genera el **Bot User OAuth Token**
   (formato `xoxb-...`). Ese token va en el campo *Bot User OAuth Token* del
   formulario (se guarda como secreto).
4. **Invitar el bot al canal destino**: en Slack, dentro del canal, escribe
   `/invite @tu-bot`. Sin esto, publicar da error `not_in_channel` (salvo que uses
   `chat:write.public` en canales públicos).
5. **Obtener IDs (opcional)**: para el *destino por defecto* puedes usar el nombre
   del canal (`#general`), o su ID. El ID de un canal aparece en su URL o al final
   del panel *About* del canal (empieza por `C`); el ID de un usuario está en su
   perfil → **Copy member ID** (empieza por `U`).

## Variables de entorno (generadas por la plataforma)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_SLACK_BOT_TOKEN` | Sí | Bot User OAuth Token `xoxb-…` (secreto) |
| `RUVIC_SLACK_DEFAULT_CHANNEL` | No | Destino por defecto: `#canal`, ID de canal (`C…`) o de usuario (`U…`) |
| `RUVIC_SLACK_TIMEOUT` | No | Timeout HTTP en segundos (default 15) |

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_SLACK_BOT_TOKEN="xoxb-..."
export RUVIC_SLACK_DEFAULT_CHANNEL="#general"   # opcional
export SLACK_TEST_USER_ID="U0123ABCD"           # opcional, para probar DM

python test_connection.py        # prueba de conexión estándar
python validate_local.py         # ejercita las capacidades de mensajería
```

Casos de fallo a verificar:

```bash
RUVIC_SLACK_BOT_TOKEN="xoxb-tokeninvalido" python test_connection.py
# FALLO: Autenticación fallida: Fallo de autenticación de Slack (invalid_auth)...

RUVIC_SLACK_DEFAULT_CHANNEL="C000INEXISTENTE" python test_connection.py
# FALLO: El token es válido..., pero no se pudo consultar el canal por defecto...
```

## Capacidades

| Operación | Método | Qué hace |
|-----------|--------|----------|
| `chat.send_message` | `send_message(text, channel=…)` | Envía a un canal (`#nombre`/`C…`) o a un usuario (`U…`, abre DM solo) |
| `chat.send_direct_message` | `send_direct_message(text, user_id=…)` | Mensaje directo a una persona por su ID |
| `chat.get_channel_info` | `get_channel_info(channel=…)` | Información de un canal |
| `chat.list_channels` | `list_channels()` | Lista canales visibles (para resolver nombre → ID) |

## Limitaciones y notas de integración

- **Invitación al canal**: para publicar en un canal el bot debe estar invitado
  (`/invite @tu-bot`), salvo canales públicos con el scope `chat:write.public`.
- **Rate limits de Slack**: `chat.postMessage` admite ~1 mensaje/segundo por canal
  (con ráfagas cortas). Ante HTTP 429 la librería lanza `SlackRateLimitError` con
  `retry_after` (segundos a esperar, tomados de la cabecera `Retry-After`).
- **Longitud del mensaje**: Slack corta el texto alrededor de 40 000 caracteres;
  para bloques usa `blocks` (Block Kit).
- **Mensajería a usuarios**: se hace por ID de usuario (`U…`); el conector abre el
  DM automáticamente con `conversations.open` (scope `im:write`).
- El token nunca se loguea ni se incluye en mensajes de excepción.
