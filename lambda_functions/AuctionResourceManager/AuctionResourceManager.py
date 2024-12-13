import json
import boto3
import os
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from dateutil import parser  # For parsing ISO 8601 datetime strings
import time  # For sleep functionality

# Initialize AWS clients
sqs = boto3.client("sqs")
lambda_client = boto3.client("lambda")
eventbridge_client = boto3.client("events")
dynamodb = boto3.resource("dynamodb")
auction_table = dynamodb.Table("auction-connections")
dynamodb = boto3.resource("dynamodb")
apigateway_management_api = boto3.client(
    "apigatewaymanagementapi", endpoint_url=os.environ["WEBSOCKET_ENDPOINT"]
)

# Environment variable for the process priority Lambda
PROCESS_PRIORITY_LAMBDA_NAME = os.getenv("PROCESS_PRIORITY_LAMBDA_NAME")


# Environment variables
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")


def get_queue_arn(queue_url):
    """
    Retrieve the ARN of an SQS queue from its URL.
    """
    response = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])
    return response["Attributes"]["QueueArn"]


def create_queue(queue_name, is_fifo=False):
    """
    Create an SQS queue with the given name.
    """
    try:
        attributes = {}
        if is_fifo:
            attributes = {"FifoQueue": "true", "ContentBasedDeduplication": "true"}
        response = sqs.create_queue(QueueName=queue_name, Attributes=attributes)
        print(f"Created queue: {queue_name}")
        return response["QueueUrl"]
    except ClientError as e:
        print(f"Error creating queue {queue_name}: {e.response['Error']['Message']}")
        raise e


def attach_queue_to_lambda(queue_url):
    """
    Attach an SQS queue as a trigger to the process priority Lambda.
    """
    try:
        queue_arn = get_queue_arn(queue_url)

        # Check if the mapping already exists
        existing_mappings = lambda_client.list_event_source_mappings(
            FunctionName=PROCESS_PRIORITY_LAMBDA_NAME
        )
        for mapping in existing_mappings["EventSourceMappings"]:
            if mapping["EventSourceArn"] == queue_arn:
                print(
                    f"Queue {queue_url} is already mapped to Lambda {PROCESS_PRIORITY_LAMBDA_NAME}."
                )
                return

        # Create the mapping with retries
        retries = 3
        for attempt in range(retries):
            try:
                response = lambda_client.create_event_source_mapping(
                    EventSourceArn=queue_arn,
                    FunctionName=PROCESS_PRIORITY_LAMBDA_NAME,
                    BatchSize=1,
                    Enabled=True,
                )
                print(
                    f"Attached queue {queue_url} to Lambda {PROCESS_PRIORITY_LAMBDA_NAME}: {response}"
                )
                return
            except ClientError as e:
                print(
                    f"Error attaching queue {queue_url} to Lambda: {e.response['Error']['Message']}"
                )
                if attempt < retries - 1:
                    print(f"Retrying attachment ({attempt + 1}/{retries})...")
                    time.sleep(2)
                else:
                    raise e

    except ClientError as e:
        print(
            f"Error attaching queue {queue_url} to Lambda: {e.response['Error']['Message']}"
        )
        raise e


def delete_queue(queue_url):
    """
    Delete an SQS queue with the given URL.
    """
    try:
        sqs.delete_queue(QueueUrl=queue_url)
        print(f"Deleted queue: {queue_url}")
    except ClientError as e:
        print(f"Error deleting queue {queue_url}: {e.response['Error']['Message']}")
        raise e


def remove_queue_trigger(queue_url):
    """
    Remove an SQS queue trigger from the process priority Lambda.
    """
    try:
        queue_arn = get_queue_arn(queue_url)
        existing_mappings = lambda_client.list_event_source_mappings(
            FunctionName=PROCESS_PRIORITY_LAMBDA_NAME
        )
        for mapping in existing_mappings["EventSourceMappings"]:
            if mapping["EventSourceArn"] == queue_arn:
                lambda_client.delete_event_source_mapping(UUID=mapping["UUID"])
                print(
                    f"Removed trigger for queue {queue_url} from Lambda {PROCESS_PRIORITY_LAMBDA_NAME}."
                )
                return
    except ClientError as e:
        print(
            f"Error removing trigger for queue {queue_url}: {e.response['Error']['Message']}"
        )
        raise e


def update_auction_status(auction_id, new_status):
    """
    Update the auction status in the DynamoDB table.
    """
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    print("Table:", table)
    try:
        response = table.update_item(
            Key={"auction_id": auction_id},
            UpdateExpression="SET auction_status = :status",
            ExpressionAttributeValues={":status": new_status},
            ReturnValues="UPDATED_NEW",
        )
        print(f"Auction {auction_id} status updated to {new_status}.")
        return response
    except ClientError as e:
        print(f"Error updating auction status: {e.response['Error']['Message']}")
        raise e


def delete_eventbridge_rule(rule_name):
    try:
        targets_response = eventbridge_client.list_targets_by_rule(Rule=rule_name)
        target_ids = [target["Id"] for target in targets_response.get("Targets", [])]

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


def send_websocket_message(auction_id, message):
    """
    Sends a WebSocket message to the all client connected to particular auction using API Gateway Management API.
    """
    try:
        user_connections_table = dynamodb.Table('user-connections')
        
        response = user_connections_table.query(
            IndexName="auction_id-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("auction_id").eq(auction_id)
        )
        connections = response.get("Items", [])

        if not connections:
            print(f"No active connections for auction {auction_id}.")
        else:
            message = {
                "auction_id": auction_id,
                "auction_status": "CREATING",
                "message": "Auction has CREATING.",
            }

            # Send message to all connected clients
            for connection in connections:
                connection_id = connection["connection_id"]
                apigateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message),
                )
        # print(f"Message sent to connection: {connection_id}")
    except boto3.exceptions.Boto3Error as e:
        print(f"WebSocket error: {str(e)}")
        if "GoneException" in str(e):
            print(f"Connection {connection_id} is no longer valid.")
            # Optional: Clean up the invalid connection in DynamoDB if necessary
    except Exception as e:
        print(f"Unexpected error sending WebSocket message: {str(e)}")


def lambda_handler(event, context):
    """
    Handle EventBridge events to create or delete auction resources.
    """
    try:
        print(f"Event received: {json.dumps(event)}")
        action = event.get("status")  # "create" or "delete"
        auction_id = event.get("auction_id")
        print(f"auction_id {auction_id}")
        print(f"action {action}")

        response = auction_table.get_item(Key={"auction_id": auction_id})
        auction_item = response.get("Item")
        print(auction_item)

        if not auction_id or action not in ["CREATING", "SCHEDULED"]:
            raise ValueError(
                "Missing or invalid 'auction_id' or 'action' in the event."
            )

        auction_connection_id = auction_item.get("auction_connectionId")
        print("Auction Connection ID: ", auction_connection_id)

        # Define queue names
        fifo_queue_name = f"AuctionActionsQueue-{auction_id}.fifo"
        priority_queue_name = f"AuctionPriorityQueue-{auction_id}"
        

        if action == "SCHEDULED" or action == "CREATING":
            # Update auction status to 'CREATING'
            update_auction_status(auction_id, "CREATING")

            message = {
                "auction_id": auction_id,
                "auction_status": "CREATING",
                "message": "Auction is under creation stage.",
            }

            send_websocket_message(auction_id, message)

            # Create queues
            fifo_queue_url = create_queue(fifo_queue_name, is_fifo=True)
            priority_queue_url = create_queue(priority_queue_name, is_fifo=False)

            # Attach priority queue to Lambda
            attach_queue_to_lambda(fifo_queue_url)

            # Delete EventBridge rule for starting the auction
            delete_eventbridge_rule(f"ResourceCreationFor_{auction_id}")

            return {
                "statusCode": 200,
                "body": f"Created resources for auction {auction_id}, including queues.",
            }

        elif action == "delete":
            # Get queue URLs
            fifo_queue_url = sqs.get_queue_url(QueueName=fifo_queue_name)["QueueUrl"]
            priority_queue_url = sqs.get_queue_url(QueueName=priority_queue_name)[
                "QueueUrl"
            ]

            # Remove trigger from Lambda
            remove_queue_trigger(priority_queue_url)

            # Delete queues
            delete_queue(fifo_queue_url)
            delete_queue(priority_queue_url)

            return {
                "statusCode": 200,
                "body": f"Deleted queues and removed triggers for auction {auction_id}.",
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Error handling auction resources: {str(e)}",
        }
