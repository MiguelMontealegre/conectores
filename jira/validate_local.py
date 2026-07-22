"""Validación local del conector jira: ejercita las capacidades principales.

Requiere las env vars RUVIC_JIRA_BASE_URL, RUVIC_JIRA_EMAIL, RUVIC_JIRA_API_TOKEN
y RUVIC_JIRA_DEFAULT_PROJECT (una clave de proyecto donde la cuenta pueda crear
tickets). Crea un ticket real de prueba, lo comenta, lo transiciona y lo busca.
"""

from ruvic_jira_connector import JiraClient, setup_logging

setup_logging("INFO")
client = JiraClient()

print("== 0. Identidad de la cuenta ==")
me = client.myself()
print(f"  {me['display_name']} ({me['email']})")

print("== 1. Crear ticket ==")
issue = client.create_issue(
    summary="Prueba del conector Ruvic Jira",
    issue_type="Task",
    description="Ticket de prueba creado automáticamente.\nSe puede borrar.",
)
key = issue["key"]
print(f"  creado {key} → {issue['url']}")

print("== 2. Comentar ticket ==")
comment = client.add_comment(key, "Comentario de prueba del conector ✅")
print(f"  comentario {comment['id']} añadido")

print("== 3. Transiciones disponibles ==")
for tr in client.list_transitions(key):
    print(f"  {tr['name']} → {tr['to_status']} (id={tr['id']})")

print("== 4. Cambiar estado ==")
try:
    moved = client.transition_issue(key, "In Progress", comment="Empezando trabajo")
    print(f"  {key} ahora en estado: {moved['status']}")
except Exception as exc:  # el flujo del proyecto puede no tener ese estado
    print(f"  (no se pudo transicionar a 'In Progress': {exc})")

print("== 5. Actualizar ticket ==")
client.update_issue(key, labels=["ruvic-prueba"])
print(f"  {key} etiquetado con 'ruvic-prueba'")

print("== 6. Buscar tickets (JQL) ==")
project = client.config.default_project
results = client.search_issues(
    f'project = "{project}" ORDER BY created DESC', max_results=5
)
for r in results:
    print(f"  [{r['status']}] {r['key']}: {r['summary']}")

print("== 7. Obtener ticket ==")
detail = client.get_issue(key)
print(f"  {detail['key']} — {detail['summary']} | estado: {detail['status']} | "
      f"labels: {detail['labels']}")
