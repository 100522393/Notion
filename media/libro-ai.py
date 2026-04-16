from google import genai
from notion_client import Client
import json
import sys
import requests
import constants as c
from multimedia import actualizar_multimedia

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
    book_name = sys.argv[1]
    print(f"El nombre del libro que recibí es: {book_name}")
else:
    print("Error: No se recibió ningún nombre de libro como argumento.")
    sys.exit(1)


# ============================================================
# UTILIDADES
# ============================================================

import time
import random
import requests


def obtener_cover_libro(nombre_libro, max_retries=5):
    """
    Devuelve la URL de la portada de un libro a partir de su nombre.
    Usa Google Books y aplica reintentos con backoff exponencial
    si recibe errores transitorios o rate limiting (429).
    """
    if not nombre_libro or not str(nombre_libro).strip():
        print("Nombre de libro vacío.")
        return None

    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": f'intitle:"{nombre_libro}"',
        "maxResults": 5,
        "langRestrict": "es",
        "printType": "books",
        "fields": "items(volumeInfo(title,imageLinks)),totalItems",
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    for intento in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=20)

            if response.status_code == 429:
                espera = min(2 ** intento, 30) + random.uniform(0, 1)
                print(f"Rate limit alcanzado en Google Books. Reintentando en {espera:.1f}s...")
                time.sleep(espera)
                continue

            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                print(f"No se encontraron resultados para: {nombre_libro}")
                return None

            for item in items:
                volume_info = item.get("volumeInfo", {})
                image_links = volume_info.get("imageLinks", {})

                for key in ("extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail"):
                    cover_url = image_links.get(key)
                    if cover_url:
                        # Google a veces devuelve http; mejor forzar https si existe
                        return cover_url.replace("http://", "https://")

            print(f"Se encontraron resultados para '{nombre_libro}', pero ninguno tenía portada.")
            return None

        except requests.exceptions.RequestException as e:
            if intento < max_retries - 1:
                espera = min(2 ** intento, 30) + random.uniform(0, 1)
                print(f"Error de red al obtener la portada: {e}. Reintentando en {espera:.1f}s...")
                time.sleep(espera)
                continue

            print(f"Error al obtener la portada del libro: {e}")
            return None

    print("No se pudo obtener la portada tras varios intentos.")
    return None


def generar_texto_gemini(prompt, model="gemini-2.5-flash"):
    response = gemini_client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text.strip() if response.text else ""


def obtener_nombre_internacional(nombre_libro):
    prompt = f"Busca el libro {nombre_libro} y responde unicamente con su nombre internacional."
    nombre_internacional = generar_texto_gemini(prompt)
    print(nombre_internacional)
    return nombre_internacional


def obtener_datos_libro_json(nombre_libro):
    """
    Obtiene datos de un libro en formato JSON desde Gemini.
    """
    try:
        nombre_internacional = obtener_nombre_internacional(nombre_libro)
        instruccion = (
            "Actúa como una base de datos y, dado un nombre, "
            "proporciona solo los siguientes datos del libro en formato JSON: "
            "'nombre_libro', 'fecha_estreno', 'generos', 'resumen', "
            "'puntuacion_media', 'paginas', 'capitulos', 'autor'. "
            "Si no encuentras el libro, responde con un JSON vacío: {}. "
            "No añadas texto fuera del JSON. "
            "El nombre del libro es: "
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


def obtener_o_crear_autor(nombre_autor):
    """
    Busca un autor por nombre y devuelve su ID. Si no existe, lo crea.
    """
    if not nombre_autor or str(nombre_autor).strip().lower() in {"n/a", "null"}:
        return None

    try:
        resultados = query_data_source(
            c.AUTORES_DATABASE_ID,
            filter_payload={
                "property": "Nombre",
                "title": {
                    "equals": nombre_autor
                }
            },
            page_size=10
        )

        if resultados.get("results"):
            print(f"Autor '{nombre_autor}' encontrado.")
            return resultados["results"][0]["id"]

        print(f"Autor '{nombre_autor}' no encontrado. Creando nueva página...")
        nueva_pagina = create_page_in_data_source(
            c.AUTORES_DATABASE_ID,
            properties={
                "Nombre": {
                    "title": [
                        {"text": {"content": nombre_autor}}
                    ]
                }
            }
        )
        return nueva_pagina["id"]

    except Exception as e:
        print(f"Ocurrió un error al buscar/crear el autor: {e}")
        return None


def crear_pagina_notion(json_data):
    """
    Crea una página en Notion con los datos de un libro.
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
            print("No se encontraron datos del libro para crear la página.")
            return None

        autor_id = obtener_o_crear_autor(data.get("autor"))
        relacion_autor = [{"id": autor_id}] if autor_id else []

        ds_info = retrieve_data_source(c.LIBROS_DATABASE_ID)
        propiedades = ds_info.get("properties", {})

        if "Géneros" not in propiedades:
            raise ValueError("La propiedad 'Géneros' no existe en la tabla de libros.")

        nueva_pagina = {
            "Nombre": {
                "title": [
                    {"text": {"content": data.get("nombre_libro", "N/A")}}
                ]
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
            "Páginas": {
                "number": data.get("paginas", 0)
            },
            "Capítulos": {
                "number": data.get("capitulos", 0)
            },
            "Autor": {
                "relation": relacion_autor
            }
        }

        pagina_creada = create_page_in_data_source(
            c.LIBROS_DATABASE_ID,
            properties=nueva_pagina
        )

        print(f"Página de '{data.get('nombre_libro', 'N/A')}' creada exitosamente en Notion.")
        return pagina_creada["id"], data.get('nombre_libro', 'N/A')

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
        return None
    except Exception as e:
        print(f"Ocurrió un error al crear la página en Notion: {e}")
        return None


def crear_capitulos(json_data, page_id):
    try:
        start_index = json_data.find("{")
        end_index = json_data.rfind("}")
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return

        json_string = json_data[start_index:end_index + 1]
        data = json.loads(json_string)
        capitulos = data.get("capitulos", 0)

        if not isinstance(capitulos, int) or capitulos <= 0:
            print("No hay capítulos válidos para crear.")
            return

        for capitulo in range(1, capitulos + 1):
            nueva_pagina = {
                "Libro": {
                    "relation": [
                        {"id": page_id}
                    ]
                },
                "Capítulo": {
                    "number": capitulo
                },
            }

            create_page_in_data_source(
                c.CAPITULOS_DATABASE_ID,
                properties=nueva_pagina
            )

    except KeyError as e:
        print(f"Key error: {e}")
    except Exception as e:
        print(f"Ocurrió un error al crear el capitulo en Notion: {e}")

    print("Capítulos generados con éxito")


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

datos_json = obtener_datos_libro_json(book_name)
print(datos_json)

if datos_json:
    page_id, nombre = crear_pagina_notion(datos_json)

    if page_id:
        print(f"Buscando portada para: {book_name}")
        cover_url = obtener_cover_libro(obtener_nombre_internacional(book_name))

        if cover_url:
            actualizar_cover_notion(page_id, cover_url)
        else:
            print("No se pudo obtener la portada. La página fue creada sin una.")

        crear_capitulos(datos_json, page_id)
        actualizar_multimedia(cover_url, page_id, nombre, "Libro")