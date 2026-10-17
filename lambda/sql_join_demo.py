import json
import boto3
import pymysql
import os
from decimal import Decimal


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    # Handle other non-serializable types gracefully
    try:
        return str(obj)
    except:
        return None


def get_db_credentials():
    """Get database credentials from Secrets Manager"""
    secrets_client = boto3.client("secretsmanager")
    try:
        response = secrets_client.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])
        secret = json.loads(response["SecretString"])
        return secret["username"], secret["password"]
    except Exception as e:
        print(f"Error getting credentials: {str(e)}")
        return None, None


def ensure_database_setup(username, password):
    """Ensure database and tables exist with sample data"""
    try:
        # Connect without specifying database first
        connection = pymysql.connect(
            host=os.environ["DB_ENDPOINT"],
            port=int(os.environ["DB_PORT"]),
            user=username,
            password=password,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

        with connection:
            with connection.cursor() as cursor:
                # Create database if it doesn't exist
                cursor.execute("CREATE DATABASE IF NOT EXISTS ecommerce")
                cursor.execute("USE ecommerce")

                # Check if tables already have data
                cursor.execute(
                    "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = 'ecommerce' AND table_name = 'Users'"
                )
                users_table_exists = cursor.fetchone()["count"] > 0

                if users_table_exists:
                    cursor.execute("SELECT COUNT(*) as count FROM Users")
                    user_count = cursor.fetchone()["count"]
                    if user_count > 0:
                        print(
                            f"Database already populated with {user_count} users. Skipping initialization."
                        )
                        return True

                print("Initializing database with sample data...")

                # Create Users table (normalized)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Users (
                        UserID VARCHAR(50) PRIMARY KEY,
                        UserName VARCHAR(100) NOT NULL,
                        Email VARCHAR(100) NOT NULL,
                        City VARCHAR(50),
                        Country VARCHAR(50),
                        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create Orders table (normalized)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Orders (
                        OrderID VARCHAR(50) PRIMARY KEY,
                        UserID VARCHAR(50) NOT NULL,
                        ProductName VARCHAR(100) NOT NULL,
                        Quantity INT NOT NULL,
                        Price DECIMAL(10,2) NOT NULL,
                        OrderDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (UserID) REFERENCES Users(UserID)
                    )
                """
                )

                # Sample data
                users = [
                    {
                        "UserID": "user-001",
                        "UserName": "Alice Johnson",
                        "Email": "alice@example.com",
                        "City": "New York",
                        "Country": "USA",
                    },
                    {
                        "UserID": "user-002",
                        "UserName": "Bob Smith",
                        "Email": "bob@example.com",
                        "City": "London",
                        "Country": "UK",
                    },
                    {
                        "UserID": "user-003",
                        "UserName": "Carol Davis",
                        "Email": "carol@example.com",
                        "City": "Toronto",
                        "Country": "Canada",
                    },
                    {
                        "UserID": "user-004",
                        "UserName": "David Wilson",
                        "Email": "david@example.com",
                        "City": "Sydney",
                        "Country": "Australia",
                    },
                    {
                        "UserID": "user-005",
                        "UserName": "Eva Brown",
                        "Email": "eva@example.com",
                        "City": "Berlin",
                        "Country": "Germany",
                    },
                ]

                orders = [
                    {
                        "OrderID": "order-001",
                        "UserID": "user-001",
                        "ProductName": "Laptop",
                        "Quantity": 1,
                        "Price": 999.99,
                    },
                    {
                        "OrderID": "order-002",
                        "UserID": "user-001",
                        "ProductName": "Mouse",
                        "Quantity": 2,
                        "Price": 25.50,
                    },
                    {
                        "OrderID": "order-003",
                        "UserID": "user-002",
                        "ProductName": "Keyboard",
                        "Quantity": 1,
                        "Price": 75.00,
                    },
                    {
                        "OrderID": "order-004",
                        "UserID": "user-003",
                        "ProductName": "Monitor",
                        "Quantity": 2,
                        "Price": 299.99,
                    },
                    {
                        "OrderID": "order-005",
                        "UserID": "user-002",
                        "ProductName": "Headphones",
                        "Quantity": 1,
                        "Price": 150.00,
                    },
                    {
                        "OrderID": "order-006",
                        "UserID": "user-004",
                        "ProductName": "Tablet",
                        "Quantity": 1,
                        "Price": 399.99,
                    },
                    {
                        "OrderID": "order-007",
                        "UserID": "user-005",
                        "ProductName": "Phone",
                        "Quantity": 1,
                        "Price": 699.99,
                    },
                    {
                        "OrderID": "order-008",
                        "UserID": "user-003",
                        "ProductName": "Webcam",
                        "Quantity": 1,
                        "Price": 89.99,
                    },
                ]

                # Insert users
                for user in users:
                    cursor.execute(
                        """
                        INSERT IGNORE INTO Users (UserID, UserName, Email, City, Country)
                        VALUES (%(UserID)s, %(UserName)s, %(Email)s, %(City)s, %(Country)s)
                    """,
                        user,
                    )

                # Insert orders
                for order in orders:
                    cursor.execute(
                        """
                        INSERT IGNORE INTO Orders (OrderID, UserID, ProductName, Quantity, Price)
                        VALUES (%(OrderID)s, %(UserID)s, %(ProductName)s, %(Quantity)s, %(Price)s)
                    """,
                        order,
                    )

                connection.commit()
                print(
                    f"Initialized database with {len(users)} users and {len(orders)} orders"
                )
                return True

    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        return False


def lambda_handler(event, context):
    try:
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        }

        # Get database credentials
        username, password = get_db_credentials()
        if not username or not password:
            return {
                "statusCode": 500,
                "headers": headers,
                "body": json.dumps(
                    {
                        "error": "Failed to retrieve database credentials",
                        "database_type": "SQL (MySQL)",
                        "architecture": "Normalized - Separate Users and Orders tables",
                    }
                ),
            }

        # Ensure database is set up (idempotent)
        setup_success = ensure_database_setup(username, password)
        if not setup_success:
            return {
                "statusCode": 500,
                "headers": headers,
                "body": json.dumps(
                    {
                        "error": "Failed to initialize database",
                        "database_type": "SQL (MySQL)",
                        "architecture": "Normalized - Separate Users and Orders tables",
                    }
                ),
            }

        # Connect to MySQL for queries
        connection = pymysql.connect(
            host=os.environ["DB_ENDPOINT"],
            port=int(os.environ["DB_PORT"]),
            user=username,
            password=password,
            database="ecommerce",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

        with connection:
            with connection.cursor() as cursor:
                # Perform JOIN query to get user orders with user details
                join_query = """
                SELECT 
                    o.OrderID,
                    o.UserID,
                    u.UserName,
                    u.Email,
                    u.City,
                    u.Country,
                    o.ProductName,
                    o.Quantity,
                    o.Price,
                    o.OrderDate,
                    (o.Quantity * o.Price) as TotalAmount
                FROM Orders o
                INNER JOIN Users u ON o.UserID = u.UserID
                ORDER BY o.OrderDate DESC
                LIMIT 10
                """

                cursor.execute(join_query)
                results = cursor.fetchall()

                # Get table statistics
                cursor.execute("SELECT COUNT(*) as user_count FROM Users")
                user_count = cursor.fetchone()["user_count"]

                cursor.execute("SELECT COUNT(*) as order_count FROM Orders")
                order_count = cursor.fetchone()["order_count"]

                return {
                    "statusCode": 200,
                    "headers": headers,
                    "body": json.dumps(
                        {
                            "database_type": "SQL (MySQL)",
                            "architecture": "Normalized - Separate Users and Orders tables",
                            "operation": "INNER JOIN to combine user and order data",
                            "authentication": "Username/Password stored in Secrets Manager",
                            "multi_az": f'Configurable (currently: {"Enabled" if os.environ.get("MULTI_AZ", "false") == "true" else "Disabled"})',
                            "statistics": {
                                "total_users": user_count,
                                "total_orders": order_count,
                                "results_returned": len(results),
                            },
                            "query_executed": join_query.strip(),
                            "results": results,
                            "advantages": [
                                "ACID compliance ensures data consistency",
                                "Complex queries with JOINs",
                                "Referential integrity with foreign keys",
                                "Mature ecosystem and tooling",
                            ],
                            "considerations": [
                                "Requires schema design upfront",
                                "Vertical scaling limitations",
                                "More complex for highly distributed systems",
                            ],
                        },
                        default=decimal_default,
                    ),
                }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps(
                {
                    "error": str(e),
                    "database_type": "SQL (MySQL)",
                    "message": "Failed to execute SQL JOIN query",
                }
            ),
        }
