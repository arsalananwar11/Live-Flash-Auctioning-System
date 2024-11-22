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
            "product_images": auction_data["images_base64"],
            "created_by": session["user_id"],
        }

        try:
            url = f"{api_gateway_url}/auctions"
            # print(f"url: {url}")
            # print(f"Creating auction with data: {auction_payload}")
            response = requests.post(
                url, json=auction_payload, headers={"Content-Type": "application/json"}
            )
            # print(f"Response: {response.status_code}")
            response.raise_for_status()
            response_data = response.json()

            if response.status_code == 201 and "auction_item" in response_data:
                return {
                    "status": "success",
                    "data": {
                        "auction_item": response_data["auction_item"],
                        "message": response_data.get(
                            "message", "Auction created successfully"
                        ),
                    },
                }
            else:
                return {
                    "status": "failure",
                    "error": "Auction creation failed",
                    "details": response_data,
                }

        except requests.exceptions.RequestException as e:
            return {"status": "failure", "error": "Request failed", "details": str(e)}
