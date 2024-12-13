import json
import boto3
import os
from datetime import datetime, timedelta, timezone
from dateutil import parser
from botocore.exceptions import ClientError
from time_helper import calculate_remaining_time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS services
sqs = boto3.client('sqs')
lambda_client = boto3.client('lambda')
eventbridge_client = boto3.client('events')

# Environment variables
PROCESS_PRIORITY_LAMBDA_NAME = os.getenv('PROCESS_PRIORITY_LAMBDA_NAME')
AUCTION_CONNECTIONS_TABLE = os.getenv('AUCTION_CONNECTIONS_TABLE')
api_gateway = boto3.client('apigatewaymanagementapi', endpoint_url=os.getenv('WEBSOCKET_ENDPOINT'))
dynamodb = boto3.resource("dynamodb")
auction_table = dynamodb.Table(AUCTION_CONNECTIONS_TABLE)

def get_or_create_queue(queue_name):
    """
    Get the URL of an SQS queue or create a new one if it doesn't exist.
    """
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        print(f"{queue_name} queue exists")
        queue_url = response['QueueUrl']
        attach_queue_to_lambda(queue_url)

        return queue_url
    except sqs.exceptions.QueueDoesNotExist:
        attributes = {
            'FifoQueue': 'true',
            'ContentBasedDeduplication': 'true'
        }

        response = sqs.create_queue(QueueName=queue_name, Attributes=attributes)
        queue_url = response['QueueUrl']
        print(f"{queue_name} queue created")

        attach_queue_to_lambda(queue_url)

        return queue_url

def attach_queue_to_lambda(queue_url):
    """
    Dynamically add the priority queue as a trigger for the process priority Lambda.
    If a mapping already exists, skip creating a new one.
    """
    print(f"trying to attach queue as a trigger to lambda: {PROCESS_PRIORITY_LAMBDA_NAME}")
    if not PROCESS_PRIORITY_LAMBDA_NAME:
        print("Error: PROCESS_PRIORITY_LAMBDA_NAME is not set.")
        return

    try:
        # Get the ARN of the queue
        queue_arn = get_queue_arn(queue_url)

        # List existing event source mappings for the Lambda function
        existing_mappings = lambda_client.list_event_source_mappings(FunctionName=PROCESS_PRIORITY_LAMBDA_NAME)

        # Check if a mapping already exists for this queue ARN        
        for mapping in existing_mappings['EventSourceMappings']:
            if mapping['EventSourceArn'] == queue_arn:
                # Check if the mapping is disabled
                if mapping['State'] != 'Enabled':
                    print(f"Re-enabling event source mapping: {mapping['UUID']}")
                    lambda_client.update_event_source_mapping(
                        UUID=mapping['UUID'],
                        Enabled=True
                    )
                else:
                    print(f"Queue {queue_url} is already mapped to Lambda {PROCESS_PRIORITY_LAMBDA_NAME} and enabled.")
                return

        # If no existing mapping is found, create a new one
        response = lambda_client.create_event_source_mapping(
            EventSourceArn=queue_arn,
            FunctionName=PROCESS_PRIORITY_LAMBDA_NAME,
            BatchSize=1,
            Enabled=True
        )
        print(f"Attached queue {queue_url} to Lambda {PROCESS_PRIORITY_LAMBDA_NAME}: {response}")

    except ClientError as e:
        print(f"Failed to attach queue {queue_url}: {e.response['Error']['Message']}")

def get_queue_arn(queue_url):
    """
    Retrieve the ARN of an SQS queue from its URL.
    """
    print(f"Fetching queue ARN")
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['QueueArn']
    )
    return response['Attributes']['QueueArn']

def convert_to_cron(timestamp):
    try:
        # Parse timestamp and convert to UTC
        dt = parser.parse(timestamp).astimezone(timezone.utc)

        # Generate cron expression
        return f"{dt.minute} {dt.hour} {dt.day} {dt.month} ? {dt.year}"
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {timestamp}. Expected ISO 8601 format.") from e


def update_eventbridge_rule(rule_name, new_time, target_lambda_arn, input_data):
    """
    Update an existing EventBridge rule with a new schedule and input.
    """
    try:
        cron_expression = convert_to_cron(new_time)
        eventbridge_client.put_rule(
            Name=rule_name,
            ScheduleExpression=f"cron({cron_expression})",
            State="ENABLED",
            Description=f"Updated trigger for auction {input_data['auction_id']} at {new_time}",
        )
        eventbridge_client.put_targets(
            Rule=rule_name,
            Targets=[
                {"Id": "1", "Arn": target_lambda_arn, "Input": json.dumps(input_data)}
            ],
        )
        
        print(f"Updated EventBridge rule {rule_name} with new time {new_time}")
    except Exception as e:
        print(f"Error updating EventBridge rule: {str(e)}")
        raise

def process_place_bid(auction_fifo_queue, auction_id, user_id, bid_amount, user_name):
    """
    Process a bid placement action.
    """
    current_time = datetime.now(timezone.utc)
    timestamp = int(current_time.timestamp())

    bid_message = {
        "action": "placeBid",
        "auction_id": auction_id,
        "user_id": user_id,
        "user_name": user_name,
        "bid_amount": bid_amount,
        "timestamp": timestamp
    }

    print(f"Placing Bid for {user_name} of {bid_amount}")

    sqs.send_message(
        QueueUrl=auction_fifo_queue,
        MessageBody=json.dumps(bid_message),
        MessageGroupId=auction_id,
        MessageDeduplicationId=f"{auction_id}-{user_id}-{bid_amount}-{timestamp}",
    )

    # Handle sniping
    auction_data = auction_table.get_item(Key={"auction_id": auction_id}).get("Item")

    if not auction_data:
        print(f"Auction {auction_id} not found in DynamoDB.")
        return
    
    end_time = parser.parse(auction_data["auction_end_time"])
    time_remaining = (end_time - current_time).total_seconds()
    
    snipes_remaining = int(auction_data.get("snipes_remaining", 0))
    default_time_increment = int(auction_data.get("default_time_increment", 0)) * 60
    default_time_increment_before = int(auction_data.get("default_time_increment_before", 0)) * 60

    if snipes_remaining > 0 and time_remaining <= default_time_increment_before:
        extended_time = end_time + timedelta(seconds=default_time_increment)
        new_end_time_str = extended_time.strftime("%Y-%m-%dT%H:%M:%S%z")
        new_end_time_str = new_end_time_str[:-2] + ":" + new_end_time_str[-2:]
        auction_status = "SNIPED"
        snipes_remaining = snipes_remaining - 1
        print(new_end_time_str)

        auction_table.update_item(
            Key={"auction_id": auction_id},
            UpdateExpression="SET auction_end_time = :new_end_time, snipes_remaining = :new_snipes, auction_status = :new_status",
            ExpressionAttributeValues={
                ":new_end_time": new_end_time_str,
                ":new_snipes": snipes_remaining,
                ":new_status": auction_status
            },
        )

        end_rule_name = auction_data.get('end_rule_name', f"EndAuction_{auction_id}")
        
        update_eventbridge_rule(
            end_rule_name,
            new_end_time_str,
            "arn:aws:lambda:us-east-1:908027408981:function:EndAuctionLambda",
            {"auction_id": auction_id, "status": "ENDED"},
        )
        print(f"Auction {auction_id} extended to {new_end_time_str}.")

        user_connections_table = dynamodb.Table('user-connections')
        
        # Query connections for the auction
        response = user_connections_table.query(
            IndexName="auction_id-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("auction_id").eq(auction_id)
        )
        connections = response.get("Items", [])
        print(f"Connections found: {connections}")

        remaining_time = calculate_remaining_time(new_end_time_str)

        message = {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Auction {auction_id} sniped',
                'auction_status': auction_status,
                # 'auction_start_time': auction_start_time,
                'auction_end_time': new_end_time_str,
                'remaining_time': remaining_time,
                'remaining_snipes': snipes_remaining
            })
        }

        for connection in connections:
            connection_id = connection.get("connection_id")
            try:
                logger.info("Sending updated time to connection: %s", connection_id)
                api_gateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message)
                )
                logger.info("Successfully sent leaderboard update to connection_id: %s", connection_id)
            except ClientError as e:
                logger.error("Failed to send message to connection_id %s: %s", connection_id, e.response['Error']['Message'], exc_info=True)

    else:
        print("Sniping prevention not possible")

def lambda_handler(event, context):
    """
    Handles user actions (place bids) and updates auction-specific queues.
    """
    print(event)
    try:
        action = event.get('action')
        auction_id = event.get('auction_id')
        user_id = event.get('user_id')
        bid_amount = event.get('bid_amount', 0)
        user_name = event.get('user_name')

        if not action or not auction_id or not user_id or not user_name:
            print("Missing Required Fields")
            return {"statusCode": 400, "body": json.dumps({"error": "Missing required fields."})}
        if not isinstance(bid_amount, (int, float)) or bid_amount <= 0:
            print("Invalid Bid Amount: ", bid_amount)
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid 'bid_amount'."})}

        auction_fifo_queue_name = f"AuctionActionsQueue-{auction_id}.fifo"
        # auction_fifo_queue = get_or_create_queue(auction_fifo_queue_name)
        auction_fifo_queue = sqs.get_queue_url(QueueName=auction_fifo_queue_name)["QueueUrl"]
        print(f"Queue URL: {auction_fifo_queue}")

        if action == "placeBid":
            process_place_bid(auction_fifo_queue, auction_id, user_id, bid_amount, user_name)
        else:
            print("Invalid Route")
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid action."})}
        
        print("Success")
        return {"statusCode": 200, "body": json.dumps({"message": f"{action} action processed for auction {auction_id}."})}

    except ClientError as e:
        print(f"ClientError: {e.response['Error']['Message']}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed due to internal error."})}
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}
