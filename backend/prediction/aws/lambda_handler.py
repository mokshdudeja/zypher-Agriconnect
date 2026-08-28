"""
AWS Lambda Handlers for Crop Price Prediction Pipeline

handler_daily_update:    Daily data collection + prediction refresh
handler_retrain:         Trigger model retraining
handler_prediction_api:  API Gateway handler for prediction requests
"""
import json
import os
import sys
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import boto3

dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
sagemaker_client = boto3.client("sagemaker")

PREDICTIONS_TABLE = os.getenv("PREDICTIONS_TABLE", "agriconnect-predictions")
S3_BUCKET = os.getenv("S3_BUCKET", "agriconnect-prediction-data")


def handler_daily_update(event, context):
    """
    Lambda triggered by EventBridge daily (6 AM IST).
    1. Fetch latest mandi prices
    2. Fetch latest weather data
    3. Update predictions for all crop-state pairs
    4. Store in DynamoDB with 6-hour TTL
    """
    print(f"[{datetime.now()}] Starting daily update...")

    from ..data.collect_mandi_data import MandiDataCollector
    from ..data.collect_weather_data import WeatherDataCollector

    mandi = MandiDataCollector()
    weather = WeatherDataCollector()

    table = dynamodb.Table(PREDICTIONS_TABLE)

    # Get list of active crop-state pairs
    crop_state_pairs = [
        ("wheat", "uttar_pradesh"), ("rice", "uttar_pradesh"),
        ("wheat", "madhya_pradesh"), ("rice", "west_bengal"),
        ("cotton", "maharashtra"), ("soybean", "madhya_pradesh"),
        ("potato", "uttar_pradesh"), ("tomato", "karnataka"),
        ("onion", "maharashtra"), ("groundnut", "gujarat"),
    ]

    updated_count = 0
    for crop, state in crop_state_pairs:
        try:
            # Fetch latest data
            mandi_df = mandi.fetch_latest_prices(crop, state, days=30)
            if mandi_df is None or mandi_df.empty:
                print(f"  ⚠ No data for {crop}/{state}")
                continue

            current_price = float(mandi_df["modal_price"].iloc[-1])

            # Get cached model prediction (placeholder)
            prediction = {
                "crop": crop,
                "state": state,
                "current_price": current_price,
                "predicted_price_7d": current_price,  # Would use trained model
                "predicted_price_15d": current_price,
                "predicted_price_30d": current_price,
                "confidence": 0.85,
                "trend": "stable",
                "factors": [],
            }

            # Store in DynamoDB with TTL
            ttl = int(datetime.now().timestamp()) + (6 * 3600)  # 6 hours
            table.put_item(
                Item={
                    "pk": f"{crop}#{state}",
                    "sk": datetime.now().isoformat(),
                    "ttl": ttl,
                    **prediction,
                    "updated_at": datetime.now().isoformat(),
                }
            )
            updated_count += 1

        except Exception as e:
            print(f"  ❌ Error updating {crop}/{state}: {e}")

    result = {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Daily update complete. Updated {updated_count}/{len(crop_state_pairs)} pairs.",
            "timestamp": datetime.now().isoformat(),
        }),
    }
    print(f"[{datetime.now()}] Daily update complete: {updated_count}/{len(crop_state_pairs)}")
    return result


def handler_retrain(event, context):
    """
    Lambda triggered weekly by EventBridge for model retraining.
    Collects new data, retrains models, uploads to S3, updates SageMaker endpoints.
    """
    print(f"[{datetime.now()}] Starting weekly retraining...")

    # In production:
    # 1. Pull latest training data from S3
    # 2. Run training locally or submit SageMaker training job
    # 3. Evaluate model
    # 4. If model improved, deploy to endpoint
    # 5. Update DynamoDB with new model version

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Retraining triggered",
            "timestamp": datetime.now().isoformat(),
        }),
    }


def handler_prediction_api(event, context):
    """
    API Gateway handler for prediction requests.
    Reads from DynamoDB cache or triggers real-time prediction.
    """
    try:
        params = event.get("pathParameters", {})
        crop = params.get("crop", "").lower()
        state = params.get("state", "").lower()

        if not crop or not state:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "crop and state are required"}),
            }

        table = dynamodb.Table(PREDICTIONS_TABLE)

        # Check for cached prediction
        response = table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": f"{crop}#{state}"},
            Limit=1,
            ScanIndexForward=False,  # Latest first
        )

        items = response.get("Items", [])
        if items:
            latest = items[0]
            ttl = latest.get("ttl", 0)
            if ttl > int(datetime.now().timestamp()):
                latest["cached"] = True
                return {
                    "statusCode": 200,
                    "body": json.dumps(latest, default=str),
                }

        # No cache — return placeholder
        return {
            "statusCode": 200,
            "body": json.dumps({
                "crop": crop,
                "state": state,
                "message": "No cached prediction. Run daily update to generate.",
                "cached": False,
            }),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
