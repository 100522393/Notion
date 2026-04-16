from google import genai
from notion_client import Client
import json
import sys
import requests
import constants as c

_data_source_cache = {}

notion = Client(auth=c.NOTION_TOKEN)

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

    # 1) Probar si ya es un data source válido
    try:
        notion.data_sources.retrieve(data_source_id=database_or_data_source_id)
        _data_source_cache[database_or_data_source_id] = database_or_data_source_id
        return database_or_data_source_id
    except Exception:
        pass

    # 2) Si no, intentar resolverlo desde una database antigua
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

def create_page_in_data_source(database_or_data_source_id, properties):
    ds_id = resolver_data_source_id(database_or_data_source_id)
    return notion.pages.create(
        parent={"data_source_id": ds_id},
        properties=properties
    )

def normalize_id(value: str) -> str:
    return value.strip()

def actualizar_multimedia(cover_url, page_id, nombre, type):
    # TODO: Una vez compruebe que esto funciona lo meto a un archivo que voy a usar en pelis series y juegos como funcion
    nueva_pagina = {
        "Nombre": {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": nombre
                        }
                    }
                ]
            },
        type: {
            "relation": [
                {"id": normalize_id(page_id)}
            ]
        },
        "Cover": {
            "files": [
                {
                    "name": "cover.jpg",
                    "type": "external",
                    "external": {
                        "url": cover_url
                    }
                }

            ]
        }
    }
    create_page_in_data_source(
        c.MULTIMEDIA_DATABASE_ID,
        properties=nueva_pagina
    )

    print(f"Página de {nombre} creada exitosamente en Notion.")