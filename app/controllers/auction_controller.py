from flask import Blueprint, render_template, jsonify, request
from app.services.main_service import MainService
from app.services.auction_service import AuctionService
from flask_login import login_required, current_user
import os

auction_controller = Blueprint("auction_controller", __name__)


@auction_controller.route("/auctions")
# @login_required
def auctions():
    message = MainService().get_message()
    message = f"{message} {current_user.name}"
    return render_template("index.html", message=message)


@auction_controller.route("/auctions/<string:auction_id>")
def auction_details(auction_id):
    target_auction = AuctionService().get_auction(auction_id)

    if target_auction is None:
        return "Auction not found", 404

    return render_template("auction_details.html", auction=target_auction)


@auction_controller.route("/get-auctions/<mode>", methods=["GET"])
def get_auctions(mode="all_auctions"):
    try:
        # Get the current user if the mode is 'my_auctions'
        user_email = request.args.get("user_email")

        if mode == "all_auctions":
            # Fetch all auctions
            auctions = AuctionService().get_all_auctions()

        elif mode == "upcoming_auctions":
            # Fetch all auctions where the end_time is in the future
            auctions = AuctionService().get_upcoming_auctions()

        elif mode == "my_auctions" and user_email:
            # Fetch auctions created by the current user (assuming user_id is passed in the request)
            auctions = AuctionService().get_my_auctions(user_email)

        else:
            # Return an error if the mode is not recognized or if user_id is missing in 'my_auctions'
            return (
                jsonify(
                    {"error": "Invalid mode or missing user_email for 'my_auctions'"}
                ),
                400,
            )

        # Prepare the response data
        auctions_list = AuctionService().prepare_auction_data(auctions)

        # Return the data as JSON
        return jsonify(auctions_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auction_controller.route('/get-websocket-url', methods=['GET'])
def get_websocket_url():
    """
    Expose the WebSocket URL from the .env file for frontend use.
    """
    websocket_url = os.getenv('WEB_SOCKET_URL')
    if websocket_url:
        return jsonify({"websocket_url": websocket_url}), 200
    else:
        return jsonify({"error": "WebSocket URL not found"}), 500
