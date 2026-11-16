from notion_client import Client
from howlongtobeatpy import HowLongToBeat
import constants as c

# --- CONFIGURACIÓN ---
NOTION_TOKEN = c.NOTION_TOKEN
DATABASE_ID = c.JUEGOS_DATABASE_ID

# El nombre de la propiedad en Notion que contiene el nombre del juego
GAME_TITLE_PROPERTY = "Name"

# El nombre de la propiedad en Notion donde se guardará el tiempo de juego
HLTB_TIME_PROPERTY = "Main Story"
# --- FIN DE CONFIGURACIÓN ---


# Inicializa el cliente de Notion
notion = Client(auth=NOTION_TOKEN)


def get_games_from_notion():
    """Obtiene todos los ítems de la base de datos de Notion."""
    print("Conectando con Notion y obteniendo juegos...")
    try:
        response = notion.databases.query(
            database_id=DATABASE_ID
        )
        return response.get("results", [])
    except Exception as e:
        print(f"Error al conectar con Notion: {e}")
        return []


def update_notion_page(page_id, game_name, hltb_time):
    """Actualiza la página de Notion con el tiempo de juego."""
    print(f"  > Actualizando '{game_name}' con {hltb_time} horas.")
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                HLTB_TIME_PROPERTY: {
                    "number": hltb_time
                }
            }
        )
        print("  ✅ Actualización completada.")
    except Exception as e:
        print(f"  ❌ Error al actualizar la página de '{game_name}': {e}")


def search_hltb_and_update(games):
    """Busca en HLTB y actualiza las páginas de Notion."""
    for game in games:
        # --- CORRECCIÓN AQUÍ ---
        # Unimos todas las partes del texto para obtener el título completo
        title_parts = game['properties'][GAME_TITLE_PROPERTY]['title']
        game_title = "".join(part['plain_text'] for part in title_parts)
        # --- FIN DE LA CORRECCIÓN ---

        page_id = game['id']

        print(f"Buscando el tiempo para '{game_title}'...")

        try:
            results = HowLongToBeat().search(game_title)
        except Exception as e:
            print(f"  ❌ Error en la búsqueda de HLTB: {e}")
            continue

        if not results:
            print(f"  > No se encontraron resultados para '{game_title}'.")
            continue

        tiempo_main = results[0].main_story

        if tiempo_main is not None:
            update_notion_page(page_id, game_title, tiempo_main)
        else:
            print(f"  > No hay datos de tiempo para la historia principal de '{game_title}'.")

    print("\nProceso de actualización finalizado.")

def run_notion_update():
    """Función principal que ejecuta todo el proceso de actualización."""
    games_to_update = get_games_from_notion()
    if games_to_update:
        search_hltb_and_update(games_to_update)

if __name__ == "__main__":
    run_notion_update()
