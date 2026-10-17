import json
import boto3
import os
from decimal import Decimal
from datetime import datetime
from boto3.dynamodb.conditions import Key

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def ensure_dynamodb_data():
    """Ensure DynamoDB has sample data (idempotent)"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
        
        # Check if table already has data
        response = table.scan(Limit=1)
        if response['Items']:
            print("DynamoDB table already has data. Skipping initialization.")
            return True
        
        print("Initializing DynamoDB with sample data...")
        
        # Sample data
        users = [
            {'UserID': 'user-001', 'UserName': 'Alice Johnson', 'Email': 'alice@example.com', 'City': 'New York', 'Country': 'USA'},
            {'UserID': 'user-002', 'UserName': 'Bob Smith', 'Email': 'bob@example.com', 'City': 'London', 'Country': 'UK'},
            {'UserID': 'user-003', 'UserName': 'Carol Davis', 'Email': 'carol@example.com', 'City': 'Toronto', 'Country': 'Canada'},
            {'UserID': 'user-004', 'UserName': 'David Wilson', 'Email': 'david@example.com', 'City': 'Sydney', 'Country': 'Australia'},
            {'UserID': 'user-005', 'UserName': 'Eva Brown', 'Email': 'eva@example.com', 'City': 'Berlin', 'Country': 'Germany'}
        ]
        
        orders = [
            {'OrderID': 'order-001', 'UserID': 'user-001', 'ProductName': 'Laptop', 'Quantity': 1, 'Price': Decimal('999.99')},
            {'OrderID': 'order-002', 'UserID': 'user-001', 'ProductName': 'Mouse', 'Quantity': 2, 'Price': Decimal('25.50')},
            {'OrderID': 'order-003', 'UserID': 'user-002', 'ProductName': 'Keyboard', 'Quantity': 1, 'Price': Decimal('75.00')},
            {'OrderID': 'order-004', 'UserID': 'user-003', 'ProductName': 'Monitor', 'Quantity': 2, 'Price': Decimal('299.99')},
            {'OrderID': 'order-005', 'UserID': 'user-002', 'ProductName': 'Headphones', 'Quantity': 1, 'Price': Decimal('150.00')},
            {'OrderID': 'order-006', 'UserID': 'user-004', 'ProductName': 'Tablet', 'Quantity': 1, 'Price': Decimal('399.99')},
            {'OrderID': 'order-007', 'UserID': 'user-005', 'ProductName': 'Phone', 'Quantity': 1, 'Price': Decimal('699.99')},
            {'OrderID': 'order-008', 'UserID': 'user-003', 'ProductName': 'Webcam', 'Quantity': 1, 'Price': Decimal('89.99')}
        ]
        
        # Create user lookup for denormalization
        user_lookup = {user['UserID']: user for user in users}
        
        # Insert denormalized orders (includes user data in each order)
        for order in orders:
            user_data = user_lookup[order['UserID']]
            denormalized_order = {
                'OrderID': order['OrderID'],
                'UserID': order['UserID'],
                'UserName': user_data['UserName'],
                'Email': user_data['Email'],
                'City': user_data['City'],
                'Country': user_data['Country'],
                'ProductName': order['ProductName'],
                'Quantity': order['Quantity'],
                'Price': order['Price'],
                'OrderDate': datetime.utcnow().isoformat(),
                'TotalAmount': order['Quantity'] * order['Price']
            }
            
            table.put_item(Item=denormalized_order)
        
        print(f"Initialized DynamoDB with {len(orders)} denormalized orders")
        return True
        
    except Exception as e:
        print(f"DynamoDB initialization error: {str(e)}")
        return False

def lambda_handler(event, context):
    try:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
        }
        
        # Ensure DynamoDB has data (idempotent)
        setup_success = ensure_dynamodb_data()
        if not setup_success:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Failed to initialize DynamoDB data',
                    'database_type': 'NoSQL (DynamoDB)',
                    'architecture': 'Denormalized - User and Order data in single table'
                })
            }
        
        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
        
        # Scan table to get all orders (with denormalized user data)
        response = table.scan(Limit=10)
        orders = response['Items']
        
        # Get table statistics
        table_stats = table.meta.client.describe_table(TableName=table.name)
        item_count = table_stats['Table']['ItemCount']
        
        # Example: Query orders for a specific user using GSI
        if orders:
            sample_user_id = orders[0]['UserID']
            user_orders_response = table.query(
                IndexName='UserIndex',
                KeyConditionExpression=Key('UserID').eq(sample_user_id),
                Limit=5
            )
            user_orders = user_orders_response['Items']
        else:
            user_orders = []
            sample_user_id = None
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'database_type': 'NoSQL (DynamoDB)',
                'architecture': 'Denormalized - User and Order data in single table',
                'operation': 'Direct queries - no JOINs needed',
                'authentication': 'IAM roles and policies',
                'multi_az': 'Built-in across multiple AZs automatically',
                'statistics': {
                    'total_orders': item_count,
                    'results_returned': len(orders),
                    'sample_user_orders': len(user_orders)
                },
                'operations_performed': [
                    'Scan table for recent orders',
                    f'Query UserIndex for user {sample_user_id}' if sample_user_id else 'No user query (no data)'
                ],
                'all_orders': orders,
                'sample_user_orders': user_orders,
                'advantages': [
                    'Horizontal scaling and high performance',
                    'Flexible schema - no migrations needed',
                    'Built-in high availability',
                    'Serverless and fully managed'
                ],
                'considerations': [
                    'Data duplication in denormalized model',
                    'Limited query flexibility compared to SQL',
                    'Eventual consistency by default',
                    'Learning curve for NoSQL design patterns'
                ]
            }, default=decimal_default)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': str(e),
                'database_type': 'NoSQL (DynamoDB)',
                'message': 'Failed to query DynamoDB table'
            })
        }
