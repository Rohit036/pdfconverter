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
PORT = int(os.getenv("PORT", "5000"))

OUTPUT_DIR = Path(__file__).resolve().parent / "generated_pdfs"
OUTPUT_DIR.mkdir(exist_ok=True)


def image_bytes_to_pdf(image_data: bytes) -> Path:
    image = Image.open(io.BytesIO(image_data))
    image.verify()

    image = Image.open(io.BytesIO(image_data))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    file_name = f"{uuid.uuid4().hex}.pdf"
    output_path = OUTPUT_DIR / file_name
    image.save(output_path, format="PDF")
    return output_path


def download_twilio_media(media_url: str) -> bytes:
    parsed = urlparse(media_url)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".twilio.com"):
        raise ValueError("Untrusted media URL")
    if not ACCOUNT_SID or not AUTH_TOKEN:
        raise RuntimeError("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN before downloading media")

    response = requests.get(
        media_url,
        auth=(ACCOUNT_SID, AUTH_TOKEN),
        timeout=30,
    )
    response.raise_for_status()
    return response.content


def get_public_base_url() -> str:
    public_base_url = os.getenv("PUBLIC_BASE_URL")
    railway_public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    railway_static_url = os.getenv("RAILWAY_STATIC_URL")

    if public_base_url:
        return public_base_url.rstrip("/")
    if railway_public_domain:
        return f"https://{railway_public_domain}".rstrip("/")
    if railway_static_url:
        return railway_static_url.rstrip("/")

    raise RuntimeError(
        "Set PUBLIC_BASE_URL or Railway public domain variables before sending PDFs"
    )


@app.get("/")
def health():
    return JSONResponse({"ok": True})


@app.get("/files/{file_name}")
def serve_pdf(file_name: str):
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

    resp = MessagingResponse()

    if num_media == 0:
        if incoming_text.lower() in {"hi", "hello", "hey"}:
            resp.message("Send me an image on WhatsApp and I will convert it to PDF.")
        else:
            resp.message("Please send an image. I will convert it to PDF and reply with the file.")
        return Response(content=str(resp), media_type="application/xml")

    media_type = form_data.get("MediaContentType0", "")
    media_url = form_data.get("MediaUrl0", "")

    if not media_type.startswith("image/"):
        resp.message("Please send an image file only.")
        return Response(content=str(resp), media_type="application/xml")

    try:
        image_data = download_twilio_media(media_url)
        pdf_path = image_bytes_to_pdf(image_data)
        pdf_url = f"{get_public_base_url()}/files/{pdf_path.name}"

        message = resp.message("Here is your PDF.")
        message.media(pdf_url)

    except Exception as exc:
        resp.message(f"Conversion failed: {exc}")

    return Response(content=str(resp), media_type="application/xml")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("whatsapp_pdf_app:app", host="0.0.0.0", port=PORT)
