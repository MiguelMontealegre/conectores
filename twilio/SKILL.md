---
name: twilio_sms
description: >
  Usa la librería ruvic_twilio_sms_connector para enviar SMS transaccionales
  por Twilio (send_sms), consultar el estado de entrega de un mensaje
  (get_status) y listar mensajes recientes (list_messages). Úsala cuando el
  usuario pida enviar un SMS, un código de verificación / OTP, una alerta o
  notificación por mensaje de texto, o revisar si un SMS fue entregado.
triggers:
- sms
- mensaje de texto
- twilio
- enviar sms
- codigo de verificacion
- otp
- notificacion sms
- estado de entrega
---

# Conector Twilio SMS (ruvic_twilio_sms_connector)

Librería Python para enviar SMS por Twilio y consultar su estado. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-twilio-sms.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `twilio_sms` está configurado. Las variables presentes dependen del modo de autenticación:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_TWILIO_SMS_ACCOUNT_SID` | Account SID (empieza por AC) |
| `RUVIC_TWILIO_SMS_AUTH_TOKEN` | (modo Auth Token) token secreto — jamás imprimirlo |
| `RUVIC_TWILIO_SMS_API_KEY_SID` | (modo API Key) SID de la API key |
| `RUVIC_TWILIO_SMS_API_KEY_SECRET` | (modo API Key) secret — jamás imprimirlo |
| `RUVIC_TWILIO_SMS_FROM_NUMBER` | Remitente en E.164 (ej. +15017122661) |
| `RUVIC_TWILIO_SMS_MESSAGING_SERVICE_SID` | Alternativa al remitente (empieza por MG) |
| `RUVIC_TWILIO_SMS_TIMEOUT` | (opcional) timeout en segundos, default 15 |

Si no existen las credenciales, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**. El cliente detecta solo el modo y el remitente; no necesitas elegirlos en el código.

## Conexión (siempre igual)

```python
from ruvic_twilio_sms_connector import TwilioSmsClient

client = TwilioSmsClient()  # lee RUVIC_TWILIO_SMS_* del entorno automáticamente
```

## Capacidad 1 — Enviar un SMS

```python
result = client.send_sms("+573001234567", "Tu código de verificación es 4821")
print(f"SMS {result['sid']} — estado inicial: {result['status']}")
```

Notas:
- El número destino DEBE ir en formato E.164: `+` seguido del código de país (ej. `+57` Colombia, `+1` EE. UU.).
- El `status` inicial suele ser `queued` o `sending`; la entrega es asíncrona. Para saber si llegó, usa `get_status` (Capacidad 2).
- El remitente ya está configurado en el conector (número o Messaging Service); no lo pases en el código.

## Capacidad 2 — Consultar el estado de entrega

```python
status = client.get_status(result["sid"])
print(f"Estado: {status['status']}")
if status["error_code"]:
    print(f"Error {status['error_code']}: {status['error_message']}")
```

Estados de Twilio: `queued` → `sending` → `sent` → `delivered` (o `undelivered` / `failed`). Como la entrega es asíncrona, justo tras enviar el estado casi nunca es `delivered` todavía; si necesitas confirmar entrega, consulta el estado después de unos segundos.

## Capacidad 3 — Listar mensajes recientes

```python
for m in client.list_messages(limit=10):
    print(f"{m['sid']} → {m['to']}: {m['status']}")

# Con filtros:
client.list_messages(to="+573001234567", date_sent="2026-07-13", limit=20)
```

## Manejo de errores

```python
from ruvic_twilio_sms_connector import (
    TwilioSmsAuthError,
    TwilioSmsDataError,
    TwilioSmsNetworkError,
    TwilioSmsRateLimitError,
)

try:
    client.send_sms("+573001234567", "Hola")
except TwilioSmsAuthError:
    print("Credenciales inválidas — revisa la configuración del conector")
except TwilioSmsRateLimitError:
    print("Límite de peticiones de Twilio; espera y reintenta")
except TwilioSmsNetworkError:
    print("No se pudo alcanzar api.twilio.com — revisa la red")
except TwilioSmsDataError as e:
    print(f"Error de datos: {e} (código Twilio: {e.code})")
```

Códigos de error frecuentes de Twilio: `21211` (número 'to' inválido), `21608` (cuenta trial: el número no está verificado), `21610` (destinatario que se dio de baja), `21612` (no se puede enrutar al número).

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_TWILIO_SMS_*` (el constructor de `TwilioSmsClient` ya lo hace).
2. Nunca imprimas `RUVIC_TWILIO_SMS_AUTH_TOKEN` ni `RUVIC_TWILIO_SMS_API_KEY_SECRET` en logs ni en la salida.
3. Valida que el número destino esté en E.164 (empieza por `+`) antes de enviar; si el usuario da un número local, pide el código de país.
4. Al enviar códigos OTP o datos sensibles, no los repitas en logs ni en la respuesta al usuario más de lo necesario.
5. La entrega es asíncrona: no asumas que `send_sms` implica entregado. Usa `get_status` para confirmar.
6. Ante `TwilioSmsRateLimitError`, espera unos segundos (`time.sleep`) y reintenta; para envíos masivos, espacia las peticiones.
7. En cuentas trial, recuerda que solo se puede enviar a números verificados en la consola de Twilio.
