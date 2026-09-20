from flask import Flask

from app.config import Config
from app.routes import init_routes


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_routes(app)
    return app
