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