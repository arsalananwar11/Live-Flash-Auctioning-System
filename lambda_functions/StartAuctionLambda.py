import boto3
import pymysql
import json
from datetime import datetime
import os

dynamodb = boto3.resource("dynamodb")
eventbridge_client = boto3.client("events")
lambda_client = boto3.client("lambda")
auction_table = dynamodb.Table("auction-connections")
apigateway_api = boto3.client(
    "apigatewaymanagementapi", endpoint_url=os.environ["WEBSOCKET_ENDPOINT"]
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
            print(f"Auction {auction_id} updated in RDS to is_active = {is_active}")
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
            print(f"Removed targets from rule: {rule_name} and its id {target_ids}")

        eventbridge_client.delete_rule(Name=rule_name)
        print(f"Deleted rule: {rule_name}")
    except eventbridge_client.exceptions.ResourceNotFoundException:
        print(f"Rule {rule_name} not found. Nothing to delete.")
    except Exception as e:
        print(f"Error deleting rule {rule_name}: {str(e)}")
        raise


def send_websocket_message(connection_id, message):
    try:
        apigateway_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message),
        )
        print(f"Message sent to connection: {connection_id}")
    except Exception as e:
        print(f"Error sending message: {e}")


def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    auction_id = event["auction_id"]

    try:
        response = auction_table.get_item(Key={"auction_id": auction_id})
        auction_item = response.get("Item")

        if not auction_item:
            print(f"Auction {auction_id} not found in DynamoDB.")
            return {"statusCode": 404, "body": "Auction not found"}

        auction_connection_id = auction_item.get("auction_connectionId")
        # auction_connection_id = auction_item.get("auction_connectionId")

        if not auction_connection_id:
            print(
                f"No connection ID for auction {auction_id}. Skipping WebSocket notification."
            )
        else:
            message = {
                "auction_id": auction_id,
                "auction_status": "STARTED",
                "message": "Auction has started.",
            }
            # Send WebSocket notification
            send_websocket_message(auction_connection_id, message)

        # Update DynamoDB auction status
        auction_table.update_item(
            Key={"auction_id": auction_id},
            UpdateExpression="SET auction_status = :status",
            ExpressionAttributeValues={":status": "STARTED"},
        )
        print(f"Auction {auction_id} status updated to STARTED in DynamoDB.")

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
