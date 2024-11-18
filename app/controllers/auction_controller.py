from datetime import datetime
from flask import Blueprint, render_template, jsonify, session, request
from app.services.main_service import MainService
from flask_login import login_required, current_user
from app.models import Auction
from sqlalchemy.orm import joinedload

auction_controller = Blueprint("auction_controller", __name__)


@auction_controller.route("/auctions")
@login_required
def auctions():
    message = MainService().get_message()
    message = f"{message} {current_user.name}"
    return render_template("index.html", message=message)


@auction_controller.route("/auction_details/<int:auction_id>")
def auction_details(auction_id):
    return render_template("auctiondetails.html")


@auction_controller.route("/get-auction/<mode>", methods=["GET"])
def get_auctions(mode="all_auctions"):
    try:
        # Get the current user if the mode is 'my_auctions'
        user_id = request.args.get("user_id")
        
        if mode == "all_auctions":
            # Fetch all auctions
            auctions = Auction.query.options(
                joinedload(Auction.interests),  # Eager load auction interests (users interested)
                joinedload(Auction.winners),  # Eager load auction winners (users who won)
            ).all()

        elif mode == "upcoming_auctions":
            # Fetch all auctions where the end_time is in the future
            auctions = Auction.query.options(
                joinedload(Auction.interests),
                joinedload(Auction.winners),
            ).filter(Auction.end_time > datetime.utcnow()).all()

        elif mode == "my_auctions" and user_id:
            # Fetch auctions created by the current user (assuming user_id is passed in the request)
            auctions = Auction.query.options(
                joinedload(Auction.interests),
                joinedload(Auction.winners),
            ).filter(Auction.created_by == user_id).all()

        else:
            # Return an error if the mode is not recognized or if user_id is missing in 'my_auctions'
            return jsonify({"error": "Invalid mode or missing user_id for 'my_auctions'"}), 400

        # Prepare the response data
        result = []
        for auction in auctions:
            auction_data = {
                "auction_id": auction.auction_id,
                "auction_item": auction.auction_item,
                "base_price": auction.base_price,
                "start_time": auction.start_time,
                "end_time": auction.end_time,
                "default_time_increment": auction.default_time_increment,
                "default_time_increment_before": auction.default_time_increment_before,
                "auction_desc": auction.auction_desc,
                "is_active": auction.is_active,
                "created_by": auction.created_by,
                "created_on": auction.created_on,
                "modified_on": auction.modified_on,
                "stop_snipes_after": auction.stop_snipes_after,
                "interests": [
                    {"user_id": interest.user_id, "user_name": interest.user.user_name}
                    for interest in auction.interests
                ],  # Get interested users
                "winners": [
                    {"user_id": winner.user_id, "user_name": winner.user.user_name}
                    for winner in auction.winners
                ],  # Get winning users
            }
            result.append(auction_data)

        # Return the data as JSON
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
