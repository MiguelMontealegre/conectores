"""Validación local del conector telegram: ejercita las 4 capacidades.

Requiere las env vars RUVIC_TELEGRAM_BOT_TOKEN y RUVIC_TELEGRAM_DEFAULT_CHAT_ID
exportadas, y un archivo de prueba para el envío de documentos.
"""

from pathlib import Path

from ruvic_telegram_connector import TelegramClient, setup_logging

setup_logging("INFO")
client = TelegramClient()

print("== 0. Identidad del bot ==")
me = client.get_me()
print(f"  @{me['username']} (id={me['id']})")

print("== 1. Enviar mensaje ==")
result = client.send_message("Prueba del conector Ruvic Telegram ✅")
print(f"  message_id={result['message_id']} chat_id={result['chat_id']}")

print("== 2. Enviar archivo ==")
sample = Path("/tmp/ruvic_prueba.txt")
sample.write_text("Archivo de prueba del conector Telegram.\n")
result = client.send_file(str(sample), caption="Archivo de prueba")
print(f"  {result['file_name']} → message_id={result['message_id']}")

print("== 3. Recibir actualizaciones ==")
updates = client.get_updates(limit=10)
for u in updates:
    print(f"  [{u['chat_title']}] {u['from_user']}: {u['text']}")
if not updates:
    print("  (sin actualizaciones pendientes — escribe algo al bot y reintenta)")

print("== 4. Información del chat por defecto ==")
info = client.get_chat()
print(f"  {info['type']}: {info.get('title') or info.get('username')} (id={info['id']})")
