import time
import boto3
import pymysql
import json
from datetime import datetime, timezone
from dateutil import parser
import os
from time_helper import calculate_remaining_time
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource("dynamodb")
eventbridge_client = boto3.client("events")
lambda_client = boto3.client("lambda")
auction_table = dynamodb.Table("auction-connections")
api_gateway = boto3.client(
    'apigatewaymanagementapi', 
    endpoint_url=os.getenv('WEBSOCKET_ENDPOINT')
)

rds_host = os.environ["DB_HOSTNAME"]
rds_port = int(os.environ["DB_PORT"])
rds_db_name = os.environ["DB_NAME"]
rds_user = os.environ["DB_USERNAME"]
rds_password = os.environ["DB_PASSWORD"]


def connect_to_rds():
    try:
        connection = pymysql.connect(
            host=rds_host,
            user=rds_user,
            password=rds_password,
            database=rds_db_name,
            port=rds_port,
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection
    except Exception as e:
        print(f"Error connecting to RDS: {str(e)}")
        raise e


def update_rds(auction_id, is_active):
    try:
        connection = connect_to_rds()
        with connection.cursor() as cursor:
            update_query = """
                UPDATE auction
                SET is_active = %s, modified_on = %s
                WHERE auction_id = %s
            """
            cursor.execute(
                update_query,
                (is_active, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), auction_id),
            )
            connection.commit()
    except Exception as e:
        print(f"Error updating RDS: {str(e)}")
    finally:
        if connection:
            connection.close()


def delete_eventbridge_rule(rule_name):
    try:
        targets_response = eventbridge_client.list_targets_by_rule(Rule=rule_name)
        target_ids = [target["Id"] for target in targets_response.get("Targets", [])]

        if target_ids:
            eventbridge_client.remove_targets(Rule=rule_name, Ids=target_ids)

        eventbridge_client.delete_rule(Name=rule_name)
        print(f"Deleted rule: {rule_name}")
    except eventbridge_client.exceptions.ResourceNotFoundException:
        print(f"Rule {rule_name} not found. Nothing to delete.")
    except Exception as e:
        print(f"Error deleting rule {rule_name}: {str(e)}")
        raise


def send_websocket_message(auction_id, message):
    """
    Sends a WebSocket message to the all client connected to particular auction using API Gateway Management API.
    """
    try:
        user_connections_table = dynamodb.Table("user-connections")

        response = user_connections_table.query(
            IndexName="auction_id-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("auction_id").eq(auction_id)
        )
        connections = response.get("Items", [])

        if not connections:
            print(f"No active connections for auction {auction_id}.")
        else:
            # Send message to all connected clients
            for connection in connections:
                connection_id = connection.get("connection_id")
                try:
                    logger.info("Sending start auction message to connection: %s", connection_id)
                    api_gateway.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps(message)
                    )
                    logger.info("Successfully sent update to connection_id: %s", connection_id)
                except ClientError as e:
                    logger.error("Failed to send message to connection_id %s: %s", connection_id, e.response['Error']['Message'], exc_info=True)
    except boto3.exceptions.Boto3Error as e:
        print(f"WebSocket error: {str(e)}")
        if "GoneException" in str(e):
            print(f"Connection {connection_id} is no longer valid.")
            # Optional: Clean up the invalid connection in DynamoDB if necessary
    except Exception as e:
        print(f"Unexpected error sending WebSocket message: {str(e)}")


def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    auction_id = event["auction_id"]

    if not auction_id:
        print("Missing auction_id in the event.")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing auction_id in the event."}),
        }

    try:
        auction_data = auction_table.get_item(Key={"auction_id": auction_id}).get("Item")

        if not auction_data:
            print(f"Auction {auction_id} not found in DynamoDB.")
            return
        # Extract auction start time and put lambda to sleep until start time occurs
        start_time_str = auction_data.get("auction_start_time")
        if not start_time_str:
            print(f"Auction {auction_id} does not have a start time.")
            return {
            "statusCode": 400,
            "body": json.dumps({"error": "Auction does not have a start time."}),
            }

        start_time = parser.parse(start_time_str)
        current_time = datetime.now(timezone.utc)
        sleep_duration = (start_time - current_time).total_seconds()

        if sleep_duration > 0:
            print(f"Sleeping for {sleep_duration} seconds until auction start time.")
            time.sleep(sleep_duration)
        else:
            print(f"Auction {auction_id} start time has already passed.")
        
        auction_table.update_item(
            Key={"auction_id": auction_id},
            UpdateExpression="SET auction_status = :status",
            ExpressionAttributeValues={":status": "STARTED"},
        )
        

        end_time = auction_data.get("auction_end_time", "")

        remaining_time = calculate_remaining_time(end_time)

        message = {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Auction {auction_id} Started',
                'auction_status': 'STARTED',
                'auction_end_time': end_time,
                'remaining_time': remaining_time
            })
        }

        send_websocket_message(auction_id, message)

        # Update RDS auction status
        update_rds(auction_id, is_active=1)

        # Delete EventBridge rule for starting the auction
        delete_eventbridge_rule(f"StartAuction_{auction_id}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": f"Auction {auction_id} started successfully."}
            ),
        }

    except Exception as e:
        print(f"Error processing auction start: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)}),
        }
