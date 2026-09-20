import unittest

from app import create_app


class QrGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_qr_page_loads(self):
        response = self.client.get("/qr-generator")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"QR Generator", response.data)

    def test_qr_generation_with_text(self):
        response = self.client.post("/qr-generator", data={"qr_text": "https://example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data:image/png;base64", response.data)

    def test_qr_generation_with_circular_dots(self):
        response = self.client.post(
            "/qr-generator",
            data={"qr_text": "https://example.com", "circular_qr": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data:image/png;base64", response.data)


if __name__ == "__main__":
    unittest.main()
