"""
DynamoDB Table Setup for Crop Price Predictions

Tables:
- agriconnect-predictions: Stores prediction results with TTL caching
"""
import boto3
import os


def create_predictions_table():
    """Create the predictions DynamoDB table."""
    dynamodb = boto3.client("dynamodb", region_name=os.getenv("AWS_REGION", "ap-south-1"))

    table_name = os.getenv("PREDICTIONS_TABLE", "agriconnect-predictions")

    try:
        dynamodb.describe_table(TableName=table_name)
        print(f"Table {table_name} already exists")
        return
    except dynamodb.exceptions.ResourceNotFoundException:
        pass

    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},   # crop#state
            {"AttributeName": "sk", "KeyType": "RANGE"},   # timestamp
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        Tags=[
            {"Key": "Project", "Value": "AgriConnect"},
        ],
    )

    # Wait for table to be active
    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=table_name)

    # Enable TTL
    dynamodb.update_time_to_live(
        TableName=table_name,
        TimeToLiveSpecification={
            "Enabled": True,
            "AttributeName": "ttl",
        },
    )

    print(f"✅ Created table: {table_name}")
    print(f"   Partition key: pk (crop#state)")
    print(f"   Sort key: sk (timestamp)")
    print(f"   TTL: ttl (6-hour cache)")


def create_model_registry_table():
    """Create table for model version tracking."""
    dynamodb = boto3.client("dynamodb", region_name=os.getenv("AWS_REGION", "ap-south-1"))
    table_name = "agriconnect-models"

    try:
        dynamodb.describe_table(TableName=table_name)
        print(f"Table {table_name} already exists")
        return
    except dynamodb.exceptions.ResourceNotFoundException:
        pass

    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "model_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "model_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    print(f"✅ Created table: {table_name}")


if __name__ == "__main__":
    create_predictions_table()
    create_model_registry_table()
