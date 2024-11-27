import json
import base64
import boto3
import os
from datetime import datetime
import pymysql  # Or the database driver you're using

# S3 client
s3_client = boto3.client('s3')

# Database connection details
proxy_host_name = os.environ['DB_HOSTNAME']
port = int(os.environ['DB_PORT'])
db_name = os.environ['DB_NAME']
db_user_name = os.environ['DB_USERNAME']
db_password = os.environ['DB_PASSWORD']
S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']

def lambda_handler(event, context):
    # Get query parameters
    mode = "all_auction"# Default to 'all_auction'
    query_parameters = event.get("queryStringParameters", {})
    body = {}

    if event.get("body"):
        try:
            body = json.loads(event.get("body", "{}"))
            print(type(event.get("body", {})))
        except json.JSONDecodeError as e:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON in request body"})
            }
        
    # if event.get("body", {}):
    #     body = json.loads(event.get("body", {}))
    
    if query_parameters:
        mode = query_parameters.get("mode")  
    
    if not body or body == {}:
        body = json.dumps(event)
        
    if isinstance(body, str):  
        body = json.loads(body)
        
    user_id = body.get("user_id")

    if mode == "my_auction" and not user_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing user_id query parameter"})
        }
    
    try:
        # Connect to the database
        connection = pymysql.connect(
            host=proxy_host_name,
            user=db_user_name,
            password=db_password, 
            database=db_name,
            port=port,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            
            if mode == "my_auction":
                select_query = """
                    SELECT * FROM auction WHERE created_by = %(user_id)s
                """
            elif mode == "upcoming_auction":
                select_query = """
                    SELECT * FROM auction WHERE start_time > NOW()
                """
            else:  # Default to 'all_auction'
                select_query = """
                    SELECT * FROM auction ORDER BY start_time DESC
                """
            cursor.execute(select_query, {"user_id": user_id})
            auctions = cursor.fetchall()
        
        # Closing connection
        connection.close()
        
        for auction in auctions:
            auction_id = auction["auction_id"]
            s3_key_prefix = f"auctions/{auction_id}/"
            auction["images"] = []
            
            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET_NAME,
                Prefix=s3_key_prefix
            )
            
            
            if "Contents" in response:
                for obj in response["Contents"]:
                    s3_key = obj["Key"]
                    # Fetch image and convert to base64
                    image_data = s3_client.get_object(
                        Bucket=S3_BUCKET_NAME, Key=s3_key
                    )["Body"].read()
                    base64_image = base64.b64encode(image_data).decode("utf-8")
                    auction["images"].append({
                        "file_name": s3_key.split("/")[-1],
                        "base64": base64_image
                    })
        print("Fetching Completed")
        # Return the response
        return {
            "statusCode": 200,
            "body": json.dumps(auctions, default=str)
        }
    
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }