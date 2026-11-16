from notion_client import Client

import constants as c

NOTION_TOKEN = c.NOTION_TOKEN
notion = Client(auth=NOTION_TOKEN)

CAPITULOS_DATABASE_ID = c.CAPITULOS_DATABASE_ID

_data_source_cache = {}


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

    try:
        notion.data_sources.retrieve(data_source_id=database_or_data_source_id)
        _data_source_cache[database_or_data_source_id] = database_or_data_source_id
        return database_or_data_source_id
    except Exception:
        pass

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


def query_data_source(database_or_data_source_id, filter_payload=None, start_cursor=None, page_size=100):
    ds_id = resolver_data_source_id(database_or_data_source_id)

    kwargs = {
        "data_source_id": ds_id,
        "page_size": page_size,
    }

    if filter_payload:
        kwargs["filter"] = filter_payload
    if start_cursor:
        kwargs["start_cursor"] = start_cursor

    return notion.data_sources.query(**kwargs)


def delete_unlinked_chapters():
    """
    Busca todas las filas en la tabla 'capitulos' donde la propiedad 'Serie' está vacía
    y las archiva.
    """
    try:
        all_results = []
        start_cursor = None

        while True:
            query_results = query_data_source(
                CAPITULOS_DATABASE_ID,
                filter_payload={
                    "property": "Serie",
                    "relation": {
                        "is_empty": True
                    }
                },
                start_cursor=start_cursor,
                page_size=100
            )

            results = query_results.get("results", [])
            all_results.extend(results)

            if not query_results.get("has_more"):
                break

            start_cursor = query_results.get("next_cursor")

        if not all_results:
            print("No se encontraron capítulos sin serie asignada.")
            return

        print(f"Se encontraron {len(all_results)} capítulos sin serie asignada. Iniciando la eliminación...")

        for page in all_results:
            page_id = page["id"]

            title_property = page["properties"].get("Nombre", {}).get("title", [])
            page_title = title_property[0]["plain_text"] if title_property else "Sin título"

            notion.pages.update(
                page_id=page_id,
                archived=True
            )
            print(f"Capítulo '{page_title}' (ID: {page_id}) eliminado.")

        print("\nProceso de limpieza completado exitosamente.")

    except Exception as e:
        print(f"Ocurrió un error: {e}")


delete_unlinked_chapters()
