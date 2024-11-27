import os

api_gateway_url = os.getenv("API_GATEWAY_URL")


class MainService:
    @staticmethod
    def get_message(message: str = None):
        if message:
            return str(message)
        return "Welcome to the Live Flash Auctioning System"
