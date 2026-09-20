import io
import unittest
from unittest.mock import patch

from app import create_app


class PdfToWordTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_pdf_to_word_page_loads(self):
        response = self.client.get("/pdf-to-word")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PDF to Word", response.data)

    @patch("app.routes._pdf_to_docx", return_value=b"PK\x03\x04")
    def test_pdf_to_word_upload(self, mock_convert):
        response = self.client.post(
            "/pdf-to-word",
            data={"pdf": (io.BytesIO(b"%PDF-1.4"), "document.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Download Word document", response.data)
        mock_convert.assert_called_once()

    def test_pdf_to_word_rejects_unsupported_file_type(self):
        response = self.client.post(
            "/pdf-to-word",
            data={"pdf": (io.BytesIO(b"text"), "document.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please upload a PDF file.", response.data)


if __name__ == "__main__":
    unittest.main()