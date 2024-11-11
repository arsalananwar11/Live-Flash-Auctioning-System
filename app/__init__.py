from flask import Flask, render_template
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

    @app.route("/")
    def index():
        return render_template(
            "index.html", message="Welcome to Live Flash Auctioning System"
        )

    # Dashboard route
    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    app.register_blueprint(main)

    return app
