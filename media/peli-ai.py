from google import genai
from notion_client import Client
import json
import sys
import requests

import constants as c

notion = Client(auth=c.NOTION_TOKEN)
gemini_client = genai.Client(api_key=c.GEMINI_API_KEY)

if len(sys.argv) > 1:
    movie_name = sys.argv[1]
    print(f"El nombre de la peli que recibí es: {movie_name}")
else:
    print("Error: No se recibió ningún nombre de peli como argumento.")
    sys.exit(1)


# ============================================================
# HELPERS NOTION NUEVA API
# ============================================================

_data_source_cache = {}


def resolver_data_source_id(database_or_data_source_id):
    """
    Acepta un ID que puede ser:
    - un data_source_id ya válido
    - un database_id antiguo

    Devuelve el data_source_id real para usar con notion.data_sources.query(...)
    y pages.create(parent={"data_source_id": ...})
    """
    if not database_or_data_source_id:
        raise ValueError("ID de database/data source vacío.")

    if database_or_data_source_id in _data_source_cache:
        return _data_source_cache[database_or_data_source_id]

    # 1) Intentamos tratarlo directamente como data_source_id
    try:
        notion.data_sources.retrieve(data_source_id=database_or_data_source_id)
        _data_source_cache[database_or_data_source_id] = database_or_data_source_id
        return database_or_data_source_id
    except Exception:
        pass

    # 2) Si falla, lo tratamos como database_id antiguo y sacamos su primer data source
    try:
        db_info = notion.databases.retrieve(database_id=database_or_data_source_id)
        data_sources = db_info.get("data_sources", [])

        if not data_sources:
            raise ValueError(
                f"La database {database_or_data_source_id} no tiene data_sources accesibles."
            )

        ds_id = data_sources[0]["id"]
        _data_source_cache[database_or_data_source_id] = ds_id
        return ds_id

    except Exception as e:
        raise ValueError(
            f"No se pudo resolver data_source_id desde '{database_or_data_source_id}': {e}"
        )


def query_data_source(database_or_data_source_id, filter_payload=None, start_cursor=None, page_size=100):
    ds_id = resolver_data_source_id(database_or_data_source_id)

    kwargs = {
        "data_source_id": ds_id,
        "page_size": page_size,
    }

    if filter_payload:
        kwargs["filter"] = filter_payload
    if start_cursor:
        kwargs["start_cursor"] = start_cursor

    return notion.data_sources.query(**kwargs)


def retrieve_data_source(database_or_data_source_id):
    ds_id = resolver_data_source_id(database_or_data_source_id)
    return notion.data_sources.retrieve(data_source_id=ds_id)


def create_page_in_data_source(database_or_data_source_id, properties):
    ds_id = resolver_data_source_id(database_or_data_source_id)
    return notion.pages.create(
        parent={"data_source_id": ds_id},
        properties=properties
    )


# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def obtener_cover_pelicula(nombre_pelicula):
    """Obtiene la URL de la carátula de OMDB."""
    url = f"http://www.omdbapi.com/?apikey={c.OMDB_API_KEY}&t={nombre_pelicula}"
    try:
        response = requests.get(url, timeout=20)
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


def generar_texto_gemini(prompt, model="gemini-2.5-flash"):
    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text.strip() if response.text else ""


def obtener_nombre_internacional(nombre_pelicula):
    prompt = f"Busca la película {nombre_pelicula} y responde unicamente con su nombre internacional."
    nombre_internacional = generar_texto_gemini(prompt)
    print(nombre_internacional)
    return nombre_internacional


def obtener_datos_pelicula_json(nombre_pelicula):
    try:
        nombre_internacional = obtener_nombre_internacional(nombre_pelicula)

        instruccion = (
            "Actúa como una base de datos y, dado un nombre, "
            "proporciona solo los siguientes datos de la película en formato JSON: "
            "'nombre_pelicula', 'fecha_estreno', 'generos', 'resumen', "
            "'puntuacion_media', 'duracion [min]', 'director', y 'saga'. "
            "Para el campo 'saga', usa el nombre oficial de la saga si existe; "
            "de lo contrario, usa null. "
            "Si no encuentras la película, responde con un JSON vacío: {}. "
            "No añadas texto fuera del JSON. "
            "El nombre de la película es: "
        )
        prompt_completo = instruccion + nombre_internacional

        respuesta = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_completo
        )
        return respuesta.text
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return None


def obtener_o_crear_director(nombre_director):
    """Busca o crea una página de Director en la tabla de Directores."""
    if not nombre_director or str(nombre_director).strip().lower() in {"n/a", "null"}:
        return None

    try:
        resultados = query_data_source(
            c.DIRECTORES_DATABASE_ID,
            filter_payload={
                "property": "Nombre",
                "title": {
                    "equals": nombre_director
                }
            },
            page_size=10
        )

        if resultados.get("results"):
            print(f"Director '{nombre_director}' encontrado.")
            return resultados["results"][0]["id"]

        print(f"Director '{nombre_director}' no encontrado. Creando nueva página...")
        nueva_pagina = create_page_in_data_source(
            c.DIRECTORES_DATABASE_ID,
            properties={
                "Nombre": {
                    "title": [
                        {
                            "text": {
                                "content": nombre_director
                            }
                        }
                    ]
                }
            }
        )
        return nueva_pagina["id"]

    except Exception as e:
        print(f"Ocurrió un error al buscar/crear el director: {e}")
        return None


def obtener_o_crear_saga(nombre_saga):
    """Busca o crea una página de Saga y devuelve su page_id."""
    if not nombre_saga or str(nombre_saga).strip().lower() in {"n/a", "null"}:
        return None

    try:
        print(f"Buscando Saga '{nombre_saga}'...")
        resultados = query_data_source(
            c.SAGA_DATABASE_ID,
            filter_payload={
                "property": "Nombre",
                "title": {
                    "equals": nombre_saga
                }
            },
            page_size=10
        )

        if resultados.get("results"):
            print(f"Saga '{nombre_saga}' encontrada.")
            return resultados["results"][0]["id"]

        print(f"Saga '{nombre_saga}' no encontrada. Creando nueva página...")
        nueva_pagina = create_page_in_data_source(
            c.SAGA_DATABASE_ID,
            properties={
                "Nombre": {
                    "title": [
                        {
                            "text": {
                                "content": nombre_saga
                            }
                        }
                    ]
                }
            }
        )
        return nueva_pagina["id"]

    except Exception as e:
        print(f"Ocurrió un error al buscar/crear la Saga: {e}")
        return None


def crear_pagina_notion(json_data):
    """Crea una página en la tabla de películas."""
    try:
        start_index = json_data.find("{")
        end_index = json_data.rfind("}")
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return None

        json_string = json_data[start_index:end_index + 1]
        data = json.loads(json_string)

        if not data:
            print("No se encontraron datos de la película para crear la página.")
            return None

        director_id = obtener_o_crear_director(data.get("director"))
        relacion_director = [{"id": director_id}] if director_id else []

        # Recuperamos propiedades del data source real
        ds_info = retrieve_data_source(c.PELICULAS_DATABASE_ID)

        propiedades = ds_info.get("properties", {})
        if "Géneros" not in propiedades:
            raise ValueError("La propiedad 'Géneros' no existe en la tabla de películas.")

        nueva_pagina = {
            "Nombre": {
                "title": [
                    {
                        "text": {
                            "content": data.get("nombre_pelicula", "N/A")
                        }
                    }
                ]
            },
            "Tipo": {
                "select": {
                    "name": "Película"
                }
            },
            "Lanzamiento": {
                "date": {
                    "start": data.get("fecha_estreno")
                }
            },
            "Géneros": {
                "multi_select": [
                    {"name": genero}
                    for genero in data.get("generos", [])
                    if genero
                ]
            },
            "Sinopsis": {
                "rich_text": [
                    {
                        "text": {
                            "content": data.get("resumen", "N/A")
                        }
                    }
                ]
            },
            "Puntuación": {
                "number": data.get("puntuacion_media", 0)
            },
            "Duración": {
                "number": data.get("duracion [min]", 0)
            },
            "Director": {
                "relation": relacion_director
            }
        }

        pagina_creada = create_page_in_data_source(
            c.PELICULAS_DATABASE_ID,
            properties=nueva_pagina
        )

        print(f"Página de '{data.get('nombre_pelicula', 'N/A')}' creada exitosamente en Notion.")
        return pagina_creada["id"]

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
        return None
    except Exception as e:
        print(f"Ocurrió un error al crear la página en Notion: {e}")
        return None


def actualizar_saga(saga_id, page_id):
    if not page_id or not saga_id or str(saga_id).strip().lower() in {"null", "n/a"}:
        print("No se procesa la Saga (ID de página o ID de Saga no válido).")
        return

    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "Saga": {
                    "relation": [{"id": saga_id}]
                }
            }
        )
        print(f"Relación Saga (ID: {saga_id}) añadida a la página con éxito.")

    except Exception as e:
        print(f"Ocurrió un error al actualizar la Saga en Notion: {e}")


def actualizar_cover_link_notion(page_id, cover_url, property_name="Cover"):
    if not page_id or not cover_url:
        print("No se puede actualizar la propiedad 'Cover' sin un ID de página o una URL válida.")
        return

    try:
        print(f"-> Subiendo enlace de imagen externo a la propiedad '{property_name}'...")

        file_name = cover_url.split("/")[-1].split("?")[0] or "cover.jpg"

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
            },
            cover={
                "type": "external",
                "external": {
                    "url": cover_url
                }
            }
        )

        print(f"✅ Enlace de carátula subido con éxito a la propiedad '{property_name}'.")

    except Exception as e:
        print(f"❌ Ocurrió un error al subir el enlace de carátula a Notion: {e}")


# ============================================================
# FLUJO PRINCIPAL
# ============================================================

datos_json = obtener_datos_pelicula_json(movie_name)
print(datos_json)

if datos_json:
    page_id = crear_pagina_notion(datos_json)

    if page_id:
        print(f"Buscando portada para: {movie_name}")
        nombre_internacional = obtener_nombre_internacional(movie_name)
        cover_url = obtener_cover_pelicula(nombre_internacional)

        if cover_url:
            actualizar_cover_link_notion(page_id, cover_url)
        else:
            print("No se pudo obtener la portada. La página fue creada sin una.")

    if page_id:
        try:
            json_string = datos_json[datos_json.find("{"): datos_json.rfind("}") + 1]
            data = json.loads(json_string)
            nombre_saga = data.get("saga")

            if nombre_saga and str(nombre_saga).strip().lower() not in {"null", "n/a"}:
                saga_id = obtener_o_crear_saga(nombre_saga)
                actualizar_saga(saga_id, page_id)
            else:
                print("No se encontró nombre de saga en el JSON para actualizar.")
        except Exception as e:
            print(f"Error al procesar/actualizar la saga desde el JSON: {e}")

print("\n--- PROCESO COMPLETADO ---")