import unittest
from unittest.mock import patch

from app import create_app


class GifMakerTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_gif_maker_page_loads(self):
        response = self.client.get("/gif-maker")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"GIF Maker", response.data)

    @patch("app.routes._video_to_gif", return_value=b"GIF89a")
    def test_gif_maker_video_upload(self, mock_convert):
        import io

        response = self.client.post(
            "/gif-maker",
            data={"video": (io.BytesIO(b"video"), "clip.mp4")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data:image/gif;base64,R0lGODlh", response.data)
        mock_convert.assert_called_once()

    @patch("app.routes._photos_to_gif", return_value=b"GIF89a")
    def test_gif_maker_photo_upload(self, mock_convert):
        import io

        response = self.client.post(
            "/gif-maker",
            data={"photos": [(io.BytesIO(b"photo one"), "first.png"), (io.BytesIO(b"photo two"), "second.jpg")]},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data:image/gif;base64,R0lGODlh", response.data)
        mock_convert.assert_called_once()

    def test_gif_maker_rejects_unsupported_file_type(self):
        import io

        response = self.client.post(
            "/gif-maker",
            data={"video": (io.BytesIO(b"video"), "clip.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MP4, MOV, AVI, MKV, or WebM", response.data)


if __name__ == "__main__":
    unittest.main()