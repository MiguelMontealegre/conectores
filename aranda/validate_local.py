"""Validación local del conector aranda: ejercita el flujo de descubrimiento.

Requiere RUVIC_ARANDA_TOKEN exportado (y opcionalmente RUVIC_ARANDA_BASE_URL).
Recorre catálogos y descubrimiento SIN crear casos. La creación real se deja
comentada al final porque depende de IDs válidos de tu instalación.
"""

from ruvic_aranda_connector import ArandaClient, setup_logging

setup_logging("INFO")
client = ArandaClient()


def _count(x):
    return len(x) if isinstance(x, list) else "(objeto)"


print("== 0. Catálogos globales ==")
print(f"  tipos de caso: {_count(client.get_item_types())}")
print(f"  urgencias:     {_count(client.get_urgency())}")
print(f"  impactos:      {_count(client.get_impact())}")
print(f"  tipos registro:{_count(client.get_registry_types())}")

print("== 1. Proyectos ==")
projects = client.get_projects()
print(f"  proyectos accesibles: {_count(projects)}")

# El resto del flujo depende de IDs de tu instalación. Ejemplo guiado:
#
# project_id = 1
# item_type = 1  # Incidente
# services = client.get_services(project_id, item_type)
# service_id = services[0]["id"]
# categories = client.get_categories_by_service(item_type, service_id)
# category_id = categories[0]["id"]
# model = client.get_model(item_type, category_id, service_id)
# model_id = model["id"]
# states = client.get_states(model_id, item_type)
# state_id = states[0]["id"]
# companies = client.get_companies(project_id, item_type)
# company_id = companies[0]["id"]
# customers = client.get_customers(project_id, item_type, company_id, service_id)
# customer_id = customers[0]["id"]
# fields = client.get_additional_fields(category_id, item_type, model_id, state_id)
#
# nuevo = client.create_item(
#     author_id=customer_id, category_id=category_id, company_id=company_id,
#     customer_id=customer_id, description="Caso de prueba del conector",
#     item_type=item_type, model_id=model_id, project_id=project_id,
#     service_id=service_id, state_id=state_id, subject="Prueba conector Ruvic",
# )
# print("caso creado:", nuevo.get("idByProject"), "id interno:", nuevo.get("id"))
# print(client.get_item_by_id(nuevo["id"]))

print("\nListo. Descomenta el bloque guiado con IDs reales para crear un caso.")
