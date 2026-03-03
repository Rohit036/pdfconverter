import io
import logging
import os
import threading
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from flask import Flask, request as flask_request
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MEDIA_DOWNLOAD_TIMEOUT = 30  # seconds

flask_app = Flask(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "👋 Hello! Send me any image and I will convert it to a PDF file for you!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the /help command is issued."""
    await update.message.reply_text(
        "📸 Just send me an image (photo) and I will send back a PDF version of it.\n\n"
        "Supported formats: JPEG, PNG, BMP, GIF, TIFF, WEBP"
    )


async def convert_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert a Telegram photo (compressed) to PDF and send it back."""
    await update.message.reply_text("⏳ Converting your image to PDF...")

    photo_file = await update.message.photo[-1].get_file()
    image_data = await photo_file.download_as_bytearray()

    try:
        pdf_bytes = _image_bytes_to_pdf(image_data)
    except Exception as exc:
        logger.error("Failed to convert photo: %s", exc)
        await update.message.reply_text(
            "❌ Sorry, I could not convert that image. Please try again with a different photo."
        )
        return

    await update.message.reply_document(
        document=pdf_bytes,
        filename="converted.pdf",
        caption="✅ Here is your PDF!",
    )


async def convert_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert an image sent as a document (uncompressed) to PDF and send it back."""
    mime = update.message.document.mime_type or ""
    if not mime.startswith("image/"):
        await update.message.reply_text(
            "⚠️ Please send an image file (JPEG, PNG, etc.)."
        )
        return

    await update.message.reply_text("⏳ Converting your image to PDF...")

    doc_file = await update.message.document.get_file()
    image_data = await doc_file.download_as_bytearray()

    try:
        pdf_bytes = _image_bytes_to_pdf(image_data)
    except Exception as exc:
        logger.error("Failed to convert document: %s", exc)
        await update.message.reply_text(
            "❌ Sorry, I could not convert that image. Please try again with a different file."
        )
        return

    await update.message.reply_document(
        document=pdf_bytes,
        filename="converted.pdf",
        caption="✅ Here is your PDF!",
    )


def _image_bytes_to_pdf(image_data: bytearray) -> io.BytesIO:
    """Convert raw image bytes to a PDF and return it as a BytesIO object.

    Raises:
        PIL.UnidentifiedImageError: If the data is not a recognisable image.
        OSError: If the image cannot be read.
    """
    image = Image.open(io.BytesIO(image_data))
    image.verify()  # detect truncated/corrupt files early
    # Re-open after verify() (verify() leaves the file pointer in an unusable state)
    image = Image.open(io.BytesIO(image_data))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    pdf_bytes = io.BytesIO()
    image.save(pdf_bytes, format="PDF")
    pdf_bytes.seek(0)
    return pdf_bytes


def send_whatsapp_message(to: str, body: str) -> None:
    """Send a WhatsApp text message via Twilio."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_WHATSAPP_NUMBER")
    if not all([account_sid, auth_token, from_number]):
        logger.error("Twilio credentials are not fully configured.")
        return
    client = TwilioClient(account_sid, auth_token)
    client.messages.create(body=body, from_=from_number, to=to)


def send_whatsapp_pdf(to: str, media_url: str) -> None:
    """Send a WhatsApp message with a PDF media URL via Twilio.

    Note: Twilio requires a publicly accessible URL to deliver media.
    In production, host the converted PDF at a public URL and pass it here.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_WHATSAPP_NUMBER")
    if not all([account_sid, auth_token, from_number]):
        logger.error("Twilio credentials are not fully configured.")
        return
    client = TwilioClient(account_sid, auth_token)
    client.messages.create(
        body="✅ Here is your PDF!",
        from_=from_number,
        to=to,
        media_url=[media_url],
    )


def handle_whatsapp_media(media_url: str, account_sid: str, auth_token: str) -> io.BytesIO:
    """Download media from Twilio and convert it to a PDF BytesIO object."""
    parsed = urlparse(media_url)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".twilio.com"):
        raise ValueError(f"Refusing to fetch media from untrusted host: {parsed.hostname!r}")
    response = requests.get(media_url, auth=(account_sid, auth_token), timeout=MEDIA_DOWNLOAD_TIMEOUT)
    response.raise_for_status()
    return _image_bytes_to_pdf(bytearray(response.content))


@flask_app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages from Twilio."""
    incoming_msg = flask_request.values.get("Body", "").strip().lower()
    from_number = flask_request.values.get("From", "")
    num_media = int(flask_request.values.get("NumMedia", 0))

    resp = MessagingResponse()

    if incoming_msg in ("help", "/help"):
        resp.message(
            "📸 Send me an image via WhatsApp and I will convert it to a PDF for you!\n\n"
            "Supported formats: JPEG, PNG, BMP, GIF, TIFF, WEBP"
        )
        return str(resp)

    if num_media == 0:
        resp.message(
            "👋 Hello! Send me any image and I will convert it to a PDF file for you!\n"
            "Type 'help' for more information."
        )
        return str(resp)

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    errors = []
    converted = 0
    for i in range(num_media):
        media_url = flask_request.values.get(f"MediaUrl{i}", "")
        media_type = flask_request.values.get(f"MediaContentType{i}", "")
        if not media_type.startswith("image/"):
            continue
        try:
            handle_whatsapp_media(media_url, account_sid, auth_token)
            send_whatsapp_pdf(from_number, media_url)
            converted += 1
        except Exception as exc:
            logger.error("Failed to convert WhatsApp media %s: %s", media_url, exc)
            errors.append(str(exc))

    if errors and converted == 0:
        resp.message("❌ Sorry, I could not convert that image. Please try again with a different photo.")
    elif converted == 0:
        resp.message("⚠️ Please send an image file (JPEG, PNG, etc.).")

    return str(resp)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Copy .env.example to .env and fill in your bot token."
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, convert_photo))
    application.add_handler(
        MessageHandler(filters.Document.IMAGE, convert_document)
    )

    port = int(os.environ.get("PORT", 5000))
    # NOTE: Flask's built-in server is used here for simplicity.
    # For production, run with a WSGI server (e.g. gunicorn) instead of threading.
    flask_thread = threading.Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=port),
        # Daemon thread: terminates when the main thread exits.
        # Active WhatsApp requests may be interrupted on shutdown.
        daemon=True,
    )
    flask_thread.start()
    logger.info("Flask server started on port %d.", port)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
