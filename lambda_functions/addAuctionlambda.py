import json
import os
import uuid
import boto3
import base64
from datetime import datetime
import pymysql

s3_client = boto3.client("s3")

# RDS settings from environment variables
proxy_host_name = os.environ["DB_HOSTNAME"]
port = int(os.environ["DB_PORT"])
db_name = os.environ["DB_NAME"]
db_user_name = os.environ["DB_USERNAME"]
db_password = os.environ["DB_PASSWORD"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]


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
            ContentType="image/jpeg",  # Update based on your image type
        )
        return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
    except Exception as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")


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
            insert_query = """
                INSERT INTO auction (auction_id, auction_item, auction_desc, base_price, start_time, end_time, is_active, created_by, created_on, modified_on
                ) VALUES (
                    %(auction_id)s, %(auction_item)s, %(auction_desc)s, %(base_price)s,
                    %(start_time)s, %(end_time)s, %(is_active)s, %(created_by)s,
                    %(created_on)s, %(modified_on)s
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
                },
            )
            connection.commit()

        # Success response
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
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)}),
        }
