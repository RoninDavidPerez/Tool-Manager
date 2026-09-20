from pathlib import Path


def allowed_image_file(filename: str) -> bool:
    allowed_extensions = {"png", "jpg", "jpeg", "webp"}
    return Path(filename).suffix.lower().lstrip(".") in allowed_extensions


def allowed_video_file(filename: str) -> bool:
    allowed_extensions = {"mp4", "mov", "avi", "mkv", "webm"}
    return Path(filename).suffix.lower().lstrip(".") in allowed_extensions


def allowed_pdf_file(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".pdf"
