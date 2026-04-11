import google.generativeai as genai
from notion_client import Client
import json
import sys
import requests

# --- IMPORTACIÓN DE CONSTANTES PROFESIONAL ---
import constants as c

# --------------------------------------------------------------------------

# --- Inicialización de Clientes (Usando c.) ---
# Usamos c.NOTION_TOKEN y c.GEMINI_API_KEY
notion = Client(auth=c.NOTION_TOKEN)
genai.configure(api_key=c.GEMINI_API_KEY)

# --- INICIO DEL SCRIPT (manejo de argumentos) ---
if len(sys.argv) > 1:
    movie_name = sys.argv[1]
    print(f"El nombre de la peli que recibí es: {movie_name}")
else:
    print("Error: No se recibió ningún nombre de peli como argumento.")
    sys.exit(1)


# --- FUNCIONES DE UTILIDAD ---

def obtener_cover_pelicula(nombre_pelicula):
    """Obtiene la URL de la carátula de OMDB."""
    # Usamos c.OMDB_API_KEY
    url = f"http://www.omdbapi.com/?apikey={c.OMDB_API_KEY}&t={nombre_pelicula}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("Response") == "True" and data.get("Poster") != "N/A":
            return data.get("Poster")
        else:
            print(f"No se encontró portada para: {nombre_pelicula}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la portada de la película: {e}")
        return None


def obtener_nombre_internacional(nombre_pelicula):
    """Obtiene el nombre internacional de la película usando Gemini."""
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    prompt = f"Busca la película {nombre_pelicula} y responde unicamente con su nombre internacional."
    r = model.generate_content(prompt)
    nombre_internacional = r.text
    print(nombre_internacional)
    return nombre_internacional


def obtener_datos_pelicula_json(nombre_pelicula):
    """Obtiene datos de una película, incluyendo el campo 'saga', de Gemini."""
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        nombre_internacional = obtener_nombre_internacional(nombre_pelicula)

        instruccion = (
            "Actúa como una base de datos y, dado un nombre, "
            "proporciona solo los siguientes datos de la película en formato JSON: "
            "'nombre_pelicula', 'fecha_estreno', 'generos', 'resumen', 'puntuacion_media', 'duracion [min]', 'director', "
            "y **'saga'**. Para el campo 'saga', usa el nombre oficial de la saga si existe; "
            "de lo contrario, usa **null**."
            "Si no encuentras la película, responde con un JSON vacío: {}. El nombre de la película es: "
        )
        prompt_completo = instruccion + nombre_internacional
        respuesta = model.generate_content(prompt_completo)
        return respuesta.text
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return None


def obtener_o_crear_director(nombre_director):
    """Busca o crea una página de Director en la BD de Directores."""
    if not nombre_director or nombre_director == "N/A": return None
    try:
        # Usamos c.DIRECTORES_DATABASE_ID
        resultados = notion.databases.query(
            database_id=c.DIRECTORES_DATABASE_ID,
            filter={"property": "Nombre", "title": {"equals": nombre_director}}
        )
        if resultados["results"]:
            print(f"Director '{nombre_director}' encontrado.")
            return resultados["results"][0]["id"]
        else:
            print(f"Director '{nombre_director}' no encontrado. Creando nueva página...")
            # Usamos c.DIRECTORES_DATABASE_ID
            nueva_pagina = notion.pages.create(
                parent={"database_id": c.DIRECTORES_DATABASE_ID},
                properties={"Nombre": {"title": [{"text": {"content": nombre_director}}]}}
            )
            return nueva_pagina["id"]
    except Exception as e:
        print(f"Ocurrió un error al buscar/crear el director: {e}")
        return None


def obtener_o_crear_saga(nombre_saga):
    """Busca o crea una página de Saga en la BD de Sagas y devuelve su ID."""
    if not nombre_saga or nombre_saga.lower() == "n/a" or nombre_saga.lower() == "null":
        return None

    try:
        # 1. Busca la Saga en la base de datos
        print(f"Buscando Saga '{nombre_saga}'...")
        # Usamos c.SAGA_DATABASE_ID
        resultados = notion.databases.query(
            database_id=c.SAGA_DATABASE_ID,
            filter={
                "property": "Nombre",
                "title": {
                    "equals": nombre_saga
                }
            }
        )

        # 2. Si la encuentra, devuelve su ID
        if resultados["results"]:
            print(f"Saga '{nombre_saga}' encontrada.")
            return resultados["results"][0]["id"]

        # 3. Si no la encuentra, la crea
        else:
            print(f"Saga '{nombre_saga}' no encontrada. Creando nueva página...")
            # Usamos c.SAGA_DATABASE_ID
            nueva_pagina = notion.pages.create(
                parent={"database_id": c.SAGA_DATABASE_ID},
                properties={"Nombre": {"title": [{"text": {"content": nombre_saga}}]}}
            )
            return nueva_pagina["id"]

    except Exception as e:
        print(f"Ocurrió un error al buscar/crear la Saga: {e}")
        return None


def crear_pagina_notion(json_data):
    """Crea una página en Notion e incluye la relación Director/Géneros."""
    try:
        # Lógica para limpiar el JSON
        start_index = json_data.find('{')
        end_index = json_data.rfind('}')
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return
        json_string = json_data[start_index: end_index + 1]
        data = json.loads(json_string)

        if not data:
            print("No se encontraron datos de la película para crear la página.")
            return

        # 1. Director
        director_id = obtener_o_crear_director(data.get("director"))
        relacion_director = [{"id": director_id}] if director_id else []

        # 2. Géneros (usando c.PELICULAS_DATABASE_ID para obtener opciones)
        db_info = notion.databases.retrieve(database_id=c.PELICULAS_DATABASE_ID)
        propiedad_multiselect_info = db_info["properties"]["Géneros"]
        opciones_map = {opcion["name"]: opcion["id"] for opcion in
                        propiedad_multiselect_info["multi_select"]["options"]}
        generos = data.get("generos", [])
        multiselect_ids = [{"id": opciones_map[opcion]} for opcion in generos if opcion in opciones_map]
        opciones_inexistentes = [opcion for opcion in generos if opcion not in opciones_map]
        for opcion_nueva in opciones_inexistentes:
            multiselect_ids.append({"name": opcion_nueva})

        nueva_pagina = {
            # Usamos c.PELICULAS_DATABASE_ID
            "parent": {"database_id": c.PELICULAS_DATABASE_ID},
            "properties": {
                "Nombre": {"title": [{"text": {"content": data.get("nombre_pelicula", "N/A")}}]},
                "Tipo": {"select": {"name": "Película"}},
                "Lanzamiento": {"date": {"start": data.get("fecha_estreno", None)}},
                "Géneros": {"multi_select": [{"name": genero} for genero in data.get("generos", [])]},
                "Sinopsis": {"rich_text": [{"text": {"content": data.get("resumen", "N/A")}}]},
                "Puntuación": {"number": data.get("puntuacion_media", 0)},
                "Duración": {"number": data.get("duracion [min]", 0)},
                "Director": {"relation": relacion_director},
                # La relación Saga se añade después con actualizar_saga si se proporciona
            }
        }

        pagina_creada = notion.pages.create(**nueva_pagina)
        print(f"Página de '{data.get('nombre_pelicula', 'N/A')}' creada exitosamente en Notion.")
        return pagina_creada["id"]

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
    except Exception as e:
        print(f"Ocurrió un error al crear la página en Notion: {e}")


def actualizar_saga(saga_id, page_id):
    """
    Actualiza la relación 'Saga' en la página de la película usando el ID de la Saga.
    """
    # 1. Validación
    if not page_id or not saga_id or str(saga_id).strip().lower() in ["null", "n/a"]:
        print("No se procesa la Saga (ID de página o ID de Saga no válido).")
        return

    try:
        # 2. Construir el objeto de relación usando el ID de la Saga
        relacion_saga = [{"id": saga_id}]

        # 3. Actualizar la página de la película en Notion
        notion.pages.update(
            page_id=page_id,
            properties={
                "Saga": {
                    "relation": relacion_saga
                }
            }
        )
        print(f"Relación Saga (ID: {saga_id}) añadida a la página con éxito.")

    except Exception as e:
        print(f"Ocurrió un error al actualizar la Saga en Notion: {e}")


def actualizar_cover_link_notion(page_id, cover_url, property_name="Cover"):
    """
    Sube la URL de la carátula como un enlace externo a la propiedad tipo
    Files & Media de Notion (Cover).
    """
    if not page_id or not cover_url:
        print("No se puede actualizar la propiedad 'Cover' sin un ID de página o una URL válida.")
        return

    try:
        print(f"-> Subiendo enlace de imagen externo a la propiedad '{property_name}'...")

        # Obtener un nombre base para el archivo (opcional, pero útil)
        file_name = cover_url.split('/')[-1].split('?')[0]

        notion.pages.update(
            page_id=page_id,
            properties={
                property_name: {
                    "files": [
                        {
                            "name": file_name,
                            "type": "external",
                            "external": {
                                "url": cover_url
                            }
                        }
                    ]
                }
            }
        )

        print(f"✅ Enlace de carátula subido con éxito a la propiedad '{property_name}'.")

    except Exception as e:
        print(f"❌ Ocurrió un error al subir el enlace de carátula a Notion: {e}")


# --- Flujo principal ---

datos_json = obtener_datos_pelicula_json(movie_name)
print(datos_json)

if datos_json:
    page_id = crear_pagina_notion(datos_json)

    if page_id:
        print(f"Buscando portada para: {movie_name}")
        cover_url = obtener_cover_pelicula(obtener_nombre_internacional(movie_name))

        if cover_url:
            actualizar_cover_link_notion(page_id, cover_url)
        else:
            print("No se pudo obtener la portada. La página fue creada sin una.")

    # La lógica para Saga se mantiene: se busca el nombre de la saga del JSON
    # y luego se actualiza la página creada.
    if page_id and datos_json:
        try:
            # Obtener el nombre de la saga del JSON de la IA (requiere re-parsear o limpiar)
            # Simplificaremos asumiendo que el JSON está limpio después de obtenerlo:
            json_string = datos_json[datos_json.find('{'): datos_json.rfind('}') + 1]
            data = json.loads(json_string)
            nombre_saga = data.get("saga")

            if nombre_saga and nombre_saga.strip().lower() not in ["null", "n/a"]:
                saga_id = obtener_o_crear_saga(nombre_saga)
                actualizar_saga(saga_id, page_id)
            else:
                print("No se encontró nombre de saga en el JSON para actualizar.")
        except Exception as e:
            print(f"Error al procesar/actualizar la saga desde el JSON: {e}")

print("\n--- PROCESO COMPLETADO ---")