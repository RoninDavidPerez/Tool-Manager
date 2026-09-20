import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
