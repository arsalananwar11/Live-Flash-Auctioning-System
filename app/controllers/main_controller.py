from datetime import datetime
import os
import traceback
import boto3
from flask import Blueprint, jsonify, render_template, request

from app.services.main_service import MainService
from flask_login import login_required


main_controller = Blueprint("main_controller", __name__)

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
s3_client = boto3.client("s3")


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


@main_controller.route("/get-presigned-url", methods=["POST"])
def get_presigned_url():
    try:
        data = request.json
        filename = data.get("filename")
        if not filename:
            return jsonify({"error": "Filename is required"}), 400

        # Generate pre-signed URL
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": filename},
            ExpiresIn=3600,
        )
        s3_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"

        return jsonify({"presigned_url": presigned_url, "s3_url": s3_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_controller.route("/create-auction", methods=["POST"])
@login_required
def create_auction():
    print("Creating auction...")
    datetime_format = "%Y-%m-%d %H:%M"

    try:
        # Collect form data
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
        # response from service
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
