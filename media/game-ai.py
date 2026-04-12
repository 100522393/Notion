from google import genai
from notion_client import Client
import json
import sys
import requests
import time
import difflib

import constants as c

# --- Inicialización de Clientes ---
notion = Client(auth=c.NOTION_TOKEN)
gemini_client = genai.Client(api_key=c.GEMINI_API_KEY)

# --- INICIO DEL SCRIPT (manejo de argumentos) ---
if len(sys.argv) > 1:
    game_name = sys.argv[1]
    print(f"El nombre del juego que recibí es: {game_name}")
else:
    print("Error: No se recibió ningún nombre de juego como argumento.")
    sys.exit(1)


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

    # 1) Intentar usarlo directamente como data source
    try:
        notion.data_sources.retrieve(data_source_id=database_or_data_source_id)
        _data_source_cache[database_or_data_source_id] = database_or_data_source_id
        return database_or_data_source_id
    except Exception:
        pass

    # 2) Si no funciona, resolverlo desde la database antigua
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


def create_page_in_data_source(database_or_data_source_id, properties):
    ds_id = resolver_data_source_id(database_or_data_source_id)
    return notion.pages.create(
        parent={"data_source_id": ds_id},
        properties=properties
    )


# ============================================================
# FUNCIONES DE AUTENTICACIÓN IGDB
# ============================================================

def _obtener_access_token(client_id, client_secret):
    """Obtiene un Access Token válido de Twitch para usar con IGDB."""
    print("Paso 1.1: Obteniendo Access Token de Twitch...")
    token_params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    try:
        response = requests.post(c.TWITCH_TOKEN_URL, params=token_params, timeout=20)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener el Token de Twitch. Verifica tus credenciales: {e}")
        return None


# ============================================================
# CARÁTULA IGDB
# ============================================================

def obtener_cover_url_igdb(nombre_juego, client_id, access_token):
    """
    Busca 50 juegos en la API de IGDB y devuelve la URL de la carátula
    del juego cuyo nombre sea el más parecido al nombre de búsqueda.
    """
    print(f"Paso 1.2: Buscando 50 opciones y seleccionando el mejor match por nombre para: '{nombre_juego}'...")

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    query_body = f"""
        search "{nombre_juego}";
        fields name, cover.url;
        limit 50;
    """

    try:
        response = requests.post(f"{c.IGDB_API_URL}/games", headers=headers, data=query_body, timeout=30)
        response.raise_for_status()
        juegos_data = response.json()

        if not juegos_data:
            print(f"❌ No se encontró ningún resultado para '{nombre_juego}'.")
            return None

        mejor_match = None
        max_similitud = -1.0

        juegos_con_caratula = [
            juego for juego in juegos_data
            if juego.get("cover", {}).get("url")
        ]

        if not juegos_con_caratula:
            print("❌ Ninguno de los resultados tenía una carátula disponible.")
            return None

        for juego in juegos_con_caratula:
            nombre_oficial = juego["name"]
            similitud = difflib.SequenceMatcher(
                None,
                nombre_juego.lower(),
                nombre_oficial.lower()
            ).ratio()

            if similitud > max_similitud:
                max_similitud = similitud
                mejor_match = juego

            if max_similitud == 1.0:
                break

        if mejor_match and max_similitud > 0.6:
            nombre_oficial = mejor_match["name"]
            caratula_url_original = mejor_match["cover"]["url"]

            print(f"✅ Juego seleccionado: **{nombre_oficial}** (Similitud: {max_similitud:.2f})")

            caratula_url = caratula_url_original.replace("t_thumb", "t_cover_big")
            if not caratula_url.startswith("http"):
                caratula_url = "https:" + caratula_url

            return caratula_url

        nombre_match = mejor_match["name"] if mejor_match else "Ninguno"
        print(f"❌ La coincidencia más cercana ({nombre_match} con {max_similitud:.2f}) no fue lo suficientemente alta.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud a IGDB: {e}")
        return None
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante la selección: {e}")
        return None


# ============================================================
# GEMINI
# ============================================================

def generar_texto_gemini(prompt, model="gemini-2.5-flash"):
    """Genera texto con el SDK nuevo de Gemini."""
    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text.strip() if response.text else ""


def obtener_nombre_internacional(nombre_juego):
    """Obtiene el nombre oficial internacional del juego para búsquedas más precisas."""
    prompt = f"Busca el videojuego {nombre_juego} y responde unicamente con su nombre internacional oficial."
    nombre_internacional = generar_texto_gemini(prompt)
    print(f"Nombre internacional: {nombre_internacional}")
    return nombre_internacional


def obtener_datos_juego_json(nombre_juego):
    """Obtiene los datos estructurados del juego desde Gemini."""
    try:
        nombre_internacional = obtener_nombre_internacional(nombre_juego)

        instruccion = (
            "Actúa como una base de datos y, dado un nombre de videojuego, "
            "proporciona solo los siguientes datos en formato JSON. "
            "Usa arrays para 'generos' y 'plataformas': "
            "'nombre_juego', 'fecha_lanzamiento' (YYYY-MM-DD), 'generos', "
            "'plataformas', 'resumen' (máximo 2 frases), "
            "'puntuacion_media' (de 0 a 10), 'duracion_horas', y 'desarrollador'. "
            "Si no encuentras el juego, responde con un JSON vacío: {}. "
            "No añadas texto fuera del JSON. "
            "El nombre del juego es: "
        )

        prompt_completo = instruccion + nombre_internacional

        for attempt in range(3):
            try:
                respuesta = gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_completo
                )
                print("Respuesta de Gemini recibida.")
                return respuesta.text
            except Exception as e:
                print(f"Error en el intento {attempt + 1} de obtener datos JSON: {e}")
                time.sleep(2 ** attempt)

        return None

    except Exception as e:
        print(f"Ocurrió un error general: {e}")
        return None


# ============================================================
# NOTION
# ============================================================

def obtener_o_crear_desarrollador(nombre_desarrollador):
    """Busca o crea una página de Desarrollador."""
    if not nombre_desarrollador or str(nombre_desarrollador).strip().lower() in {"n/a", "null"}:
        return None

    try:
        print(f"Buscando Desarrollador '{nombre_desarrollador}'...")

        resultados = query_data_source(
            c.DESARROLLADORES_DATABASE_ID,
            filter_payload={
                "property": "Nombre",
                "title": {
                    "equals": nombre_desarrollador
                }
            },
            page_size=10
        )

        if resultados.get("results"):
            print(f"Desarrollador '{nombre_desarrollador}' encontrado.")
            return resultados["results"][0]["id"]

        print(f"Desarrollador '{nombre_desarrollador}' no encontrado. Creando nueva página...")
        nueva_pagina = create_page_in_data_source(
            c.DESARROLLADORES_DATABASE_ID,
            properties={
                "Nombre": {
                    "title": [
                        {"text": {"content": nombre_desarrollador}}
                    ]
                }
            }
        )
        return nueva_pagina["id"]

    except Exception as e:
        print(f"Ocurrió un error al buscar/crear el desarrollador: {e}")
        return None


def crear_pagina_notion(json_data):
    """Crea la página en Notion con los datos del JSON."""
    page_id = None

    try:
        start_index = json_data.find("{")
        end_index = json_data.rfind("}")
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return None

        json_string = json_data[start_index:end_index + 1]
        data = json.loads(json_string)

        if not data:
            print("No se encontraron datos del juego para crear la página.")
            return None

        nombre_juego_final = data.get("nombre_juego", "Juego sin nombre")

        developer_id = obtener_o_crear_desarrollador(data.get("desarrollador"))
        relacion_developer = [{"id": developer_id}] if developer_id else []

        generos_list = [
            {"name": genero}
            for genero in data.get("generos", [])
            if genero
        ]
        plataformas_list = [
            {"name": plataforma}
            for plataforma in data.get("plataformas", [])
            if plataforma
        ]

        propiedades = {
            "Nombre": {
                "title": [
                    {"text": {"content": nombre_juego_final}}
                ]
            },
            "Lanzamiento": {
                "date": {
                    "start": data.get("fecha_lanzamiento")
                }
            },
            "Géneros": {
                "multi_select": generos_list
            },
            "Plataforma": {
                "multi_select": plataformas_list
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
                "number": data.get("duracion_horas", 0)
            },
            "Desarrollador": {
                "relation": relacion_developer
            },
        }

        pagina_creada = create_page_in_data_source(
            c.JUEGOS_DATABASE_ID,
            properties=propiedades
        )

        page_id = pagina_creada["id"]
        print(f"Página de '{nombre_juego_final}' creada exitosamente en Notion. ID: {page_id}")
        return page_id

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
        return None
    except Exception as e:
        print(f"Ocurrió un error al crear la página en Notion: {e}")
        return None


def actualizar_cover_link_notion(page_id, cover_url, property_name="Cover"):
    """
    Sube la URL de la carátula como un enlace externo a la propiedad tipo
    Files & Media de Notion.
    """
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
            }
        )

        print(f"✅ Enlace de carátula subido con éxito a la propiedad '{property_name}'.")

    except Exception as e:
        print(f"❌ Ocurrió un error al subir el enlace de carátula a Notion: {e}")


# ============================================================
# FLUJO PRINCIPAL
# ============================================================

print("\n--- PASO A: Obtener datos estructurados del juego (JSON) ---")
datos_json = obtener_datos_juego_json(game_name)
print("\nDatos JSON finales recibidos:")
print(datos_json)

page_id = None
cover_url = None

if datos_json:
    print("\n--- PASO B: Preparar la Carátula VÍA IGDB ---")

    token = _obtener_access_token(c.TWITCH_CLIENT_ID, c.TWITCH_CLIENT_SECRET)

    if token:
        cover_url = obtener_cover_url_igdb(game_name, c.TWITCH_CLIENT_ID, token)
    else:
        print("No se pudo obtener el Access Token. No se buscará la portada.")

    print("\n--- PASO C: Crear página en Notion ---")
    page_id = crear_pagina_notion(datos_json)

    if page_id and cover_url:
        print("\n--- PASO D: Subir la Carátula como Enlace Externo a la propiedad 'Cover' ---")
        actualizar_cover_link_notion(page_id, cover_url, property_name="Cover")
    elif page_id:
        print("La página fue creada, pero no se pudo adjuntar la carátula.")

print("\n--- PROCESO COMPLETADO ---")