"""Validación local del conector gchat: ejercita las capacidades.

Requiere las env vars RUVIC_GCHAT_* exportadas (modo webhook o cuenta de
servicio). ATENCIÓN: este script SÍ publica mensajes en el espacio.
"""

from ruvic_gchat_connector import GchatClient, setup_logging

setup_logging("INFO")
client = GchatClient()
print(f"Modo detectado: {client.config.mode}")

print("== 1. Enviar mensaje ==")
result = client.send_message("Prueba del conector Ruvic Google Chat ✅")
print(f"  message_name={result['message_name']}")

print("== 1b. Mensajes en hilo ==")
client.send_message("Inicio de prueba de hilo…", thread_key="ruvic-validacion")
client.send_message("Fin de prueba de hilo ✅", thread_key="ruvic-validacion")
print("  dos mensajes agrupados con thread_key='ruvic-validacion'")

if client.config.mode == "service_account":
    print("== 2. Listar espacios ==")
    spaces = client.list_spaces()
    for s in spaces:
        print(f"  {s['name']}: {s['display_name']} ({s['type']})")
    if not spaces:
        print("  (la app no está agregada a ningún espacio todavía)")

    print("== 3. Información del espacio por defecto ==")
    if client.config.default_space:
        info = client.get_space()
        print(f"  {info['display_name']} (type={info['type']})")
    else:
        print("  (sin RUVIC_GCHAT_DEFAULT_SPACE configurado — omitido)")
else:
    print("== 2/3. list_spaces y get_space no aplican en modo webhook ==")
