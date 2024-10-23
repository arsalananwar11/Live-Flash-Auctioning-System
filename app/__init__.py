from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


def create_app():
    app = Flask(__name__)

    # Load configuration from environment variables
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # Register blueprints for controllers
    from app.controllers.main_controller import main

    app.register_blueprint(main)

    return app
