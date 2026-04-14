from notion_client import Client
import requests
import time
import constants as c
import sys

# --- CONSTANTES ---
# Reemplaza con tus claves.
PELICULAS_DATABASE_ID = c.PELICULAS_DATABASE_ID
OMDB_API_KEY = c.OMDB_API_KEY

# Nombre de la propiedad que contendrá la URL (DEBE COINCIDIR CON NOTION)
PROPERTY_COVER_NAME = "Cover"

# Inicialización
try:
    notion = Client(auth=c.NOTION_TOKEN)
except Exception as e:
    print(f"Error al inicializar Notion: {e}")
    sys.exit(1)


# --- FUNCIONES DE UTILIDAD (MODIFICADAS/ELIMINADAS) ---

def obtener_cover_pelicula(nombre_pelicula):
    """Obtiene la URL de la portada de la película desde OMDb usando directamente el nombre."""
    # Intentamos buscar directamente con el nombre de Notion
    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={nombre_pelicula}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "True" and data.get("Poster") != "N/A":
            print(f"-> URL de portada encontrada en OMDb.")
            return data.get("Poster")
        else:
            print(f"-> No se encontró URL de portada en OMDb para: {nombre_pelicula}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"-> Error al obtener la portada de la película: {e}")
        return None


# La función obtener_nombre_internacional (con Gemini) fue eliminada.

def actualizar_propiedad_cover_notion(page_id, cover_url):
    """
    Actualiza la PROPIEDAD 'Cover' (de tipo Archivos y Multimedia).
    """
    if not page_id or not cover_url:
        print("No se puede actualizar la propiedad Cover sin un ID de página o una URL válida.")
        return
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                PROPERTY_COVER_NAME: {
                    "files": [
                        {
                            "type": "external",
                            "name": "Cover Image",
                            "external": {
                                "url": cover_url
                            }
                        }
                    ]
                }
            }
        )
        print(f"-> Propiedad '{PROPERTY_COVER_NAME}' (Files & Media) actualizada con éxito.")
    except Exception as e:
        print(f"-> Ocurrió un error al actualizar la propiedad Cover en Notion: {e}")


# --- FUNCIÓN PRINCIPAL DEL NUEVO SCRIPT ---

def actualizar_todas_las_caratulas():
    """
    Itera sobre la base de datos de películas y actualiza la propiedad 'Cover'
    usando solo el nombre de Notion (sin Gemini).
    """
    print(f"Iniciando búsqueda de portadas en la base de datos ID: {PELICULAS_DATABASE_ID}")
    next_cursor = None
    total_procesadas = 0
    total_actualizadas = 0

    while True:
        try:
            # 1. Consultar la base de datos con paginación
            results = notion.databases.query(
                database_id=PELICULAS_DATABASE_ID,
                start_cursor=next_cursor,
            )

            if not results["results"]:
                print("No hay más páginas de resultados para procesar.")
                break

            # 2. Iterar sobre los resultados
            for page in results["results"]:
                total_procesadas += 1
                page_id = page["id"]

                # Obtener el nombre de la película
                nombre_prop = page["properties"].get("Nombre")  # Asume que el título de la película es 'Nombre'
                movie_name = "Nombre Desconocido"

                if nombre_prop and nombre_prop["type"] == "title" and nombre_prop["title"]:
                    movie_name = nombre_prop["title"][0]["plain_text"]
                else:
                    print(f"[{total_procesadas}] Página ID {page_id}: No se encontró un nombre válido. Saltando.")
                    continue

                print(f"\n--- [{total_procesadas}] Procesando: {movie_name} (ID: {page_id}) ---")

                # Comprobar si la PROPIEDAD 'Cover' ya tiene un valor (archivos)
                current_property_value = page["properties"].get(PROPERTY_COVER_NAME)
                if current_property_value and current_property_value.get("files"):
                    print(f"-> La propiedad '{PROPERTY_COVER_NAME}' ya contiene un archivo. Saltando la obtención.")
                    continue

                # 3. Obtener la URL de la portada (usando directamente el nombre de Notion)
                cover_url = obtener_cover_pelicula(movie_name)  # <-- Llamada directa

                # 4. Actualizar la PROPIEDAD 'Cover' en Notion
                if cover_url:
                    actualizar_propiedad_cover_notion(page_id, cover_url)
                    total_actualizadas += 1

                # Pausa para manejar los límites de la API
                time.sleep(0.5)

                # 5. Manejar el cursor para la siguiente página
            next_cursor = results.get("next_cursor")
            if not next_cursor:
                break

        except Exception as e:
            print(f"Ocurrió un error grave durante el proceso: {e}")
            break

    print("\n=======================================================")
    print(f"RESUMEN DEL PROCESO:")
    print(f"Páginas procesadas: {total_procesadas}")
    print(f"Propiedades '{PROPERTY_COVER_NAME}' actualizadas: {total_actualizadas}")
    print("Proceso de actualización de portadas finalizado.")
    print("=======================================================")


# --- EJECUCIÓN DEL SCRIPT ---
if __name__ == "__main__":
    actualizar_todas_las_caratulas()