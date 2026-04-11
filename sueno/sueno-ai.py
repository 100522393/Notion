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