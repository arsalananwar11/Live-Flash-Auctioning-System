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
api_gateway = boto3.client(
    "apigatewaymanagementapi", endpoint_url=os.getenv("WEBSOCKET_ENDPOINT")
)

# Environment variables
LEADERBOARD_TABLE = os.getenv("LEADERBOARD_TABLE")
USER_CONNECTIONS_TABLE = os.getenv("USER_CONNECTIONS_TABLE")


def lambda_handler(event, context):
    """
    Process messages from auction-specific priority queues and broadcast updates.
    """
    logger.info("Event received: %s", json.dumps(event))
    try:
        for record in event["Records"]:
            logger.info("Processing record: %s", json.dumps(record))
            # Extract the message body and decode JSON
            message = json.loads(record["body"])
            logger.info("Decoded message: %s", json.dumps(message))

            action = message.get("action")
            auction_id = message.get("auction_id")
            user_id = message.get("user_id")
            user_name = message.get("user_name")
            bid_amount = message.get("bid_amount", 0)  # Convert to Decimal
            timestamp = Decimal(str(message.get("timestamp", 0)))  # Convert to Decimal

            if not auction_id or not user_id:
                logger.warning(
                    "Missing 'auction_id' or 'user_id' in message: %s",
                    json.dumps(message),
                )
                continue

            if action == "placeBid":
                logger.info(
                    "Processing placeBid action for auction_id: %s, user_id: %s",
                    auction_id,
                    user_id,
                )
                process_place_bid(auction_id, user_id, bid_amount, timestamp, user_name)
            else:
                logger.warning("Invalid action received: %s", action)

            # Broadcast the updated leaderboard
            logger.info("Broadcasting leaderboard for auction_id: %s", auction_id)
            broadcast_leaderboard(auction_id)

        logger.info("All records processed successfully.")
        return {"statusCode": 200, "body": "Messages processed successfully."}

    except Exception as e:
        logger.error("Unexpected error occurred: %s", str(e), exc_info=True)
        return {"statusCode": 500, "body": "Internal Server Error"}


def process_place_bid(auction_id, user_id, bid_amount, timestamp, user_name):
    try:
        # Convert bid_amount and timestamp to Decimal
        bid_amount_decimal = Decimal(
            str(bid_amount)
        )  # Convert to string before Decimal
        timestamp_decimal = Decimal(str(timestamp))  # Convert to string before Decimal

        logger.info(
            "Adding/Updating bid in leaderboard. Auction ID: %s, User ID: %s, Bid Amount: %s, Timestamp: %s",
            auction_id,
            user_id,
            bid_amount_decimal,
            timestamp_decimal,
        )

        table = dynamodb.Table(LEADERBOARD_TABLE)
        table.put_item(
            Item={
                "auction_id": auction_id,
                "user_id": user_id,
                "bid_amount": bid_amount_decimal,  # Use Decimal
                "timestamp": timestamp_decimal,  # Use Decimal
                "user_name": user_name,
            }
        )
        logger.info(
            "Successfully added/updated bid for user %s in auction %s",
            user_id,
            auction_id,
        )
    except ClientError as e:
        logger.error(
            "Failed to update leaderboard table: %s",
            e.response["Error"]["Message"],
            exc_info=True,
        )


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


def broadcast_leaderboard(auction_id):
    """
    Broadcast the updated leaderboard to all WebSocket clients.
    """
    try:
        logger.info("Fetching WebSocket connections for auction_id: %s", auction_id)
        user_connections_table = dynamodb.Table(USER_CONNECTIONS_TABLE)

        # Query connections for the auction
        response = user_connections_table.query(
            IndexName="auction_id-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("auction_id").eq(
                auction_id
            ),
        )
        connections = response.get("Items", [])
        print(f"Connections found: {connections}")

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

        # Broadcast to all connections
        for connection in connections:
            connection_id = connection.get("connection_id")
            try:
                logger.info(
                    "Sending leaderboard update to connection_id: %s", connection_id
                )
                api_gateway.post_to_connection(
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
        leaderboard_sorted = sorted(
            leaderboard, key=lambda x: (-x["bid_amount"], x["timestamp"])
        )
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
