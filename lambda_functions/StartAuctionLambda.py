import boto3
import pymysql
import json
from datetime import datetime
import os

dynamodb = boto3.resource("dynamodb")
eventbridge_client = boto3.client('events')
auction_table = dynamodb.Table("auction-connections")
apigateway_management_api = boto3.client("apigatewaymanagementapi", endpoint_url=os.environ["WEBSOCKET_ENDPOINT"])

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
        target_ids = [target['Id'] for target in targets_response.get('Targets', [])]

        if target_ids:
            eventbridge_client.remove_targets(Rule=rule_name, Ids=target_ids)
            print(f"Removed targets from rule: {rule_name}")

        eventbridge_client.delete_rule(Name=rule_name)
        print(f"Deleted rule: {rule_name}")
    except eventbridge_client.exceptions.ResourceNotFoundException:
        print(f"Rule {rule_name} not found. Nothing to delete.")
    except Exception as e:
        print(f"Error deleting rule {rule_name}: {str(e)}")
        raise
    
def send_websocket_message(connection_id, message):
    try:
        apigateway_management_api.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message),
        )
        print(f"Message sent to connection: {connection_id}")
    except Exception as e:
        print(f"Error sending message: {e}")

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    auction_id = event["auction_id"]

    # Update DynamoDB
    auction_table.update_item(
        Key={"auction_id": auction_id},
        UpdateExpression="SET auction_status = :status",
        ExpressionAttributeValues={":status": "IN_PROGRESS"}
    )
    
    send_websocket_message(auction_connection_id, message)

    # Update RDS
    connection = connect_to_rds()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE auction SET is_active = 1 WHERE auction_id = %s",
            (auction_id,)
        )
        connection.commit()

    
    delete_eventbridge_rule(f"StartAuction_{auction_id}")
