from flask import Blueprint, render_template
from app.services.main_service import MainService
from app.services.auction_service import AuctionService
from flask_login import login_required, current_user

auction_controller = Blueprint("auction_controller", __name__)

@auction_controller.route("/auctions")
@login_required
def auctions():
    message = MainService().get_message()
    message = f"{message} {current_user.name}"
    return render_template("index.html", message=message)


@auction_controller.route("/auctions/<string:auction_id>")
def auction_details(auction_id):
    target_auction = AuctionService().get_auction(auction_id)

    if target_auction is None:
        return "Auction not found", 404

    return render_template("auctiondetails.html", auction=target_auction)