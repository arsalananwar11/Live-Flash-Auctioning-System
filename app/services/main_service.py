import base64
from flask import session
import requests
import os

api_gateway_url = os.getenv("API_GATEWAY_URL")


class MainService:
    @staticmethod
    def get_message(message: str = None):
        if message:
            return str(message)
        return "Welcome to the Live Flash Auctioning System"

    @staticmethod
    def create_auction(auction_data):
        images_base64 = []
        for image in auction_data["images"]:
            image_base64 = base64.b64encode(image.read()).decode("utf-8")
            images_base64.append(image_base64)

        auction_payload = {
            "auction_item": auction_data["auction_item"],
            "auction_desc": auction_data["auction_desc"],
            "base_price": auction_data["base_price"],
            "start_time": auction_data["start_time"],
            "end_time": auction_data["end_time"],
            "default_time_increment": auction_data["default_time_increment"],
            "default_time_increment_before": auction_data[
                "default_time_increment_before"
            ],
            "stop_snipes_after": auction_data["stop_snipes_after"],
            "product_images": images_base64,
            "created_by": session["user_id"],
        }

        try:
            url = f"{api_gateway_url}/add-auction"
            response = requests.post(
                url, json=auction_payload, headers={"Content-Type": "application/json"}
            )

            try:
                response_data = response.json()

                if response.status_code == 201:
                    return {
                        "status": "success",
                        "status_code": 201,
                        "data": {
                            "auction_id": response_data["data"].get("auction_id"),
                            "message": response_data["data"].get(
                                "message", "Auction created successfully"
                            ),
                        },
                    }
                else:
                    return {
                        "status": "failure",
                        "status_code": response.status_code,
                        "error": response_data.get(
                            "status_message", "Unknown error occurred"
                        ),
                        "details": response_data,
                    }

            except ValueError:
                return {
                    "status": "failure",
                    "status_code": response.status_code,
                    "error": "Invalid JSON response",
                    "details": response.text,
                }

        except requests.exceptions.RequestException as e:
            return {"status": "failure", "error": "Request failed", "details": str(e)}
        

    @staticmethod
    def get_auctions(mode, user_id=None):
        try:
            if mode == "my_auctions":
                if not user_id:
                    return {
                        "status": "failure",
                        "status_code": 400,
                        "error": "Missing user_id for my_auction mode.",
                    }
                payload = {"user_id": user_id}
                params = {"mode": mode}
                response = requests.get(
                    f"{api_gateway_url}/get-auctions",
                    params=params,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            elif mode == "upcoming_auctions":
                params = {"mode": mode}
                response = requests.get(
                    f"{api_gateway_url}/get-auctions",
                    params=params,
                    headers={"Content-Type": "application/json"},
                )
            else:
                response = requests.get(
                    f"{api_gateway_url}/get-auctions",
                    headers={"Content-Type": "application/json"},
                )

            try:
                response_data = response.json()

                if response.status_code == 200:
                    return {
                        "status": "success",
                        "status_code": 200,
                        "data": response_data,
                    }
                else:
                    return {
                        "status": "failure",
                        "status_code": response.status_code,
                        "error": response_data.get(
                            "error", "Unknown error occurred while fetching auctions."
                        ),
                        "details": response_data,
                    }

            except ValueError:
                return {
                    "status": "failure",
                    "status_code": response.status_code,
                    "error": "Invalid JSON response from API.",
                    "details": response.text,
                }

        except requests.exceptions.RequestException as e:
            return {"status": "failure", "error": "Request to API Gateway failed.", "details": str(e)}
