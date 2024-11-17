from flask import Blueprint, render_template
from app.services.main_service import MainService
from flask_login import login_required, current_user

auction_controller = Blueprint("auction_controller", __name__)


@auction_controller.route("/auctions")
@login_required
def auctions():
    message = MainService().get_message()
    message = f"{message} {current_user.name}"
    return render_template("index.html", message=message)
