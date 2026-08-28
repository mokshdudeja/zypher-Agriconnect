"""
AgriConnect Crop Price Prediction — Configuration
"""

import os
from pathlib import Path

# ============================================================
# Paths
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models" / "checkpoints"

for d in [DATA_DIR, PROCESSED_DIR, MODEL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# Supported Crops & States
# ============================================================
CROPS = [
    "wheat", "rice", "maize", "cotton", "soybean",
    "groundnut", "mustard", "sugarcane", "tomato",
    "potato", "onion", "chilli", "turmeric", "cumin",
]

INDIAN_STATES = [
    "uttar_pradesh", "madhya_pradesh", "maharashtra",
    "rajasthan", "karnataka", "andhra_pradesh",
    "tamil_nadu", "gujarat", "west_bengal",
    "haryana", "punjab", "bihar", "odisha",
    "telangana", "chhattisgarh", "jharkhand",
]

# Agmarknet commodity mapping (name → agmarknet_commodity_id)
AGMARKNET_CROPS = {
    "wheat": "Wheat",
    "rice": "Paddy(Dhan)",
    "maize": "Maize",
    "cotton": "Cotton",
    "soybean": "Soyabean",
    "groundnut": "Groundnut",
    "mustard": "Mustard",
    "sugarcane": "Sugarcane",
    "tomato": "Tomato",
    "potato": "Potato",
    "onion": "Onion",
    "chilli": "Chilly",
    "turmeric": "Turmeric",
    "cumin": "Cumin",
}

# ============================================================
# Feature Engineering Windows
# ============================================================
LAG_PERIODS = [30, 90, 180]          # 1m, 3m, 6m in days
ROLLING_WINDOWS = [90, 180, 365]     # 3m, 6m, 12m in days

# ============================================================
# Model Hyperparameters
# ============================================================
XGBOOST_PARAMS = {
    "n_estimators": 500,
    "max_depth": 8,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "min_child_weight": 5,
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "random_state": 42,
    "n_jobs": -1,
}

LSTM_PARAMS = {
    "sequence_length": 60,       # lookback in days
    "hidden_size": 128,
    "num_layers": 2,
    "dropout": 0.2,
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100,
    "patience": 10,              # early stopping patience
}

ENSEMBLE_WEIGHTS = {
    "xgboost": 0.40,
    "lstm": 0.35,
    "prophet": 0.25,
}

# ============================================================
# AWS Configuration
# ============================================================
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET = os.getenv("S3_BUCKET", "agriconnect-prediction-data")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "agriconnect-predictions")
SAGEMAKER_ENDPOINT = os.getenv("SAGEMAKER_ENDPOINT", "agriconnect-price-predictor")
LAMBDA_FUNCTION = os.getenv("LAMBDA_FUNCTION", "agriconnect-price-pipeline")

# ============================================================
# Open-Meteo Weather API
# ============================================================
OPEN_METEO_BASE = "https://api.open-meteo.com/v1"
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1"

# State → lat/lng mapping for weather data
STATE_COORDS = {
    "uttar_pradesh": (26.8467, 80.9462),
    "madhya_pradesh": (22.9734, 78.6569),
    "maharashtra": (19.7515, 75.7139),
    "rajasthan": (27.0238, 74.2179),
    "karnataka": (15.3173, 75.7139),
    "andhra_pradesh": (15.9129, 79.7400),
    "tamil_nadu": (11.1271, 78.6569),
    "gujarat": (22.2587, 71.1924),
    "west_bengal": (22.9868, 87.8550),
    "haryana": (29.0588, 76.0856),
    "punjab": (31.1471, 75.3412),
    "bihar": (25.0961, 85.3131),
    "odisha": (20.9517, 85.0985),
    "telangana": (18.1124, 79.0193),
    "chhattisgarh": (21.2787, 81.8661),
    "jharkhand": (23.6102, 85.2799),
}

# ============================================================
# Seasons
# ============================================================
SEASONS = {
    "kharif": (6, 10),    # June – October (monsoon crops)
    "rabi": (11, 3),      # November – March (winter crops)
    "zaid": (3, 6),       # March – June (summer crops)
}

CROP_SEASON_MAP = {
    "wheat": "rabi",
    "rice": "kharif",
    "maize": "kharif",
    "cotton": "kharif",
    "soybean": "kharif",
    "groundnut": "kharif",
    "mustard": "rabi",
    "sugarcane": "kharif",
    "tomato": "kharif",
    "potato": "rabi",
    "onion": "rabi",
    "chilli": "kharif",
    "turmeric": "kharif",
    "cumin": "rabi",
}

# ============================================================
# API / Output
# ============================================================
PREDICTION_HORIZONS = [7, 15, 30]  # days ahead
CONFIDENCE_THRESHOLD = 0.65

# Output schema (matches frontend contract)
OUTPUT_SCHEMA = {
    "crop": str,
    "state": str,
    "current_price": float,
    "predicted_price_7d": float,
    "predicted_price_15d": float,
    "predicted_price_30d": float,
    "confidence": float,
    "trend": str,       # "bullish" | "bearish" | "neutral"
    "factors": list,    # list of driving factors
}
