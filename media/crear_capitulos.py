import os
from notion_client import Client

# Reemplaza 'TU_TOKEN_AQUÍ' con tu token de integración
NOTION_TOKEN = "ntn_m12866236193ptit989YPuaiDuz4agnqm0wF52MOtfF02T"
notion = Client(auth=NOTION_TOKEN)

# Reemplaza este ID con el de tu tabla de 'capitulos'
CAPITULOS_DATABASE_ID = "24b04cb05183802fb87efa3729f1c7c5"


def delete_unlinked_chapters():
    """
    Busca todas las filas en la tabla 'capitulos' donde la propiedad 'Serie' está vacía
    y las elimina.
    """
    try:
        # 1. Busca las páginas donde la propiedad de relación 'Serie' está vacía
        query_results = notion.databases.query(
            database_id=CAPITULOS_DATABASE_ID,
            filter={
                "property": "Serie",
                "relation": {
                    "is_empty": True
                }
            }
        )

        # Si no se encuentran resultados, no hay nada que eliminar
        if not query_results["results"]:
            print("No se encontraron capítulos sin serie asignada.")
            return

        # 2. Recorre los resultados y elimina cada página
        pages_to_delete = query_results["results"]
        print(f"Se encontraron {len(pages_to_delete)} capítulos sin serie asignada. Iniciando la eliminación...")

        for page in pages_to_delete:
            page_id = page["id"]

            # Obtiene el título del capítulo
            # El código revisa si el título está vacío y lo reemplaza por "Sin título"
            title_property = page["properties"].get("Nombre", {}).get("title", [])
            page_title = title_property[0]["plain_text"] if title_property else "Sin título"

            # El método 'pages.update' se usa para archivar la página
            notion.pages.update(
                page_id=page_id,
                archived=True
            )
            print(f"Capítulo '{page_title}' (ID: {page_id}) eliminado.")

        print("\nProceso de limpieza completado exitosamente.")

    except Exception as e:
        print(f"Ocurrió un error: {e}")


# Llama a la función para ejecutar el programa
delete_unlinked_chapters()