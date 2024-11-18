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

@auction_controller.route("/auction_details/<int:auction_id>")
def auction_details(auction_id):
    print(f"Auction details for auction ID: {auction_id}")
    return render_template("auctiondetails.html")