from datetime import datetime
import json
import uuid
import boto3
import time
from datetime import timedelta
from time_helper import calculate_remaining_time
from botocore.exceptions import ClientError
from leaderboard_helper import broadcast_leaderboard
import pymysql
import os

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
auction_table = dynamodb.Table('auction-connections')
user_table = dynamodb.Table('user-connections')

# RDS Connection Parameters (set in environment variables)
RDS_HOST = os.environ['RDS_HOST']
RDS_USER = os.environ['RDS_USER']
RDS_PASSWORD = os.environ['RDS_PASSWORD']
RDS_DB_NAME = os.environ['RDS_DB_NAME']


# Custom JSON encoder to handle datetime serialization

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()  # Convert datetime to ISO 8601 string
        return super().default(obj)

# Establish RDS Connection


def get_rds_connection():
    return pymysql.connect(
        host=RDS_HOST,
        user=RDS_USER,
        password=RDS_PASSWORD,
        database=RDS_DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


def lambda_handler(event, context):
    """
    Handles WebSocket events for $connect, $disconnect, and $default.
    """
    route_key = event['requestContext']['routeKey']
    connection_id = event['requestContext']['connectionId']
    response = {}
    print("Event:", event['requestContext'])

    if route_key == '$connect':
        # Handle $connect
        print(f"Connection established: {connection_id}")
        response = {
            'statusCode': 200,
            'body': json.dumps({'message': 'Connection successful!', 'connectionId': connection_id})
        }

    elif route_key == '$disconnect':
        # Handle $disconnect

        # Query instead of scan for better performance
        user_items = user_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('connection_id').eq(connection_id)
        )

        for item in user_items['Items']:
            auction_id = item['auction_id']
            auction_connection_id = item['auction_connectionId']

            # Delete the connectionId entry from UserConnections
            user_table.delete_item(Key={'connection_id': connection_id, 'auction_id': auction_id})
            print(f"Removed connection {connection_id} from auction {auction_id}")
        print(f"Disconnected: {connection_id}")

        response = {
            'statusCode': 200,
            'body': json.dumps({'message': 'Disconnected successfully!'})
        }

    elif route_key == '$default':
        # Handle $default
        print("Before Try")
        try:
            raw_body = event.get('body', '{}')
            body = json.loads(raw_body) if raw_body.strip() else {}
            action = body.get('action')
            auction_id = body.get('auction_id')
            user_id = body.get('user_id')
            print("Raw Body: ", raw_body)
            print("body:", body)
            print("in try")
            if action == 'join':
                print("in join")
                auction_id = body.get('auction_id')
                user_id = body.get('user_id')
                print("in join 2")

                if not auction_id or not user_id:
                    raise ValueError("Missing required fields: auction_id or user_id")
                print("Auction ID:", auction_id)
                print("User ID:", user_id)

                # Check if an auction_connectionId exists
                auction_response = auction_table.get_item(Key={'auction_id': auction_id})
                print("Auction Response:", auction_response)
                auction_connection_id = auction_response.get('Item', {}).get('auction_connectionId')
                print("Auction Connection ID:", auction_connection_id)
                broadcast_leaderboard(auction_id, connection_id)
                # auction_end_time = time.time() + 15*60
                # remaining_timedelta = timedelta(seconds=int(remaining))
                # formatted_time = str(remaining_timedelta)
                auction_end_time = auction_response.get('Item', {}).get('auction_end_time')
                remaining_time = calculate_remaining_time(auction_end_time)
                auction_status = auction_response.get('Item', {}).get('auction_status')  # {'about_to_start', 'in_progress', 'ended'}
                print(f"Remaining Time: {remaining_time}")

                # Create auction_connectionId if not present
                if not auction_connection_id:
                    auction_connection_id = str(uuid.uuid4())
                    auction_table.update_item(
                        Key={'auction_id': auction_id},
                        UpdateExpression="auction_connection_id = :id",
                        ExpressionAttributeValues={
                            ":cid": auction_connection_id
                        }

                    )
                    # 'auction_connectionId': auction_connection_id,
                    # 'auction_status': auction_status,
                    # # 'auction_start_time': auction_start_time,
                    # 'auction_end_time': auction_end_time,
                    # 'remaining_time': remaining_time,

                    print(f"Created auction_connectionId {auction_connection_id} for auction {auction_id}")

                # Map connectionId to auction
                user_table.put_item(Item={
                    'connection_id': connection_id,
                    'auction_connectionId': auction_connection_id,
                    'auction_id': auction_id,
                    'user_id': user_id
                })
                print(f"User {user_id} joined auction {auction_id} with connection {connection_id}")

                response = {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': f'Joined auction {auction_id}',
                        'auction_connectionId': auction_connection_id,
                        'auction_status': auction_status,
                        # 'auction_start_time': auction_start_time,
                        'auction_end_time': auction_end_time,
                        'remaining_time': remaining_time
                    })
                }
            else:
                response = {
                    'statusCode': 400,
                    'body': json.dumps({'message': 'Unknown or missing action'})
                }
        except ValueError as ve:
            print(f"Validation error: {ve}")
            response = {
                'statusCode': 400,
                'body': json.dumps({'message': str(ve)})
            }

        except ClientError as e:
            print(f"DynamoDB error: {e.response['Error']['Message']}")
            response = {
                'statusCode': 500,
                'body': json.dumps({'message': 'Internal server error'})
            }

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            response = {
                'statusCode': 400,
                'body': json.dumps({'message': 'Invalid JSON in request'})
            }
        # Describe the table
        # Initialize DynamoDB client
        # dynamodb_client = boto3.client('dynamodb')
        # auction_table = 'auction-connections'
        # response = dynamodb_client.describe_table(TableName=auction_table)

        # # Extract table details
        # table_description = response['Table']

        # # Print the schema
        # print("Table Description:")
        # print(json.dumps(table_description, cls=CustomJSONEncoder))
    else:
        # Handle unknown routes (optional)
        print(f"Unknown route: {route_key}")
        response = {
            'statusCode': 400,
            'body': json.dumps({'message': 'Unknown route'})
        }

    return response
