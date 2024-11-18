from flask import Flask
from app.controllers import login_controller, main_controller, auction_controller
from dotenv import load_dotenv
import os
from flask_migrate import Migrate
from app.models import db

# Load environment variables from .env file
load_dotenv()


def create_app():
    app = Flask(__name__)

    # Set configuration from environment variables
    app.config.update(
        {
            "SECRET_KEY": os.getenv("SECRET_KEY"),
            "COGNITO_REGION": os.getenv("COGNITO_REGION"),
            "COGNITO_USERPOOL_ID": os.getenv("COGNITO_USER_POOL_ID"),
            "COGNITO_APP_CLIENT_ID": os.getenv("COGNITO_CLIENT_ID"),
            "COGNITO_DOMAIN": os.getenv("COGNITO_DOMAIN"),
            "COGNITO_CHECK_TOKEN_EXPIRATION": os.getenv(
                "COGNITO_CHECK_TOKEN_EXPIRATION"
            ),
            "COGNITO_JWT_HEADER_NAME": os.getenv("COGNITO_JWT_HEADER_NAME"),
            "COGNITO_JWT_HEADER_PREFIX": os.getenv("COGNITO_JWT_HEADER_PREFIX"),
            "COGNITO_REDIRECT_URI": os.getenv("COGNITO_REDIRECT_URI"),
            "COGNITO_HOSTED_LOGIN_URL": (
                f"https://{os.getenv('COGNITO_DOMAIN')}/login"
                f"?client_id={os.getenv('COGNITO_CLIENT_ID')}"
                "&response_type=token"
                "&scope=email+openid+phone"
                f"&redirect_uri={os.getenv('COGNITO_REDIRECT_URI')}/callback"
            ),
            "COGNITO_HOSTED_LOGOUT_URL": (
                f"https://{os.getenv('COGNITO_DOMAIN')}/logout?"
                f"client_id={os.getenv('COGNITO_CLIENT_ID')}"
                f"&response_type=token"
                f"&redirect_uri={os.getenv('COGNITO_REDIRECT_URI')}"
            ),
            "SQLALCHEMY_DATABASE_URI": os.getenv("SQLALCHEMY_DATABASE_URI"),
            "SQLALCHEMY_TRACK_MODIFICATIONS": os.getenv(
                "SQLALCHEMY_TRACK_MODIFICATIONS"
            ),
        }
    )

    # Initialize the database
    db.init_app(app)
    migrate = Migrate(app, db)  # noqa

    # Register Blueprints
    app.register_blueprint(login_controller)
    app.register_blueprint(main_controller)
    app.register_blueprint(auction_controller)

    return app
