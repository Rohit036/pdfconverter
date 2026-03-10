import io
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

import whatsapp_pdf_app


def make_image_bytes(color: str, size: tuple[int, int] = (16, 16)) -> bytes:
    image = Image.new("RGB", size, color=color)
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    return image_bytes.getvalue()


class WhatsAppPdfAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(whatsapp_pdf_app.app)
        self.temp_dir = tempfile.mkdtemp()
        self.original_output_dir = whatsapp_pdf_app.OUTPUT_DIR
        self.original_public_base_url = whatsapp_pdf_app.PUBLIC_BASE_URL
        whatsapp_pdf_app.OUTPUT_DIR = Path(self.temp_dir)
        whatsapp_pdf_app.OUTPUT_DIR.mkdir(exist_ok=True)
        whatsapp_pdf_app.PUBLIC_BASE_URL = "https://example.com"
        whatsapp_pdf_app.USER_MODES.clear()

    def tearDown(self) -> None:
        whatsapp_pdf_app.OUTPUT_DIR = self.original_output_dir
        whatsapp_pdf_app.PUBLIC_BASE_URL = self.original_public_base_url
        whatsapp_pdf_app.USER_MODES.clear()
        shutil.rmtree(self.temp_dir)

    def test_greeting_shows_both_conversion_options(self) -> None:
        response = self.client.post(
            "/whatsapp",
            data={"Body": "hello", "From": "whatsapp:+10000000000", "NumMedia": "0"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Single page conversion", response.text)
        self.assertIn("Multipage conversion", response.text)

    def test_single_page_mode_creates_one_pdf_per_uploaded_image(self) -> None:
        sender = "whatsapp:+10000000001"
        self.client.post("/whatsapp", data={"Body": "1", "From": sender, "NumMedia": "0"})

        with patch.object(
            whatsapp_pdf_app,
            "download_twilio_media",
            side_effect=[make_image_bytes("red"), make_image_bytes("blue")],
        ):
            response = self.client.post(
                "/whatsapp",
                data={
                    "Body": "",
                    "From": sender,
                    "NumMedia": "2",
                    "MediaUrl0": "https://api.twilio.com/image-1",
                    "MediaContentType0": "image/png",
                    "MediaUrl1": "https://api.twilio.com/image-2",
                    "MediaContentType1": "image/png",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.count("<Media>https://example.com/files/"), 2)
        self.assertEqual(len(list(whatsapp_pdf_app.OUTPUT_DIR.glob("*.pdf"))), 2)

    def test_multipage_mode_merges_uploaded_images_into_one_pdf(self) -> None:
        sender = "whatsapp:+10000000002"
        self.client.post("/whatsapp", data={"Body": "2", "From": sender, "NumMedia": "0"})

        with patch.object(
            whatsapp_pdf_app,
            "download_twilio_media",
            side_effect=[
                make_image_bytes("green", size=(16, 16)),
                make_image_bytes("yellow", size=(18, 18)),
            ],
        ):
            response = self.client.post(
                "/whatsapp",
                data={
                    "Body": "",
                    "From": sender,
                    "NumMedia": "2",
                    "MediaUrl0": "https://api.twilio.com/image-1",
                    "MediaContentType0": "image/png",
                    "MediaUrl1": "https://api.twilio.com/image-2",
                    "MediaContentType1": "image/png",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("merged PDF", response.text)
        self.assertEqual(response.text.count("<Media>https://example.com/files/"), 1)

        pdf_files = list(whatsapp_pdf_app.OUTPUT_DIR.glob("*.pdf"))
        self.assertEqual(len(pdf_files), 1)
        page_markers = re.findall(rb"/Type /Page\b", pdf_files[0].read_bytes())
        self.assertGreaterEqual(len(page_markers), 2)


if __name__ == "__main__":
    unittest.main()
