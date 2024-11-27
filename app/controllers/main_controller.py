from datetime import datetime
import traceback
from flask import Blueprint, jsonify, render_template, request, session
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


# Dashboard route
@main_controller.route("/dashboard")
@login_required
def open_dashboard():
    return render_template("dashboard.html")


# Dashboard route
@main_controller.route("/create")
@login_required
def open_create_auction():
    return render_template("create-auction-page.html")


@main_controller.route("/create-auction", methods=["POST"])
@login_required
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
        response = MainService().create_auction(auction_data)
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


@main_controller.route("/api/get-auctions", methods=["GET"])
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

        response = MainService().get_auctions(mode, user_id)
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
