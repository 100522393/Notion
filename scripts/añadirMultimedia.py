import os
import time
from typing import Any, Dict, List, Optional, Set

import requests
import constants as c


# =========================
# CONFIG
# =========================

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "secret_xxx")

# Puedes seguir guardando los IDs antiguos de database.
# El script resolverá automáticamente el primer data_source asociado.
SERIES_DB_ID = c.SERIES_DATABASE_ID
GAMES_DB_ID = c.JUEGOS_DATABASE_ID
MULTIMEDIA_DB_ID = c.MULTIMEDIA_DATABASE_ID

# Opcional: si ya tienes los data_source_id exactos, úsalos aquí.
# Si se dejan en None, se resolverán desde el database_id.
SERIES_DATA_SOURCE_ID = getattr(c, "SERIES_DATA_SOURCE_ID", None)
GAMES_DATA_SOURCE_ID = getattr(c, "JUEGOS_DATA_SOURCE_ID", None)
MULTIMEDIA_DATA_SOURCE_ID = getattr(c, "MULTIMEDIA_DATA_SOURCE_ID", None)

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

# Última versión estable documentada por Notion
NOTION_VERSION = "2026-03-11"
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
    last_resp: Optional[requests.Response] = None

    for attempt in range(max_retries):
        try:
            resp = session.request(method, url, timeout=30, **kwargs)
            last_resp = resp

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

        except requests.RequestException as e:
            wait = 2 ** attempt
            print(f"[WARN] Error de red: {e}. Reintentando en {wait}s...")
            time.sleep(wait)

    if last_resp is not None:
        return last_resp

    raise RuntimeError("No se pudo completar la petición a Notion tras varios intentos.")


def normalize_id(value: str) -> str:
    return value.strip()


# =========================
# DATABASE -> DATA SOURCE
# =========================

def retrieve_database(database_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/databases/{normalize_id(database_id)}"
    resp = notion_request("GET", url)

    if not resp.ok:
        raise RuntimeError(
            f"Error obteniendo database {database_id}: "
            f"{resp.status_code} - {resp.text}"
        )

    return resp.json()


def resolve_data_source_id(
    explicit_data_source_id: Optional[str],
    database_id: str,
    label: str,
) -> str:
    """
    Resuelve el data_source_id actual.
    - Si se pasa explícitamente, lo usa.
    - Si no, intenta resolverlo desde el database_id.
    """
    if explicit_data_source_id:
        return normalize_id(explicit_data_source_id)

    database = retrieve_database(database_id)
    data_sources = database.get("data_sources", [])

    if not data_sources:
        raise RuntimeError(
            f"No se encontraron data_sources para {label} (database_id={database_id}). "
            "Comprueba que el ID sea correcto y que la integración tenga acceso."
        )

    if len(data_sources) > 1:
        names = [ds.get("name", "<sin nombre>") for ds in data_sources]
        raise RuntimeError(
            f"{label} tiene múltiples data sources: {names}. "
            "Define explícitamente el *_DATA_SOURCE_ID correcto en constants.py."
        )

    return data_sources[0]["id"]


# =========================
# QUERY DATA SOURCE
# =========================

def query_data_source(data_source_id: str) -> List[Dict[str, Any]]:
    """
    Consulta todas las filas de un data source con paginación.
    """
    url = f"{BASE_URL}/data_sources/{normalize_id(data_source_id)}/query"
    results: List[Dict[str, Any]] = []
    payload: Dict[str, Any] = {"page_size": 100}

    while True:
        resp = notion_request("POST", url, json=payload)
        if not resp.ok:
            raise RuntimeError(
                f"Error consultando data source {data_source_id}: "
                f"{resp.status_code} - {resp.text}"
            )

        data = resp.json()
        results.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        payload["start_cursor"] = data["next_cursor"]

    return results


def get_page_ids_from_data_source(data_source_id: str) -> List[str]:
    pages = query_data_source(data_source_id)
    return [page["id"] for page in pages if page.get("object") == "page"]


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
# PAGE HELPERS
# =========================

def get_page(page_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/pages/{normalize_id(page_id)}"
    resp = notion_request("GET", url)

    if not resp.ok:
        raise RuntimeError(
            f"Error obteniendo página {page_id}: "
            f"{resp.status_code} - {resp.text}"
        )

    return resp.json()


def get_page_title(page_id: str) -> str:
    data = get_page(page_id)
    props = data.get("properties", {})

    for prop in props.values():
        if prop.get("type") == "title":
            title_array = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_array).strip() or "Sin título"

    return "Sin título"


# =========================
# CREATE PAGE IN MULTIMEDIA
# =========================

def create_multimedia_page_with_relation(
    multimedia_data_source_id: str,
    title_property_name: str,
    relation_property_name: str,
    related_page_id: str,
) -> str:
    """
    Crea una nueva página en Multimedia con el título = nombre real de la página relacionada.
    """
    url = f"{BASE_URL}/pages"
    title_text = get_page_title(related_page_id)

    payload = {
        "parent": {
            "type": "data_source_id",
            "data_source_id": normalize_id(multimedia_data_source_id),
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
                    {"id": normalize_id(related_page_id)}
                ]
            }
        }
    }

    if DRY_RUN:
        print(
            f"[DRY_RUN] Crear página '{title_text}' "
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
    source_data_source_id: str,
    multimedia_data_source_id: str,
    relation_property_name: str,
    label: str,
) -> None:
    print(f"\nProcesando {label}...")

    source_ids = get_page_ids_from_data_source(source_data_source_id)
    multimedia_pages = query_data_source(multimedia_data_source_id)

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
            multimedia_data_source_id=multimedia_data_source_id,
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

def get_property_id_from_page(page: Dict[str, Any], property_name: str) -> Optional[str]:
    prop = page.get("properties", {}).get(property_name)
    if not prop:
        return None
    return prop.get("id")


def get_page_property_items(page_id: str, property_id: str) -> List[Dict[str, Any]]:
    """
    Recupera una propiedad de página. Algunas propiedades devuelven lista paginada,
    otras devuelven un solo objeto property_item.
    """
    items: List[Dict[str, Any]] = []
    next_cursor = None

    while True:
        url = f"{BASE_URL}/pages/{normalize_id(page_id)}/properties/{property_id}"
        params = {}

        if next_cursor:
            params["start_cursor"] = next_cursor

        resp = notion_request("GET", url, params=params)

        if not resp.ok:
            raise RuntimeError(
                f"Error obteniendo property items de {page_id}/{property_id}: "
                f"{resp.status_code} - {resp.text}"
            )

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


def extract_url_from_file(file_obj: Any) -> Optional[str]:
    if not isinstance(file_obj, dict):
        return None

    t = file_obj.get("type")

    if t == "external":
        return file_obj.get("external", {}).get("url")

    if t == "file":
        return file_obj.get("file", {}).get("url")

    if t == "file_upload":
        # No suele contener URL utilizable todavía, pero lo dejamos contemplado.
        return file_obj.get("file_upload", {}).get("url")

    return None


def extract_url_from_property_item(item: Any) -> Optional[str]:
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


def get_cover_url_from_sources(page: Dict[str, Any]) -> Optional[str]:
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


def get_current_cover(page: Dict[str, Any]) -> Optional[str]:
    prop = page.get("properties", {}).get(CONFIG["cover_target_property"])

    if not prop or prop.get("type") != "files":
        return None

    files = prop.get("files", [])
    if not files:
        return None

    first = files[0]
    return extract_url_from_file(first)


def update_cover(page_id: str, url: str) -> None:
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

    resp = notion_request("PATCH", f"{BASE_URL}/pages/{normalize_id(page_id)}", json=payload)

    if not resp.ok:
        raise RuntimeError(
            f"Error actualizando cover {page_id}: "
            f"{resp.status_code} - {resp.text}"
        )


def sync_covers(multimedia_data_source_id: str) -> None:
    print("\nSincronizando covers...")

    pages = query_data_source(multimedia_data_source_id)

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

def main() -> None:
    if not NOTION_TOKEN or NOTION_TOKEN == "secret_xxx":
        raise RuntimeError("Debes configurar NOTION_TOKEN con tu token de integración.")

    series_data_source_id = resolve_data_source_id(
        SERIES_DATA_SOURCE_ID,
        SERIES_DB_ID,
        "Series",
    )
    games_data_source_id = resolve_data_source_id(
        GAMES_DATA_SOURCE_ID,
        GAMES_DB_ID,
        "Games",
    )
    multimedia_data_source_id = resolve_data_source_id(
        MULTIMEDIA_DATA_SOURCE_ID,
        MULTIMEDIA_DB_ID,
        "Multimedia",
    )

    print("Creando páginas en Multimedia para Series...")
    create_pages_for_relation(
        source_data_source_id=series_data_source_id,
        multimedia_data_source_id=multimedia_data_source_id,
        relation_property_name=CONFIG["multimedia_series_relation_property"],
        label="Serie",
    )

    print("\nCreando páginas en Multimedia para Games...")
    create_pages_for_relation(
        source_data_source_id=games_data_source_id,
        multimedia_data_source_id=multimedia_data_source_id,
        relation_property_name=CONFIG["multimedia_games_relation_property"],
        label="Game",
    )

    print("\n--- SYNC COVERS ---")
    sync_covers(multimedia_data_source_id)


if __name__ == "__main__":
    main()