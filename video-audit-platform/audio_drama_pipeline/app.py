import os

from flask import Flask
from flask_cors import CORS

from .config import Config
from .routes import init_app as init_routes


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    os.makedirs(app.config["DOWNLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["WORK_FOLDER"], exist_ok=True)
    os.makedirs(app.config["MEMORY_FOLDER"], exist_ok=True)

    CORS(app)
    init_routes(app)
    return app
