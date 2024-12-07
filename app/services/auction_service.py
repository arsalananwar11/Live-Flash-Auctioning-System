import base64
from flask import session
import requests
import os

api_gateway_url = os.getenv("API_GATEWAY_URL")


class AuctionService:
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
            return {
                "status": "failure",
                "error": "Request to API Gateway failed.",
                "details": str(e),
            }

    @staticmethod
    def get_target_auction(auction_id):
        try:
            params = {"mode": "single_auction", "auction_id": auction_id}
            response = requests.get(
                f"{api_gateway_url}/get-auctions",
                params=params,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code == 200:
                auction = response.json()
                return auction
            else:
                print(f"Error fetching auction details: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Request Exception: {str(e)}")
            return None

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
    def prepare_auction_data(auctions):
        # Prepare the response data
        auctions_list = []
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
            auctions_list.append(auction_data)

        return auctions_list

    @staticmethod
    def edit_auction(auction_id, auction_data):
        images_base64 = []
        for image in auction_data["images"]:
            image_base64 = base64.b64encode(image.read()).decode("utf-8")
            images_base64.append(image_base64)

        auction_payload = {
            "auction_id": auction_id,
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
            "modified_by": session["user_id"],
        }

        try:
            url = f"{api_gateway_url}/edit-auction"
            print(f"send request to {url}")
            response = requests.patch(
                url, json=auction_payload, headers={"Content-Type": "application/json"}
            )
            print(f"response: {response}")
            try:
                response_data = response.json()

                if response.status_code == 200:
                    return {
                        "status": "success",
                        "status_code": 200,
                        "data": {
                            "auction_id": response_data["data"].get("auction_id"),
                            "message": response_data["data"].get(
                                "message", "Auction updated successfully"
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
