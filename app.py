import sys
import subprocess
import re
from flask import Flask, request, Response, render_template
from pathlib import Path
import os

from alarma import enviar_alarma_icloud

app = Flask(__name__)

# =============================================================
# 1. COLORES
# =============================================================

COLORES = {
    "pelicula": "#DC143C",
    "serie": "#007BFF",
    "saga": "#FFC300",
    "libro": "#FF00FF",
    "game": "#7CFC00",
    "alarma": "#FFFF33",
}

# =============================================================
# 2. PATHS
# =============================================================

BASE_DIR = Path(__file__).resolve().parent

SCRIPTS = {
    "pelicula": BASE_DIR / "media/peli-ai.py",
    "serie": BASE_DIR / "media/serie-ai.py",
    "saga": BASE_DIR / "media/saga-ai.py",
    "libro": BASE_DIR / "media/libro-ai.py",
    "game": BASE_DIR / "media/game-ai.py",
    "hltb": BASE_DIR / "media/howlongtobeat.py",
    "sueno": BASE_DIR / "sueno/sueno_todos.py",
    "sueno_trigger": BASE_DIR / "sueno/disparador_sueno.py",
}

# =============================================================
# 3. ENTORNO
# =============================================================

env_config = os.environ.copy()
env_config["PYTHONPATH"] = str(BASE_DIR)
env_config["PYTHONUTF8"] = "1"
env_config["PYTHONIOENCODING"] = "utf-8"

PYTHON_EXEC = sys.executable
if sys.platform == "win32":
    pyw = PYTHON_EXEC.replace("python.exe", "pythonw.exe")
    if os.path.exists(pyw):
        PYTHON_EXEC = pyw


def run_script(script_path, *args):
    subprocess.Popen(
        [PYTHON_EXEC, str(script_path), *args],
        cwd=str(BASE_DIR),
        env=env_config
    )

# =============================================================
# 4. RUTAS SIMPLES
# =============================================================

@app.route('/howlongtobeat')
def howlongtobeat():
    try:
        run_script(SCRIPTS["hltb"])
    except Exception as e:
        return f"Error: {e}", 500

    return render_template("close.html")


@app.route('/sueno_todos')
def sueno_todos():
    try:
        run_script(SCRIPTS["sueno"])
    except Exception as e:
        return f"Error: {e}", 500

    return render_template("close.html")


@app.route('/sueno')
def sueno():
    try:
        run_script(SCRIPTS["sueno_trigger"])
    except Exception as e:
        return f"Error: {e}", 500

    return render_template("close.html")


# =============================================================
# 5. MEDIA ROUTES (FORMULARIOS)
# =============================================================

def handle_media_route(script_key, label, input_name, color_key):
    COLOR = COLORES[color_key]

    if request.method == 'POST':
        value = request.form.get(input_name)

        if not value:
            return render_template("error.html", mensaje="Campo vacío"), 400

        try:
            run_script(SCRIPTS[script_key], value)
        except Exception as e:
            return render_template("error.html", mensaje=str(e)), 500

        return render_template(
            "success.html",
            nombre=f"{label}: {value}",
            color=COLOR
        )

    return render_template(
        "form.html",
        titulo=f"Introduce la {label.lower()}",
        action_url=request.path,
        input_name=input_name,
        color=COLOR
    )


@app.route('/pelicula', methods=['GET', 'POST'])
def pelicula():
    return handle_media_route("pelicula", "Peli", "movie_name", "pelicula")


@app.route('/serie', methods=['GET', 'POST'])
def serie():
    return handle_media_route("serie", "Serie", "show_name", "serie")


@app.route('/saga', methods=['GET', 'POST'])
def saga():
    return handle_media_route("saga", "Saga", "saga_name", "saga")


@app.route('/book', methods=['GET', 'POST'])
def book():
    return handle_media_route("libro", "Libro", "book_name", "libro")


@app.route('/game', methods=['GET', 'POST'])
def game():
    return handle_media_route("game", "Videojuego", "game_name", "game")


# =============================================================
# 6. ALARMA
# =============================================================

@app.route('/alarma', methods=['GET', 'POST'])
def alarma():
    COLOR = COLORES["alarma"]

    if request.method == 'POST':
        hora = request.form.get('alarma')

        if not hora:
            return render_template("error.html", mensaje="Campo vacío"), 400

        patron = r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"

        if not re.match(patron, hora):
            return render_template(
                "success.html",
                nombre="⚠️ Formato incorrecto (usa HH:MM)",
                color=COLOR
            )

        try:
            enviar_alarma_icloud(hora)
        except Exception as e:
            return render_template("error.html", mensaje=str(e)), 500

        return render_template(
            "success.html",
            nombre=f"ALARMA: {hora}",
            color=COLOR
        )

    return render_template(
        "form.html",
        titulo="Introduce la alarma",
        action_url="/alarma",
        input_name="alarma",
        color=COLOR
    )


# =============================================================
# 7. RUN
# =============================================================

if __name__ == '__main__':
    app.run(debug=True)