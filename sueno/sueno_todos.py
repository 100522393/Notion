import subprocess
import time
from notion_client import Client
import constants as c

# --- INICIALIZACIÓN (Igual que antes) ---
try:
    notion = Client(auth=c.NOTION_TOKEN)
except Exception as e:
    print(f"Error: {e}")
    exit()


def buscar_sueños_sin_imagen():
    """Busca en Notion sueños pendientes de imagen."""
    # ... (Misma lógica de búsqueda que el script anterior) ...
    pages_without_images = []
    filter_query = {"property": "Tipo", "select": {"equals": "Sueño"}}
    query_response = notion.databases.query(database_id=c.JOURNAL_DATABASE_ID, filter=filter_query)

    for page in query_response["results"]:
        page_id = page["id"]
        blocks = notion.blocks.children.list(block_id=page_id)
        if not any(block["type"] == "image" for block in blocks["results"]):
            pages_without_images.append(page_id)
    return pages_without_images


# --- EJECUCIÓN CON POPEN ---
if __name__ == "__main__":
    pendientes = buscar_sueños_sin_imagen()
    print(f"Total a procesar: {len(pendientes)}\n")

    for i, page_id in enumerate(pendientes):
        print(f"[{i + 1}/{len(pendientes)}] Iniciando proceso Popen para: {page_id}")

        # Abrimos el proceso hijo
        # stdout=None permite que el hijo imprima directamente en tu terminal actual
        proceso = subprocess.Popen(
            ["python", "sueno/sueno-ai.py", page_id],
            text=True
        )

        # IMPORTANTE: .wait() bloquea el bucle hasta que 'sueno-ai.py' termine.
        # Esto garantiza que sea "uno por uno".
        codigo_retorno = proceso.wait()

        if codigo_retorno == 0:
            print(f"✔ Proceso {page_id} finalizado correctamente.")
        else:
            print(f"✘ Proceso {page_id} falló con código: {codigo_retorno}")

        time.sleep(1)

    print("\n--- Ejecución masiva terminada ---")