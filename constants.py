import os
from dotenv import load_dotenv

load_dotenv()

# ====================================================
# I. SERVICIOS DE AUTENTICACIÓN Y CLAVES DE API
# ====================================================

# Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Notion
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

# Twitch / IGDB
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_TOKEN_URL = os.getenv("TWITCH_TOKEN_URL", "https://id.twitch.tv/oauth2/token")
IGDB_API_URL = os.getenv("IGDB_API_URL", "https://api.igdb.com/v4")

# OMDB
OMDB_API_KEY = os.getenv("OMDB_API_KEY")

# iCloud
ICLOUD_EMAIL = os.getenv("ICLOUD_EMAIL")
ICLOUD_APP_PASSWORD = os.getenv("ICLOUD_APP_PASSWORD")

# ====================================================
# II. NOTION: BASES DE DATOS (DATABASE IDs)
# ====================================================

# --- Medios de Lectura (Libros) ---
LIBROS_DATABASE_ID = os.getenv("LIBROS_DATABASE_ID")
AUTORES_DATABASE_ID = os.getenv("AUTORES_DATABASE_ID")
CAPITULOS_DATABASE_ID = os.getenv("CAPITULOS_DATABASE_ID")

# --- Medios Visuales (Películas, Series, etc.) ---
PELICULAS_DATABASE_ID = os.getenv("PELICULAS_DATABASE_ID")
SERIES_DATABASE_ID = os.getenv("SERIES_DATABASE_ID")
DIRECTORES_DATABASE_ID = os.getenv("DIRECTORES_DATABASE_ID")
SAGA_DATABASE_ID = os.getenv("SAGA_DATABASE_ID")
EPISODIOS_DATABASE_ID = os.getenv("EPISODIOS_DATABASE_ID")
JOURNAL_DATABASE_ID = os.getenv("JOURNAL_DATABASE_ID")

# --- Videojuegos ---
JUEGOS_DATABASE_ID = os.getenv("JUEGOS_DATABASE_ID")
DESARROLLADORES_DATABASE_ID = os.getenv("DESARROLLADORES_DATABASE_ID")