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