#!/usr/bin/env python3
import os
import sys
import time
import requests
from typing import Any, Dict, List, Optional
import constants as c

NOTION_TOKEN = c.NOTION_TOKEN
DATABASE_ID = c.MULTIMEDIA_DATABASE_ID

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# Propiedades de origen (lookup/rollup)
SOURCE_PROPERTIES = ["Cover_s", "Cover_v"]

# Propiedad destino
TARGET_PROPERTY = "Cover"

# Si True, solo muestra qué haría sin escribir cambios
DRY_RUN = False

if not NOTION_TOKEN or not DATABASE_ID:
    print("Faltan variables de entorno:")
    print("  export NOTION_TOKEN='secret_xxx'")
    print("  export NOTION_DATABASE_ID='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def notion_request(method: str, url: str, **kwargs) -> requests.Response:
    """Hace requests a Notion con reintentos básicos."""
    for attempt in range(5):
        resp = requests.request(method, url, headers=HEADERS, timeout=30, **kwargs)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "2"))
            print(f"Rate limit alcanzado. Esperando {retry_after}s...")
            time.sleep(retry_after)
            continue

        if 200 <= resp.status_code < 300:
            return resp

        # Reintentos simples para errores temporales
        if resp.status_code >= 500 and attempt < 4:
            time.sleep(2 ** attempt)
            continue

        print(f"Error Notion [{resp.status_code}] en {url}")
        try:
            print(resp.json())
        except Exception:
            print(resp.text)
        resp.raise_for_status()

    raise RuntimeError(f"No se pudo completar la petición: {method} {url}")


def query_database(database_id: str) -> List[Dict[str, Any]]:
    """Recorre toda la base de datos paginando."""
    pages: List[Dict[str, Any]] = []
    next_cursor = None

    while True:
        payload: Dict[str, Any] = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        resp = notion_request(
            "POST",
            f"{BASE_URL}/databases/{database_id}/query",
            json=payload,
        )
        data = resp.json()

        results = data.get("results", [])
        pages.extend(results)

        if not data.get("has_more"):
            break

        next_cursor = data.get("next_cursor")

    return pages


def get_property_id_from_page(page: Dict[str, Any], property_name: str) -> Optional[str]:
    """Saca el id real de la propiedad a partir del objeto page."""
    prop = page.get("properties", {}).get(property_name)
    if not prop:
        return None
    return prop.get("id")


def get_page_property_items(page_id: str, property_id: str) -> List[Dict[str, Any]]:
    """
    Recupera todos los items de una propiedad.
    Esto es importante para rollups/lookups, porque la respuesta normal puede venir truncada.
    """
    items: List[Dict[str, Any]] = []
    next_cursor = None

    while True:
        url = f"{BASE_URL}/pages/{page_id}/properties/{property_id}"
        params = {}
        if next_cursor:
            params["start_cursor"] = next_cursor

        resp = notion_request("GET", url, params=params)
        data = resp.json()

        # Cuando devuelve una lista paginada
        if data.get("object") == "list":
            items.extend(data.get("results", []))
            if data.get("has_more"):
                next_cursor = data.get("next_cursor")
                continue
            break

        # Cuando devuelve un único property_item
        items.append(data)
        break

    return items


def extract_url_from_file_object(file_obj: Dict[str, Any]) -> Optional[str]:
    """
    Extrae URL desde objetos file de Notion.
    Soporta external y file.
    """
    if not isinstance(file_obj, dict):
        return None

    file_type = file_obj.get("type")
    if file_type == "external":
        return file_obj.get("external", {}).get("url")
    if file_type == "file":
        return file_obj.get("file", {}).get("url")
    if file_type == "file_upload":
        # En algunos casos file_upload no trae una URL directa usable
        return file_obj.get("file_upload", {}).get("url")

    return None


def extract_url_from_property_item(item: Dict[str, Any]) -> Optional[str]:
    """
    Intenta encontrar una URL de imagen dentro de un property_item.
    Cubre varios casos que pueden aparecer en rollups/lookups.
    """
    if not isinstance(item, dict):
        return None

    item_type = item.get("type")

    # Caso directo: property_item tipo files
    if item_type == "files":
        for f in item.get("files", []):
            url = extract_url_from_file_object(f)
            if url:
                return url

    # Caso raro: un rollup puede venir anidado
    if item_type == "rollup":
        rollup = item.get("rollup", {})
        rollup_type = rollup.get("type")

        if rollup_type == "array":
            for subitem in rollup.get("array", []):
                url = extract_url_from_property_item(subitem)
                if url:
                    return url

        elif rollup_type == "number":
            return None
        elif rollup_type == "date":
            return None
        elif rollup_type == "unsupported":
            return None

    # A veces en listas de property items viene directamente como files
    if item.get("object") == "property_item" and "files" in item:
        for f in item.get("files", []):
            url = extract_url_from_file_object(f)
            if url:
                return url

    return None


def get_first_cover_url(page: Dict[str, Any]) -> Optional[str]:
    """
    Busca URL primero en Cover_s y luego en Cover_v.
    """
    page_id = page["id"]

    for prop_name in SOURCE_PROPERTIES:
        prop_id = get_property_id_from_page(page, prop_name)
        if not prop_id:
            continue

        items = get_page_property_items(page_id, prop_id)

        for item in items:
            url = extract_url_from_property_item(item)
            if url:
                return url

    return None


def get_current_cover_value(page: Dict[str, Any]) -> Optional[str]:
    """
    Lee el valor actual de la propiedad cover si es tipo URL.
    """
    prop = page.get("properties", {}).get(TARGET_PROPERTY)
    if not prop:
        return None

    if prop.get("type") == "url":
        return prop.get("url")

    return None


def update_cover_property(page_id: str, url_value: str) -> None:
    """
    Actualiza la propiedad 'Cover' de tipo files
    usando la URL encontrada como archivo externo.
    """
    payload = {
        "properties": {
            "Cover": {
                "files": [
                    {
                        "name": "cover",
                        "type": "external",
                        "external": {
                            "url": url_value
                        }
                    }
                ]
            }
        }
    }

    notion_request("PATCH", f"{BASE_URL}/pages/{page_id}", json=payload)


def main() -> None:
    print("Consultando base de datos...")
    pages = query_database(DATABASE_ID)
    print(f"Total páginas encontradas: {len(pages)}")

    updated = 0
    skipped = 0
    errors = 0

    for index, page in enumerate(pages, start=1):
        page_id = page["id"]

        try:
            new_url = get_first_cover_url(page)
            current_url = get_current_cover_value(page)

            if not new_url:
                print(f"[{index}/{len(pages)}] {page_id} -> sin URL en Cover_s / Cover_v")
                skipped += 1
                continue

            if current_url == new_url:
                print(f"[{index}/{len(pages)}] {page_id} -> ya estaba actualizado")
                skipped += 1
                continue

            print(f"[{index}/{len(pages)}] {page_id} -> cover = {new_url}")

            if not DRY_RUN:
                update_cover_property(page_id, new_url)

            updated += 1

        except Exception as e:
            print(f"[{index}/{len(pages)}] ERROR en {page_id}: {e}")
            errors += 1

    print("\nResumen")
    print(f"  Actualizados: {updated}")
    print(f"  Saltados:     {skipped}")
    print(f"  Errores:      {errors}")


if __name__ == "__main__":
    main()