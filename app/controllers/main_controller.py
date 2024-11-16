from flask import Blueprint, render_template
from app.services.main_service import MainService
from flask_login import login_required

main_controller = Blueprint("main_controller", __name__)


@main_controller.route("/")
def index():
    message = MainService().get_message()
    return render_template("index.html", message=message)


@main_controller.route("/status")
@login_required
def status():
    message = MainService().get_message(
        "The auction system is live and responding to requests!"
    )
    return render_template("index.html", message=message)
