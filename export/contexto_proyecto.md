# Proyecto: Notion

## Estructura

```text
- Notion/
  - actualizar_covers.py
  - actualizar_covers2.py
  - alarma.py
  - app.py
  - constants.py
  - .idea/
    - inspectionProfiles/
  - media/
    - crear_capitulos.py
    - game-ai.py
    - howlongtobeat.py
    - libro-ai.py
    - peli-ai.py
    - saga-ai.py
    - serie-ai.py
  - sueno/
    - disparador_sueno.py
    - sueno-ai.py
    - sueno_todos.py
```

## Archivos

### `actualizar_covers.py`

```python
from notion_client import Client
import requests
import time
import sys

# --- CONSTANTES ---
# Reemplaza con tus claves.
NOTION_TOKEN = "ntn_m12866236193ptit989YPuaiDuz4agnqm0wF52MOtfF02T"
PELICULAS_DATABASE_ID = "24b04cb051838016803bd575af7c3f88"
OMDB_API_KEY = "826779cd"

# Nombre de la propiedad que contendrá la URL (DEBE COINCIDIR CON NOTION)
PROPERTY_COVER_NAME = "Cover"

# Inicialización
try:
    notion = Client(auth=NOTION_TOKEN)
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
```

### `actualizar_covers2.py`

```python
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
```

### `alarma.py`

```python
import smtplib
from email.message import EmailMessage


def enviar_alarma_icloud(hora):
    # --- CONFIGURACIÓN ---
    tu_correo_icloud = "nesbe717@icloud.com"  # Tu dirección real
    password_aplicacion = "rnqf-pvpa-zutr-hnrz"  # La clave de 16 letras de Apple

    # Creamos el mensaje
    msg = EmailMessage()
    msg.set_content(f"Activando alarma para las {hora}")
    msg['Subject'] = f"ALARM:{hora}"  # El "trigger" para el iPhone
    msg['From'] = tu_correo_icloud
    msg['To'] = tu_correo_icloud  # Te lo envías a ti mismo

    try:
        # Configuración del servidor de Apple
        # iCloud usa el puerto 587 con STARTTLS
        server = smtplib.SMTP('smtp.mail.me.com', 587)
        server.starttls()  # Cifrado de seguridad obligatorio para Apple
        server.login(tu_correo_icloud, password_aplicacion)
        server.send_message(msg)
        server.quit()
        print(f"🚀 Email enviado a iCloud. Alarma programada: {hora}")
    except Exception as e:
        print(f"❌ Error al enviar: {e}")
```

### `app.py`

```python
import sys
import subprocess
import re
from flask import Flask, request, Response
from pathlib import Path
import os  # Importar os para manejo robusto de paths

from alarma import *
app = Flask(__name__)

# =============================================================
# 1. CONSTANTES DE COLOR (CENTRALIZADAS)
# =============================================================

# Definición de colores neón por tipo de contenido
COLORES = {
    "pelicula": "#DC143C",  # Crimson (Rojo)
    "serie": "#007BFF",  # Blue (Azul)
    "saga": "#FFC300",  # Amber (Ámbar)
    "libro": "#FF00FF",  # Magenta (Rosa/Fucsia)
    "game": "#7CFC00",  # Lawn Green (Verde Brillante)
    "alarma": "#FFFF33",
}


# =============================================================
# 2. FUNCIONES DE PLANTILLA (MODIFICADAS)
# =============================================================

def generar_formulario_html(titulo, action_url, input_name, button_color):
    """Genera el HTML del formulario de entrada con estilos neón dinámicos."""
    # El código de esta función no necesita cambios, solo usa el button_color pasado.
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{titulo}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"> 
        <style>
            :root {{
                --neon-color: {button_color}; /* Variable CSS para el color */
                --neon-glow: 0 0 5px var(--neon-color), 
                             0 0 15px var(--neon-color), 
                             0 0 25px var(--neon-color), 
                             0 0 40px {button_color}AA; 
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #121212; 
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh; 
                margin: 0;
            }}
            .container {{
                background-color: #1e1e1e; 
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
                text-align: center;
                width: 350px; 
            }}
            h1 {{
                color: #f0f0f0; 
                margin-bottom: 25px;
                font-size: 1.8em;
            }}
            label {{
                display: block;
                text-align: left;
                margin-bottom: 8px;
                font-weight: bold;
                color: #aaa;
            }}
            input[type="text"] {{
                width: 100%;
                padding: 12px;
                margin-bottom: 25px;
                border: 2px solid #555;
                border-radius: 5px;
                box-sizing: border-box;
                font-size: 1em;
                background-color: #333;
                color: #fff;
            }}
            input[type="submit"] {{
                background-color: #1e1e1e;
                color: white;
                padding: 12px 20px;
                border: 2px solid var(--neon-color); 
                border-radius: 8px;
                cursor: pointer;
                font-size: 1.1em;
                width: 100%;
                font-weight: bold;
                letter-spacing: 1px;
                transition: all 0.4s ease-in-out;
                box-shadow: 0 0 5px var(--neon-color); 
            }}
            input[type="submit"]:hover,
            input[type="submit"]:focus {{
                color: black; 
                background-color: var(--neon-color); 
                text-shadow: none;
                box-shadow: var(--neon-glow);
                transform: scale(1.03); 
            }}
            @media (max-width: 600px) {{
                body {{
                    padding: 0 10px; 
                    height: 100vh; 
                }}
                .container {{
                    width: 95%; 
                    padding: 20px 15px; 
                    border-radius: 8px; 
                    box-shadow: none; 
                }}
                h1 {{
                    font-size: 1.5em; 
                }}
                input[type="submit"] {{
                    padding: 10px 15px;
                    font-size: 1em;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{titulo}</h1>
            <form action="{action_url}" method="post">
                <label for="{input_name}">Nombre del contenido:</label>
                <input type="text" id="{input_name}" name="{input_name}" required>
                <input type="submit" value="Ejecutar Script">
            </form>
        </div>
    </body>
    </html>
    """


def generar_respuesta_exito(nombre_contenido, success_color):
    """Genera la respuesta con el mensaje de éxito usando un color dinámico."""

    # Adaptamos la variable CSS para usar el color de la ruta
    neon_glow_style = (
        f"0 0 5px {success_color}, "
        f"0 0 15px {success_color}, "
        f"0 0 25px {success_color}, "
        f"0 0 40px {success_color}AA"
    )

    return f"""
    <html>
        <head>
            <title>Proceso Iniciado</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0"> 
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    background-color: #121212; 
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    text-align: center; 
                }}
                .container {{
                    background-color: #1e1e1e; 
                    padding: 40px 30px;
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
                    width: 350px;
                    max-width: 90%; 
                    /* Aplicar un resplandor al contenedor basado en el color */
                    border: 1px solid {success_color}33; 
                    box-shadow: {neon_glow_style};
                }}
                h1 {{ 
                    color: {success_color}; /* Color dinámico para el título */ 
                    font-size: 1.8em;
                    margin-bottom: 20px;
                    text-shadow: 0 0 10px {success_color}88; /* Sombra sutil neón */
                }}
                p {{
                    color: #aaa; 
                    font-size: 1.1em;
                }}

                /* ESTILOS PARA MÓVIL (Media Query) */
                @media (max-width: 600px) {{
                    body {{
                        height: 100vh;
                        padding: 0 10px;
                    }}
                    .container {{
                        width: 95%;
                        padding: 30px 20px;
                        box-shadow: none; /* Quitamos el box-shadow grande en móvil */
                    }}
                    h1 {{
                        font-size: 1.5em; 
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Proceso iniciado</h1>
                <p>El script se está ejecutando en segundo plano para: <br><strong>{nombre_contenido}</strong></p>
                <p>Esta pestaña permanecerá abierta.</p>
            </div>
        </body>
    </html>
    """

# =============================================================
# 3. DEFINICIÓN DE CONSTANTES Y RUTAS (EJECUCIÓN)
# =============================================================

BASE_DIR = Path(__file__).resolve().parent
SCRIPT_PATH_HLTB = BASE_DIR / "media/howlongtobeat.py"
SCRIPT_PATH_PELICULA = BASE_DIR / "media/peli-ai.py"
SCRIPT_PATH_SERIE = BASE_DIR / "media/serie-ai.py"
SCRIPT_PATH_SAGA = BASE_DIR / "media/saga-ai.py"
SCRIPT_PATH_LIBRO = BASE_DIR / "media/libro-ai.py"
SCRIPT_PATH_GAME = BASE_DIR / "media/game-ai.py"
SCRIPT_PATH_SUEÑOS = BASE_DIR / "sueno/sueno_todos.py"
SCRIPT_PATH_DISPARADOR_SUENO = BASE_DIR / "sueno/disparador_sueno.py"

# Configuración global de entorno para que todos los hijos vean la raíz
env_config = os.environ.copy()
env_config["PYTHONPATH"] = str(BASE_DIR)
env_config["PYTHONUTF8"] = "1"
env_config["PYTHONIOENCODING"] = "utf-8"

PYTHON_W_EXECUTABLE = sys.executable
if sys.platform == "win32":
    potential_pythonw = str(sys.executable).replace("python.exe", "pythonw.exe")
    if os.path.exists(potential_pythonw):
        PYTHON_W_EXECUTABLE = potential_pythonw


# -------------------------
# RUTA /howlongtobeat (Actualizada con env)
# -------------------------
@app.route('/howlongtobeat')
def update_notion():
    try:
        subprocess.Popen(
            [PYTHON_W_EXECUTABLE, str(SCRIPT_PATH_HLTB)],
            cwd=str(BASE_DIR),
            env=env_config
        )
    except Exception as e:
        print(f"Error al lanzar el script: {e}")
        return "Error al iniciar el proceso.", 500

    return Response("""
    <html><head><script>window.onload = function() { window.close(); }</script></head>
    <body style="background:#000;"></body></html>
    """)


# -------------------------
# RUTA /pelicula (Actualizada con env)
# -------------------------
@app.route('/pelicula', methods=['GET', 'POST'])
def handle_pelicula_route():
    COLOR = COLORES["pelicula"]
    if request.method == 'POST':
        movie_name = request.form.get('movie_name')
        try:
            subprocess.Popen(
                [PYTHON_W_EXECUTABLE, str(SCRIPT_PATH_PELICULA), movie_name],
                cwd=str(BASE_DIR),
                env=env_config
            )
        except Exception as e:
            return f"Error: {e}", 500
        return generar_respuesta_exito(f"Peli: {movie_name}", success_color=COLOR)
    return generar_formulario_html("Introduce la peli", "/pelicula", "movie_name", COLOR)


# -------------------------
# RUTA /serie (Actualizada con env)
# -------------------------
@app.route('/serie', methods=['GET', 'POST'])
def handle_serie_route():
    COLOR = COLORES["serie"]
    if request.method == 'POST':
        show_name = request.form.get('show_name')
        try:
            subprocess.Popen(
                [PYTHON_W_EXECUTABLE, str(SCRIPT_PATH_SERIE), show_name],
                cwd=str(BASE_DIR),
                env=env_config
            )
        except Exception as e:
            return f"Error: {e}", 500
        return generar_respuesta_exito(f"Serie: {show_name}", success_color=COLOR)
    return generar_formulario_html("Introduce la serie", "/serie", "show_name", COLOR)


# -------------------------
# RUTA /saga (Actualizada con env)
# -------------------------
@app.route('/saga', methods=['GET', 'POST'])
def handle_saga_route():
    COLOR = COLORES["saga"]
    if request.method == 'POST':
        saga_name = request.form.get('saga_name')
        try:
            subprocess.Popen(
                [PYTHON_W_EXECUTABLE, str(SCRIPT_PATH_SAGA), saga_name],
                cwd=str(BASE_DIR),
                env=env_config
            )
        except Exception as e:
            return f"Error: {e}", 500
        return generar_respuesta_exito(f"Saga: {saga_name}", success_color=COLOR)
    return generar_formulario_html("Introduce la saga", "/saga", "saga_name", COLOR)


# -------------------------
# RUTA /book (Actualizada con env)
# -------------------------
@app.route('/book', methods=['GET', 'POST'])
def handle_book_route():
    COLOR = COLORES["libro"]
    if request.method == 'POST':
        book_name = request.form.get('book_name')
        try:
            subprocess.Popen(
                [PYTHON_W_EXECUTABLE, str(SCRIPT_PATH_LIBRO), book_name],
                cwd=str(BASE_DIR),
                env=env_config
            )
        except Exception as e:
            return f"Error: {e}", 500
        return generar_respuesta_exito(f"Libro: {book_name}", success_color=COLOR)
    return generar_formulario_html("Introduce el libro", "/book", "book_name", COLOR)


# -------------------------
# RUTA /game (Actualizada con env)
# -------------------------
@app.route('/game', methods=['GET', 'POST'])
def handle_game_route():
    COLOR = COLORES["game"]
    if request.method == 'POST':
        game_name = request.form.get('game_name')
        try:
            subprocess.Popen(
                [PYTHON_W_EXECUTABLE, str(SCRIPT_PATH_GAME), game_name],
                cwd=str(BASE_DIR),
                env=env_config
            )
        except Exception as e:
            return f"Error: {e}", 500
        return generar_respuesta_exito(f"Videojuego: {game_name}", success_color=COLOR)
    return generar_formulario_html("Introduce el videojuego", "/game", "game_name", COLOR)


# -------------------------
# RUTA /sueno_todos (Consolidado con env_config)
# -------------------------
@app.route('/sueno_todos')
def handle_sueno_trigger():
    try:
        subprocess.Popen(
            [sys.executable, str(SCRIPT_PATH_SUEÑOS.absolute())],
            cwd=str(BASE_DIR),
            env=env_config
        )
        return Response(
            """<html><head><script>window.close();</script></head><body style="background:transparent;"></body></html>""")
    except Exception as e:
        return f"Error: {e}", 500


# -------------------------
# RUTA /sueno (Consolidado con env_config)
# -------------------------
@app.route('/sueno')
def handle_sueno_checkbox():
    try:
        subprocess.Popen(
            [sys.executable, str(SCRIPT_PATH_DISPARADOR_SUENO)],
            cwd=str(BASE_DIR),
            env=env_config,
        )
        return Response(
            """<html><head><script>window.close();</script></head><body style="background:transparent;"></body></html>""")
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/alarma', methods=['GET', 'POST'])
def handle_alarma_route():
    COLOR = COLORES["alarma"]
    valido = False
    if request.method == 'POST':
        alarma = request.form.get('alarma')
        try:
            patron = r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
            if re.match(patron, alarma):
                enviar_alarma_icloud(alarma)
                valido = True

        except Exception as e:
            return f"Error: {e}", 500
        if valido:
            return generar_respuesta_exito(f"ALARMA: {alarma}", success_color=COLOR)
        else:
            return generar_respuesta_exito((f"⚠️ Formato de hora incorrecto.\n\n"), success_color=COLOR)
    return generar_formulario_html("Introduce la alarma", "/alarma", "alarma", COLOR)

if __name__ == '__main__':
    app.run(debug=True)
```

### `constants.py`

```python
# ====================================================
# I. SERVICIOS DE AUTENTICACIÓN Y CLAVES DE API
# ====================================================

# Google Gemini (Inteligencia Artificial)
GEMINI_API_KEY = "AIzaSyCBg_Tf6tBJPhCdJR5Pv8Pa6paOPp2XVSw"

# Notion (Token de Acceso)
NOTION_TOKEN = "ntn_m12866236193ptit989YPuaiDuz4agnqm0wF52MOtfF02T"

# Twitch / IGDB (Gaming Services)
TWITCH_CLIENT_ID = 'qmcgq4tbi7dwauxcbrix0442nedcop'
TWITCH_CLIENT_SECRET = 'e5xmnkw2eszm1eymgetvm1hu6hxhoe'
TWITCH_TOKEN_URL = 'https://id.twitch.tv/oauth2/token'
IGDB_API_URL = 'https://api.igdb.com/v4'

# OMDB (The Open Movie Database - Cine/TV)
OMDB_API_KEY = "826779cd"


# ====================================================
# II. NOTION: BASES DE DATOS (DATABASE IDs)
# ====================================================

# --- Medios de Lectura (Libros) ---
LIBROS_DATABASE_ID = "24c04cb051838072800ccaa866b213a2"
AUTORES_DATABASE_ID = "2aa04cb0518380aa926cfe8f85ae7963"
CAPITULOS_DATABASE_ID = "24c04cb0518380489fd3d67cdbe0bac0"

# --- Medios Visuales (Películas, Series, etc.) ---
PELICULAS_DATABASE_ID = "24b04cb051838016803bd575af7c3f88"
SERIES_DATABASE_ID = "24b04cb051838016803bd575af7c3f88" # Misma ID que Películas
DIRECTORES_DATABASE_ID = "25304cb0518380c9a8a1f72b326dcc6a"
SAGA_DATABASE_ID = "25304cb051838040b3b2cee9c7d6245a"
EPISODIOS_DATABASE_ID = "24b04cb05183802fb87efa3729f1c7c5"
JOURNAL_DATABASE_ID = "28c04cb05183802f87bde9ae58bcca8c"

# --- Videojuegos ---
JUEGOS_DATABASE_ID = "24404cb0518381b4b31ad44e54791150"
DESARROLLADORES_DATABASE_ID = "2b004cb05183803b9776c7cf50683616"
```

### `media\crear_capitulos.py`

```python
import os
from notion_client import Client

# Reemplaza 'TU_TOKEN_AQUÍ' con tu token de integración
NOTION_TOKEN = "ntn_m12866236193ptit989YPuaiDuz4agnqm0wF52MOtfF02T"
notion = Client(auth=NOTION_TOKEN)

# Reemplaza este ID con el de tu tabla de 'capitulos'
CAPITULOS_DATABASE_ID = "24b04cb05183802fb87efa3729f1c7c5"


def delete_unlinked_chapters():
    """
    Busca todas las filas en la tabla 'capitulos' donde la propiedad 'Serie' está vacía
    y las elimina.
    """
    try:
        # 1. Busca las páginas donde la propiedad de relación 'Serie' está vacía
        query_results = notion.databases.query(
            database_id=CAPITULOS_DATABASE_ID,
            filter={
                "property": "Serie",
                "relation": {
                    "is_empty": True
                }
            }
        )

        # Si no se encuentran resultados, no hay nada que eliminar
        if not query_results["results"]:
            print("No se encontraron capítulos sin serie asignada.")
            return

        # 2. Recorre los resultados y elimina cada página
        pages_to_delete = query_results["results"]
        print(f"Se encontraron {len(pages_to_delete)} capítulos sin serie asignada. Iniciando la eliminación...")

        for page in pages_to_delete:
            page_id = page["id"]

            # Obtiene el título del capítulo
            # El código revisa si el título está vacío y lo reemplaza por "Sin título"
            title_property = page["properties"].get("Nombre", {}).get("title", [])
            page_title = title_property[0]["plain_text"] if title_property else "Sin título"

            # El método 'pages.update' se usa para archivar la página
            notion.pages.update(
                page_id=page_id,
                archived=True
            )
            print(f"Capítulo '{page_title}' (ID: {page_id}) eliminado.")

        print("\nProceso de limpieza completado exitosamente.")

    except Exception as e:
        print(f"Ocurrió un error: {e}")


# Llama a la función para ejecutar el programa
delete_unlinked_chapters()
```

### `media\game-ai.py`

```python
import google.generativeai as genai
from notion_client import Client
import json
import sys
import requests
import time
import os
import difflib  # <-- NECESARIO PARA COMPARAR NOMBRES

# --- IMPORTACIÓN DE CONSTANTES PROFESIONAL ---
import constants as c # <--- ¡Aquí está el cambio clave!
# --------------------------------------------------------------------------

# --- Inicialización de Clientes (Usando c.) ---
# Usamos c.NOTION_TOKEN y c.GEMINI_API_KEY
notion = Client(auth=c.NOTION_TOKEN)
genai.configure(api_key=c.GEMINI_API_KEY)

# --- INICIO DEL SCRIPT (manejo de argumentos) ---
if len(sys.argv) > 1:
    game_name = sys.argv[1]
    print(f"El nombre del juego que recibí es: {game_name}")
else:
    print("Error: No se recibió ningún nombre de juego como argumento.")
    sys.exit(1)


# --- FUNCIONES DE AUTENTICACIÓN IGDB ---

def _obtener_access_token(client_id, client_secret):
    """Obtiene un Access Token válido de Twitch para usar con IGDB."""
    print("Paso 1.1: Obteniendo Access Token de Twitch...")
    token_params = {
        'client_id': client_id,
        'client_secret': client_secret,
        # Usamos c.TWITCH_TOKEN_URL
        'grant_type': 'client_credentials'
    }
    try:
        response = requests.post(c.TWITCH_TOKEN_URL, params=token_params) # c.TWITCH_TOKEN_URL
        response.raise_for_status()
        token_data = response.json()
        return token_data.get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener el Token de Twitch. Verifica tus credenciales: {e}")
        return None


# --- FUNCIÓN PRINCIPAL DE CARÁTULA IGDB (MODIFICADA CON SIMILITUD) ---

def obtener_cover_url_igdb(nombre_juego, client_id, access_token):
    """
    Busca 50 juegos en la API de IGDB y devuelve la URL de la carátula
    del juego cuyo nombre sea el más parecido al nombre de búsqueda.
    """
    print(f"Paso 1.2: Buscando 50 opciones y seleccionando el mejor match por nombre para: '{nombre_juego}'...")

    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    # 🎯 CONSULTA AQL: Aumentamos el límite a 50 para tener más opciones para comparar
    query_body = f"""
        search "{nombre_juego}";
        fields name, cover.url;
        limit 50;
    """

    try:
        # Usamos c.IGDB_API_URL
        response = requests.post(f'{c.IGDB_API_URL}/games', headers=headers, data=query_body)
        response.raise_for_status()
        juegos_data = response.json()

        if not juegos_data:
            print(f"❌ No se encontró ningún resultado para '{nombre_juego}'.")
            return None

        # --- Lógica de Similitud de Nombres en Python ---

        mejor_match = None
        max_similitud = -1.0

        # Solo consideramos juegos que tienen una carátula (cover.url)
        juegos_con_caratula = [juego for juego in juegos_data if juego.get('cover', {}).get('url')]

        if not juegos_con_caratula:
            print("❌ Ninguno de los resultados tenía una carátula disponible.")
            return None

        for juego in juegos_con_caratula:
            nombre_oficial = juego['name']

            # 1. Calculamos la similitud de la cadena (ratio de 0.0 a 1.0)
            similitud = difflib.SequenceMatcher(None, nombre_juego.lower(), nombre_oficial.lower()).ratio()

            # 2. Seleccionamos el juego con la puntuación más alta
            if similitud > max_similitud:
                max_similitud = similitud
                mejor_match = juego

            # Si encontramos una similitud perfecta (1.0), terminamos inmediatamente
            if max_similitud == 1.0:
                break

        # Si encontramos un match con buena similitud
        if mejor_match and max_similitud > 0.6:  # Un umbral razonable para evitar basura

            nombre_oficial = mejor_match['name']
            caratula_url_original = mejor_match['cover']['url']

            print(f"✅ Juego seleccionado: **{nombre_oficial}** (Similitud: {max_similitud:.2f})")

            # Procesamiento de la URL para obtener la versión grande
            caratula_url = caratula_url_original.replace('t_thumb', 't_cover_big')
            if not caratula_url.startswith('http'):
                caratula_url = 'https:' + caratula_url

            return caratula_url
        else:
            print(
                f"❌ La coincidencia más cercana ({mejor_match['name']} con {max_similitud:.2f}) no fue lo suficientemente alta.")
            return None


    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud a IGDB: {e}")
        return None
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante la selección: {e}")
        return None


def obtener_nombre_internacional(nombre_juego):
    """Obtiene el nombre oficial internacional del juego para búsquedas más precisas."""
    # El modelo ya está configurado con c.GEMINI_API_KEY
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    prompt = f"Busca el videojuego {nombre_juego} y responde unicamente con su nombre internacional oficial."
    r = model.generate_content(prompt)
    nombre_internacional = r.text.strip()
    print(f"Nombre internacional: {nombre_internacional}")
    return nombre_internacional


def obtener_datos_juego_json(nombre_juego):
    """Obtiene los datos estructurados del juego desde Gemini."""
    try:
        # El modelo ya está configurado con c.GEMINI_API_KEY
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        nombre_internacional = obtener_nombre_internacional(nombre_juego)

        instruccion = (
            "Actúa como una base de datos y, dado un nombre de videojuego, "
            "proporciona solo los siguientes datos en formato JSON. Usa arrays para 'generos' y 'plataformas': "
            "'nombre_juego', 'fecha_lanzamiento' (YYYY-MM-DD), 'generos', 'plataformas', 'resumen' (máximo 2 frases), "
            "'puntuacion_media' (de 0 a 10), 'duracion_horas', y 'desarrollador'. "
            "Si no encuentras el juego, responde con un JSON vacío: {}."
            "El nombre del juego es: "
        )
        prompt_completo = instruccion + nombre_internacional

        for attempt in range(3):
            try:
                respuesta = model.generate_content(prompt_completo)
                print("Respuesta de Gemini recibida.")
                return respuesta.text
            except Exception as e:
                print(f"Error en el intento {attempt + 1} de obtener datos JSON: {e}")
                time.sleep(2 ** attempt)

        return None

    except Exception as e:
        print(f"Ocurrió un error general: {e}")
        return None


def obtener_o_crear_desarrollador(nombre_desarrollador):
    """Busca o crea una página de Desarrollador en la BD de Desarrolladores."""
    if not nombre_desarrollador or nombre_desarrollador.lower() in ["n/a", "null"]: return None
    try:
        print(f"Buscando Desarrollador '{nombre_desarrollador}'...")
        # Usamos c.DESARROLLADORES_DATABASE_ID
        resultados = notion.databases.query(
            database_id=c.DESARROLLADORES_DATABASE_ID,
            filter={"property": "Nombre", "title": {"equals": nombre_desarrollador}}
        )
        if resultados["results"]:
            print(f"Desarrollador '{nombre_desarrollador}' encontrado.")
            return resultados["results"][0]["id"]
        else:
            print(f"Desarrollador '{nombre_desarrollador}' no encontrado. Creando nueva página...")
            # Usamos c.DESARROLLADORES_DATABASE_ID
            nueva_pagina = notion.pages.create(
                parent={"database_id": c.DESARROLLADORES_DATABASE_ID},
                properties={"Nombre": {"title": [{"text": {"content": nombre_desarrollador}}]}}
            )
            return nueva_pagina["id"]
    except Exception as e:
        print(f"Ocurrió un error al buscar/crear el desarrollador: {e}")
        return None


def crear_pagina_notion(json_data):
    """Crea la página en Notion con los datos del JSON."""
    page_id = None
    try:
        start_index = json_data.find('{')
        end_index = json_data.rfind('}')
        if start_index == -1 or end_index == -1:
            print("No se pudo encontrar un JSON válido en la respuesta de la IA.")
            return
        json_string = json_data[start_index: end_index + 1]
        data = json.loads(json_string)

        if not data:
            print("No se encontraron datos del juego para crear la página.")
            return

        game_name = data.get("nombre_juego", "Juego sin nombre")

        developer_id = obtener_o_crear_desarrollador(data.get("desarrollador"))
        relacion_developer = [{"id": developer_id}] if developer_id else []

        generos_list = [{"name": g} for g in data.get("generos", [])]
        plataformas_list = [{"name": p} for p in data.get("plataformas", [])]

        nueva_pagina = {
            # Usamos c.JUEGOS_DATABASE_ID
            "parent": {"database_id": c.JUEGOS_DATABASE_ID},
            "properties": {
                "Nombre": {"title": [{"text": {"content": game_name}}]},
                "Lanzamiento": {"date": {"start": data.get("fecha_lanzamiento", None)}},
                "Géneros": {"multi_select": generos_list},
                "Plataforma": {"multi_select": plataformas_list},
                "Sinopsis": {"rich_text": [{"text": {"content": data.get("resumen", "N/A")}}]},
                "Puntuación": {"number": data.get("puntuacion_media", 0)},
                "Duración": {"number": data.get("duracion_horas", 0)},
                "Desarrollador": {"relation": relacion_developer},
            }
        }

        pagina_creada = notion.pages.create(**nueva_pagina)
        page_id = pagina_creada["id"]
        print(f"Página de '{game_name}' creada exitosamente en Notion. ID: {page_id}")
        return page_id

    except json.JSONDecodeError as e:
        print(f"El JSON de la IA no es válido después de la limpieza: {e}")
    except Exception as e:
        print(f"Ocurrió un error al crear la página en Notion: {e}")
        return None
    return page_id


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


# --- Flujo principal ADAPTADO PARA EL ENLACE EXTERNO ---

print("\n--- PASO A: Obtener datos estructurados del juego (JSON) ---")
datos_json = obtener_datos_juego_json(game_name)
print("\nDatos JSON finales recibidos:")
print(datos_json)

page_id = None
cover_url = None

if datos_json:
    print("\n--- PASO B: Preparar la Carátula VÍA IGDB ---")

    # 1. Obtener Access Token de Twitch
    # Usamos c.TWITCH_CLIENT_ID y c.TWITCH_CLIENT_SECRET
    token = _obtener_access_token(c.TWITCH_CLIENT_ID, c.TWITCH_CLIENT_SECRET)

    if token:
        # 2. Obtener la URL de la portada, seleccionando el mejor match por similitud
        # Usamos c.TWITCH_CLIENT_ID
        cover_url = obtener_cover_url_igdb(game_name, c.TWITCH_CLIENT_ID, token)
    else:
        print("No se pudo obtener el Access Token. No se buscará la portada.")

    print("\n--- PASO C: Crear página en Notion ---")
    page_id = crear_pagina_notion(datos_json)

    if page_id and cover_url:
        print("\n--- PASO D: Subir la Carátula como Enlace Externo a la propiedad 'Cover' ---")
        # 4. Subir la URL a la propiedad "Cover"
        actualizar_cover_link_notion(page_id, cover_url, property_name="Cover")
    elif page_id:
        print("La página fue creada, pero no se pudo adjuntar la carátula.")

print("\n--- PROCESO COMPLETADO ---")
```

### `media\howlongtobeat.py`

```python
import os
from notion_client import Client
from howlongtobeatpy import HowLongToBeat

# --- CONFIGURACIÓN ---
# ⚠️ Reemplaza estos valores con tu token de Notion y el ID de tu base de datos.
NOTION_TOKEN = "ntn_m12866236193ptit989YPuaiDuz4agnqm0wF52MOtfF02T"
DATABASE_ID = "24404cb0518381b4b31ad44e54791150"

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
```

### `media\libro-ai.py`

```python
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
```

### `media\peli-ai.py`

```python
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
```

### `media\saga-ai.py`

```python
import google.generativeai as genai
import subprocess
import sys
import os

# --- CONSTANTES ---
# !!! REEMPLAZA ESTAS CLAVES CON LAS TUYAS !!!
ARCHIVO_A_EJECUTAR = "peli-ai.py"  # Nombre del script de arriba

# --- CONFIGURACIÓN INICIAL ---
genai.configure(api_key=c.GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')


def obtener_peliculas_de_saga(nombre_saga):
    """Usa Gemini para obtener una lista limpia de nombres de películas."""
    print(f"🤖 Preguntando a Gemini por las películas de la saga: '{nombre_saga}'...")

    prompt = (
        f"Dame **únicamente** la lista de las películas que componen la saga '{nombre_saga}', "
        f"incluyendo precuelas, secuelas y spin-offs, sin números, viñetas, ni texto introductorio, "
        f"y separadas por saltos de línea."
    )

    try:
        response = model.generate_content(prompt)
        peliculas = [
            peli.strip()
            for peli in response.text.split('\n')
            if peli.strip()
        ]
        return peliculas
    except Exception as e:
        print(f"❌ Error al consultar a Gemini: {e}")
        return []


def ejecutar_script_por_pelicula(nombre_pelicula, nombre_saga_base):
    """Ejecuta peli-ai.py pasando la película Y el nombre base de la saga."""

    # Prepara el comando: [intérprete, script, arg_pelicula, arg_saga]
    comando = [sys.executable, ARCHIVO_A_EJECUTAR, nombre_pelicula, nombre_saga_base]

    print(f"\n🚀 Procesando película: **{nombre_pelicula}** (Saga: {nombre_saga_base})")

    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Éxito al procesar '{nombre_pelicula}'.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Falla en peli-ai.py al procesar '{nombre_pelicula}'.")
        print(f"   Mensaje de error: {e.stderr.strip()}")
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el archivo '{ARCHIVO_A_EJECUTAR}'.")


# --- FLUJO PRINCIPAL ---
if __name__ == "__main__":

    if not os.path.exists(ARCHIVO_A_EJECUTAR):
        print(f"❌ ERROR CRÍTICO: No se encuentra el archivo '{ARCHIVO_A_EJECUTAR}'.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Uso: python saga_processor.py \"Nombre de la Saga\"")
        print("Ejemplo: python saga_processor.py \"Star Wars\"")
        sys.exit(1)

    nombre_saga = sys.argv[1]

    peliculas_de_la_saga = obtener_peliculas_de_saga(nombre_saga)

    if not peliculas_de_la_saga:
        print("\n🚫 No se encontraron películas. Terminando.")
        sys.exit(0)

    print(f"\n--- Se encontraron {len(peliculas_de_la_saga)} películas. Comenzando el proceso ---")

    for peli in peliculas_de_la_saga:
        # Pasa el nombre de la película Y el nombre base de la saga
        ejecutar_script_por_pelicula(peli, nombre_saga)

    print("\n🎉 Proceso de saga completado.")
```

### `media\serie-ai.py`

```python
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
```

### `sueno\disparador_sueno.py`

```python
import subprocess
import constants as c
from notion_client import Client

notion = Client(auth=c.NOTION_TOKEN)


def ejecutar_procesador(page_id):
    """Llama al segundo script usando Popen."""
    print(f"🛠️ Iniciando proceso para ID: {page_id}...")

    # Iniciamos el proceso
    proceso = subprocess.Popen(
        ["python", "sueno/sueno-ai.py", page_id]
    )

    # .communicate() espera a que el proceso termine y devuelve (stdout, stderr)
    stdout, stderr = proceso.communicate()

    if proceso.returncode == 0:
        print(f"✅ Éxito:\n{stdout}")
        return True
    else:
        print(f"❌ Error en el proceso hijo:\n{stderr}")
        return False


def buscar_y_disparar():
    query = notion.databases.query(
        database_id=c.JOURNAL_DATABASE_ID,
        filter={
            "and": [
                {"property": "Tipo", "select": {"equals": "Sueño"}},
                {"property": "Disparador", "checkbox": {"equals": True}}
            ]
        }
    )

    resultados = query.get("results", [])

    for page in resultados:
        page_id = page["id"]

        # Ejecución
        if ejecutar_procesador(page_id):
            notion.pages.update(
                page_id=page_id,
                properties={"Disparador": {"checkbox": False}}
            )
            print(f"✔ Notificación: Notion actualizado para {page_id}")


if __name__ == "__main__":
    buscar_y_disparar()
```

### `sueno\sueno-ai.py`

```python
import sys
import time
from io import BytesIO
from notion_client import Client
from google import genai
from google.genai import types
import cloudinary
import cloudinary.uploader
import constants as c

# Configuración Cloudinary
CLOUDINARY_CONFIG = {
    "cloud_name": "dzqqem54n",
    "api_key": "984936899817499",
    "api_secret": "SZFekFZ2NKgekAJAFWDJTX7b7y4"
}

# Inicialización de clientes
notion = Client(auth=c.NOTION_TOKEN)
gemini_client = genai.Client(api_key=c.GEMINI_API_KEY)
cloudinary.config(**CLOUDINARY_CONFIG)


def borrar_imagenes_existentes(page_id):
    response = notion.blocks.children.list(block_id=page_id)
    for block in response.get("results", []):
        if block["type"] == "image":
            notion.blocks.delete(block_id=block["id"])


def procesar_sueno(page_id):
    try:
        # 1. Obtener la información de la página actual
        page = notion.pages.retrieve(page_id=page_id)

        # Obtener el texto del sueño (ajusta el nombre de la propiedad si varía)
        try:
            texto_sueno = "".join([t["plain_text"] for t in page["properties"]["Texto"]["rich_text"]])
        except:
            print("No se pudo obtener el texto del sueño.")
            return False

        # 2. Limpiar imágenes viejas
        borrar_imagenes_existentes(page_id)

        # 3. Generar imagen con Gemini
        print(f"🎨 Generando imagen para el sueño...")
        prompt = f"Imagen cohesiva y surrealista del siguiente sueño: '{texto_sueno}'. Atmósfera onírica y dramática."

        response = gemini_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9")
        )

        if not response.generated_images:
            return False

        # 4. Subir a Cloudinary
        img_bytes = response.generated_images[0].image.image_bytes
        upload_res = cloudinary.uploader.upload(
            file=BytesIO(img_bytes),
            public_id=f"dream_{page_id}",
            folder="notion_dreams",
            overwrite=True
        )
        url_final = upload_res["secure_url"]

        # 5. Insertar en Notion
        notion.blocks.children.append(
            block_id=page_id,
            children=[{
                "object": "block",
                "type": "image",
                "image": {"type": "external", "external": {"url": url_final}}
            }]
        )
        return True

    except Exception as e:
        print(f"Error técnico: {e}")
        return False


if __name__ == "__main__":
    # Verificamos que se haya pasado el page_id como argumento
    if len(sys.argv) < 2:
        print("Error: No se proporcionó page_id")
        sys.exit(1)

    target_page_id = sys.argv[1]
    exito = procesar_sueno(target_page_id)

    if exito:
        sys.exit(0)  # Salida exitosa
    else:
        sys.exit(1)  # Salida con error
```

### `sueno\sueno_todos.py`

```python
import subprocess
import time
from notion_client import Client
import constants as c

# --- INICIALIZACIÓN (Igual que antes) ---
try:
    notion = Client(auth=c.NOTION_TOKEN)
except Exception as e:
    print(f"Error: {e}")
    exit()


def buscar_sueños_sin_imagen():
    """Busca en Notion sueños pendientes de imagen."""
    # ... (Misma lógica de búsqueda que el script anterior) ...
    pages_without_images = []
    filter_query = {"property": "Tipo", "select": {"equals": "Sueño"}}
    query_response = notion.databases.query(database_id=c.JOURNAL_DATABASE_ID, filter=filter_query)

    for page in query_response["results"]:
        page_id = page["id"]
        blocks = notion.blocks.children.list(block_id=page_id)
        if not any(block["type"] == "image" for block in blocks["results"]):
            pages_without_images.append(page_id)
    return pages_without_images


# --- EJECUCIÓN CON POPEN ---
if __name__ == "__main__":
    pendientes = buscar_sueños_sin_imagen()
    print(f"Total a procesar: {len(pendientes)}\n")

    for i, page_id in enumerate(pendientes):
        print(f"[{i + 1}/{len(pendientes)}] Iniciando proceso Popen para: {page_id}")

        # Abrimos el proceso hijo
        # stdout=None permite que el hijo imprima directamente en tu terminal actual
        proceso = subprocess.Popen(
            ["python", "sueno/sueno-ai.py", page_id],
            text=True
        )

        # IMPORTANTE: .wait() bloquea el bucle hasta que 'sueno-ai.py' termine.
        # Esto garantiza que sea "uno por uno".
        codigo_retorno = proceso.wait()

        if codigo_retorno == 0:
            print(f"✔ Proceso {page_id} finalizado correctamente.")
        else:
            print(f"✘ Proceso {page_id} falló con código: {codigo_retorno}")

        time.sleep(1)

    print("\n--- Ejecución masiva terminada ---")
```
