# Conector Twilio SMS — `twilio_sms`

Conector Ruvic para **enviar SMS transaccionales por Twilio** y **consultar el
estado de entrega** de los mensajes. Soporta dos modos de autenticación:

| Modo | Credenciales | Cuándo usarlo |
|------|--------------|---------------|
| **Auth Token** | Account SID + Auth Token | Pruebas / configuración rápida |
| **API Key** | Account SID + API Key SID + Secret | **Producción** (revocable sin rotar el token de la cuenta) |

## Instalación

```bash
pip install git+https://github.com/tu-org/conector-twilio-sms.git#subdirectory=lib
```

- Python ≥ 3.10 (probado en 3.12).
- Única dependencia: `requests>=2.31,<3.0` (no usa el SDK de Twilio; llama la
  REST API directamente).
- Requiere salida HTTPS hacia `api.twilio.com`.

## Prerrequisitos en Twilio

1. **Cuenta de Twilio** ([twilio.com/console](https://www.twilio.com/console)).
2. **Un remitente**, uno de:
   - Un **número de teléfono** habilitado para SMS (Console → Phone Numbers →
     comprar/gestionar). Va en formato E.164 (ej. `+15017122661`).
   - Un **Messaging Service SID** (Console → Messaging → Services). Recomendado
     para volumen, failover y cumplimiento; empieza por `MG`.
3. **Credenciales**, uno de:
   - **Account SID + Auth Token**: ambos en el panel principal de la consola.
   - **API Key** (recomendado): Console → Account → API keys & tokens → crear
     API key. El *Secret* se muestra **una sola vez**; guárdalo al crearlo.
4. **Verificaciones regulatorias** según el destino: verificación toll-free
   para EE. UU./Canadá, registro 10DLC, o bundle regulatorio para otros países.
   Sin esto, algunos destinos rechazan los SMS.
5. **Cuenta trial**: solo permite enviar a **números verificados** en la
   consola, y antepone un texto de prueba al mensaje. Verifica el número
   destino en Console → Phone Numbers → Verified Caller IDs.

## Variables de entorno (generadas por la plataforma)

| Variable | Modo | Descripción |
|----------|------|-------------|
| `RUVIC_TWILIO_SMS_ACCOUNT_SID` | ambos | Account SID (empieza por AC) |
| `RUVIC_TWILIO_SMS_AUTH_TOKEN` | auth_token | Auth Token (secreto) |
| `RUVIC_TWILIO_SMS_API_KEY_SID` | api_key | API Key SID (empieza por SK) |
| `RUVIC_TWILIO_SMS_API_KEY_SECRET` | api_key | API Key Secret (secreto) |
| `RUVIC_TWILIO_SMS_FROM_NUMBER` | ambos* | Número remitente en E.164 |
| `RUVIC_TWILIO_SMS_MESSAGING_SERVICE_SID` | ambos* | Messaging Service (alternativa al número) |
| `RUVIC_TWILIO_SMS_TIMEOUT` | ambos (opc.) | Timeout HTTP en segundos (default 15) |

\* Se requiere **uno** de `FROM_NUMBER` o `MESSAGING_SERVICE_SID`. Si ambos
están definidos, prevalece el Messaging Service. El modo de autenticación se
infiere de cuáles credenciales estén presentes (si hay API key, prevalece).

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_TWILIO_SMS_ACCOUNT_SID="ACxxxx"
export RUVIC_TWILIO_SMS_AUTH_TOKEN="xxxx"           # o el par API_KEY_SID/SECRET
export RUVIC_TWILIO_SMS_FROM_NUMBER="+15017122661"  # o MESSAGING_SERVICE_SID

python test_connection.py            # valida credenciales (NO envía SMS)

export TEST_TO="+573001234567"       # número verificado si es cuenta trial
python validate_local.py             # SÍ envía un SMS real (puede costar)
```

Casos de fallo a verificar:

```bash
# Auth Token inválido → FALLO: Autenticación fallida (HTTP 401)...
RUVIC_TWILIO_SMS_AUTH_TOKEN="malo" python test_connection.py

# Sin remitente → FALLO: Falta el remitente del conector twilio_sms...
env -u RUVIC_TWILIO_SMS_FROM_NUMBER -u RUVIC_TWILIO_SMS_MESSAGING_SERVICE_SID python test_connection.py

# Número destino sin '+' → TwilioSmsDataError en send_sms
```

## Limitaciones y notas de integración

- **Entrega asíncrona**: `send_sms` devuelve `queued`/`sending`, no `delivered`.
  Para confirmar la entrega hay que consultar `get_status` después (o usar un
  `StatusCallback`, que requiere un endpoint público — fuera del alcance del
  sandbox del conector).
- **Rate limits**: dependen del tipo de número (un long code envía ~1 msg/s).
  Ante HTTP 429 la librería lanza `TwilioSmsRateLimitError`.
- **Costos**: cada SMS enviado tiene costo real (salvo test credentials). El
  `validate_local.py` envía un mensaje real.
- **Cuentas trial**: solo a números verificados y con prefijo de prueba.
- **API keys vs Auth Token**: Twilio recomienda API keys en producción porque
  se pueden revocar individualmente sin rotar el Auth Token de toda la cuenta.
- **Números ofuscados en logs**: la librería enmascara los teléfonos en los
  logs (deja país + últimos 2 dígitos). Las credenciales nunca se loguean.
- El conector es de **solo salida** (envío + consulta). La recepción de SMS
  entrantes requiere un webhook con endpoint público, incompatible con el
  sandbox efímero — igual que en el conector de Telegram.
