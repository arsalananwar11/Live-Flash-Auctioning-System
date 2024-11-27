import boto3
import json
import os

# Initialize the DynamoDB resource
dynamodb = boto3.resource("dynamodb")

# Define the DynamoDB table to store connections
CONNECTIONS_TABLE = os.getenv("CONNECTIONS_TABLE")


def lambda_handler(event, context):
    """
    Handles WebSocket `$connect` and `$disconnect` events with user_id and auction_id.
    """
    connection_id = event["requestContext"]["connectionId"]
    route_key = event["requestContext"]["routeKey"]
    table = dynamodb.Table(CONNECTIONS_TABLE)
    print(connection_id, route_key)
    print(table)

    try:
        if route_key == "$connect":
            # Extract user_id and auction_id from query parameters or headers
            print("Route connect")
            params = event.get("queryStringParameters", {})
            user_id = params.get("user_id")
            auction_id = params.get("auction_id")
            print(params, user_id, auction_id)

            if not user_id or not auction_id:
                return {
                    "statusCode": 400,
                    "body": "Missing 'user_id' or 'auction_id' in query parameters.",
                }

            # Store the connection with auction_id and user_id in DynamoDB
            table.put_item(
                Item={
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "auction_id": auction_id,
                }
            )

            print(
                f"User {user_id} connected to auction {auction_id} with connection ID {connection_id}."
            )
            return {"statusCode": 200, "body": f"Connected to auction {auction_id}."}

        elif route_key == "$disconnect":
            # Remove the connection from DynamoDB
            table.delete_item(Key={"connection_id": connection_id})
            print(f"Connection ID {connection_id} disconnected.")
            return {"statusCode": 200, "body": "Disconnected."}

        else:
            # Unsupported route
            return {"statusCode": 400, "body": f"Unsupported route: {route_key}"}

    except Exception as e:
        print(f"Error handling route {route_key}: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
        }
