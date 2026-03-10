import io
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

app = FastAPI()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "5000"))

OUTPUT_DIR = Path("generated_pdfs")
OUTPUT_DIR.mkdir(exist_ok=True)
USER_MODES = {}

OPTION_MESSAGE = (
    "👋 Choose a conversion option:\n"
    "1. Single page conversion - send one or more images and I will create one PDF per image.\n"
    "2. Multipage conversion - send one or more images and I will merge them into one PDF in upload order.\n\n"
    "Reply with 1 or 2 to continue."
)
MODE_ALIASES = {
    "1": "single",
    "single": "single",
    "single page": "single",
    "single page conversion": "single",
    "2": "multipage",
    "multi": "multipage",
    "multiple": "multipage",
    "multipage": "multipage",
    "multi page": "multipage",
    "multipage conversion": "multipage",
    "merge": "multipage",
}


def normalize_mode_choice(text: str) -> str | None:
    normalized = " ".join(text.lower().split())
    return MODE_ALIASES.get(normalized)


def build_option_message(current_mode: str | None = None) -> str:
    if current_mode == "single":
        return f"{OPTION_MESSAGE}\n\nCurrent mode: Single page conversion."
    if current_mode == "multipage":
        return f"{OPTION_MESSAGE}\n\nCurrent mode: Multipage conversion."
    return OPTION_MESSAGE


def load_pdf_ready_image(image_data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(image_data))
    image.verify()

    image = Image.open(io.BytesIO(image_data))
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def image_bytes_to_pdf(image_data: bytes) -> Path:
    image = load_pdf_ready_image(image_data)
    file_name = f"{uuid.uuid4().hex}.pdf"
    output_path = OUTPUT_DIR / file_name
    image.save(output_path, format="PDF")
    return output_path


def merge_images_to_pdf(image_data_list: list[bytes]) -> Path:
    if not image_data_list:
        raise ValueError("Please send at least one image file.")

    images = [load_pdf_ready_image(image_data) for image_data in image_data_list]
    file_name = f"{uuid.uuid4().hex}.pdf"
    output_path = OUTPUT_DIR / file_name
    first_image, *remaining_images = images
    first_image.save(
        output_path,
        format="PDF",
        save_all=True,
        append_images=remaining_images,
    )
    return output_path


def download_twilio_media(media_url: str) -> bytes:
    parsed = urlparse(media_url)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".twilio.com"):
        raise ValueError("Untrusted media URL")
    if not ACCOUNT_SID or not AUTH_TOKEN:
        raise ValueError("Twilio credentials are not configured")

    response = requests.get(
        media_url,
        auth=(ACCOUNT_SID, AUTH_TOKEN),
        timeout=30,
    )
    response.raise_for_status()
    return response.content


@app.get("/")
def health():
    return JSONResponse({"ok": True})


@app.get("/files/{file_name}")
def serve_pdf(file_name: str):
    if file_name != Path(file_name).name or not file_name.lower().endswith(".pdf"):
        return JSONResponse({"error": "file not found"}, status_code=404)

    file_path = OUTPUT_DIR / file_name
    if not file_path.exists():
        return JSONResponse({"error": "file not found"}, status_code=404)

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_name,
    )


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    form_data = await request.form()

    num_media = int(form_data.get("NumMedia", 0))
    incoming_text = (form_data.get("Body") or "").strip()
    sender = (form_data.get("From") or "").strip()
    selected_mode = normalize_mode_choice(incoming_text)

    resp = MessagingResponse()

    if selected_mode and sender:
        USER_MODES[sender] = selected_mode

    if num_media == 0:
        if selected_mode == "single":
            resp.message(
                "Single page conversion selected. Send one or more images and I will reply with one PDF per image."
            )
        elif selected_mode == "multipage":
            resp.message(
                "Multipage conversion selected. Send one or more images and I will merge them into one PDF in upload order."
            )
        else:
            resp.message(build_option_message(USER_MODES.get(sender)))
        return Response(content=str(resp), media_type="application/xml")

    active_mode = selected_mode or USER_MODES.get(sender)
    if not active_mode:
        resp.message(f"Please choose a conversion option before sending images.\n\n{build_option_message()}")
        return Response(content=str(resp), media_type="application/xml")

    media_urls = []
    for index in range(num_media):
        media_type = form_data.get(f"MediaContentType{index}", "")
        media_url = form_data.get(f"MediaUrl{index}", "")
        if not media_type.startswith("image/"):
            resp.message("Please send image files only.")
            return Response(content=str(resp), media_type="application/xml")
        media_urls.append(media_url)

    try:
        image_data_list = [download_twilio_media(media_url) for media_url in media_urls]

        if active_mode == "single":
            for index, image_data in enumerate(image_data_list, start=1):
                pdf_path = image_bytes_to_pdf(image_data)
                pdf_url = build_pdf_url(pdf_path)
                message_text = "Here is your PDF." if len(image_data_list) == 1 else f"Here is PDF {index} of {len(image_data_list)}."
                message = resp.message(message_text)
                message.media(pdf_url)
        else:
            pdf_path = merge_images_to_pdf(image_data_list)
            pdf_url = build_pdf_url(pdf_path)
            message = resp.message(
                f"Here is your merged PDF with {len(image_data_list)} page(s)."
            )
            message.media(pdf_url)

    except Exception as exc:
        resp.message(f"Conversion failed: {exc}")

    return Response(content=str(resp), media_type="application/xml")


def build_pdf_url(pdf_path: Path) -> str:
    if not PUBLIC_BASE_URL:
        raise ValueError("PUBLIC_BASE_URL is not configured")
    return f"{PUBLIC_BASE_URL}/files/{pdf_path.name}"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("whatsapp_pdf_app:app", host="0.0.0.0", port=PORT, reload=True)
