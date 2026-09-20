import io
import unittest

from app import create_app


class ColorExtractorTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_color_extractor_page_loads(self):
        response = self.client.get("/color-extractor")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Color Extractor", response.data)

    def test_color_extractor_upload(self):
        image_data = io.BytesIO()
        from PIL import Image

        image = Image.new("RGB", (50, 50), color=(255, 0, 0))
        image.save(image_data, format="PNG")
        image_data.seek(0)

        response = self.client.post(
            "/color-extractor",
            data={"image": (image_data, "test.png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"#", response.data)


if __name__ == "__main__":
    unittest.main()
