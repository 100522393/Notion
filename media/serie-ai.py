# -*- coding: utf-8 -*-
import google.generativeai as genai
from notion_client import Client
import json
import sys
import requests
import constants as c

# --- Inicialización de Clientes (Usando c.) ---
# Usamos c.NOTION_TOKEN y c.GEMINI_API_KEY
notion = Client(auth=c.NOTION_TOKEN)
genai.configure(api_key=c.GEMINI_API_KEY)

model = genai.GenerativeModel('models/gemini-2.5-flash')

# sys.argv es una lista que contiene los argumentos de la línea de comandos.

def obtener_cover_serie(nombre_serie):
    """
    Obtiene la URL de la portada de una serie usando la API de OMDb.
    """
    # Usamos c.OMDB_API_KEY
    url = f"http://www.omdbapi.com/?apikey={c.OMDB_API_KEY}&t={nombre_serie}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # OMDb devuelve 'True' si encuentra la serie y 'N/A' si no tiene póster
        if data.get("Response") == "True" and data.get("Poster") != "N/A":
            return data.get("Poster")
        else:
            print(f"No se encontró portada para: {nombre_serie}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la portada de la serie: {e}")
        return None

if len(sys.argv) > 1:
    show_name = sys.argv[1]

    # Aquí iría tu lógica, usando la variable show_name
    print(f"El nombre de la serie que recibí es: {show_name}")

    # Ejemplo: Si tienes una función para procesar la serie, la llamas aquí.
    # procesar_serie(show_name)

else:
    print("Error: No se recibió ningún nombre de serie como argumento.")
    sys.exit(1)  # Finaliza el script con un código de error.


def obtener_nombre_internacional(nombre_serie):
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    prompt = f"Busca la serie {nombre_serie} y responde unicamente con su nombre internacional."
    r = model.generate_content(prompt)
    nombre_internacional = r.text
    print(nombre_internacional)
    return nombre_internacional

def obtener_datos_serie_json(nombre_serie):
    """
    Obtiene datos de una serie en formato JSON de la API de Gemini.
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        nombre_internacional = obtener_nombre_internacional(nombre_serie)
        instruccion = (
            "Actúa como una base de datos y, dado un nombre, "
            "proporciona solo los siguientes datos de la serie en formato JSON: "
            "'nombre_serie', 'fecha_estreno', 'generos', 'resumen', 'puntuacion_media', 'duracion_capitulo_min', 'numero_temporadas', 'director'. Si no encuentras la serie, "
            "responde con un JSON vacío: {}. Si hay mas de un director quedate uno. La fecha debe seguir este formato: YYYY-MM-DD. El nombre de la serie es: "
        )
        prompt_completo = instruccion + nombre_internacional
        respuesta = model.generate_content(prompt_completo)
        return respuesta.text
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return None


def obtener_o_crear_director(nombre_director):
    """
    Busca un director por nombre y devuelve su ID. Si no existe, lo crea.
    """
    if not nombre_director or nombre_director == "N/A":
        return None

    try:
        # 1. Busca el director en la base de datos
        # Usamos c.DIRECTORES_DATABASE_ID
        resultados = notion.databases.query(
            database_id=c.DIRECTORES_DATABASE_ID,
            filter={
                "property": "Nombre",
                "title": {
                    "equals": nombre_director
                }
            }
        )

        # 2. Si lo encuentra, devuelve su ID
        if resultados["results"]:
            print(f"Director '{nombre_director}' encontrado.")
            return resultados["results"][0]["id"]

        # 3. Si no lo encuentra, lo crea
        else:
            print(f"Director '{nombre_director}' no encontrado. Creando nueva página...")
            # Usamos c.DIRECTORES_DATABASE_ID
            nueva_pagina = notion.pages.create(
                parent={"database_id": c.DIRECTORES_DATABASE_ID},
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
        # Lógica para limpiar el JSON
        start_index = json_data.find('{')
        end_index = json_data.rfind('}')
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return
        json_string = json_data[start_index: end_index + 1]
        data = json.loads(json_string)

        if not data:
            print("No se encontraron datos de la serie para crear la página.")
            return

        # Obtener el ID del director (o crearlo si no existe)
        director_id = obtener_o_crear_director(data.get("director"))

        # Construir la relación si se encontró un ID
        relacion_director = []
        if director_id:
            relacion_director.append({"id": director_id})

        # Crear un mapeo de nombre_opcion -> id_opcion para un acceso rápido
        # Usamos c.SERIES_DATABASE_ID
        db_info = notion.databases.retrieve(database_id=c.SERIES_DATABASE_ID)
        propiedad_multiselect_info = db_info["properties"]["Géneros"]
        opciones_map = {opcion["name"]: opcion["id"] for opcion in
                        propiedad_multiselect_info["multi_select"]["options"]}

        generos = data.get("generos", [])
        multiselect_ids = [{"id": opciones_map[opcion]} for opcion in generos if opcion in opciones_map]

        # Si una opción no existe, puedes decidir si la creas o la ignoras
        # Si decides crearla, tendrás que usar el 'name' en su lugar
        opciones_inexistentes = [opcion for opcion in generos if opcion not in opciones_map]
        for opcion_nueva in opciones_inexistentes:
            multiselect_ids.append({"name": opcion_nueva})

        nueva_pagina = {
            # Usamos c.SERIES_DATABASE_ID
            "parent": {"database_id": c.SERIES_DATABASE_ID},
            "properties": {
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
                    "date": {"start": data.get("fecha_estreno", None)}
                },
                "Géneros": {
                    "multi_select": [
                        {"name": genero} for genero in data.get("generos", [])
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
                    "relation": relacion_director  # Propiedad de relación
                }
            }
        }

        pagina_creada = notion.pages.create(**nueva_pagina)
        print(f"Página de '{data.get('nombre_serie', 'N/A')}' creada exitosamente en Notion.")
        return pagina_creada["id"]

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
    except Exception as e:
        print(f"Ocurrió un error al crear la página en Notion: {e}")

def crear_capitulos(nombre_serie, page_id):
    nombre_internacional = obtener_nombre_internacional(nombre_serie)
    prompt_temporadas = f"Devuelve las temporadas de esta serie [{nombre_internacional}] con en el numero de capitulos por temporada con un json en este formato: 'temp1': '13', temp2: '12'"
    temporadas = model.generate_content(prompt_temporadas)
    print(temporadas.text)
    json_data = temporadas.text
    """
        Crea entradas de episodios en la base de datos de Notion.
        """
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
            print("No se encontraron datos de las temporadas para crear las páginas.")
            return

        for key, value in data.items():
            try:
                # Extract the season number from the key (e.g., "temp1" -> 1).
                temporada = int(key.replace("temp", ""))

                # Convert the episode count to an integer.
                episodios_count = int(value)

                # Create a page for each episode in the season.
                for episodio in range(1, episodios_count + 1):
                    nueva_pagina = {
                        # Usamos c.EPISODIOS_DATABASE_ID
                        "parent": {"database_id": c.EPISODIOS_DATABASE_ID},
                        "properties": {
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
                    }
                    pagina_creada = notion.pages.create(**nueva_pagina)
            except ValueError as e:
                print(f"Error converting key '{key}' or value '{value}' to an integer: {e}")
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
            cover={
                "type": "external",
                "external": {
                    "url": cover_url
                }
            }
        )
        print(f"Portada de la página '{page_id}' actualizada con éxito.")
    except Exception as e:
        print(f"Ocurrió un error al actualizar la portada en Notion: {e}")

# --- Flujo principal ---
datos_json = obtener_datos_serie_json(show_name)
print(datos_json)


if datos_json:
    page_id = crear_pagina_notion(datos_json)
    if page_id:
        # Paso 3: Obtener la URL de la portada de la serie
        print(f"Buscando portada para: {show_name}")
        cover_url = obtener_cover_serie(obtener_nombre_internacional(show_name))

        # Si se encontró una portada, actualiza la página
        if cover_url:
            actualizar_cover_notion(page_id, cover_url)
        else:
            print("No se pudo obtener la portada. La página fue creada sin una.")
    crear_capitulos(show_name, page_id)