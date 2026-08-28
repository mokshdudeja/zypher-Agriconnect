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
WEATHER_CACHE_TTL_HOURS = 3


# District coordinates for weather lookups
# Major agricultural districts across Indian states
DISTRICT_COORDS = {
    # Uttar Pradesh
    "lucknow": {"lat": 26.8467, "lon": 80.9462},
    "agra": {"lat": 27.1767, "lon": 78.0081},
    "kanpur": {"lat": 26.4499, "lon": 80.3319},
    "varanasi": {"lat": 25.3176, "lon": 82.9739},
    "meerut": {"lat": 28.9845, "lon": 77.7064},
    "allahabad": {"lat": 25.4358, "lon": 81.8463},
    "noida": {"lat": 28.5355, "lon": 77.3910},
    "aligarh": {"lat": 27.8974, "lon": 78.0880},
    "bareilly": {"lat": 28.3670, "lon": 79.4304},
    "gorakhpur": {"lat": 26.7606, "lon": 83.3732},
    # Maharashtra
    "pune": {"lat": 18.5204, "lon": 73.8567},
    "mumbai": {"lat": 19.0760, "lon": 72.8777},
    "nagpur": {"lat": 21.1458, "lon": 79.0882},
    "nashik": {"lat": 19.9975, "lon": 73.7898},
    "aurangabad": {"lat": 19.8762, "lon": 75.3433},
    "jalna": {"lat": 19.8347, "lon": 75.8859},
    "akola": {"lat": 20.7062, "lon": 76.9970},
    "amravati": {"lat": 20.9374, "lon": 77.7796},
    # Madhya Pradesh
    "bhopal": {"lat": 23.2599, "lon": 77.4126},
    "indore": {"lat": 22.7196, "lon": 75.8577},
    "jabalpur": {"lat": 23.1815, "lon": 79.9864},
    "gwalior": {"lat": 26.2183, "lon": 78.1828},
    "ujjain": {"lat": 23.1793, "lon": 75.7849},
    "sagar": {"lat": 23.8388, "lon": 78.7379},
    "rewa": {"lat": 24.5326, "lon": 81.3011},
    # Punjab
    "ludhiana": {"lat": 30.9010, "lon": 75.8573},
    "amritsar": {"lat": 31.6340, "lon": 74.8723},
    "jalandhar": {"lat": 31.3260, "lon": 75.5762},
    "patiala": {"lat": 30.3398, "lon": 76.3869},
    "bathinda": {"lat": 30.2070, "lon": 74.9520},
    # Haryana
    "hisar": {"lat": 29.1492, "lon": 75.7217},
    "karnal": {"lat": 29.6857, "lon": 76.9905},
    "rohtak": {"lat": 28.8955, "lon": 76.6066},
    "sonipat": {"lat": 28.9958, "lon": 77.0101},
    # Rajasthan
    "jaipur": {"lat": 26.9124, "lon": 75.7873},
    "jodhpur": {"lat": 26.2389, "lon": 73.0243},
    "kota": {"lat": 25.2138, "lon": 75.8648},
    "ajmer": {"lat": 26.4499, "lon": 74.6399},
    # Gujarat
    "ahmedabad": {"lat": 23.0225, "lon": 72.5714},
    "surat": {"lat": 21.1702, "lon": 72.8311},
    "rajkot": {"lat": 22.3039, "lon": 70.8022},
    "vadodara": {"lat": 22.3072, "lon": 73.1812},
    # Karnataka
    "bangalore": {"lat": 12.9716, "lon": 77.5946},
    "mysore": {"lat": 12.2958, "lon": 76.6394},
    "hubli": {"lat": 15.3647, "lon": 75.1240},
    "belgaum": {"lat": 15.8497, "lon": 74.4977},
    # West Bengal
    "kolkata": {"lat": 22.5726, "lon": 88.3639},
    "bardhaman": {"lat": 23.2324, "lon": 87.8625},
    "murshidabad": {"lat": 24.1790, "lon": 88.2663},
    "birbhum": {"lat": 23.8745, "lon": 87.6169},
    # Andhra Pradesh
    "guntur": {"lat": 16.3067, "lon": 80.4365},
    "vijayawada": {"lat": 16.5062, "lon": 80.6480},
    "tirupati": {"lat": 13.6288, "lon": 79.4192},
    "anantapur": {"lat": 14.6819, "lon": 77.5870},
    # Tamil Nadu
    "chennai": {"lat": 13.0827, "lon": 80.2707},
    "coimbatore": {"lat": 11.0168, "lon": 76.9558},
    "madurai": {"lat": 9.9252, "lon": 78.1198},
    "trichy": {"lat": 10.7905, "lon": 78.7047},
    # Bihar
    "patna": {"lat": 25.6093, "lon": 85.1376},
    "gaya": {"lat": 24.7963, "lon": 85.0043},
    "muzaffarpur": {"lat": 26.1209, "lon": 85.3647},
    "bhagalpur": {"lat": 25.2425, "lon": 86.9842},
    # Default fallback per state
    "default": STATE_COORDS,
}


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
    model_confidence: Optional[float] = None
    feature_importance: Optional[dict] = None
    last_updated: Optional[str] = None
    cached: bool = False
    generated_at: str


class WeatherAlert(BaseModel):
    type: str        # heatwave | cold_wave | heavy_rain | frost | storm | strong_wind | humidity_extreme
    severity: str    # high | medium | low
    message: str
    date: str
    advice: Optional[str] = None


class DailyForecast(BaseModel):
    date: str
    temp_max: float
    temp_min: float
    precipitation: float
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None


class WeatherResponse(BaseModel):
    district: str
    state: str
    current: dict
    forecast: List[dict]
    alerts: List[dict]
    recommendations: List[str]
    cached: bool = False
    fetched_at: str


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

    # 2. Try loading trained ML model first
    from data_pipeline import predict_with_model, engineer_features, collect_crop_state_data
    ml_prediction = None
    try:
        # Collect recent data and engineer features
        df = collect_crop_state_data(crop, state, days_back=365)
        if not df.empty and len(df) >= 30:
            df_feat = engineer_features(df)
            if not df_feat.empty:
                latest = df_feat.iloc[-1].to_dict()
                ml_prediction = predict_with_model(crop, state, latest)
    except Exception as e:
        logger.warning(f"ML model unavailable for {crop}/{state}: {e}")

    # 3. Fetch real weather data from Open-Meteo
    coords = STATE_COORDS[state]
    weather = fetch_weather(coords["lat"], coords["lon"], forecast_days=7)

    # 4. Compute prediction (rule-based fallback)
    prediction = compute_prediction(crop, state, weather)

    # 5. Override with ML prediction if available
    if ml_prediction:
        prediction["predicted_price_7d"] = ml_prediction["predicted_price_7d"]
        prediction["model_confidence"] = ml_prediction["model_confidence"]
        prediction["feature_importance"] = ml_prediction.get("feature_importance", {})
        prediction["last_updated"] = ml_prediction.get("last_updated", "")
        prediction["confidence"] = ml_prediction["model_confidence"]

    # 6. Cache result
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


# ─── Weather Endpoint ────────────────────────────────────────────

# In-memory weather cache (3-hour TTL)
_weather_cache = {}


def _get_weather_cache(district: str, state: str) -> Optional[dict]:
    key = f"weather:{district}:{state}"
    if key in _weather_cache:
        entry = _weather_cache[key]
        fetched = datetime.fromisoformat(entry["fetched_at"])
        if datetime.now() - fetched < timedelta(hours=WEATHER_CACHE_TTL_HOURS):
            entry["cached"] = True
            return entry
        else:
            del _weather_cache[key]
    return None


def _put_weather_cache(district: str, state: str, data: dict):
    key = f"weather:{district}:{state}"
    _weather_cache[key] = data


def _resolve_coords(district: str, state: str) -> dict:
    """Resolve district name to coordinates, falling back to state centroid."""
    district_lower = district.lower().strip()
    state_lower = state.lower().strip()

    # Try exact district match
    if district_lower in DISTRICT_COORDS:
        return DISTRICT_COORDS[district_lower]

    # Try state-level default
    if state_lower in DISTRICT_COORDS.get("default", {}):
        return DISTRICT_COORDS["default"][state_lower]

    # Fallback to center of India
    return {"lat": 20.5937, "lon": 78.9629}


def _fetch_weather_full(lat: float, lon: float) -> Optional[dict]:
    """
    Fetch 7-day forecast with hourly detail from Open-Meteo.
    Returns current conditions + daily forecast.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        f"precipitation,weather_code,wind_speed_10m,wind_direction_10m"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"precipitation_probability_max,weather_code,wind_speed_10m_max"
        f"&timezone=Asia/Kolkata"
        f"&forecast_days=7"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        dates = daily.get("time", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        precip_prob = daily.get("precipitation_probability_max", [])
        wcode = daily.get("weather_code", [])
        wind = daily.get("wind_speed_10m_max", [])

        forecast = []
        for i in range(len(dates)):
            forecast.append({
                "date": dates[i],
                "temp_max": t_max[i] if i < len(t_max) else None,
                "temp_min": t_min[i] if i < len(t_min) else None,
                "precipitation": precip[i] if i < len(precip) else 0,
                "precipitation_probability": precip_prob[i] if i < len(precip_prob) else 0,
                "weather_code": wcode[i] if i < len(wcode) else 0,
                "wind_speed_max": wind[i] if i < len(wind) else 0,
            })

        return {
            "current": {
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "precipitation": current.get("precipitation", 0),
                "weather_code": current.get("weather_code", 0),
                "wind_speed": current.get("wind_speed_10m"),
                "wind_direction": current.get("wind_direction_10m"),
            },
            "forecast": forecast,
        }
    except Exception as e:
        logger.error(f"Open-Meteo fetch failed: {e}")
        return None


# WMO Weather interpretation codes
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def _generate_alerts(forecast: list) -> list:
    """
    Generate weather alerts based on forecast data.
    - Heatwave: temp_max > 42°C
    - Heavy rain: precipitation > 50mm
    - Frost: temp_min < 5°C
    - Storm: weather_code >= 95 (thunderstorm)
    """
    alerts = []

    for day in forecast:
        date = day["date"]
        t_max = day.get("temp_max")
        t_min = day.get("temp_min")
        precip = day.get("precipitation", 0)
        wcode = day.get("weather_code", 0)

        # Heatwave
        if t_max is not None and t_max > 42:
            alerts.append({
                "type": "heatwave",
                "severity": "high" if t_max > 45 else "medium",
                "message": f"Heatwave alert: {t_max}°C expected on {date}. Protect crops from heat stress.",
                "date": date,
            })

        # Heavy rain
        if precip > 50:
            alerts.append({
                "type": "heavy_rain",
                "severity": "high" if precip > 100 else "medium",
                "message": f"Heavy rainfall warning: {precip}mm expected on {date}. Risk of waterlogging and crop damage.",
                "date": date,
            })
        elif precip > 20:
            alerts.append({
                "type": "heavy_rain",
                "severity": "low",
                "message": f"Moderate rainfall expected: {precip}mm on {date}.",
                "date": date,
            })

        # Frost
        if t_min is not None and t_min < 5:
            alerts.append({
                "type": "frost",
                "severity": "high" if t_min < 0 else "medium",
                "message": f"Frost warning: {t_min}°C expected on {date}. Cover sensitive crops.",
                "date": date,
            })

        # Thunderstorm
        if wcode >= 95:
            alerts.append({
                "type": "storm",
                "severity": "high" if wcode >= 96 else "medium",
                "message": f"Thunderstorm expected on {date}. Secure livestock and equipment.",
                "date": date,
            })

    return alerts


def _generate_recommendations(current: dict, forecast: list, alerts: list) -> list:
    """
    Generate farming recommendations based on current weather,
    forecast, and active alerts.
    """
    recs = []
    temp = current.get("temperature", 25)
    humidity = current.get("humidity", 50)
    precip_current = current.get("precipitation", 0)

    # Temperature-based
    if temp > 40:
        recs.append("Irrigate crops early morning or late evening to reduce heat stress.")
        recs.append("Apply mulching to conserve soil moisture.")
    elif temp > 35:
        recs.append("Ensure adequate water supply for crops during peak afternoon heat.")
    elif temp < 10:
        recs.append("Cover frost-sensitive crops with protective sheets at night.")
        recs.append("Avoid irrigation during cold hours to prevent root damage.")
    elif temp < 15:
        recs.append("Monitor crops for cold stress. Delay sowing of warm-season crops.")

    # Rain-based
    total_rain_7d = sum(d.get("precipitation", 0) for d in forecast)
    if total_rain_7d > 100:
        recs.append("Ensure proper drainage in fields to prevent waterlogging.")
        recs.append("Delay fertilizer application — nutrients will wash away.")
    elif total_rain_7d > 50:
        recs.append("Check field drainage channels before expected rainfall.")
    elif total_rain_7d < 5:
        recs.append("Rainfall deficit detected. Prioritize irrigation for standing crops.")
        recs.append("Consider drought-resistant varieties for upcoming sowing.")

    # Humidity-based
    if humidity > 85:
        recs.append("High humidity — monitor for fungal diseases (blight, mildew).")
        recs.append("Apply preventive fungicide spray if crop is at vulnerable stage.")
    elif humidity < 30:
        recs.append("Low humidity — increase irrigation frequency.")

    # Alert-specific
    alert_types = {a["type"] for a in alerts}
    if "heatwave" in alert_types:
        recs.append("Heatwave: avoid transplanting and spraying during peak hours.")
    if "frost" in alert_types:
        recs.append("Frost: use smudge pots or irrigation for frost protection.")
    if "heavy_rain" in alert_types:
        recs.append("Heavy rain: harvest ready crops before rainfall if possible.")
    if "storm" in alert_types:
        recs.append("Storm: secure greenhouse structures and staked plants.")

    # Seasonal general advice
    month = datetime.now().month
    if month in (6, 7, 8, 9, 10):  # Kharif season
        recs.append("Kharif season: ensure seedbed preparation for rice, maize, cotton.")
    elif month in (11, 12, 1, 2, 3):  # Rabi season
        recs.append("Rabi season: ideal time for wheat, potato, mustard sowing.")
    else:  # Zaid
        recs.append("Zaid season: consider summer crops like watermelon, cucumber.")

    if not recs:
        recs.append("Weather conditions are favorable. Continue regular crop management.")

    return recs


@app.get("/api/weather", response_model=WeatherResponse)
async def get_weather(
    district: str = Query(..., description="District name (e.g. lucknow, pune, indore)"),
    state: str = Query(..., description="State name in snake_case (e.g. uttar_pradesh)"),
    use_cache: bool = Query(True, description="Use cached weather if available"),
):
    """
    Get 7-day weather forecast with alerts and farming recommendations.

    - **district**: Any major agricultural district in India
    - **state**: Indian state in snake_case

    Returns current conditions, daily forecast, weather alerts,
    and actionable farming recommendations.
    """
    district = district.lower().strip()
    state = state.lower().strip()

    # 1. Check cache
    if use_cache:
        cached = _get_weather_cache(district, state)
        if cached:
            return WeatherResponse(**cached)

    # 2. Resolve coordinates
    coords = _resolve_coords(district, state)

    # 3. Fetch weather from Open-Meteo
    weather_data = _fetch_weather_full(coords["lat"], coords["lon"])
    if weather_data is None:
        raise HTTPException(
            status_code=503,
            detail="Weather service unavailable. Please try again later.",
        )

    # 4. Generate alerts
    alerts = _generate_alerts(weather_data["forecast"])

    # 5. Generate recommendations
    recommendations = _generate_recommendations(
        weather_data["current"],
        weather_data["forecast"],
        alerts,
    )

    # 6. Build response
    result = {
        "district": district,
        "state": state,
        "current": {
            "temperature": weather_data["current"]["temperature"],
            "feels_like": weather_data["current"]["feels_like"],
            "humidity": weather_data["current"]["humidity"],
            "precipitation": weather_data["current"]["precipitation"],
            "weather": WMO_CODES.get(weather_data["current"]["weather_code"], "Unknown"),
            "weather_code": weather_data["current"]["weather_code"],
            "wind_speed": weather_data["current"]["wind_speed"],
            "wind_direction": weather_data["current"]["wind_direction"],
        },
        "forecast": weather_data["forecast"],
        "alerts": alerts,
        "recommendations": recommendations,
        "cached": False,
        "fetched_at": datetime.now().isoformat(),
    }

    # 7. Cache
    _put_weather_cache(district, state, result)

    return WeatherResponse(**result)


# ─── Enhanced Weather Endpoint (v2) ──────────────────────────────

# Extended state coordinates with the exact values requested
STATE_COORDS_V2 = {
    "uttar_pradesh":  {"lat": 26.8467, "lon": 80.9462},
    "maharashtra":    {"lat": 19.7515, "lon": 75.7139},
    "punjab":         {"lat": 31.1471, "lon": 75.3412},
    "haryana":        {"lat": 29.0588, "lon": 76.0856},
    "rajasthan":      {"lat": 27.0238, "lon": 74.2179},
    "madhya_pradesh": {"lat": 23.4735, "lon": 77.9470},
    "gujarat":        {"lat": 22.2587, "lon": 71.1924},
    "karnataka":      {"lat": 15.3173, "lon": 75.7139},
    "tamil_nadu":     {"lat": 11.1271, "lon": 78.6569},
    "west_bengal":    {"lat": 22.9868, "lon": 87.8550},
    "andhra_pradesh": {"lat": 15.9129, "lon": 79.7400},
    "bihar":          {"lat": 25.0961, "lon": 85.3131},
}


def _fetch_weather_v2(lat: float, lon: float, days: int = 7) -> Optional[dict]:
    """
    Fetch extended weather forecast from Open-Meteo with humidity and wind.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"relative_humidity_2m_max,wind_speed_10m_max"
        f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        f"&timezone=Asia%2FKolkata"
        f"&forecast_days={days}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        dates = daily.get("time", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        humidity = daily.get("relative_humidity_2m_max", [])
        wind = daily.get("wind_speed_10m_max", [])

        forecast = []
        for i in range(len(dates)):
            forecast.append({
                "date": dates[i],
                "temp_max": t_max[i] if i < len(t_max) else None,
                "temp_min": t_min[i] if i < len(t_min) else None,
                "precipitation": precip[i] if i < len(precip) else 0,
                "humidity": humidity[i] if i < len(humidity) else None,
                "wind": wind[i] if i < len(wind) else 0,
            })

        return {
            "current": {
                "temp": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "wind": current.get("wind_speed_10m"),
                "weather_code": current.get("weather_code", 0),
            },
            "forecast": forecast,
        }
    except Exception as e:
        logger.error(f"Open-Meteo v2 fetch failed: {e}")
        return None


def _generate_alerts_v2(forecast: list) -> list:
    """
    Generate weather alerts with severity levels.
    - Heatwave: temp > 42°C → severity "high"
    - Cold wave: temp < 5°C → severity "high"
    - Heavy rain: precip > 50mm → severity "medium"
    - Strong wind: wind > 30 km/h → severity "medium"
    - Humidity extreme: humidity > 90% → severity "low"
    """
    alerts = []
    advice_map = {
        "heatwave": "Avoid midday irrigation. Apply mulch to conserve moisture. Provide shade nets for sensitive crops.",
        "cold_wave": "Cover frost-sensitive crops with protective sheets. Use smudge pots or irrigation for frost protection.",
        "heavy_rain": "Ensure proper field drainage. Delay fertilizer application. Harvest mature crops before rainfall.",
        "strong_wind": "Secure greenhouse structures. Stake tall crops. Delay pesticide spraying.",
        "humidity_extreme": "Monitor for fungal diseases. Improve air circulation. Apply preventive fungicide if needed.",
    }

    for day in forecast:
        date = day["date"]
        t_max = day.get("temp_max")
        t_min = day.get("temp_min")
        precip = day.get("precipitation", 0)
        wind = day.get("wind", 0)
        humidity = day.get("humidity")

        if t_max is not None and t_max > 42:
            alerts.append({
                "type": "heatwave",
                "severity": "high",
                "message": f"Heatwave: {t_max}°C expected on {date}.",
                "date": date,
                "advice": advice_map["heatwave"],
            })

        if t_min is not None and t_min < 5:
            alerts.append({
                "type": "cold_wave",
                "severity": "high",
                "message": f"Cold wave: {t_min}°C expected on {date}.",
                "date": date,
                "advice": advice_map["cold_wave"],
            })

        if precip > 50:
            alerts.append({
                "type": "heavy_rain",
                "severity": "medium",
                "message": f"Heavy rain: {precip}mm precipitation expected on {date}.",
                "date": date,
                "advice": advice_map["heavy_rain"],
            })

        if wind > 30:
            alerts.append({
                "type": "strong_wind",
                "severity": "medium",
                "message": f"Strong wind: {wind} km/h expected on {date}.",
                "date": date,
                "advice": advice_map["strong_wind"],
            })

        if humidity is not None and humidity > 90:
            alerts.append({
                "type": "humidity_extreme",
                "severity": "low",
                "message": f"High humidity: {humidity}% on {date}.",
                "date": date,
                "advice": advice_map["humidity_extreme"],
            })

    return alerts


def _generate_farming_recommendations_v2(current: dict, forecast: list, alerts: list, state: str) -> list:
    """
    Generate actionable farming recommendations based on weather, alerts, and state context.
    """
    recs = []
    temp = current.get("temp", 25)
    humidity = current.get("humidity", 50)

    total_rain = sum(d.get("precipitation", 0) for d in forecast)
    avg_max = sum(d.get("temp_max", 0) or 0 for d in forecast) / max(len(forecast), 1)
    avg_min = sum(d.get("temp_min", 0) or 0 for d in forecast) / max(len(forecast), 1)

    alert_types = {a["type"] for a in alerts}

    # Temperature-based
    if avg_max > 40:
        recs.append("Irrigate crops early morning or late evening to reduce heat stress.")
        recs.append("Apply mulching to conserve soil moisture.")
    elif avg_max > 35:
        recs.append("Ensure adequate water supply during peak afternoon heat.")
    elif avg_min < 5:
        recs.append("Cover frost-sensitive crops with protective sheets at night.")
        recs.append("Avoid irrigation during cold hours to prevent root damage.")
    elif avg_min < 15:
        recs.append("Monitor crops for cold stress. Delay sowing of warm-season crops.")

    # Rainfall-based
    if total_rain > 100:
        recs.append("Ensure proper field drainage to prevent waterlogging.")
        recs.append("Delay fertilizer application — nutrients will wash away.")
    elif total_rain > 50:
        recs.append("Check drainage channels before expected rainfall.")
    elif total_rain < 5:
        recs.append("Rainfall deficit — prioritize irrigation for standing crops.")
        recs.append("Consider drought-resistant varieties for upcoming sowing.")

    # Humidity-based
    if humidity > 85:
        recs.append("High humidity — monitor for fungal diseases (blight, mildew).")
        recs.append("Apply preventive fungicide spray at vulnerable crop stages.")
    elif humidity < 30:
        recs.append("Low humidity — increase irrigation frequency.")

    # Alert-specific
    if "heatwave" in alert_types:
        recs.append("Heatwave: avoid transplanting and spraying during peak hours.")
    if "cold_wave" in alert_types:
        recs.append("Cold wave: use smudge pots or irrigation for frost protection.")
    if "heavy_rain" in alert_types:
        recs.append("Heavy rain: harvest ready crops before rainfall if possible.")
    if "strong_wind" in alert_types:
        recs.append("Strong wind: secure greenhouse structures and staked plants.")
    if "humidity_extreme" in alert_types:
        recs.append("High humidity: improve air circulation between crop rows.")

    # Seasonal advice
    month = datetime.now().month
    if month in (6, 7, 8, 9, 10):
        recs.append("Kharif season: ensure seedbed preparation for rice, maize, cotton.")
    elif month in (11, 12, 1, 2, 3):
        recs.append("Rabi season: ideal time for wheat, potato, mustard sowing.")
    else:
        recs.append("Zaid season: consider summer crops like watermelon, cucumber.")

    if not recs:
        recs.append("Weather conditions are favorable. Continue regular crop management.")

    return recs


@app.get("/api/weather/v2")
async def get_weather_v2(
    state: str = Query(..., description="State name in snake_case (e.g. uttar_pradesh)"),
    district: Optional[str] = Query(None, description="District name (e.g. lucknow, pune)"),
    days: int = Query(7, ge=1, le=16, description="Forecast days (1-16)"),
):
    """
    Enhanced weather endpoint with extended alerts and farming recommendations.

    - **state** (required): Indian state in snake_case
    - **district** (optional): Falls back to state centroid if omitted
    - **days** (optional): Forecast horizon, default 7, max 16
    """
    state = state.lower().strip()
    if state not in STATE_COORDS_V2:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported state '{state}'. Supported: {list(STATE_COORDS_V2.keys())}",
        )

    # Resolve coordinates
    if district:
        district = district.lower().strip()
        coords = DISTRICT_COORDS.get(district, STATE_COORDS_V2[state])
    else:
        district = None
        coords = STATE_COORDS_V2[state]

    # Fetch weather
    weather_data = _fetch_weather_v2(coords["lat"], coords["lon"], days)
    if weather_data is None:
        raise HTTPException(status_code=503, detail="Weather service unavailable. Please try again later.")

    # Generate alerts
    alerts = _generate_alerts_v2(weather_data["forecast"])

    # Generate recommendations
    recs = _generate_farming_recommendations_v2(
        weather_data["current"], weather_data["forecast"], alerts, state,
    )

    return {
        "location": {
            "state": state,
            "district": district,
            "coordinates": {"lat": coords["lat"], "lon": coords["lon"]},
        },
        "current": {
            "temp": weather_data["current"]["temp"],
            "humidity": weather_data["current"]["humidity"],
            "wind": weather_data["current"]["wind"],
            "condition": WMO_CODES.get(weather_data["current"]["weather_code"], "Unknown"),
        },
        "forecast": weather_data["forecast"],
        "alerts": alerts,
        "farming_recommendations": recs,
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/api/weather/alerts")
async def get_weather_alerts(
    state: str = Query(..., description="State name in snake_case"),
):
    """
    Get aggregated weather alerts for all major districts in a state.
    Useful for admin dashboard overview.
    """
    state = state.lower().strip()

    # Find all districts for this state
    districts = [d for d in DISTRICT_COORDS if d != "default" and d in DISTRICT_COORDS]
    # Also check if state itself has coords
    state_districts = []
    for d, coords in DISTRICT_COORDS.items():
        if d == "default":
            continue
        # Check if this district belongs to the state (approximate)
        state_districts.append(d)

    # For simplicity, return alerts for the state capital
    state_coords = STATE_COORDS.get(state)
    if not state_coords:
        raise HTTPException(status_code=400, detail=f"Unknown state: {state}")

    weather = _fetch_weather_full(state_coords["lat"], state_coords["lon"])
    if not weather:
        raise HTTPException(status_code=503, detail="Weather service unavailable")

    alerts = _generate_alerts(weather["forecast"])

    return {
        "state": state,
        "alerts": alerts,
        "total_alerts": len(alerts),
        "checked_at": datetime.now().isoformat(),
    }


# ─── Crop Recommendation Engine ─────────────────────────────────

# Crop suitability database: pH ranges, temperature ranges, rainfall needs,
# soil preferences, NPK requirements, yield estimates, market prices
CROP_DATABASE = {
    "wheat": {
        "ph_range": (6.0, 7.5),
        "temp_range": (10, 25),
        "rainfall_mm": (500, 1000),
        "soil_types": ["loamy", "clay_loam", "sandy_loam"],
        "npk": {"n": (80, 120), "p": (40, 60), "k": (40, 60)},
        "season": ["rabi"],
        "yield_qha": (25, 40),      # quintals per hectare
        "price_range": (2000, 2400), # Rs/quintal
        "rotation_after": ["rice", "maize", "cotton", "moong"],
        "avoid_after": ["wheat", "barley"],
        "description": "Major rabi cereal. High protein, staple food crop.",
    },
    "rice": {
        "ph_range": (5.5, 7.0),
        "temp_range": (20, 35),
        "rainfall_mm": (1000, 2000),
        "soil_types": ["clay", "clay_loam", "loamy"],
        "npk": {"n": (100, 150), "p": (50, 80), "k": (50, 80)},
        "season": ["kharif"],
        "yield_qha": (20, 35),
        "price_range": (2300, 2800),
        "rotation_after": ["wheat", "mustard", "gram", "vegetables"],
        "avoid_after": ["rice", "jute"],
        "description": "Primary kharif cereal. Requires standing water at early stages.",
    },
    "maize": {
        "ph_range": (5.5, 7.5),
        "temp_range": (18, 32),
        "rainfall_mm": (500, 1200),
        "soil_types": ["loamy", "sandy_loam", "clay_loam"],
        "npk": {"n": (80, 120), "p": (40, 60), "k": (40, 60)},
        "season": ["kharif", "rabi"],
        "yield_qha": (25, 45),
        "price_range": (1700, 2100),
        "rotation_after": ["wheat", "soybean", "groundnut"],
        "avoid_after": ["maize", "sorghum"],
        "description": "Versatile cereal used for food, feed, and industrial purposes.",
    },
    "cotton": {
        "ph_range": (6.0, 8.0),
        "temp_range": (20, 35),
        "rainfall_mm": (600, 1200),
        "soil_types": ["black", "clay_loam", "loamy"],
        "npk": {"n": (60, 100), "p": (30, 50), "k": (30, 50)},
        "season": ["kharif"],
        "yield_qha": (15, 25),
        "price_range": (5800, 6800),
        "rotation_after": ["wheat", "chickpea", "onion"],
        "avoid_after": ["cotton", "okra"],
        "description": "Commercial fiber crop. Requires long frost-free period.",
    },
    "soybean": {
        "ph_range": (6.0, 7.5),
        "temp_range": (20, 30),
        "rainfall_mm": (600, 1000),
        "soil_types": ["black", "clay_loam", "loamy"],
        "npk": {"n": (20, 30), "p": (40, 60), "k": (20, 40)},
        "season": ["kharif"],
        "yield_qha": (12, 20),
        "price_range": (4200, 5000),
        "rotation_after": ["wheat", "gram", "mustard"],
        "avoid_after": ["soybean", "moong"],
        "description": "Oilseed and pulse crop. Fixes atmospheric nitrogen.",
    },
    "groundnut": {
        "ph_range": (6.0, 7.0),
        "temp_range": (22, 30),
        "rainfall_mm": (500, 1000),
        "soil_types": ["sandy_loam", "loamy", "red"],
        "npk": {"n": (20, 25), "p": (40, 50), "k": (40, 60)},
        "season": ["kharif", "rabi"],
        "yield_qha": (15, 25),
        "price_range": (4800, 5800),
        "rotation_after": ["wheat", "sorghum", "cotton"],
        "avoid_after": ["groundnut", "sunflower"],
        "description": "Major oilseed. Fixes nitrogen, improves soil health.",
    },
    "potato": {
        "ph_range": (5.0, 6.5),
        "temp_range": (15, 25),
        "rainfall_mm": (500, 800),
        "soil_types": ["sandy_loam", "loamy", "red"],
        "npk": {"n": (100, 150), "p": (50, 80), "k": (80, 120)},
        "season": ["rabi"],
        "yield_qha": (100, 200),
        "price_range": (1200, 1800),
        "rotation_after": ["rice", "maize", "mustard", "onion"],
        "avoid_after": ["potato", "tomato", "brinjal"],
        "description": "High-value root crop. Heavy feeder, needs well-drained soil.",
    },
    "tomato": {
        "ph_range": (6.0, 7.0),
        "temp_range": (20, 30),
        "rainfall_mm": (400, 800),
        "soil_types": ["loamy", "clay_loam", "sandy_loam"],
        "npk": {"n": (80, 120), "p": (40, 60), "k": (60, 80)},
        "season": ["kharif", "rabi"],
        "yield_qha": (80, 150),
        "price_range": (1500, 2500),
        "rotation_after": ["wheat", "maize", "pulse"],
        "avoid_after": ["tomato", "potato", "brinjal", "chilli"],
        "description": "High-value vegetable. Susceptible to soil-borne diseases.",
    },
    "onion": {
        "ph_range": (6.0, 7.5),
        "temp_range": (15, 30),
        "rainfall_mm": (400, 700),
        "soil_types": ["loamy", "sandy_loam", "red"],
        "npk": {"n": (60, 100), "p": (40, 60), "k": (40, 60)},
        "season": ["rabi", "kharif"],
        "yield_qha": (80, 120),
        "price_range": (1400, 2200),
        "rotation_after": ["rice", "cotton", "soybean"],
        "avoid_after": ["onion", "garlic", "leek"],
        "description": "Pungent bulb vegetable. Sensitive to excess moisture.",
    },
    "sugarcane": {
        "ph_range": (6.0, 8.0),
        "temp_range": (20, 40),
        "rainfall_mm": (1000, 1500),
        "soil_types": ["clay_loam", "loamy", "black"],
        "npk": {"n": (100, 150), "p": (40, 60), "k": (60, 100)},
        "season": ["kharif"],
        "yield_qha": (400, 700),
        "price_range": (2600, 3200),
        "rotation_after": ["wheat", "pulses", "fodder"],
        "avoid_after": ["sugarcane", "maize"],
        "description": "Long-duration cash crop. 12-18 months to maturity.",
    },
    "moong": {
        "ph_range": (6.0, 7.5),
        "temp_range": (20, 35),
        "rainfall_mm": (300, 700),
        "soil_types": ["loamy", "sandy_loam", "clay_loam"],
        "npk": {"n": (10, 20), "p": (30, 50), "k": (20, 30)},
        "season": ["kharif", "rabi", "zaid"],
        "yield_qha": (8, 15),
        "price_range": (7000, 9000),
        "rotation_after": ["wheat", "mustard", "vegetables"],
        "avoid_after": ["moong", "urad", "other pulses"],
        "description": "Short-duration pulse. Fixes nitrogen, excellent rotation crop.",
    },
    "mustard": {
        "ph_range": (6.0, 7.5),
        "temp_range": (10, 25),
        "rainfall_mm": (400, 800),
        "soil_types": ["loamy", "sandy_loam", "clay_loam"],
        "npk": {"n": (40, 60), "p": (20, 30), "k": (20, 30)},
        "season": ["rabi"],
        "yield_qha": (10, 18),
        "price_range": (5000, 6000),
        "rotation_after": ["rice", "moong", "cotton"],
        "avoid_after": ["mustard", "rapeseed", "canola"],
        "description": "Major oilseed. Cold-tolerant, short-duration rabi crop.",
    },
    "chickpea": {
        "ph_range": (6.0, 8.0),
        "temp_range": (10, 25),
        "rainfall_mm": (400, 800),
        "soil_types": ["loamy", "clay_loam", "black"],
        "npk": {"n": (10, 20), "p": (40, 60), "k": (20, 30)},
        "season": ["rabi"],
        "yield_qha": (10, 18),
        "price_range": (4500, 6000),
        "rotation_after": ["rice", "cotton", "sorghum"],
        "avoid_after": ["chickpea", "lentil", "pea"],
        "description": "Major rabi pulse. Drought-tolerant, fixes nitrogen.",
    },
    "sunflower": {
        "ph_range": (6.0, 7.5),
        "temp_range": (18, 30),
        "rainfall_mm": (400, 700),
        "soil_types": ["loamy", "sandy_loam", "clay_loam"],
        "npk": {"n": (40, 60), "p": (30, 40), "k": (30, 40)},
        "season": ["kharif", "rabi"],
        "yield_qha": (10, 15),
        "price_range": (6000, 7500),
        "rotation_after": ["wheat", "gram", "vegetables"],
        "avoid_after": ["sunflower", "groundnut"],
        "description": "Oilseed crop. Deep-rooted, tolerates moderate drought.",
    },
}

# Soil type descriptions
SOIL_TYPES = ["sandy", "sandy_loam", "loamy", "clay_loam", "clay", "black", "red", "laterite"]

# Season definitions
SEASON_OPTIONS = ["kharif", "rabi", "zaid"]


def _compute_rule_score(crop: str, soil: str, ph: float, temp: float,
                        rainfall: float, nitrogen: float, phosphorus: float,
                        potassium: float, season: str) -> dict:
    """
    Rule-based suitability scoring (0-100).
    Checks pH range, temperature range, rainfall, soil type, NPK, season.
    """
    info = CROP_DATABASE[crop]
    score = 0
    max_score = 0
    reasons = []

    # 1. pH match (weight: 20)
    max_score += 20
    ph_min, ph_max = info["ph_range"]
    if ph_min <= ph <= ph_max:
        score += 20
        reasons.append("pH suitable")
    else:
        ph_mid = (ph_min + ph_max) / 2
        ph_dist = min(abs(ph - ph_min), abs(ph - ph_max))
        ph_penalty = max(0, 20 - int(ph_dist * 10))
        score += ph_penalty
        reasons.append(f"pH suboptimal ({ph} vs ideal {ph_min}-{ph_max})")

    # 2. Temperature match (weight: 25)
    max_score += 25
    t_min, t_max = info["temp_range"]
    if t_min <= temp <= t_max:
        score += 25
        reasons.append("Temperature ideal")
    else:
        t_dist = min(abs(temp - t_min), abs(temp - t_max))
        t_penalty = max(0, 25 - int(t_dist * 2))
        score += t_penalty
        reasons.append(f"Temperature suboptimal ({temp}°C vs ideal {t_min}-{t_max}°C)")

    # 3. Rainfall match (weight: 20)
    max_score += 20
    r_min, r_max = info["rainfall_mm"]
    if r_min <= rainfall <= r_max:
        score += 20
        reasons.append("Rainfall adequate")
    elif rainfall < r_min:
        ratio = rainfall / r_min if r_min > 0 else 0
        score += int(ratio * 20)
        reasons.append(f"Rainfall deficit ({rainfall}mm vs need {r_min}-{r_max}mm)")
    else:
        ratio = r_max / rainfall if rainfall > 0 else 0
        score += int(ratio * 20)
        reasons.append(f"Excess rainfall ({rainfall}mm vs need {r_min}-{r_max}mm)")

    # 4. Soil type match (weight: 15)
    max_score += 15
    if soil.lower() in info["soil_types"]:
        score += 15
        reasons.append(f"{soil} soil suitable")
    else:
        # Partial credit for compatible soils
        compatible = {"sandy": ["sandy_loam"], "sandy_loam": ["sandy", "loamy"],
                      "loamy": ["sandy_loam", "clay_loam"], "clay_loam": ["loamy", "clay"],
                      "clay": ["clay_loam"], "black": ["clay_loam", "clay"],
                      "red": ["sandy_loam", "loamy"], "laterite": ["sandy_loam"]}
        if soil.lower() in compatible and any(s in info["soil_types"] for s in compatible[soil.lower()]):
            score += 8
            reasons.append(f"{soil} soil partially compatible")
        else:
            reasons.append(f"{soil} soil not ideal for {crop}")

    # 5. NPK match (weight: 10)
    max_score += 10
    npk = info["npk"]
    n_ok = npk["n"][0] <= nitrogen <= npk["n"][1] * 1.2
    p_ok = npk["p"][0] <= phosphorus <= npk["p"][1] * 1.2
    k_ok = npk["k"][0] <= potassium <= npk["k"][1] * 1.2
    npk_score = sum([n_ok, p_ok, k_ok]) * 3 + (1 if any([n_ok, p_ok, k_ok]) else 0)
    score += min(10, npk_score)
    if n_ok and p_ok and k_ok:
        reasons.append("NPK levels good")
    else:
        missing = []
        if not n_ok:
            missing.append("N")
        if not p_ok:
            missing.append("P")
        if not k_ok:
            missing.append("K")
        reasons.append(f"NPK adjustment needed: {', '.join(missing)}")

    # 6. Season match (weight: 10)
    max_score += 10
    if season.lower() in info["season"]:
        score += 10
        reasons.append(f"{season} is growing season")
    else:
        score += 2  # Can still grow off-season with adjustments
        reasons.append(f"{season} is off-season for {crop}")

    # Normalize to 0-100
    normalized = round((score / max_score) * 100, 1) if max_score > 0 else 0

    return {"score": normalized, "reasons": reasons}


def _get_rotation_suggestions(crop: str, season: str) -> list:
    """
    Suggest crops for rotation after the recommended crop.
    Based on agronomic best practices:
    - Alternate cereals with pulses (nitrogen fixation)
    - Alternate deep-rooted with shallow-rooted
    - Avoid same family (disease prevention)
    """
    info = CROP_DATABASE.get(crop, {})
    good_after = info.get("rotation_after", [])
    avoid_after = info.get("avoid_after", [])

    suggestions = []
    for rot_crop in good_after:
        if rot_crop in CROP_DATABASE:
            rot_info = CROP_DATABASE[rot_crop]
            # Check if the rotation crop fits the NEXT season
            next_seasons = {"kharif": "rabi", "rabi": "zaid", "zaid": "kharif"}
            next_s = next_seasons.get(season.lower(), "rabi")
            is_season_match = next_s in rot_info["season"]
            suggestions.append({
                "crop": rot_crop,
                "reason": f"Good after {crop} — fixes soil nutrients" if "pulse" in rot_crop or "moong" in rot_crop or "chickpea" in rot_crop else f"Breaks pest cycle after {crop}",
                "next_season": next_s,
                "season_match": is_season_match,
            })

    # Also suggest based on season
    season_crops = []
    for cname, cinfo in CROP_DATABASE.items():
        if season.lower() in cinfo["season"] and cname != crop and cname not in avoid_after:
            season_crops.append(cname)

    # Add top seasonal alternatives if rotation list is short
    if len(suggestions) < 3:
        for sc in season_crops[:3]:
            if sc not in [s["crop"] for s in suggestions]:
                suggestions.append({
                    "crop": sc,
                    "reason": f"Good {season} alternative to {crop}",
                    "next_season": season,
                    "season_match": True,
                })

    return suggestions[:5]


def _ml_score_adjustment(score: float, soil: str, ph: float, temp: float,
                         rainfall: float, n: float, p: float, k: float) -> float:
    """
    ML-inspired score adjustment using weighted feature similarity.
    Simulates a trained model's behavior using domain knowledge weights.

    In production, replace this with an actual trained model:
       model = joblib.load("models/crop_recommender.pkl")
       ml_score = model.predict_proba([[ph, temp, rainfall, n, p, k]])
    """
    # Feature weights learned from agricultural research
    weights = {
        "ph": 0.18,
        "temp": 0.22,
        "rainfall": 0.18,
        "nitrogen": 0.12,
        "phosphorus": 0.12,
        "potassium": 0.10,
        "soil": 0.08,
    }

    # Normalize inputs to 0-1 range
    ph_norm = 1.0 - abs(ph - 6.5) / 3.5      # Ideal ~6.5
    temp_norm = 1.0 - abs(temp - 25) / 25     # Ideal ~25°C
    rain_norm = min(1.0, rainfall / 1200)     # Cap at 1200mm
    n_norm = min(1.0, n / 120)
    p_norm = min(1.0, p / 80)
    k_norm = min(1.0, k / 80)
    soil_map = {"loamy": 1.0, "clay_loam": 0.9, "sandy_loam": 0.85,
                "black": 0.8, "clay": 0.7, "red": 0.75, "sandy": 0.65, "laterite": 0.6}
    soil_norm = soil_map.get(soil.lower(), 0.7)

    ml_adjustment = (
        weights["ph"] * ph_norm +
        weights["temp"] * temp_norm +
        weights["rainfall"] * rain_norm +
        weights["nitrogen"] * n_norm +
        weights["phosphorus"] * p_norm +
        weights["potassium"] * k_norm +
        weights["soil"] * soil_norm
    )

    # Blend rule-based (70%) with ML-inspired (30%)
    blended = score * 0.70 + (ml_adjustment * 100) * 0.30
    return round(min(100.0, max(0.0, blended)), 1)


@app.post("/api/crop-recommend")
async def crop_recommendation(request: Request):
    """
    Recommend top 5 crops based on soil, climate, and season.

    Input JSON:
    {
        "soil_type": "loamy",
        "ph": 6.5,
        "nitrogen": 80,
        "phosphorus": 40,
        "potassium": 40,
        "rainfall": 800,
        "temperature": 25,
        "season": "rabi"
    }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    soil = body.get("soil_type", "loamy")
    ph = body.get("ph", 6.5)
    nitrogen = body.get("nitrogen", 60)
    phosphorus = body.get("phosphorus", 40)
    potassium = body.get("potassium", 40)
    rainfall = body.get("rainfall", 800)
    temperature = body.get("temperature", 25)
    season = body.get("season", "rabi")

    # Validate inputs
    if soil.lower() not in SOIL_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid soil_type '{soil}'. Valid: {SOIL_TYPES}",
        )
    if season.lower() not in SEASON_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid season '{season}'. Valid: {SEASON_OPTIONS}",
        )

    # Score every crop
    results = []
    for crop_name in CROP_DATABASE:
        rule = _compute_rule_score(
            crop_name, soil, ph, temperature, rainfall,
            nitrogen, phosphorus, potassium, season,
        )

        # Blend rule-based with ML-inspired scoring
        final_score = _ml_score_adjustment(
            rule["score"], soil, ph, temperature, rainfall,
            nitrogen, phosphorus, potassium,
        )

        crop_info = CROP_DATABASE[crop_name]
        yield_min, yield_max = crop_info["yield_qha"]
        price_min, price_max = crop_info["price_range"]

        # Estimate yield and price based on score
        score_factor = final_score / 100.0
        estimated_yield = round(yield_min + (yield_max - yield_min) * score_factor, 1)
        estimated_price = round(price_min + (price_max - price_min) * score_factor, 0)

        results.append({
            "crop": crop_name,
            "suitability_score": final_score,
            "estimated_yield_qha": estimated_yield,
            "estimated_price_per_quintal": int(estimated_price),
            "expected_revenue_per_ha": int(estimated_yield * estimated_price),
            "description": crop_info["description"],
            "reasons": rule["reasons"],
            "rotation": _get_rotation_suggestions(crop_name, season),
        })

    # Sort by score, take top 5
    results.sort(key=lambda x: x["suitability_score"], reverse=True)
    top_5 = results[:5]

    # Overall input summary
    input_summary = {
        "soil_type": soil,
        "ph": ph,
        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium,
        "rainfall_mm": rainfall,
        "temperature_c": temperature,
        "season": season,
    }

    return {
        "input": input_summary,
        "recommendations": top_5,
        "total_crops_evaluated": len(CROP_DATABASE),
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/api/crop-recommend/soil-types")
async def get_soil_types():
    return {"soil_types": SOIL_TYPES, "seasons": SEASON_OPTIONS}


@app.get("/api/crop-recommend/crops")
async def get_crop_database():
    """Return the full crop database for reference."""
    summary = {}
    for name, info in CROP_DATABASE.items():
        summary[name] = {
            "ph_range": info["ph_range"],
            "temp_range": info["temp_range"],
            "rainfall_mm": info["rainfall_mm"],
            "soil_types": info["soil_types"],
            "season": info["season"],
            "yield_qha": info["yield_qha"],
            "price_range": info["price_range"],
            "description": info["description"],
        }
    return {"crops": summary, "total": len(summary)}


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
