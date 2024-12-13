import json
import os
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
        body = json.loads(event.get("body", {}))
        if not body or body == {}:
            body = json.dumps(event)

        if isinstance(body, str):  # If the body is a string, parse it as JSON
            body = json.loads(body)

        # Extract auction_id and other required fields
        auction_id = body.get("auction_id")
        auction_item = body.get("auction_item")
        auction_desc = body.get("auction_desc")
        base_price = body.get("base_price")
        start_time = body.get("start_time")
        end_time = body.get("end_time")
        product_images = body.get("product_images", [])
        modified_by = body.get("modified_by")
        default_time_increment = body.get("default_time_increment")
        default_time_increment_before = body.get("default_time_increment_before")
        stop_snipes_after = body.get("stop_snipes_after")

        if not auction_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing auction ID."}),
            }

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

        # Handle image uploads if any
        for idx, base64_image in enumerate(product_images):
            filename = f"image_{idx + 1}.jpg"
            upload_to_s3(base64_image, auction_id, filename)

        # Update auction in the database
        connection = connect_to_rds()
        with connection.cursor() as cursor:
            update_query = """
                UPDATE auction
                SET
                    auction_item = %(auction_item)s,
                    auction_desc = %(auction_desc)s,
                    base_price = %(base_price)s,
                    start_time = %(start_time)s,
                    end_time = %(end_time)s,
                    modified_on = %(modified_on)s,
                    modified_by = %(modified_by)s,
                    default_time_increment = %(default_time_increment)s,
                    default_time_increment_before = %(default_time_increment_before)s,
                    stop_snipes_after = %(stop_snipes_after)s
                WHERE auction_id = %(auction_id)s
            """

            cursor.execute(
                update_query,
                {
                    "auction_id": auction_id,
                    "auction_item": auction_item,
                    "auction_desc": auction_desc,
                    "base_price": base_price,
                    "start_time": start_time,
                    "end_time": end_time,
                    "modified_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "modified_by": modified_by,
                    "default_time_increment": default_time_increment,
                    "default_time_increment_before": default_time_increment_before,
                    "stop_snipes_after": stop_snipes_after,
                },
            )
            connection.commit()

        # Success response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "status_code": 200,
                    "status_message": "Auction updated successfully.",
                    "data": {"auction_id": auction_id},
                }
            ),
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)}),
        }
