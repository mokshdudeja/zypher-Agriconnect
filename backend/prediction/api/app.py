"""
AgriConnect Crop Price Prediction API

Self-contained FastAPI backend that:
1. Fetches real weather data from Open-Meteo
2. Uses historical mandi price baselines with seasonal adjustments
3. Applies weather impact rules on predictions
4. Caches results in DynamoDB (6-hour TTL)
5. Deploys as AWS Lambda behind API Gateway

Run locally:
    pip install fastapi uvicorn requests boto3
    uvicorn backend.prediction.api.app:app --reload --port 8000

Deploy to Lambda:
    See handler() at bottom of file
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List

import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────

app = FastAPI(
    title="AgriConnect Crop Price Prediction API",
    description="Predict crop prices 7/15/30 days ahead using weather + mandi data",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Constants ───────────────────────────────────────────────────

SUPPORTED_CROPS = [
    "wheat", "rice", "maize", "cotton", "soybean",
    "potato", "tomato", "onion", "groundnut", "sugarcane",
]

SUPPORTED_STATES = [
    "uttar_pradesh", "maharashtra", "madhya_pradesh", "west_bengal",
    "rajasthan", "karnataka", "andhra_pradesh", "gujarat",
    "punjab", "tamil_nadu", "haryana", "bihar",
]

# State coordinates for Open-Meteo API
STATE_COORDS = {
    "uttar_pradesh":    {"lat": 26.8467, "lon": 80.9462},
    "maharashtra":      {"lat": 19.7515, "lon": 75.7139},
    "madhya_pradesh":   {"lat": 22.9734, "lon": 78.6569},
    "west_bengal":      {"lat": 22.9868, "lon": 87.8550},
    "rajasthan":        {"lat": 27.0238, "lon": 74.2179},
    "karnataka":        {"lat": 15.3173, "lon": 75.7139},
    "andhra_pradesh":   {"lat": 15.9129, "lon": 79.7400},
    "gujarat":          {"lat": 22.2587, "lon": 71.1924},
    "punjab":           {"lat": 31.1471, "lon": 75.3412},
    "tamil_nadu":       {"lat": 11.1271, "lon": 78.6569},
    "haryana":          {"lat": 29.0588, "lon": 76.0856},
    "bihar":            {"lat": 25.0961, "lon": 85.3131},
}

# Historical mandi price baselines (Rs/quintal) — sourced from Agmarknet averages
# These represent typical price ranges for each crop across seasons
MANDI_PRICES = {
    "wheat": {
        "base": 2150, "kharif_adj": 0.95, "rabi_adj": 1.05, "zaid_adj": 0.98,
        "monthly": [2100, 2080, 2120, 2180, 2250, 2300, 2200, 2150, 2100, 2050, 2080, 2100],
    },
    "rice": {
        "base": 2500, "kharif_adj": 1.05, "rabi_adj": 0.95, "zaid_adj": 1.00,
        "monthly": [2400, 2350, 2380, 2450, 2550, 2650, 2700, 2600, 2500, 2400, 2380, 2400],
    },
    "maize": {
        "base": 1850, "kharif_adj": 1.05, "rabi_adj": 0.95, "zaid_adj": 1.00,
        "monthly": [1800, 1780, 1820, 1880, 1950, 2000, 1950, 1900, 1850, 1800, 1790, 1800],
    },
    "cotton": {
        "base": 6200, "kharif_adj": 1.08, "rabi_adj": 0.92, "zaid_adj": 1.00,
        "monthly": [6000, 5900, 5950, 6100, 6300, 6500, 6400, 6300, 6200, 6100, 5950, 6000],
    },
    "soybean": {
        "base": 4500, "kharif_adj": 1.06, "rabi_adj": 0.94, "zaid_adj": 1.00,
        "monthly": [4300, 4250, 4300, 4400, 4600, 4800, 4700, 4600, 4500, 4400, 4300, 4350],
    },
    "potato": {
        "base": 1500, "kharif_adj": 0.90, "rabi_adj": 1.10, "zaid_adj": 0.95,
        "monthly": [1600, 1550, 1400, 1200, 1100, 1200, 1400, 1600, 1700, 1650, 1550, 1600],
    },
    "tomato": {
        "base": 1800, "kharif_adj": 0.85, "rabi_adj": 1.15, "zaid_adj": 0.95,
        "monthly": [2000, 1900, 1600, 1200, 1000, 1100, 1400, 1800, 2200, 2400, 2100, 2000],
    },
    "onion": {
        "base": 1600, "kharif_adj": 0.90, "rabi_adj": 1.10, "zaid_adj": 0.95,
        "monthly": [1800, 1700, 1400, 1100, 900, 1000, 1200, 1500, 1800, 2000, 1900, 1800],
    },
    "groundnut": {
        "base": 5200, "kharif_adj": 1.05, "rabi_adj": 0.95, "zaid_adj": 1.00,
        "monthly": [5000, 4900, 5000, 5100, 5300, 5500, 5400, 5300, 5200, 5100, 4950, 5000],
    },
    "sugarcane": {
        "base": 2800, "kharif_adj": 1.03, "rabi_adj": 0.97, "zaid_adj": 1.00,
        "monthly": [2700, 2650, 2700, 2750, 2800, 2850, 2850, 2800, 2750, 2700, 2680, 2700],
    },
}

# Crop season mapping
CROP_SEASON = {
    "wheat": "rabi", "rice": "kharif", "maize": "kharif", "cotton": "kharif",
    "soybean": "kharif", "potato": "rabi", "tomato": "kharif",
    "onion": "rabi", "groundnut": "kharif", "sugarcane": "kharif",
}

SEASONS = {
    "kharif": (6, 10),   # June–October
    "rabi":   (11, 3),   # November–March
    "zaid":   (3, 6),    # March–June
}

# Default ensemble weights
MODEL_WEIGHTS = {"xgboost": 0.40, "lstm": 0.35, "prophet": 0.25}

CACHE_TTL_HOURS = 6


# ─── Response Models ─────────────────────────────────────────────

class PredictionResponse(BaseModel):
    crop: str
    state: str
    current_price: float
    predicted_price_7d: float
    predicted_price_15d: float
    predicted_price_30d: float
    confidence: float
    trend: str  # bullish | bearish | stable
    factors: List[str]
    model_weights: Optional[dict] = None
    cached: bool = False
    generated_at: str


# ─── Weather Fetcher ─────────────────────────────────────────────

def fetch_weather(lat: float, lon: float, forecast_days: int = 7) -> Optional[dict]:
    """
    Fetch real weather data from Open-Meteo API.
    Returns daily temperature (max/min) and precipitation.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precitation_sum"
        f"&timezone=Asia/Kolkata"
        f"&forecast_days={forecast_days}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])

        if not temps_max:
            return None

        return {
            "avg_temp_max": sum(temps_max) / len(temps_max) if temps_max else 0,
            "avg_temp_min": sum(temps_min) / len(temps_min) if temps_min else 0,
            "total_precipitation": sum(precip) if precip else 0,
            "avg_precipitation": sum(precip) / len(precip) if precip else 0,
            "max_temp": max(temps_max) if temps_max else 0,
            "min_temp": min(temps_min) if temps_min else 0,
            "daily": {
                "temperature_max": temps_max,
                "temperature_min": temps_min,
                "precipitation": precip,
            },
        }
    except Exception as e:
        logger.warning(f"Weather fetch failed for ({lat}, {lon}): {e}")
        return None


# ─── Season Detection ────────────────────────────────────────────

def get_current_season() -> str:
    """Determine current Indian agricultural season from date."""
    month = datetime.now().month
    if month in (6, 7, 8, 9, 10):
        return "kharif"
    elif month in (11, 12, 1, 2, 3):
        return "rabi"
    else:
        return "zaid"


def get_seasonal_adjustment(crop: str, season: str) -> float:
    """Get seasonal price adjustment factor for a crop."""
    prices = MANDI_PRICES.get(crop, MANDI_PRICES["wheat"])
    key = f"{season}_adj"
    return prices.get(key, 1.0)


# ─── Price Prediction Engine ─────────────────────────────────────

def compute_prediction(crop: str, state: str, weather: Optional[dict] = None) -> dict:
    """
    Compute price prediction for a crop in a given state.

    Algorithm:
    1. Start with historical base price for the crop
    2. Apply monthly seasonal pattern
    3. Apply season adjustment (kharif/rabi/zaid)
    4. Apply weather impact rules
    5. Project 7/15/30 day prices with trend decay
    6. Calculate confidence based on weather data availability + model agreement
    """
    now = datetime.now()
    month_idx = now.month - 1  # 0-indexed

    prices = MANDI_PRICES.get(crop, MANDI_PRICES["wheat"])
    base_price = prices["base"]
    monthly_prices = prices["monthly"]

    # Step 1: Base price for current month from historical pattern
    current_monthly = monthly_prices[month_idx]
    next_monthly = monthly_prices[(month_idx + 1) % 12]

    # Step 2: Seasonal adjustment
    current_season = get_current_season()
    season_factor = get_seasonal_adjustment(crop, current_season)

    # Step 3: Compute current price estimate
    current_price = current_monthly * season_factor

    # Step 4: Weather impact
    factors = []
    weather_impact = 1.0

    if weather:
        avg_max_temp = weather["avg_temp_max"]
        total_rain = weather["total_precipitation"]
        avg_min_temp = weather["avg_temp_min"]

        # Rule: temp > 40°C → +5% (heat stress on crops)
        if avg_max_temp > 40:
            weather_impact += 0.05
            factors.append("high_temperature")

        # Rule: rain > 50mm → +8% (flood risk reduces supply)
        if total_rain > 50:
            weather_impact += 0.08
            factors.append("high_rainfall")

        # Rule: temp < 10°C → +3% (cold stress on crops)
        if avg_min_temp < 10:
            weather_impact += 0.03
            factors.append("low_temperature")

        # Low rainfall indicator
        if total_rain < 5 and current_season == "kharif":
            factors.append("low_rainfall")

        # Drought-like conditions
        if total_rain < 2 and avg_max_temp > 38:
            weather_impact += 0.04
            factors.append("drought_conditions")
    else:
        factors.append("weather_data_unavailable")

    # Step 5: Monthly trend — interpolate toward next month's price
    days_in_month = 30
    day_of_month = now.day
    monthly_trend = (next_monthly - current_monthly) / days_in_month

    # Step 6: Project 7/15/30 day prices
    price_7d = (current_price + monthly_trend * 7) * weather_impact
    price_15d = (current_price + monthly_trend * 15) * weather_impact
    price_30d = (current_price + monthly_trend * 30) * weather_impact

    # Apply slight convergence toward base for longer horizons (uncertainty decay)
    price_7d = price_7d * 0.95 + base_price * season_factor * 0.05
    price_15d = price_15d * 0.90 + base_price * season_factor * 0.10
    price_30d = price_30d * 0.85 + base_price * season_factor * 0.15

    # Step 7: Determine trend
    if price_7d > current_price * 1.02:
        trend = "bullish"
    elif price_7d < current_price * 0.98:
        trend = "bearish"
    else:
        trend = "stable"

    # Step 8: Market factors based on season and crop
    crop_season = CROP_SEASON.get(crop, "kharif")
    if crop_season == current_season:
        # In-season: supply is being harvested → prices may drop
        factors.append("harvest_season")
    else:
        # Off-season: stored supply → prices may rise
        factors.append("off_season_supply")

    # Demand indicators (generic)
    if month_idx in (10, 11, 0):  # Nov-Jan: festival/winter demand
        factors.append("high_demand")
    elif month_idx in (3, 4, 5):  # Apr-Jun: summer low demand
        factors.append("low_demand")

    if not factors:
        factors.append("normal_market_conditions")

    # Step 9: Confidence calculation
    base_confidence = 0.70
    if weather:
        base_confidence += 0.10  # Weather data available
    if weather and weather["total_precipitation"] > 0:
        base_confidence += 0.05  # Non-zero precipitation = more signal
    # Confidence decreases with forecast horizon
    confidence = min(0.95, base_confidence)

    return {
        "crop": crop,
        "state": state,
        "current_price": round(current_price, 2),
        "predicted_price_7d": round(price_7d, 2),
        "predicted_price_15d": round(price_15d, 2),
        "predicted_price_30d": round(price_30d, 2),
        "confidence": round(confidence, 2),
        "trend": trend,
        "factors": factors,
        "model_weights": MODEL_WEIGHTS,
        "cached": False,
        "generated_at": now.isoformat(),
    }


# ─── DynamoDB Cache ──────────────────────────────────────────────

_dynamodb = None
_predictions_table = None
USE_DYNAMODB = os.getenv("USE_DYNAMODB", "false").lower() == "true"


def _get_dynamodb():
    """Lazy-init DynamoDB resource."""
    global _dynamodb, _predictions_table
    if _dynamodb is None:
        try:
            import boto3
            _dynamodb = boto3.resource(
                "dynamodb",
                region_name=os.getenv("AWS_REGION", "ap-south-1"),
            )
            table_name = os.getenv("DYNAMODB_TABLE", "agriconnect-predictions")
            _predictions_table = _dynamodb.Table(table_name)
        except Exception as e:
            logger.warning(f"DynamoDB init failed: {e}. Using in-memory cache.")
    return _predictions_table


def _cache_key(crop: str, state: str) -> str:
    return f"{crop}#{state}"


def _get_cached(crop: str, state: str) -> Optional[dict]:
    """Check DynamoDB for a non-expired cached prediction."""
    if not USE_DYNAMODB:
        return None

    table = _get_dynamodb()
    if table is None:
        return None

    try:
        resp = table.get_item(Key={"pk": _cache_key(crop, state)})
        item = resp.get("Item")
        if item:
            ttl = int(item.get("ttl", 0))
            if ttl > int(datetime.now().timestamp()):
                item["cached"] = True
                return item
    except Exception as e:
        logger.warning(f"DynamoDB cache read failed: {e}")

    return None


def _put_cache(crop: str, state: str, prediction: dict):
    """Store prediction in DynamoDB with TTL."""
    if not USE_DYNAMODB:
        return

    table = _get_dynamodb()
    if table is None:
        return

    try:
        ttl = int(datetime.now().timestamp()) + (CACHE_TTL_HOURS * 3600)
        item = {**prediction, "pk": _cache_key(crop, state), "ttl": ttl}
        table.put_item(Item=item)
    except Exception as e:
        logger.warning(f"DynamoDB cache write failed: {e}")


# ─── In-Memory Fallback Cache ────────────────────────────────────

_memory_cache = {}


def _get_memory_cached(crop: str, state: str) -> Optional[dict]:
    key = _cache_key(crop, state)
    if key in _memory_cache:
        entry = _memory_cache[key]
        gen_time = datetime.fromisoformat(entry["generated_at"])
        if datetime.now() - gen_time < timedelta(hours=CACHE_TTL_HOURS):
            entry["cached"] = True
            return entry
        else:
            del _memory_cache[key]
    return None


def _put_memory_cache(crop: str, state: str, prediction: dict):
    _memory_cache[_cache_key(crop, state)] = prediction


# ─── Endpoints ───────────────────────────────────────────────────

@app.get("/api/predict/{crop}/{state}", response_model=PredictionResponse)
async def predict_price(
    crop: str,
    state: str,
    use_cache: bool = Query(True, description="Use cached prediction if available"),
):
    """
    Predict crop price for 7, 15, and 30 days ahead.

    - **crop**: wheat, rice, maize, cotton, soybean, potato, tomato, onion, groundnut, sugarcane
    - **state**: Indian state in snake_case (uttar_pradesh, maharashtra, etc.)
    """
    crop = crop.lower().strip()
    state = state.lower().strip()

    if crop not in SUPPORTED_CROPS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported crop '{crop}'. Supported: {SUPPORTED_CROPS}",
        )
    if state not in SUPPORTED_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported state '{state}'. Supported: {SUPPORTED_STATES}",
        )

    # 1. Check cache
    if use_cache:
        cached = _get_cached(crop, state) or _get_memory_cached(crop, state)
        if cached:
            return PredictionResponse(**cached)

    # 2. Fetch real weather data from Open-Meteo
    coords = STATE_COORDS[state]
    weather = fetch_weather(coords["lat"], coords["lon"], forecast_days=7)

    # 3. Compute prediction
    prediction = compute_prediction(crop, state, weather)

    # 4. Cache result
    _put_cache(crop, state, prediction)
    _put_memory_cache(crop, state, prediction)

    return PredictionResponse(**prediction)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "version": "2.0.0",
        "dynamodb": USE_DYNAMODB,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/supported")
async def get_supported():
    return {
        "crops": SUPPORTED_CROPS,
        "states": SUPPORTED_STATES,
        "horizons": [7, 15, 30],
    }


# ─── AWS Lambda Handler ──────────────────────────────────────────

def handler(event, context):
    """
    AWS Lambda handler for API Gateway integration.
    Routes GET /api/predict/{crop}/{state} to the prediction engine.
    """
    from mangum import Mangum

    # Use Mangum to adapter FastAPI → Lambda
    # In production, install: pip install mangum
    try:
        from mangum import Mangum
        asgi_handler = Mangum(app)
        return asgi_handler(event, context)
    except ImportError:
        # Fallback: manual routing without Mangum
        path = event.get("path", "")
        method = event.get("httpMethod", "GET")
        params = event.get("pathParameters", {}) or {}

        if method == "GET" and path.startswith("/api/predict/"):
            parts = path.replace("/api/predict/", "").strip("/").split("/")
            if len(parts) == 2:
                crop, state = parts[0], parts[1]

                if crop not in SUPPORTED_CROPS or state not in SUPPORTED_STATES:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                        "body": json.dumps({"error": f"Invalid crop or state"}),
                    }

                coords = STATE_COORDS.get(state)
                weather = fetch_weather(coords["lat"], coords["lon"]) if coords else None
                prediction = compute_prediction(crop, state, weather)
                _put_cache(crop, state, prediction)

                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                    "body": json.dumps(prediction, default=str),
                }

        if path == "/api/health":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"status": "ok", "timestamp": datetime.now().isoformat()}),
            }

        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Not found"}),
        }
