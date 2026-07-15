"""Validación local del conector twilio_sms: ejercita las capacidades.

Requiere las env vars RUVIC_TWILIO_SMS_* exportadas y un número destino de
prueba en la variable TEST_TO (en cuenta trial debe estar verificado).
ATENCIÓN: este script SÍ envía un SMS real (puede tener costo).

    export TEST_TO="+573001234567"
    python validate_local.py
"""

import os
import time

from ruvic_twilio_sms_connector import TwilioSmsClient, setup_logging

setup_logging("INFO")
client = TwilioSmsClient()
print(f"Modo: {client.config.mode}")

to = os.environ.get("TEST_TO")
if not to:
    raise SystemExit("Define TEST_TO con el número destino de prueba (E.164).")

print("== 1. Enviar SMS ==")
result = client.send_sms(to, "Prueba del conector Ruvic Twilio SMS ✅")
sid = result["sid"]
print(f"  sid={sid} status={result['status']}")

print("== 2. Consultar estado (tras 5 s) ==")
time.sleep(5)
status = client.get_status(sid)
print(f"  status={status['status']} error={status['error_code']}")

print("== 3. Listar mensajes recientes ==")
for m in client.list_messages(limit=5):
    print(f"  {m['sid']} → {m['to']}: {m['status']}")
