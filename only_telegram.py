import io
import logging
import os

from dotenv import load_dotenv
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


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

    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()