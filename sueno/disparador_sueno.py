import subprocess
import constants as c
from notion_client import Client

notion = Client(auth=c.NOTION_TOKEN)


def ejecutar_procesador(page_id):
    """Llama al segundo script usando Popen."""
    print(f"🛠️ Iniciando proceso para ID: {page_id}...")

    # Iniciamos el proceso
    proceso = subprocess.Popen(
        ["python", "sueno/sueno-ai.py", page_id]
    )

    # .communicate() espera a que el proceso termine y devuelve (stdout, stderr)
    stdout, stderr = proceso.communicate()

    if proceso.returncode == 0:
        print(f"✅ Éxito:\n{stdout}")
        return True
    else:
        print(f"❌ Error en el proceso hijo:\n{stderr}")
        return False


def buscar_y_disparar():
    query = notion.databases.query(
        database_id=c.JOURNAL_DATABASE_ID,
        filter={
            "and": [
                {"property": "Tipo", "select": {"equals": "Sueño"}},
                {"property": "Disparador", "checkbox": {"equals": True}}
            ]
        }
    )

    resultados = query.get("results", [])

    for page in resultados:
        page_id = page["id"]

        # Ejecución
        if ejecutar_procesador(page_id):
            notion.pages.update(
                page_id=page_id,
                properties={"Disparador": {"checkbox": False}}
            )
            print(f"✔ Notificación: Notion actualizado para {page_id}")


if __name__ == "__main__":
    buscar_y_disparar()