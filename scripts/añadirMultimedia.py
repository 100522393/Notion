import os
import time
import requests
from typing import List, Dict, Any, Set
import constants as c

# =========================
# CONFIG
# =========================

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "secret_xxx")

SERIES_DB_ID = c.SERIES_DATABASE_ID
GAMES_DB_ID = c.JUEGOS_DATABASE_ID

# ID de la base / data source de Multimedia
MULTIMEDIA_DB_ID = c.MULTIMEDIA_DATABASE_ID

CONFIG = {
    # Propiedades relation en Multimedia
    "multimedia_series_relation_property": "Serie",
    "multimedia_games_relation_property": "Game",

    # Propiedad título de Multimedia
    "multimedia_title_property": "Nombre",
    # Cover sync
    "cover_source_properties": ["Cover_v", "Cover_s"],  # prioridad
    "cover_target_property": "Cover",
}

DRY_RUN = False

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# =========================
# HTTP
# =========================

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
})


def notion_request(method: str, url: str, **kwargs) -> requests.Response:
    max_retries = 5

    for attempt in range(max_retries):
        resp = session.request(method, url, timeout=30, **kwargs)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            print(f"[WARN] Rate limited. Esperando {retry_after}s...")
            time.sleep(retry_after)
            continue

        if 500 <= resp.status_code < 600:
            wait = 2 ** attempt
            print(f"[WARN] Error servidor {resp.status_code}. Reintentando en {wait}s...")
            time.sleep(wait)
            continue

        return resp

    return resp



# =========================
# QUERY DATABASE
# =========================

def query_database(database_id: str) -> List[Dict[str, Any]]:
    """
    Consulta todas las filas de una database con paginación.
    """
    url = f"{BASE_URL}/databases/{database_id}/query"
    results: List[Dict[str, Any]] = []
    payload: Dict[str, Any] = {"page_size": 100}

    while True:
        resp = notion_request("POST", url, json=payload)
        if not resp.ok:
            raise RuntimeError(
                f"Error consultando database {database_id}: "
                f"{resp.status_code} - {resp.text}"
            )

        data = resp.json()
        results.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        payload["start_cursor"] = data["next_cursor"]

    return results


def get_page_ids(database_id: str) -> List[str]:
    pages = query_database(database_id)
    return [page["id"] for page in pages]


# =========================
# EXISTING RELATIONS
# =========================

def get_existing_relation_ids(
    multimedia_pages: List[Dict[str, Any]],
    relation_property_name: str
) -> Set[str]:
    existing_ids: Set[str] = set()

    for page in multimedia_pages:
        prop = page.get("properties", {}).get(relation_property_name)

        if not prop or prop.get("type") != "relation":
            continue

        for rel in prop.get("relation", []):
            rel_id = rel.get("id")
            if rel_id:
                existing_ids.add(rel_id)

    return existing_ids


# =========================
# CREATE PAGE IN MULTIMEDIA
# =========================

def get_page_title(page_id: str) -> str:
    url = f"{BASE_URL}/pages/{page_id}"

    resp = notion_request("GET", url)

    if not resp.ok:
        raise RuntimeError(f"Error obteniendo página {page_id}: {resp.text}")

    data = resp.json()
    props = data.get("properties", {})

    # Buscar la propiedad de tipo title
    for prop in props.values():
        if prop.get("type") == "title":
            title_array = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_array)

    return "Sin título"

def create_multimedia_page_with_relation(
    multimedia_db_id: str,
    title_property_name: str,
    relation_property_name: str,
    related_page_id: str,
) -> str:
    """
    Crea una nueva página en Multimedia con el título = nombre real de la página relacionada
    """
    url = f"{BASE_URL}/pages"

    # 🔥 obtener nombre real
    title_text = get_page_title(related_page_id)

    payload = {
        "parent": {
            "type": "database_id",
            "database_id": multimedia_db_id
        },
        "properties": {
            title_property_name: {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": title_text
                        }
                    }
                ]
            },
            relation_property_name: {
                "relation": [
                    {"id": related_page_id}
                ]
            }
        }
    }

    if DRY_RUN:
        print(
            f"[DRY_RUN] Crear página {title_text} "
            f"({relation_property_name}={related_page_id})"
        )
        return "dry-run-page-id"

    resp = notion_request("POST", url, json=payload)

    if not resp.ok:
        raise RuntimeError(
            f"Error creando página en Multimedia: "
            f"{resp.status_code} - {resp.text}"
        )

    return resp.json()["id"]


# =========================
# PROCESS RELATIONS
# =========================

def create_pages_for_relation(
    source_db_id: str,
    multimedia_db_id: str,
    relation_property_name: str,
    label: str,
) -> None:
    print(f"\nProcesando {label}...")

    source_ids = get_page_ids(source_db_id)
    multimedia_pages = query_database(multimedia_db_id)

    existing_ids = get_existing_relation_ids(
        multimedia_pages,
        relation_property_name
    )

    print(f"{label}: encontrados {len(source_ids)} IDs origen")
    print(f"{label}: ya existentes {len(existing_ids)} relaciones")

    created = 0
    skipped = 0

    for related_page_id in source_ids:
        if related_page_id in existing_ids:
            skipped += 1
            print(f"[SKIP] Ya existe relación {label}: {related_page_id}")
            continue

        new_page_id = create_multimedia_page_with_relation(
            multimedia_db_id=multimedia_db_id,
            title_property_name=CONFIG["multimedia_title_property"],
            relation_property_name=relation_property_name,
            related_page_id=related_page_id,
        )

        existing_ids.add(related_page_id)
        created += 1
        print(f"[OK] Creado: {new_page_id} -> {related_page_id}")

    print("\nResumen:")
    print(f"- {label} creados: {created}")
    print(f"- {label} ya existían: {skipped}")

# =========================
# COVER SYNC
# =========================

def get_property_id_from_page(page: Dict[str, Any], property_name: str):
    prop = page.get("properties", {}).get(property_name)
    if not prop:
        return None
    return prop.get("id")


def get_page_property_items(page_id: str, property_id: str):
    items = []
    next_cursor = None

    while True:
        url = f"{BASE_URL}/pages/{page_id}/properties/{property_id}"
        params = {}

        if next_cursor:
            params["start_cursor"] = next_cursor

        resp = notion_request("GET", url, params=params)

        if not resp.ok:
            raise RuntimeError(f"Error obteniendo property items: {resp.text}")

        data = resp.json()

        if data.get("object") == "list":
            items.extend(data.get("results", []))

            if data.get("has_more"):
                next_cursor = data.get("next_cursor")
                continue

            break

        items.append(data)
        break

    return items


def extract_url_from_file(file_obj):
    if not isinstance(file_obj, dict):
        return None

    t = file_obj.get("type")

    if t == "external":
        return file_obj.get("external", {}).get("url")

    if t == "file":
        return file_obj.get("file", {}).get("url")

    return None


def extract_url_from_property_item(item):
    if not isinstance(item, dict):
        return None

    if item.get("type") == "files":
        for f in item.get("files", []):
            url = extract_url_from_file(f)
            if url:
                return url

    if item.get("type") == "rollup":
        rollup = item.get("rollup", {})
        if rollup.get("type") == "array":
            for sub in rollup.get("array", []):
                url = extract_url_from_property_item(sub)
                if url:
                    return url

    return None


def get_cover_url_from_sources(page):
    page_id = page["id"]

    for prop_name in CONFIG["cover_source_properties"]:
        prop_id = get_property_id_from_page(page, prop_name)
        if not prop_id:
            continue

        items = get_page_property_items(page_id, prop_id)

        for item in items:
            url = extract_url_from_property_item(item)
            if url:
                return url

    return None


def get_current_cover(page):
    prop = page.get("properties", {}).get(CONFIG["cover_target_property"])

    if not prop or prop.get("type") != "files":
        return None

    files = prop.get("files", [])
    if not files:
        return None

    f = files[0]

    if f.get("type") == "external":
        return f.get("external", {}).get("url")

    if f.get("type") == "file":
        return f.get("file", {}).get("url")

    return None


def update_cover(page_id: str, url: str):
    payload = {
        "properties": {
            CONFIG["cover_target_property"]: {
                "files": [
                    {
                        "name": "cover",
                        "type": "external",
                        "external": {
                            "url": url
                        }
                    }
                ]
            }
        }
    }

    if DRY_RUN:
        print(f"[DRY_RUN] Update cover {page_id} -> {url}")
        return

    resp = notion_request("PATCH", f"{BASE_URL}/pages/{page_id}", json=payload)

    if not resp.ok:
        raise RuntimeError(f"Error actualizando cover: {resp.text}")

def sync_covers(multimedia_db_id: str):
    print("\nSincronizando covers...")

    pages = query_database(multimedia_db_id)

    updated = 0
    skipped = 0

    for i, page in enumerate(pages, 1):
        page_id = page["id"]

        try:
            new_url = get_cover_url_from_sources(page)
            current_url = get_current_cover(page)

            if not new_url:
                skipped += 1
                print(f"[{i}/{len(pages)}] Sin cover source")
                continue

            if new_url == current_url:
                skipped += 1
                print(f"[{i}/{len(pages)}] OK (ya actualizado)")
                continue

            update_cover(page_id, new_url)
            updated += 1

            print(f"[{i}/{len(pages)}] Updated cover")

        except Exception as e:
            print(f"[ERROR] {page_id}: {e}")

    print("\nResumen covers:")
    print(f"- Actualizados: {updated}")
    print(f"- Saltados: {skipped}")

# =========================
# MAIN
# =========================

def main():
    if not NOTION_TOKEN or NOTION_TOKEN == "secret_xxx":
        raise RuntimeError("Debes configurar NOTION_TOKEN con tu token de integración.")

    print("Creando páginas en Multimedia para Series...")
    create_pages_for_relation(
        source_db_id=SERIES_DB_ID,
        multimedia_db_id=MULTIMEDIA_DB_ID,
        relation_property_name=CONFIG["multimedia_series_relation_property"],
        label="Serie"
    )

    print("\nCreando páginas en Multimedia para Games...")
    create_pages_for_relation(
        source_db_id=GAMES_DB_ID,
        multimedia_db_id=MULTIMEDIA_DB_ID,
        relation_property_name=CONFIG["multimedia_games_relation_property"],
        label="Game"
    )


if __name__ == "__main__":
    main()
    print("\n--- SYNC COVERS ---")
    sync_covers(MULTIMEDIA_DB_ID)