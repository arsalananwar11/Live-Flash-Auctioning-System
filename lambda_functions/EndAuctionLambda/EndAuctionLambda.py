import boto3
import pymysql
import json
from datetime import datetime, timezone
import os
from botocore.exceptions import ClientError
from decimal import Decimal
from dateutil import parser

dynamodb = boto3.resource("dynamodb")
eventbridge_client = boto3.client("events")
auction_table = dynamodb.Table("auction-connections")
apigateway_management_api = boto3.client(
    "apigatewaymanagementapi", endpoint_url=os.environ["WEBSOCKET_ENDPOINT"]
)
s3 = boto3.client("s3")
cognito_idp = boto3.client("cognito-idp")  
ses = boto3.client("ses")
sqs = boto3.client("sqs")


S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL") 


rds_host = os.environ["DB_HOSTNAME"]
rds_port = int(os.environ["DB_PORT"])
rds_db_name = os.environ["DB_NAME"]
rds_user = os.environ["DB_USERNAME"]
rds_password = os.environ["DB_PASSWORD"]

def convert_decimal_and_timestamp(obj):
    """
    Recursively converts Decimal objects to float and Unix timestamps to UTC in a dictionary or list.
    """
    if isinstance(obj, list):
        return [convert_decimal_and_timestamp(i) for i in obj]
    elif isinstance(obj, dict):
        updated_dict = {}
        for k, v in obj.items():
            if k == "timestamp" and isinstance(v, (int, float, Decimal)):
                updated_dict[k] = datetime.fromtimestamp(float(v), tz=timezone.utc).isoformat()
            else:
                updated_dict[k] = convert_decimal_and_timestamp(v)
        return updated_dict
    elif isinstance(obj, Decimal):
        return float(obj)  
    else:
        return obj


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


def get_user_email(user_id):
    """
    Fetch the email of a user from Cognito User Pool using their user_id.
    """
    try:
        response = cognito_idp.admin_get_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=user_id
        )
        for attribute in response['UserAttributes']:
            if attribute['Name'] == 'email':
                return attribute['Value']
    except ClientError as e:
        print(f"Error fetching email for user {user_id}: {str(e)}")
    return None

def send_email(top_bidders, auction_item):
    try:
        num_bidders = len(top_bidders)
        bidders_to_show = min(num_bidders, 3)
        bidders_text = f"Here are the top {bidders_to_show} bidders:"

        leaderboard_table = "\n".join(
            [
                f"""
                <tr style="background-color: {'#f9f9f9' if i % 2 == 0 else '#ffffff'};">
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{i+1}</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{bidder['user_name']}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">${bidder['bid_amount']:.2f}</td>
                </tr>
                """
                for i, bidder in enumerate(top_bidders[:bidders_to_show])
            ]
        )

        for bidder in top_bidders:
            email = bidder.get("email")
            user_name = bidder.get("user_name", "Participant")
            if not email:
                print(f"Skipping bidder without email: {bidder}")
                continue

            body_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; background-color: #f4f4f4; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                        <h2 style="color: #333;">Hi {user_name},</h2>
                        <p style="color: #555;">Thank you for taking part in the auction.</p>
                        <p style="color: #555;">The auction for <strong style="color: #007bff;">{auction_item}</strong> has ended. {bidders_text}</p>
                        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background-color: #fdfdfd;">
                            <thead>
                                <tr style="background-color: #007bff; color: white;">
                                    <th style="padding: 10px; border: 1px solid #ddd;">Rank</th>
                                    <th style="padding: 10px; border: 1px solid #ddd;">User Name</th>
                                    <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Bid Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {leaderboard_table}
                            </tbody>
                        </table>
                        <p style="color: #555;">We hope to see you again in future auctions!</p>
                        <div style="text-align: center; margin-top: 20px;">
                            <a href="https://flash-bids.com/dashboard" style="background-color: #007bff; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; display: inline-block;">View More Auctions</a>
                        </div>
                        <p style="color: #aaa; font-size: 12px; text-align: center; margin-top: 20px;">&copy; 2024 Auction Platform, All rights reserved.</p>
                    </div>
                </body>
            </html>
            """

            ses.send_email(
                Source=SES_SENDER_EMAIL,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": f"Results for the Auction {auction_item}"},
                    "Body": {"Html": {"Data": body_html}},
                },
            )
            print(f"Email sent to {email}")
    except ClientError as e:
        print(f"Error sending email: {str(e)}")

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

def send_websocket_message(auction_id, message):
    """
    Sends a WebSocket message to the all client connected to particular auction using API Gateway Management API.
    """
    try:
        user_connections_table = dynamodb.Table("user-connections")

        response = user_connections_table.scan(
            FilterExpression="auction_id = :auction_id",
            ExpressionAttributeValues={":auction_id": auction_id},
        )
        connections = response.get("Items", [])
        print(f"Connections {connections}")

        if not connections:
            print(f"No active connections for auction {auction_id}.")
        else:

            
            for connection in connections:
                connection_id = connection["connection_id"]
                apigateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message),
                )
        
    except boto3.exceptions.Boto3Error as e:
        print(f"WebSocket error: {str(e)}")
        if "GoneException" in str(e):
            print(f"Connection {connection_id} is no longer valid.")
            
    except Exception as e:
        print(f"Unexpected error sending WebSocket message: {str(e)}")

def get_top_bidders(leaderboard_data):
    """
    Fetch the top bidders by bid_amount from leaderboard_data.
    If participants are less than 3, return only up to 2 bidders.
    """
    try:
        
        sorted_bids = sorted(leaderboard_data, key=lambda x: x["bid_amount"], reverse=True)

        
        max_bidders = 3 if len(sorted_bids) >= 3 else 2

        
        top_bidders = sorted_bids[:max_bidders]

        return top_bidders
    except Exception as e:
        print(f"Error fetching top bidders: {str(e)}")
        return []


def save_to_s3(bucket_name, auction_id, data):
    """
    Save auction data to S3 in JSON format.
    """
    file_name = f"bid_placement_history/{auction_id}.json"
    try:
        
        data = convert_decimal_and_timestamp(data)
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=json.dumps(data),
            ContentType="application/json"
        )
        print(f"Data for auction {auction_id} saved to S3 as {file_name}")
    except ClientError as e:
        print(f"Error saving data to S3: {str(e)}")
        raise e

def get_auction_details(auction_id):
    """
    Fetch auction details from the RDS auction table using the auction_id.
    """
    try:
        connection = connect_to_rds()
        with connection.cursor() as cursor:
            cursor.execute("SELECT auction_item FROM auction WHERE auction_id = %s", (auction_id,))
            auction_details = cursor.fetchone()
            return auction_details
    except Exception as e:
        print(f"Error fetching auction details: {str(e)}")
        return None
    finally:
        if connection:
            connection.close()

def delete_sqs_queue(auction_id):
    """
    Deletes the specified SQS queue dynamically based on the auction_id.
    """
    queue_name = f"AuctionActionsQueue-{auction_id}.fifo"  
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        
        
        sqs.delete_queue(QueueUrl=queue_url)
        print(f"Queue {queue_name} has been deleted successfully.")
    except ClientError as e:
        print(f"Error deleting queue {queue_name}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error deleting queue {queue_name}: {str(e)}")



def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    auction_id = event["auction_id"]
    auction_data = auction_table.get_item(Key={"auction_id": auction_id}).get("Item")

    if not auction_data:
        print(f"Auction {auction_id} not found in DynamoDB.")
        return

    
    end_time_str = auction_data.get("auction_end_time")
    if not end_time_str:
        print(f"Auction {auction_id} does not have a start time.")
        return {
        "statusCode": 400,
        "body": json.dumps({"error": "Auction does not have a start time."}),
        }

    end_time = parser.parse(end_time_str)
    current_time = datetime.now(timezone.utc)
    sleep_duration = (end_time - current_time).total_seconds()

    if sleep_duration > 0:
        print(f"Sleeping for {sleep_duration} seconds until auction start time.")
        time.sleep(sleep_duration)
    else:
        print(f"Auction {auction_id} start time has already passed.")

    
    auction_table.update_item(
        Key={"auction_id": auction_id},
        UpdateExpression="SET auction_status = :status",
        ExpressionAttributeValues={":status": "ENDED"},
    )
    
    leaderboard_table = dynamodb.Table("AuctionLeaderboards")
    response = leaderboard_table.query(
        KeyConditionExpression="auction_id = :auction_id",
        ExpressionAttributeValues={":auction_id": auction_id},
    )
    leaderboard_data = response.get("Items", [])

    
    auction_details = get_auction_details(auction_id)
    auction_item = auction_details.get("auction_item", "Auction Item") if auction_details else "Auction Item"


    
    save_to_s3(S3_BUCKET_NAME, auction_id, leaderboard_data)
    

    
    participant_emails = []
    for participant in leaderboard_data:
        email = get_user_email(participant["user_id"])
        if email:
            participant_emails.append(email)
    

    message = {
        "auction_id": auction_id,
        "auction_status": "ENDED",
        "message": "Auction has ENDED.",
    }

    send_websocket_message(auction_id, message)

    
    top_bidders = get_top_bidders(leaderboard_data)
    for i, bidder in enumerate(top_bidders, start=1):
        print(f"{i}. User: {bidder['user_name']}, Bid Amount: {bidder['bid_amount']}")

    
    for bidder in top_bidders:
        bidder['email'] = get_user_email(bidder['user_id'])

    
    send_email(top_bidders, auction_item)  

    
    connection = connect_to_rds()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE auction SET is_active = 0 WHERE auction_id = %s", (auction_id,)
        )
        connection.commit()

    delete_eventbridge_rule(f"EndAuction_{auction_id}")

    
    delete_sqs_queue(auction_id)