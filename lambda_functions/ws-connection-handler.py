import json


def lambda_handler(event, context):
    """
    Handles WebSocket events for $connect, $disconnect, and $default.
    """
    route_key = event['requestContext']['routeKey']
    connection_id = event['requestContext']['connectionId']
    response = {}

    if route_key == '$connect':
        # Handle $connect
        print(f"Connection established: {connection_id}")
        response = {
            'statusCode': 200,
            'body': json.dumps({'message': 'Connection successful!', 'connectionId': connection_id})
        }

    elif route_key == '$disconnect':
        # Handle $disconnect
        print(f"Disconnected: {connection_id}")
        response = {
            'statusCode': 200,
            'body': json.dumps({'message': 'Disconnected successfully!'})
        }

    elif route_key == '$default':
        # Handle $default
        print(f"Default route invoked by: {connection_id}")
        try:
            # Safely parse the body if it's not empty
            raw_body = event.get('body', '{}')
            body = json.loads(raw_body) if raw_body.strip() else {}
            print(f"Received message: {body}")
            response = {
                'statusCode': 200,
                'body': json.dumps({'message': 'Default route response', 'received': body,
                                    'connectionId': connection_id})
            }
        except json.JSONDecodeError as e:
            print(f"Failed to parse body: {e}")
            response = {
                'statusCode': 400,
                'body': json.dumps({'message': 'Invalid JSON in body'})
            }
    else:
        # Handle unknown routes (optional)
        print(f"Unknown route: {route_key}")
        response = {
            'statusCode': 400,
            'body': json.dumps({'message': 'Unknown route'})
        }

    return response
