# -*- coding: utf-8 -*-
from google import genai
from notion_client import Client
import json
import sys
import requests
import constants as c

# --- Inicialización de Clientes ---
notion = Client(auth=c.NOTION_TOKEN)
gemini_client = genai.Client(api_key=c.GEMINI_API_KEY)

# ============================================================
# HELPERS NOTION NUEVA API
# ============================================================

_data_source_cache = {}


def resolver_data_source_id(database_or_data_source_id):
    """
    Acepta un ID que puede ser:
    - un data_source_id real
    - un database_id antiguo

    Devuelve el data_source_id correcto para la API nueva.
    """
    if not database_or_data_source_id:
        raise ValueError("ID de database/data source vacío.")

    if database_or_data_source_id in _data_source_cache:
        return _data_source_cache[database_or_data_source_id]

    # 1) Probar si ya es un data source válido
    try:
        notion.data_sources.retrieve(data_source_id=database_or_data_source_id)
        _data_source_cache[database_or_data_source_id] = database_or_data_source_id
        return database_or_data_source_id
    except Exception:
        pass

    # 2) Si no, intentar resolverlo desde una database antigua
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
# ARGUMENTOS
# ============================================================

if len(sys.argv) > 1:
    show_name = sys.argv[1]
    print(f"El nombre de la serie que recibí es: {show_name}")
else:
    print("Error: No se recibió ningún nombre de serie como argumento.")
    sys.exit(1)


# ============================================================
# UTILIDADES
# ============================================================

def obtener_cover_serie(nombre_serie):
    """
    Obtiene la URL de la portada de una serie usando la API de OMDb.
    """
    url = f"http://www.omdbapi.com/?apikey={c.OMDB_API_KEY}&t={nombre_serie}"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "True" and data.get("Poster") != "N/A":
            return data.get("Poster")
        else:
            print(f"No se encontró portada para: {nombre_serie}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la portada de la serie: {e}")
        return None


def generar_texto_gemini(prompt, model="gemini-2.5-flash"):
    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text.strip() if response.text else ""


def obtener_nombre_internacional(nombre_serie):
    prompt = f"Busca la serie {nombre_serie} y responde unicamente con su nombre internacional."
    nombre_internacional = generar_texto_gemini(prompt)
    print(nombre_internacional)
    return nombre_internacional


def obtener_datos_serie_json(nombre_serie):
    """
    Obtiene datos de una serie en formato JSON desde Gemini.
    """
    try:
        nombre_internacional = obtener_nombre_internacional(nombre_serie)
        instruccion = (
            "Actúa como una base de datos y, dado un nombre, "
            "proporciona solo los siguientes datos de la serie en formato JSON: "
            "'nombre_serie', 'fecha_estreno', 'generos', 'resumen', "
            "'puntuacion_media', 'duracion_capitulo_min', 'numero_temporadas', 'director'. "
            "Si no encuentras la serie, responde con un JSON vacío: {}. "
            "Si hay más de un director quédate con uno. "
            "La fecha debe seguir este formato: YYYY-MM-DD. "
            "No añadas texto fuera del JSON. "
            "El nombre de la serie es: "
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
    """
    Busca un director por nombre y devuelve su ID. Si no existe, lo crea.
    """
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
                        {"text": {"content": nombre_director}}
                    ]
                }
            }
        )
        return nueva_pagina["id"]

    except Exception as e:
        print(f"Ocurrió un error al buscar/crear el director: {e}")
        return None


def crear_pagina_notion(json_data):
    """
    Crea una página en Notion con los datos de la serie.
    """
    try:
        start_index = json_data.find("{")
        end_index = json_data.rfind("}")
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return None

        json_string = json_data[start_index:end_index + 1]
        data = json.loads(json_string)

        if not data:
            print("No se encontraron datos de la serie para crear la página.")
            return None

        director_id = obtener_o_crear_director(data.get("director"))
        relacion_director = [{"id": director_id}] if director_id else []

        ds_info = retrieve_data_source(c.SERIES_DATABASE_ID)
        propiedades = ds_info.get("properties", {})

        if "Géneros" not in propiedades:
            raise ValueError("La propiedad 'Géneros' no existe en la tabla de series.")

        nueva_pagina = {
            "Nombre": {
                "title": [
                    {"text": {"content": data.get("nombre_serie", "N/A")}}
                ]
            },
            "Tipo": {
                "select": {
                    "name": "Serie"
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
                    {"text": {"content": data.get("resumen", "N/A")}}
                ]
            },
            "Puntuación": {
                "number": data.get("puntuacion_media", 0)
            },
            "Duración": {
                "number": data.get("duracion_capitulo_min", 0)
            },
            "Temporadas": {
                "number": data.get("numero_temporadas", 0)
            },
            "Director": {
                "relation": relacion_director
            }
        }

        pagina_creada = create_page_in_data_source(
            c.SERIES_DATABASE_ID,
            properties=nueva_pagina
        )

        print(f"Página de '{data.get('nombre_serie', 'N/A')}' creada exitosamente en Notion.")
        return pagina_creada["id"], data.get("nombre_serie", "N/A")

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
        return None
    except Exception as e:
        print(f"Ocurrió un error al crear la página en Notion: {e}")
        return None


def crear_capitulos(nombre_serie, page_id):
    nombre_internacional = obtener_nombre_internacional(nombre_serie)
    prompt_temporadas = (
        f"Devuelve las temporadas de esta serie [{nombre_internacional}] "
        f"con el número de capítulos por temporada en JSON con este formato: "
        f'{{"temp1": 13, "temp2": 12}}. '
        f"No añadas texto fuera del JSON."
    )

    json_data = generar_texto_gemini(prompt_temporadas)
    print(json_data)

    try:
        start_index = json_data.find("{")
        end_index = json_data.rfind("}")
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return

        json_string = json_data[start_index:end_index + 1]
        data = json.loads(json_string)

        if not data:
            print("No se encontraron datos de las temporadas para crear las páginas.")
            return

        for key, value in data.items():
            try:
                temporada = int(key.replace("temp", ""))
                episodios_count = int(value)

                for episodio in range(1, episodios_count + 1):
                    nueva_pagina = {
                        "Serie": {
                            "relation": [
                                {"id": page_id}
                            ]
                        },
                        "Temporada": {
                            "number": temporada
                        },
                        "Episodio": {
                            "number": episodio
                        },
                    }

                    create_page_in_data_source(
                        c.EPISODIOS_DATABASE_ID,
                        properties=nueva_pagina
                    )

            except ValueError as e:
                print(f"Error convirtiendo key '{key}' o value '{value}' a entero: {e}")
            except KeyError as e:
                print(f"Key error: {e}")

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
    except Exception as e:
        print(f"Ocurrió un error al crear las páginas de episodios en Notion: {e}")


def actualizar_cover_notion(page_id, cover_url):
    """
    Actualiza la portada de una página de Notion.
    """
    if not page_id or not cover_url:
        print("No se puede actualizar la portada sin un ID de página o una URL válida.")
        return

    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "Cover": {
                    "files": [
                        {
                            "name" : "cover.jpg",
                            "type": "external",
                            "external": {
                                "url": cover_url
                            }
                        }
                    ]
                }
            },
            cover = {
                "type": "external",
                "external": {
                    "url": cover_url
                }
            }
        )
        print(f"Portada de la página '{page_id}' actualizada con éxito.")
    except Exception as e:
        print(f"Ocurrió un error al actualizar la portada en Notion: {e}")


# ============================================================
# FLUJO PRINCIPAL
# ============================================================

datos_json = obtener_datos_serie_json(show_name)
print(datos_json)

def normalize_id(value: str) -> str:
    return value.strip()

def añadir_multimedia(cover_url, page_id, nombre):
    # TODO: Una vez compruebe que esto funciona lo meto a un archivo que voy a usar en pelis series y juegos como funcion
    nueva_pagina = {
        "Nombre": {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": nombre
                        }
                    }
                ]
            },
        "Serie": {
            "relation": [
                {"id": normalize_id(page_id)}
            ]
        },
        "Cover": {
            "files": [
                {
                    "name": "cover.jpg",
                    "type": "external",
                    "external": {
                        "url": cover_url
                    }
                }

            ]
        }
    }
    pagina_creada = create_page_in_data_source(
        c.MULTIMEDIA_DATABASE_ID,
        properties=nueva_pagina
    )

    print(f"Página de {nombre} creada exitosamente en Notion.")

if datos_json:
    page_id, nombre = crear_pagina_notion(datos_json)

    if page_id:
        print(f"Buscando portada para: {show_name}")
        cover_url = obtener_cover_serie(obtener_nombre_internacional(show_name))

        if cover_url:
            actualizar_cover_notion(page_id, cover_url)
        else:
            print("No se pudo obtener la portada. La página fue creada sin una.")

        crear_capitulos(show_name, page_id)
        añadir_multimedia(cover_url, page_id, nombre)