import boto3
import json
import os
from decimal import Decimal
from botocore.exceptions import ClientError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS services
dynamodb = boto3.resource("dynamodb")
broadcast_gateway = boto3.client(
    "apigatewaymanagementapi", endpoint_url=os.getenv("BROADCAST_ENDPOINT")
)

# Environment variables
LEADERBOARD_TABLE = os.getenv("LEADERBOARD_TABLE")


def broadcast_leaderboard(auction_id, connection_id):
    """
    Broadcast the updated leaderboard to the connection_id.
    """
    try:
        # Fetch leaderboard
        leaderboard = fetch_leaderboard(auction_id)

        # Convert Decimal types to JSON-serializable types
        leaderboard = convert_decimal(leaderboard)

        # Prepare message
        message = {
            "type": "leaderboardUpdate",
            "auction_id": auction_id,
            "leaderboard": leaderboard,
        }

        # Broadcast to connection_id
        try:
            logger.info(
                "Sending leaderboard update to connection_id: %s", connection_id
            )
            broadcast_gateway.post_to_connection(
                ConnectionId=connection_id, Data=json.dumps(message)
            )
            logger.info(
                "Successfully sent leaderboard update to connection_id: %s",
                connection_id,
            )
        except ClientError as e:
            logger.error(
                "Failed to send message to connection_id %s: %s",
                connection_id,
                e.response["Error"]["Message"],
                exc_info=True,
            )

    except Exception as e:
        print(f"Failed to broadcast leaderboard: {str(e)}")


def fetch_leaderboard(auction_id):
    """
    Fetch the sorted leaderboard for an auction.
    """
    try:
        logger.info("Fetching leaderboard for auction_id: %s", auction_id)
        table = dynamodb.Table(LEADERBOARD_TABLE)
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("auction_id").eq(
                auction_id
            ),
            ScanIndexForward=False,  # DynamoDB default sorting is ascending; use False for descending
        )
        leaderboard = response.get("Items", [])
        leaderboard_sorted = sorted(leaderboard, key=lambda x: -x["bid_amount"])
        logger.info(
            "Fetched leaderboard for auction_id %s: %s", auction_id, leaderboard_sorted
        )
        return leaderboard_sorted
    except ClientError as e:
        logger.error(
            "Failed to fetch leaderboard from table: %s",
            e.response["Error"]["Message"],
            exc_info=True,
        )
        return []


def convert_decimal(obj):
    """
    Recursively converts Decimal objects to float in a dictionary or list.
    """
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)  # Or int(obj) if you need integers
    else:
        return obj
