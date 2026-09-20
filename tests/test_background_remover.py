import io
import unittest
from unittest.mock import patch

from app import create_app
from app.routes import _smart_background_remove


class BackgroundRemoverTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_background_remover_page_loads(self):
        response = self.client.get("/background-remover")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Background Remover", response.data)

    def test_background_remover_upload(self):
        image_data = io.BytesIO()
        from PIL import Image

        image = Image.new("RGB", (50, 50), color="red")
        image.save(image_data, format="PNG")
        image_data.seek(0)

        response = self.client.post(
            "/background-remover",
            data={"image": (image_data, "test.png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data:image/png;base64", response.data)

    @patch("app.routes.remove")
    def test_background_remover_uses_native_soft_mask(self, mock_remove):
        from PIL import Image

        image = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        mock_remove.return_value = image

        output = _smart_background_remove(image)

        self.assertEqual(output.mode, "RGBA")
        mock_remove.assert_called_once_with(
            image,
            alpha_matting=False,
        )


if __name__ == "__main__":
    unittest.main()
