from datetime import datetime
import traceback
from flask import Blueprint, render_template, jsonify, request
from app.services.main_service import MainService
from app.services.auction_service import AuctionService
from flask_login import login_required, current_user
import os
from flask import session


auction_controller = Blueprint("auction_controller", __name__)


@auction_controller.route("/auctions")
# @login_required
def auctions():
    message = MainService().get_message()
    message = f"{message} {current_user.name}"
    return render_template("index.html", message=message)


@auction_controller.route("/auctions/<string:auction_id>")
def auction_details(auction_id):
    try:
        # Fetch the target auction
        target_auction = AuctionService().get_target_auction(auction_id)

        if target_auction is None:
            return "Auction not found", 404

        # Fetch WebSocket URL from the environment
        websocket_url = os.getenv("WEB_SOCKET_URL")
        if not websocket_url:
            return "WebSocket URL not configured", 500

        # Simulate a user ID for testing purposes
        user_id = current_user.id

        # Convert start_time and end_time to datetime object
        start_time_str = target_auction.get("start_time")
        # end_time_str = target_auction.get("end_time")
        start_time = None
        # end_time = None
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                # Log the error and keep `start_time` as None
                print(f"Error parsing start_time: {e}")
        # if end_time_str:
        #     try:
        #         end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        #     except ValueError as e:
        #         # Log the error and keep `end_time` as None
        #         print(f"Error parsing end_time: {e}")

        # Pass data to the frontend
        return render_template(
            "auction_details.html",
            auction=target_auction,
            websocket_url=websocket_url,
            user_id=user_id,
            auction_id=auction_id,
            start_time=start_time,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# def auction_details(auction_id):
#     # target_auction = AuctionService().get_auction(auction_id)

#     # if target_auction is None:
#     #     return "Auction not found", 404

#     # return render_template("auction_details.html", auction=target_auction)
#     try:
#         # Fetch the target auction
#         target_auction = AuctionService().get_target_auction(auction_id)

#         if target_auction is None:
#             return "Auction not found", 404

#         # Fetch WebSocket URL from the environment
#         websocket_url = os.getenv("WEB_SOCKET_URL")
#         if not websocket_url:
#             return "WebSocket URL not configured", 500

#         # Simulate a user ID for testing purposes
#         user_id = current_user.id

#         # Pass data to the frontend
#         return render_template(
#             "auction_details.html",
#             auction=target_auction,
#             websocket_url=websocket_url,
#             user_id=user_id,
#             auction_id=auction_id,
#         )
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@auction_controller.route("/create")
@login_required
def open_create_auction():
    return render_template("create-auction-page.html")


@auction_controller.route("/api/get-auctions", methods=["GET"])
@login_required
def get_auctions():
    user_id = None
    try:
        if request.method == "GET":
            mode = request.args.get("mode")
            if mode == "my_auctions":
                user_id = session.get("user_id")

        else:
            return jsonify({"error": "Method Not Allowed"}), 405

        # if mode != "my_auctions":
        #     return jsonify({"error": "Fetching auctions is not implemented yet."}), 501

        response = AuctionService.get_auctions(mode, user_id)
        if response.get("status") == "success":
            return jsonify(response.get("data")), 200
        else:
            return (
                jsonify(
                    {
                        "error": response.get("error", "Failed to fetch auctions."),
                        "details": response.get("details"),
                    }
                ),
                response.get("status_code", 500),
            )

    except Exception as e:
        print("Exception occurred while fetching auctions:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@auction_controller.route("/create-auction", methods=["POST"])
# @login_required
def create_auction():
    datetime_format = "%Y-%m-%d %H:%M"
    try:
        start_date = request.form.get("start_date")
        start_time = request.form.get("start_time")
        start_datetime = f"{start_date} {start_time}"
        end_date = request.form.get("end_date")
        end_time = request.form.get("end_time")
        end_datetime = f"{end_date} {end_time}"
        image_file = request.files.getlist("images")

        auction_data = {
            "auction_item": request.form.get("auction_item"),
            "auction_desc": request.form.get("auction_desc"),
            "base_price": float(request.form.get("base_price")),
            "start_time": datetime.strptime(
                start_datetime, datetime_format
            ).isoformat(),
            "end_time": datetime.strptime(end_datetime, datetime_format).isoformat(),
            "default_time_increment": int(
                request.form.get("default_time_increment", 5)
            ),
            "default_time_increment_before": int(
                request.form.get("default_time_increment_before", 5)
            ),
            "stop_snipes_after": int(request.form.get("stop_snipes_after", 10)),
            "images": image_file,
        }

        # Call the service to create auction
        response = AuctionService().create_auction(auction_data)
        if response.get("status_code") == 201:
            return jsonify({"message": "Auction created successfully!"}), 200
        else:
            return (
                jsonify(
                    {"error": "Failed to create auction", "details": response.json()}
                ),
                response.status_code,
            )

    except Exception as e:
        print("Exception occurred:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@auction_controller.route("/get-websocket-url", methods=["GET"])
def get_websocket_url():
    """
    Expose the WebSocket URL from the .env file for frontend use.
    """
    websocket_url = os.getenv("WEB_SOCKET_URL")
    if websocket_url:
        return jsonify({"websocket_url": websocket_url}), 200
    else:
        return jsonify({"error": "WebSocket URL not found"}), 500


@auction_controller.route("/user-details", methods=["GET"])
@login_required
def get_user_details():
    """
    Fetch and return user details to the frontend.
    """
    try:
        user_details = {
            "id": current_user.id,
            "email": session.get("email"),
            "name": session.get("name"),
        }
        return jsonify(user_details), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
