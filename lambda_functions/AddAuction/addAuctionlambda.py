import json
import os
import uuid
import boto3
import base64
from datetime import datetime, timedelta, timezone
from dateutil import parser
import pymysql
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")
eventbridge_client = boto3.client("events")
lambda_client = boto3.client("lambda")
sqs_client = boto3.client("sqs")
cognito_idp = boto3.client("cognito-idp")  # For fetching user details from Cognito
dynamodb = boto3.resource("dynamodb")
auction_table = dynamodb.Table("auction-connections")


SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

# RDS settings from environment variables
proxy_host_name = os.environ["DB_HOSTNAME"]
port = int(os.environ["DB_PORT"])
db_name = os.environ["DB_NAME"]
db_user_name = os.environ["DB_USERNAME"]
db_password = os.environ["DB_PASSWORD"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")


def get_user_email(user_id):
    """
    Fetch the email of a user from Cognito User Pool using their user_id.
    """
    try:
        response = cognito_idp.admin_get_user(
            UserPoolId=COGNITO_USER_POOL_ID, Username=user_id
        )
        for attribute in response["UserAttributes"]:
            if attribute["Name"] == "email":
                return attribute["Value"]
    except ClientError as e:
        print(f"Error fetching email for user {user_id}: {str(e)}")
    return None


def convert_to_cron(timestamp):
    try:
        # Parse timestamp and convert to UTC
        dt = parser.parse(timestamp).astimezone(timezone.utc) - timedelta(minutes=1)

        # Generate cron expression
        return f"{dt.minute} {dt.hour} {dt.day} {dt.month} ? {dt.year}"
    except ValueError as e:
        raise ValueError(
            f"Invalid timestamp format: {timestamp}. Expected ISO 8601 format."
        ) from e


def create_eventbridge_rule(rule_name, time, target_lambda_arn, input_data):
    """
    Creates an EventBridge rule for scheduling the auction-related events.
    """
    try:
        cron_expression = convert_to_cron(time)

        eventbridge_client.put_rule(
            Name=rule_name,
            ScheduleExpression=f"cron({cron_expression})",
            State="ENABLED",
            Description=f"Trigger for auction {input_data['auction_id']} at {time}",
        )

        # Add targets to the rule
        eventbridge_client.put_targets(
            Rule=rule_name,
            Targets=[
                {"Id": "1", "Arn": target_lambda_arn, "Input": json.dumps(input_data)}
            ],
        )

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
    default_time_increment,
    default_time_increment_before,
    stop_snipes_after,
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
                "snipes_remaining": stop_snipes_after,
                "default_time_increment": default_time_increment,
                "default_time_increment_before": default_time_increment_before,
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

        body = json.loads(event.get("body", {}))
        # print("Body: ", body)
        if not body or body == {}:
            body = json.dumps(event)

        if isinstance(body, str):
            body = json.loads(body)

        auction_id = str(uuid.uuid4())

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

    update_dynamodb_with_rules(
        auction_id,
        start_time,
        end_time,
        default_time_increment,
        default_time_increment_before,
        stop_snipes_after,
    )

    start_time_dt = parser.parse(start_time).astimezone(timezone.utc)
    current_time = datetime.now(timezone.utc)
    time_diff = (start_time_dt - current_time).total_seconds()

    create_eventbridge_rule(
        f"EndAuction_{auction_id}",
        end_time,
        "arn:aws:lambda:us-east-1:908027408981:function:EndAuctionLambda",
        {"auction_id": auction_id, "status": "ENDED"},
    )

    try:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id, user_name FROM users")
                recipients = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching users from RDS: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to fetch users"}),
            }

        for recipient in recipients:
            try:
                user_id = recipient.get("user_id")
                user_name = recipient.get("user_name")
                if not user_id:
                    print("Skipping recipient without user_id.")
                    continue
                email = get_user_email(user_id)

                if not email:
                    print(f"Skipping user {user_id} as email could not be retrieved.")
                    continue

                sqs_message = {
                    "email": email,
                    "user_name": user_name,
                    "auction_details": {
                        "auction_id": auction_id,
                        "auction_item": auction_item,
                        "auction_desc": auction_desc,
                        "base_price": base_price,
                        "start_time": start_time,
                        "end_time": end_time,
                        "created_by": created_by,
                    },
                }

                # Send the message to SQS
                print(f"Sending message to SQS for user {user_id} with email {email}")
                sqs_client.send_message(
                    QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(sqs_message)
                )
                print(f"Message sent to SQS for user {user_id} with email {email}")

            except Exception as e:
                print(f"Error adding message to SQS for user {user_id}: {str(e)}")

        if time_diff <= 180:  # Less than or equal to 6 minutes

            lambda_client.invoke(
                FunctionName="arn:aws:lambda:us-east-1:908027408981:function:AuctionResourceManager",
                InvocationType="RequestResponse",  # synchronous invocation "RequestResponse"
                Payload=json.dumps({"auction_id": auction_id, "status": "CREATING"}),
            )

            lambda_client.invoke(
                FunctionName="arn:aws:lambda:us-east-1:908027408981:function:StartAuctionLambda",
                InvocationType="Event",  # synchronous invocation "RequestResponse"
                Payload=json.dumps({"auction_id": auction_id, "status": "STARTED"}),
            )

        else:

            formatted_start_time = parser.parse(start_time).astimezone(timezone.utc)
            creation_time = formatted_start_time - timedelta(minutes=3)

            create_eventbridge_rule(
                f"ResourceCreationFor_{auction_id}",
                creation_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "arn:aws:lambda:us-east-1:908027408981:function:AuctionResourceManager",
                {"auction_id": auction_id, "status": "CREATING"},
            )

            create_eventbridge_rule(
                f"StartAuction_{auction_id}",
                start_time,
                "arn:aws:lambda:us-east-1:908027408981:function:StartAuctionLambda",
                {"auction_id": auction_id, "status": "STARTED"},
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
