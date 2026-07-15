# Conector Google Chat — `gchat`

Conector Ruvic de **mensajería a espacios de Google Chat**, con dos modos de
autenticación:

| Modo | Alcance | Complejidad de configuración |
|------|---------|------------------------------|
| **Webhook entrante** | Enviar mensajes a UN espacio (el del webhook) | Mínima: se crea desde el propio espacio |
| **Cuenta de servicio (Chat API)** | Enviar a cualquier espacio donde la app esté agregada, listar espacios, consultar espacios | Requiere proyecto de Google Cloud |

## Instalación

```bash
pip install git+https://github.com/tu-org/conector-gchat.git#subdirectory=lib
```

- Python ≥ 3.10 (probado en 3.12).
- Dependencias: `requests>=2.31,<3.0` y `google-auth>=2.28,<3.0`.
- Requiere salida HTTPS hacia `chat.googleapis.com` y `oauth2.googleapis.com`.

## Prerrequisitos — Modo webhook

1. En Google Chat, abre el **espacio** destino (los webhooks solo existen en
   espacios, no en mensajes directos).
2. Nombre del espacio → **Apps e integraciones** → **Webhooks** →
   **Añadir webhook**: asigna nombre (y avatar opcional).
3. Copia la **URL completa** generada (incluye los parámetros `key` y
   `token` — sin ellos no funciona). Esa URL va al campo *URL del webhook*
   (se guarda como secreto).

Nota: se necesita permiso para gestionar apps e integraciones en el espacio;
en algunos dominios de Workspace el administrador puede tener los webhooks
deshabilitados.

> Verifica el flujo en la consola/UI real al momento de escribir la guía de
> portal (`docs/index.html`); los menús de Google cambian con frecuencia.

## Prerrequisitos — Modo cuenta de servicio (Chat API)

1. En **Google Cloud Console**: crea (o elige) un proyecto.
2. **APIs y servicios → Biblioteca** → busca **Google Chat API** → **Habilitar**.
3. **IAM y administración → Cuentas de servicio** → **Crear cuenta de
   servicio** → luego, en la cuenta creada: **Claves → Agregar clave →
   Crear clave nueva → JSON**. Descarga el archivo; su contenido completo va
   al campo *Credenciales de la cuenta de servicio (JSON)*.
4. **APIs y servicios → Google Chat API → Configuración**: configura la
   **app de Chat** (nombre, avatar, descripción) y habilita que pueda
   agregarse a espacios. Sin este paso la API responde 403/404.
5. En cada **espacio destino**: agregar la app de Chat como miembro
   (＋ Añadir personas y apps → nombre de tu app).
6. Scope OAuth usado por la librería: `https://www.googleapis.com/auth/chat.bot`
   (autenticación de app; no requiere delegación de dominio para enviar
   mensajes como la app).

## Variables de entorno (generadas por la plataforma)

| Variable | Modo | Descripción |
|----------|------|-------------|
| `RUVIC_GCHAT_WEBHOOK_URL` | webhook | URL completa del webhook (secreta) |
| `RUVIC_GCHAT_SERVICE_ACCOUNT_JSON` | service_account | JSON completo de credenciales (secreto) |
| `RUVIC_GCHAT_DEFAULT_SPACE` | service_account (opcional) | Espacio destino por defecto (`spaces/XXXX`) |
| `RUVIC_GCHAT_TIMEOUT` | ambos (opcional) | Timeout HTTP en segundos (default 15) |

El modo se infiere de cuál credencial está definida (si ambas, prevalece la
cuenta de servicio).

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

# Modo webhook:
export RUVIC_GCHAT_WEBHOOK_URL='https://chat.googleapis.com/v1/spaces/XXXX/messages?key=...&token=...'

# O modo cuenta de servicio:
export RUVIC_GCHAT_SERVICE_ACCOUNT_JSON="$(cat credenciales.json)"
export RUVIC_GCHAT_DEFAULT_SPACE='spaces/AAAAAAAAAAA'   # opcional

python test_connection.py        # prueba de conexión (no publica mensajes)
python validate_local.py         # ejercita las capacidades (SÍ publica)
```

Casos de fallo a verificar:

```bash
# URL de webhook con token mutilado → FALLO: Autenticación fallida...
RUVIC_GCHAT_WEBHOOK_URL='https://chat.googleapis.com/v1/spaces/XXXX/messages?key=abc&token=malo' python test_connection.py

# JSON inválido → FALLO: ...no contiene un JSON válido...
RUVIC_GCHAT_SERVICE_ACCOUNT_JSON='{esto no es json' python test_connection.py

# Sin variables → FALLO: Faltan credenciales del conector gchat...
env -i PATH="$PATH" python test_connection.py
```

## Limitaciones y notas de integración

- **Mensajes**: máximo 4096 caracteres en el campo `text` (validado por la
  librería). Formato básico: `*negrita*`, `_cursiva_`, `<url|texto>`.
- **Modo webhook**: solo envío de mensajes y solo al espacio del webhook;
  `list_spaces`/`get_space` lanzan `GchatAuthError` explicando la limitación.
- **Modo cuenta de servicio**: la app debe estar agregada a cada espacio
  destino; si no, la API responde 404 (traducido a `GchatDataError` con
  mensaje accionable).
- **Rate limits**: la Chat API limita por proyecto y por espacio; ante HTTP
  429 la librería lanza `GchatRateLimitError`.
- **Hilos**: `thread_key` agrupa mensajes en un hilo (con fallback a mensaje
  nuevo si el espacio no usa hilos).
- La prueba de conexión NO publica mensajes: en modo webhook valida la URL
  con un POST vacío (respuesta 400 esperada = URL válida), y en modo cuenta
  de servicio llama `spaces.list`.
- Ninguna credencial (URL del webhook, JSON, tokens) se loguea ni se incluye
  en mensajes de excepción.
