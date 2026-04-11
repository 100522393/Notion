import os
from notion_client import Client

# --- 1. Configuración de Variables ---
# Valores proporcionados por el usuario
NOTION_TOKEN = "ntn_m12866236193ptit989YPuaiDuz4agnqm0wF52MOtfF02T"
DATABASE_ID = "2c704cb05183807cb1dfe98ba020cf27"

# ¡IMPORTANTE! Reemplaza estos nombres para que coincidan con tu base de datos de Notion
RELATION_PROPERTY_NAME = "Relation"  # Ej: "Artículo de Origen"
COVER_PROPERTY_NAME = "Cover"  # Propiedad de la página, no necesita cambio si quieres actualizar el banner

# --- 2. Inicialización del Cliente ---
if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError("El token de Notion o el ID de la Base de Datos no están configurados.")

notion = Client(auth=NOTION_TOKEN)


# --- 3. Funciones de Ayuda (Mismo código que antes) ---

def get_related_page_id(page_properties, relation_name):
    """
    Extrae el Page ID de la propiedad de Relación.
    """
    try:
        relation_property = page_properties.get(relation_name)
        if relation_property and relation_property['type'] == 'relation' and relation_property['relation']:
            # Solo tomamos el primer ID si hay múltiples relaciones
            return relation_property['relation'][0]['id']
        return None
    except Exception as e:
        print(f"Error al obtener el ID de la relación: {e}")
        return None


def get_cover_image_url(related_page_id):
    """
    Obtiene la URL de la imagen de la portada (Cover) de una página.
    """
    try:
        # Recuperar la página relacionada
        related_page = notion.pages.retrieve(page_id=related_page_id)

        # Verificar si la página tiene una Cover
        cover_data = related_page.get("cover")
        if cover_data:
            # La Cover puede ser 'external' (URL) o 'file' (subida a Notion)
            if cover_data['type'] == 'external':
                return cover_data['external']['url']
            elif cover_data['type'] == 'file':
                # La URL de un 'file' de Notion es temporal
                return cover_data['file']['url']
        return None
    except Exception as e:
        print(f"Error al obtener la información de la página relacionada {related_page_id}: {e}")
        return None


def update_page_cover(page_id, image_url, property_name="Cover"):
    """
    Actualiza una propiedad de la base de datos de tipo 'Files & Media' (Fichero y Multimedia)
    con una URL de imagen externa.
    """
    print(f"Intentando actualizar la propiedad '{property_name}' para la página {page_id} con URL: {image_url}")

    if not image_url:
        print(f"La URL de la imagen está vacía para la página {page_id}. No se puede actualizar.")
        return

    try:
        # La propiedad 'Files' espera una lista de objetos de archivo/medio
        payload = {
            property_name: {
                "files": [
                    {
                        "name": "Imagen de Relación",  # Puedes poner un nombre descriptivo
                        "type": "external",
                        "external": {
                            "url": image_url
                        }
                    }
                ]
            }
        }

        # Usamos el método notion.pages.update para actualizar las propiedades de la página
        notion.pages.update(
            page_id=page_id,
            properties=payload
        )
        print(f"✅ Propiedad de Fichero y Multimedia '{property_name}' de la página {page_id} actualizada con éxito.")

    except Exception as e:
        print(f"❌ Error al actualizar la propiedad de Fichero de la página {page_id}: {e}")


# NOTA: Para que esto funcione, debes asegurarte de que la imagen original
# que obtienes de la página relacionada sea 'external'. Si es 'file' (subida a Notion),
# necesitarás un paso adicional para descargarla y subirla, o usar el tipo 'file' en el payload:
#
#     "files": [
#         {
#             "type": "file",
#             "name": "Imagen Subida",
#             "file": {
#                 "url": image_url
#             }
#         }
#     ]
#
# Usaremos la lógica que ya tenías para obtener la URL.
# Si el origen es 'file' (subido a Notion), es mejor usar la versión 'file' en el payload.


# --- 4. Lógica Principal (Mismo código que antes) ---

def main():
    print(f"Iniciando el proceso para la base de datos: {DATABASE_ID}")

    start_cursor = None

    while True:
        try:
            results = notion.databases.query(
                database_id=DATABASE_ID,
                start_cursor=start_cursor,
            )
        except Exception as e:
            print(f"Error al consultar la base de datos: {e}")
            break

        for page in results['results']:
            page_id = page['id']
            page_properties = page['properties']

            # --- ⚠️ Verifica el nombre de esta propiedad aquí ⚠️ ---
            related_page_id = get_related_page_id(page_properties, RELATION_PROPERTY_NAME)

            if not related_page_id:
                # Si deseas que se detenga si la relación no es correcta, puedes quitar el 'continue'
                # y verificar tu nombre de propiedad.
                print(f"\nProcesando página con ID: {page_id}")
                print(
                    f"   - No se encontró un Page ID relacionado en la propiedad '{RELATION_PROPERTY_NAME}'. Saltando.")
                continue

            print(f"\nProcesando página con ID: {page_id}")
            print(f"   - Page ID relacionado encontrado: {related_page_id}")

            cover_image_url = get_cover_image_url(related_page_id)

            if not cover_image_url:
                print("   - La página relacionada no tiene una imagen de Cover. Saltando.")
                continue

            print(f"   - URL de Cover de la página relacionada: {cover_image_url}")

            update_page_cover(page_id, cover_image_url)

        if results['has_more']:
            start_cursor = results['next_cursor']
        else:
            print("\nFin del proceso de paginación.")
            break


if __name__ == "__main__":
    main()