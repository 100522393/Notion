import google.generativeai as genai
from notion_client import Client
import json
import sys
import requests
import constants as c

notion = Client(auth=c.NOTION_TOKEN)
genai.configure(api_key=c.GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# sys.argv es una lista que contiene los argumentos de la línea de comandos.
# sys.argv[0] es el nombre del propio script (por ejemplo, 'peli-ai.py').
# sys.argv[1] es el primer argumento, que en este caso es el nombre de la peli.


def obtener_cover_libro(nombre_libro):
    """
    Obtiene la URL de la portada de un libro usando la API de Google Books.
    Busca la imagen de mayor calidad (extraLarge, large, medium, small, thumbnail).
    """

    # Construir la URL de búsqueda. Usamos intitle para mayor precisión.
    url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{nombre_libro}&maxResults=1"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Verificar si se encontraron resultados
        if data.get("totalItems", 0) > 0 and "items" in data:
            volume_info = data["items"][0].get("volumeInfo", {})
            image_links = volume_info.get("imageLinks", {})

            # Preferimos la imagen de mayor calidad disponible
            # Google Books ofrece: extraLarge, large, medium, small, thumbnail

            cover_url = image_links.get("extraLarge")
            if not cover_url:
                cover_url = image_links.get("large")
            if not cover_url:
                cover_url = image_links.get("medium")
            if not cover_url:
                cover_url = image_links.get("small")
            if not cover_url:
                cover_url = image_links.get("thumbnail")

            if cover_url:
                # La URL de la portada se devuelve
                return cover_url
            else:
                print(f"Se encontró el libro '{nombre_libro}' pero no tenía URL de portada.")
                return None
        else:
            print(f"No se encontraron resultados en Google Books para: {nombre_libro}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la portada del libro: {e}")
        return None

if len(sys.argv) > 1:
    book_name = sys.argv[1]

    # Aquí iría tu lógica, usando la variable book_name
    print(f"El nombre del libro que recibí es: {book_name}")

    # Ejemplo: Si tienes una función para procesar la peli, la llamas aquí.
    # procesar_peli(book_name)

else:
    print("Error: No se recibió ningún nombre de peli como argumento.")
    sys.exit(1)  # Finaliza el script con un código de error.


def obtener_nombre_internacional(nombre_libro):
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    prompt = f"Busca el libro {nombre_libro} y responde unicamente con su nombre internacional."
    r = model.generate_content(prompt)
    nombre_internacional = r.text
    print(nombre_internacional)
    return nombre_internacional

def obtener_datos_libro_json(nombre_libro):
    """
    Obtiene datos de una película en
     formato JSON de la API de Gemini.
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        nombre_internacional = obtener_nombre_internacional(nombre_libro)
        instruccion = (
            "Actúa como una base de datos y, dado un nombre, "
            "proporciona solo los siguientes datos de la película en formato JSON: "
            "'nombre_libro', 'fecha_estreno', 'generos', 'resumen', 'puntuacion_media', 'paginas', 'capitulos', 'autor'. Si no encuentras la película, "
            "responde con un JSON vacío: {}. El nombre de la película es: "
        )
        prompt_completo = instruccion + nombre_internacional
        respuesta = model.generate_content(prompt_completo)
        return respuesta.text
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return None


def obtener_o_crear_autor(nombre_autor):
    """
    Busca un autor por nombre y devuelve su ID. Si no existe, lo crea.
    """
    if not nombre_autor or nombre_autor == "N/A":
        return None

    try:
        # 1. Busca el autor en la base de datos
        resultados = notion.databases.query(
            database_id=c.AUTORES_DATABASE_ID,
            filter={
                "property": "Nombre",
                "title": {
                    "equals": nombre_autor
                }
            }
        )

        # 2. Si lo encuentra, devuelve su ID
        if resultados["results"]:
            print(f"Director '{nombre_autor}' encontrado.")
            return resultados["results"][0]["id"]

        # 3. Si no lo encuentra, lo crea
        else:
            print(f"Director '{nombre_autor}' no encontrado. Creando nueva página...")
            nueva_pagina = notion.pages.create(
                parent={"database_id": c.AUTORES_DATABASE_ID},
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
    Crea una página en Notion con los datos de una película.
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
            print("No se encontraron datos de la película para crear la página.")
            return

        # Obtener el ID del autor (o crearlo si no existe)
        autor_id = obtener_o_crear_autor(data.get("autor"))

        # Construir la relación si se encontró un ID
        relacion_autor = []
        if autor_id:
            relacion_autor.append({"id": autor_id})

        # Crear un mapeo de nombre_opcion -> id_opcion para un acceso rápido
        db_info = notion.databases.retrieve(database_id=c.LIBROS_DATABASE_ID)
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
            "parent": {"database_id": c.LIBROS_DATABASE_ID},
            "properties": {
                "Nombre": {
                    "title": [
                        {"text": {"content": data.get("nombre_libro", "N/A")}}
                    ]
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
                "Páginas": {
                    "number": data.get("paginas", 0)
                },
                "Capítulos": {
                    "number": data.get("capitulos", 0)
                },
                "Autor": {
                    "relation": relacion_autor  # Propiedad de relación
                }
            }
        }

        pagina_creada = notion.pages.create(**nueva_pagina)
        print(f"Página de '{data.get('nombre_libro', 'N/A')}' creada exitosamente en Notion.")
        return pagina_creada["id"]

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
    except Exception as e:
        print(f"Ocurrió un error al crear la página en Notion: {e}")

def crear_capitulos(json_data, page_id):
    try:
        # Lógica para limpiar el JSON
        start_index = json_data.find('{')
        end_index = json_data.rfind('}')
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return
        json_string = json_data[start_index: end_index + 1]
        data = json.loads(json_string)
        capitulos = data.get("capitulos", 0)

        for capitulo in range(1, capitulos + 1):
            nueva_pagina = {
                "parent": {"database_id": c.CAPITULOS_DATABASE_ID},
                "properties": {
                    "Libro": {
                        "relation": [
                            {"id": page_id}
                        ]
                    },
                    "Capítulo": {
                        "number": capitulo
                    },
                }
            }
            pagina_creada = notion.pages.create(**nueva_pagina)
    except KeyError as e:
        print(f"Key error: {e}")
    except Exception as e:
        print(f"Ocurrió un error al crear el capitulo en Notion: {e}")
    print("Cápitulos generados con exito")

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

datos_json = obtener_datos_libro_json(book_name)
print(datos_json)


if datos_json:
    page_id = crear_pagina_notion(datos_json)
    # Si la página se creó con éxito...
    if page_id:
        # Paso 3: Obtener la URL de la portada de la película
        print(f"Buscando portada para: {book_name}")
        cover_url = obtener_cover_libro(obtener_nombre_internacional(book_name))

        # Si se encontró una portada, actualiza la página
        if cover_url:
            actualizar_cover_notion(page_id, cover_url)
        else:
            print("No se pudo obtener la portada. La página fue creada sin una.")
    crear_capitulos(datos_json, page_id)