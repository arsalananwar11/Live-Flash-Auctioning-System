from flask import (
    Blueprint,
    render_template,
    request,
    current_app,
    session,
    redirect,
    url_for,
)

import requests
import jwt
from flask_login import (
    UserMixin,
    login_user,
    logout_user,
    current_user,
)
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.models.db_models import Users  # Import your Users model
from app.models import db  # Import your SQLAlchemy database instance

login_controller = Blueprint("login_controller", __name__)


class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name


@login_controller.route("/login")
def login():
    """Redirect the user to Cognito's Hosted UI for authentication."""
    return redirect(current_app.config["COGNITO_HOSTED_LOGIN_URL"])


@login_controller.route("/callback")
def callback():
    """
    Handle the redirect from the Cognito Hosted UI.
    Extract the token from the URL fragment and validate it.
    """
    token = request.args.get("id_token")
    print(f"Token received: {token}")
    if token:
        _, status_code = decode_cognito_token(token)
        if status_code == 200:
            print(session)
            session["access_token"] = token

            # Log user in
            user_id = session["user_id"]
            # user_email = session["email"]
            user_name = session["name"]

            # Insert or update the user in the RDS database
            existing_user = Users.query.filter_by(user_id=user_id).first()
            if not existing_user:
                # Insert new user
                new_user = Users(user_id=user_id, user_name=user_name)
                db.session.add(new_user)
                print(f"New user added: {user_name}")
            else:
                # Update existing user's name (if needed)
                if existing_user.user_name != user_name:
                    existing_user.user_name = user_name
                    print(f"User updated: {user_name}")

            db.session.commit()  # Save changes to the database

            # Log user in
            user = User(
                id=session["user_id"], email=session["email"], name=session["name"]
            )
            login_user(user)
            return redirect(url_for("main_controller.open_dashboard"))

    return render_template("callback.html")


@login_controller.route("/logout")
def logout():
    """Log out the user by clearing the session and redirecting to the landing page."""
    session.clear()
    logout_user()
    return redirect(url_for("main_controller.index"))


def decode_cognito_token(token):
    try:

        # Fetch the public keys from Cognito
        jwk_url = f"https://cognito-idp.{current_app.config['COGNITO_REGION']}.amazonaws.com/{current_app.config['COGNITO_USERPOOL_ID']}/.well-known/jwks.json"
        response = requests.get(jwk_url)
        jwks = response.json()

        # Get the 'kid' from the token header
        headers = jwt.get_unverified_header(token)
        kid = headers["kid"]

        # Find the matching key
        key = next(k for k in jwks["keys"] if k["kid"] == kid)

        # Convert JWK to public key
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)

        # Decode and verify the token
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=current_app.config["COGNITO_APP_CLIENT_ID"],
        )
        # print(f"Decoded Token: {decoded_token}")
        user_id = decoded_token.get("sub")
        email = decoded_token.get("email")
        name = decoded_token.get("name")

        session["user_id"] = user_id
        session["email"] = email
        session["name"] = name
        return "Token decoded successfully", 200
    except ExpiredSignatureError:
        return "The token has expired", 401
    except InvalidTokenError as e:
        return f"Invalid token: {str(e)}", 401
    except Exception as e:
        return f"An error occurred: {str(e)}", 500


@login_controller.route("/home")
def home():
    if current_user.is_authenticated:
        if "access_token" in session:
            return redirect(url_for("main_controller.open_dashboard"))

    return redirect(url_for("login_controller.login"))
