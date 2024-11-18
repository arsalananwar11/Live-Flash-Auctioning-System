import base64
from flask import Blueprint, jsonify, render_template, request
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
    try:
        # Get form data
        # product_name = request.form.get("product_name")
        # product_description = request.form.get("product_description")
        # start_date = request.form.get("start_date")
        # start_time = request.form.get("start_time")
        # end_date = request.form.get("end_date")
        # end_time = request.form.get("end_time")
        # initial_bid = request.form.get("initial_bid")
        # terms_accepted = request.form.get("terms")
        images_base64 = request.form.get(
            "images"
        )  # This will be a JSON string of Base64 images

        # Process the images
        if images_base64:
            images = eval(images_base64)  # Convert JSON string to Python list
            for i, img in enumerate(images):
                # Save images or process them
                with open(f"image_{i}.png", "wb") as f:
                    f.write(base64.b64decode(img))

        # print(f"product_name = {product_name} and product_description = {product_description}")
        # print(f"start_date  = {start_date} and start time = {start_time}")
        # print(f"end_date  = {end_date} and end time = {end_time}")
        # print(f"initial bi = {initial_bid}")

        # Perform any additional processing or database insertion
        return jsonify({"message": "Auction created successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
