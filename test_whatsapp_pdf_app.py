import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import whatsapp_pdf_app


class WhatsAppPdfAppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(whatsapp_pdf_app.app)

    def test_health_endpoint(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_whatsapp_greeting_without_media(self):
        response = self.client.post("/whatsapp", data={"Body": "hello", "NumMedia": "0"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Send me an image on WhatsApp", response.text)

    def test_whatsapp_uses_railway_public_domain_for_pdf_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "sample.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")

            with patch.dict(
                "os.environ",
                {"PUBLIC_BASE_URL": "", "RAILWAY_PUBLIC_DOMAIN": "demo.up.railway.app"},
                clear=False,
            ):
                with patch.object(
                    whatsapp_pdf_app, "download_twilio_media", return_value=b"image-bytes"
                ), patch.object(whatsapp_pdf_app, "image_bytes_to_pdf", return_value=pdf_path):
                    response = self.client.post(
                        "/whatsapp",
                        data={
                            "Body": "",
                            "NumMedia": "1",
                            "MediaContentType0": "image/png",
                            "MediaUrl0": "https://api.twilio.com/test-media",
                        },
                    )

        self.assertEqual(response.status_code, 200)
        self.assertIn("https://demo.up.railway.app/files/sample.pdf", response.text)

    def test_whatsapp_returns_clear_error_without_public_url(self):
        with patch.dict(
            "os.environ",
            {"PUBLIC_BASE_URL": "", "RAILWAY_PUBLIC_DOMAIN": "", "RAILWAY_STATIC_URL": ""},
            clear=False,
        ):
            with patch.object(
                whatsapp_pdf_app, "download_twilio_media", return_value=b"image-bytes"
            ), patch.object(
                whatsapp_pdf_app, "image_bytes_to_pdf", return_value=Path("generated_pdfs/test.pdf")
            ):
                response = self.client.post(
                    "/whatsapp",
                    data={
                        "Body": "",
                        "NumMedia": "1",
                        "MediaContentType0": "image/png",
                        "MediaUrl0": "https://api.twilio.com/test-media",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Set PUBLIC_BASE_URL", response.text)


if __name__ == "__main__":
    unittest.main()
