import json
import os
import uuid
import boto3
import base64
from datetime import datetime, timedelta
import pymysql


s3_client = boto3.client("s3")
eventbridge_client = boto3.client("events")
lambda_client = boto3.client("lambda")

dynamodb = boto3.resource("dynamodb")
auction_table = dynamodb.Table("auction-connections")

# RDS settings from environment variables
proxy_host_name = os.environ["DB_HOSTNAME"]
port = int(os.environ["DB_PORT"])
db_name = os.environ["DB_NAME"]
db_user_name = os.environ["DB_USERNAME"]
db_password = os.environ["DB_PASSWORD"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]


def convert_to_cron(timestamp):
    """
    Converts an ISO 8601 timestamp (with or without Z) to a cron expression for EventBridge.
    Example: "2024-12-12T16:58:00" -> "58 16 12 12 ? 2024"
    """
    try:
        # Handle timestamps with or without 'Z'
        if timestamp.endswith("Z"):
            dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        else:
            dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")

        # Generate cron expression
        return f"{dt.minute} {dt.hour} {dt.day} {dt.month} ? {dt.year}"
    except ValueError as e:
        raise ValueError(
            f"Invalid timestamp format: {timestamp}. Expected ISO 8601 format."
        ) from e


def create_eventbridge_rule(rule_name, time, target_lambda_arn, input_data):

    cron_expression = convert_to_cron(time)

    try:
        response = eventbridge_client.put_rule(
            Name=rule_name,
            ScheduleExpression=f"cron({cron_expression})",
            State="ENABLED",
            Description=f"Trigger for auction {input_data['auction_id']} at {time}",
        )
        rule_arn = response["RuleArn"]

        eventbridge_client.put_targets(
            Rule=rule_name,
            Targets=[
                {"Id": "1", "Arn": target_lambda_arn, "Input": json.dumps(input_data)}
            ],
        )

        # Add permission for EventBridge to invoke the Lambda
        lambda_client.add_permission(
            FunctionName=target_lambda_arn,
            StatementId=f"{rule_name}-permission",
            Action="lambda:InvokeFunction",
            Principal="events.amazonaws.com",
            SourceArn=rule_arn,
        )

        print(f"Created EventBridge rule: {rule_name}")
        return rule_name
    except Exception as e:
        print(f"Error creating EventBridge rule: {str(e)}")
        raise


def connect_to_rds():
    try:

        connection = pymysql.connect(
            host=proxy_host_name,
            user=db_user_name,
            password=db_password,
            database=db_name,
            port=port,
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection
    except Exception as e:
        print(f"Error connecting to RDS: {str(e)}")
        raise e


def upload_to_s3(base64_data, auction_id, filename):
    try:
        decoded_data = base64.b64decode(base64_data)
        s3_key = f"auctions/{auction_id}/{filename}"
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=decoded_data,
            ContentType="image/jpeg",
        )
        return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
    except Exception as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")


def update_dynamodb_with_rules(
    auction_id,
    start_time,
    end_time,
    start_rule_name,
    end_rule_name,
    resource_creation_rule_name,
):
    """
    Updates the DynamoDB table to add start_rule_name and end_rule_name.
    """
    try:
        auction_table.put_item(
            Item={
                "auction_id": auction_id,
                "auction_start_time": start_time,
                "auction_end_time": end_time,
                "auction_status": "SCHEDULED",
                "start_rule_name": start_rule_name,
                "end_rule_name": end_rule_name,
                "resource_creation_rule_name": resource_creation_rule_name,
            }
        )
        print(f"DynamoDB updated for auction {auction_id} with rules.")
    except Exception as e:
        print(f"Error updating DynamoDB: {str(e)}")
        raise


def lambda_handler(event, context):
    # Log the incoming event for debugging
    print("Received event:", json.dumps(event))

    try:
        # print(f"Getting Body")
        # body = json.loads(event.get("body", {}))
        body = json.loads(event.get("body", {}))
        if not body or body == {}:
            body = json.dumps(event)

        if isinstance(body, str):  # If the body is a string, parse it as JSON
            body = json.loads(body)

        # Generate auction UUID
        auction_id = str(uuid.uuid4())

        # Extract required fields
        auction_item = body.get("auction_item")
        auction_desc = body.get("auction_desc")
        base_price = body.get("base_price")
        start_time = body.get("start_time")
        end_time = body.get("end_time")
        product_images = body.get("product_images", [])
        created_by = body.get("created_by")
        default_time_increment = body.get("default_time_increment")
        default_time_increment_before = body.get("default_time_increment_before")
        stop_snipes_after = body.get("stop_snipes_after")

        if (
            not auction_item
            and not auction_desc
            and not base_price
            and not start_time
            and not end_time
        ):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields."}),
            }

        for idx, base64_image in enumerate(product_images):
            filename = f"image_{idx + 1}.jpg"
            upload_to_s3(base64_image, auction_id, filename)

        # Insert auction and images into the database
        connection = connect_to_rds()
        with connection.cursor() as cursor:
            insert_query = """INSERT INTO auction (auction_id, auction_item, auction_desc, base_price, start_time, end_time, is_active, created_by,
            created_on, modified_on, default_time_increment,
            default_time_increment_before, stop_snipes_after)
            VALUES (
                    %(auction_id)s, %(auction_item)s, %(auction_desc)s, %(base_price)s,
                    %(start_time)s, %(end_time)s, %(is_active)s, %(created_by)s,
                    %(created_on)s, %(modified_on)s, %(default_time_increment)s,
                    %(default_time_increment_before)s, %(stop_snipes_after)s
                )
            """

            cursor.execute(
                insert_query,
                {
                    "auction_id": auction_id,
                    "auction_item": auction_item,
                    "auction_desc": auction_desc,
                    "base_price": base_price,
                    "start_time": start_time,
                    "end_time": end_time,
                    "is_active": 0,
                    "created_by": created_by,
                    "created_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "modified_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "default_time_increment": default_time_increment,
                    "default_time_increment_before": default_time_increment_before,
                    "stop_snipes_after": stop_snipes_after,
                },
            )
            connection.commit()

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)}),
        }

    try:
        start_rule_name = create_eventbridge_rule(
            f"StartAuction_{auction_id}",
            start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "arn:aws:lambda:us-east-1:908027408981:function:StartAuctionLambda",
            {"auction_id": auction_id, "status": "STARTED"},
        )
        end_rule_name = create_eventbridge_rule(
            f"EndAuction_{auction_id}",
            end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "arn:aws:lambda:us-east-1:908027408981:function:EndAuctionLambda",
            {"auction_id": auction_id, "status": "ENDED"},
        )
        # creationTime = start_time - timedelta(minutes=5)
        formatted_start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        creationTime = formatted_start_time - timedelta(minutes=5)
        resource_creation_rule_name = create_eventbridge_rule(
            f"ResourceCreationFor_{auction_id}",
            creationTime.strftime("%Y-%m-%dT%H:%M:%S"),
            "arn:aws:lambda:us-east-1:908027408981:function:AuctionResourceManager",
            {"auction_id": auction_id, "status": "CREATING"},
        )

        update_dynamodb_with_rules(
            auction_id,
            start_time,
            end_time,
            start_rule_name,
            end_rule_name,
            resource_creation_rule_name,
        )

        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "status_code": 201,
                    "status_message": "Auction created successfully.",
                    "data": {
                        "auction_id": auction_id,
                        "message": "Your auction has been listed successfully.",
                    },
                }
            ),
        }

    except Exception as e:
        print(f"Error scheduling auction messages: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "Failed to schedule auction messages", "details": str(e)}
            ),
        }
