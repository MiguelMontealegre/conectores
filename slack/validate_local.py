"""Validación local del conector slack: ejercita las capacidades de mensajería.

Requiere la env var RUVIC_SLACK_BOT_TOKEN exportada, y RUVIC_SLACK_DEFAULT_CHANNEL
(un #canal o ID de canal donde el bot esté invitado). Para probar el DM a un
usuario, exporta también SLACK_TEST_USER_ID con un ID de usuario (U…).
"""

import os

from ruvic_slack_connector import SlackClient, setup_logging

setup_logging("INFO")
client = SlackClient()

print("== 0. Identidad del bot ==")
me = client.auth_test()
print(f"  {me['user']} (id={me['user_id']}) en {me['team']}")

print("== 1. Enviar mensaje a canal ==")
result = client.send_message("Prueba del conector Ruvic Slack ✅")
print(f"  ts={result['ts']} channel={result['channel']}")

print("== 2. Enviar mensaje directo a usuario ==")
user_id = os.environ.get("SLACK_TEST_USER_ID")
if user_id:
    dm = client.send_direct_message("Hola, esto es un DM de prueba 👋", user_id=user_id)
    print(f"  ts={dm['ts']} dm_channel={dm['channel']}")
else:
    print("  (define SLACK_TEST_USER_ID=U... para probar el DM)")

print("== 3. Información del canal por defecto ==")
if client.config.default_channel and client.config.default_channel.startswith(("C", "G")):
    info = client.get_channel_info()
    print(f"  #{info['name']} (id={info['id']}, miembro={info['is_member']})")
else:
    print("  (el destino por defecto no es un ID de canal; se omite)")

print("== 4. Listar canales ==")
for c in client.list_channels(limit=10):
    marca = "✓" if c["is_member"] else " "
    print(f"  [{marca}] #{c['name']} ({c['id']})")
