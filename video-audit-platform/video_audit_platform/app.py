import os

from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import db
from .routes import init_app as init_routes


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    os.makedirs(app.config["DOWNLOAD_FOLDER"], exist_ok=True)

    CORS(app)
    db.init_app(app)
    init_routes(app)
    return app
