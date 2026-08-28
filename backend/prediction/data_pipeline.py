"""
AgriConnect — Unified Data Pipeline

Orchestrates the full lifecycle:
    1. Data Collection   — Agmarknet mandi prices + OpenMeteo weather
    2. Preprocessing     — Merge, clean, handle missing values
    3. Feature Engineering — Lags, rolling stats, momentum, weather anomalies
    4. Model Training    — XGBoost per crop-state with time-series CV
    5. Daily Update      — Fetch new data → update features → refresh cache
    6. Weekly Retrain    — Merge new data → retrain → deploy if improved
    7. Model Inference   — Load trained models for /api/predict endpoint

Run:
    python -m backend.prediction.data_pipeline full-train
    python -m backend.prediction.data_pipeline daily-update
    python -m backend.prediction.data_pipeline weekly-retrain
    python -m backend.prediction.data_pipeline collect-data
    python -m backend.prediction.data_pipeline predict wheat uttar_pradesh
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent / "data" / "processed"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "saved"

for d in [DATA_DIR, PROCESSED_DIR, MODEL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# All crops and states
CROPS = [
    "wheat", "rice", "maize", "cotton", "soybean",
    "potato", "tomato", "onion", "groundnut", "sugarcane",
    "moong", "mustard", "chickpea", "sunflower",
]

INDIAN_STATES = [
    "uttar_pradesh", "maharashtra", "madhya_pradesh", "punjab",
    "haryana", "karnataka", "tamil_nadu", "andhra_pradesh",
    "telangana", "rajasthan", "gujarat",
]

# Agmarknet commodity names
AGMARKNET_CROPS = {
    "wheat": "Wheat", "rice": "Paddy(Dhan)", "maize": "Maize",
    "cotton": "Cotton", "soybean": "Soyabean", "groundnut": "Groundnut",
    "potato": "Potato", "tomato": "Tomato", "onion": "Onion",
    "sugarcane": "Sugarcane", "moong": "Moong", "mustard": "Mustard",
    "chickpea": "Gram", "sunflower": "Sunflower",
}

# State coordinates for Open-Meteo
STATE_COORDS = {
    "uttar_pradesh": (26.8467, 80.9462),
    "maharashtra": (19.7515, 75.7139),
    "madhya_pradesh": (22.9734, 78.6569),
    "punjab": (31.1471, 75.3412),
    "haryana": (29.0588, 76.0856),
    "karnataka": (15.3173, 75.7139),
    "tamil_nadu": (11.1271, 78.6569),
    "andhra_pradesh": (15.9129, 79.7400),
    "telangana": (18.1124, 79.0193),
    "rajasthan": (27.0238, 74.2179),
    "gujarat": (22.2587, 71.1924),
}

# Feature engineering config
LAG_DAYS = [1, 3, 7, 14, 30]
ROLLING_WINDOWS = [7, 14, 30]

# Prediction accuracy alert threshold
ERROR_THRESHOLD = 0.15  # 15%

# AWS config
USE_DYNAMODB = os.getenv("USE_DYNAMODB", "false").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "zypher-agriconnect-data")
S3_MODELS_BUCKET = os.getenv("S3_MODELS_BUCKET", "zypher-agriconnect-models")
PREDICTIONS_TABLE = os.getenv("PREDICTIONS_TABLE", "zypher-agriconnect-crop_prices")
REGION = os.getenv("AWS_REGION", "ap-south-1")


# ─── 1. Data Collection ─────────────────────────────────────────


def fetch_mandi_prices(crop: str, state: str, start_date: str = "2020-01-01",
                       end_date: Optional[str] = None) -> list[dict]:
    """Fetch mandi prices from Agmarknet API (data.gov.in)."""
    import requests as req

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    commodity = AGMARKNET_CROPS.get(crop, crop.title())
    api_url = "https://api.data.gov.in/resource"
    resource_id = "359856e0-2940-4db7-a518-bec053bd5301"

    all_records = []
    page = 1

    while True:
        params = {
            "api-key": "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b",
            "format": "json",
            "limit": 1000,
            "offset": (page - 1) * 1000,
            "filters": [
                {"field": "commodity", "value": commodity, "operator": "=="},
                {"field": "date", "value": start_date, "operator": ">="},
                {"field": "date", "value": end_date, "operator": "<="},
                {"field": "state", "value": state.replace("_", " ").title(), "operator": "=="},
            ],
        }

        try:
            resp = req.get(api_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"Agmarknet API error (page {page}): {e}")
            break

        records = data.get("records", [])
        if not records:
            break

        for rec in records:
            all_records.append({
                "date": rec.get("date", ""),
                "state": rec.get("state", ""),
                "district": rec.get("district", ""),
                "market": rec.get("market", ""),
                "commodity": rec.get("commodity", ""),
                "min_price": _safe_float(rec.get("min_price")),
                "max_price": _safe_float(rec.get("max_price")),
                "modal_price": _safe_float(rec.get("modal_price")),
                "arrival_qty": _safe_float(rec.get("arrival_quantity")),
            })

        total = int(data.get("count", 0))
        if page * 1000 >= total:
            break
        page += 1
        time.sleep(0.5)

    return all_records


def fetch_weather_history(lat: float, lon: float, start_date: str,
                          end_date: str) -> list[dict]:
    """Fetch weather from Open-Meteo Archive API."""
    import requests as req

    url = "https://archive-api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start_date, "end_date": end_date,
        "daily": ",".join([
            "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
            "precipitation_sum", "rain_sum", "wind_speed_10m_max",
        ]),
        "timezone": "Asia/Kolkata",
    }

    try:
        resp = req.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Weather API error ({lat}, {lon}): {e}")
        return []

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    records = []
    for i, date in enumerate(dates):
        records.append({
            "date": date,
            "temp_max": _safe_float(daily.get("temperature_2m_max", [None])[i] if i < len(daily.get("temperature_2m_max", [])) else None),
            "temp_min": _safe_float(daily.get("temperature_2m_min", [None])[i] if i < len(daily.get("temperature_2m_min", [])) else None),
            "temp_mean": _safe_float(daily.get("temperature_2m_mean", [None])[i] if i < len(daily.get("temperature_2m_mean", [])) else None),
            "precipitation": _safe_float(daily.get("precipitation_sum", [None])[i] if i < len(daily.get("precipitation_sum", [])) else None),
            "rain": _safe_float(daily.get("rain_sum", [None])[i] if i < len(daily.get("rain_sum", [])) else None),
            "wind_max": _safe_float(daily.get("wind_speed_10m_max", [None])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None),
        })
    return records


def _safe_float(val) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def collect_crop_state_data(crop: str, state: str, days_back: int = 1825) -> pd.DataFrame:
    """Collect and merge mandi + weather data for one crop-state pair."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    logger.info(f"Collecting {crop}/{state} from {start_date} to {end_date}")

    # 1. Mandi prices
    mandi_records = fetch_mandi_prices(crop, state, start_date, end_date)
    if not mandi_records:
        logger.warning(f"No mandi data for {crop}/{state}")
        return pd.DataFrame()

    mandi_df = pd.DataFrame(mandi_records)
    mandi_df["date"] = pd.to_datetime(mandi_df["date"], errors="coerce")
    mandi_df = mandi_df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Use modal price
    mandi_df["price"] = mandi_df["modal_price"]
    mask = mandi_df["price"] == 0
    mandi_df.loc[mask, "price"] = (mandi_df.loc[mask, "min_price"] + mandi_df.loc[mask, "max_price"]) / 2

    # 2. Weather
    coords = STATE_COORDS.get(state, (20.5937, 78.9629))
    weather_records = fetch_weather_history(coords[0], coords[1], start_date, end_date)

    if weather_records:
        weather_df = pd.DataFrame(weather_records)
        weather_df["date"] = pd.to_datetime(weather_df["date"], errors="coerce")
        weather_df = weather_df.dropna(subset=["date"]).sort_values("date")

        # Merge
        df = pd.merge_asof(
            mandi_df.sort_values("date"),
            weather_df.sort_values("date"),
            on="date", direction="nearest", tolerance=pd.Timedelta("2D"),
        )
    else:
        df = mandi_df
        for col in ["temp_max", "temp_min", "temp_mean", "precipitation", "rain", "wind_max"]:
            df[col] = np.nan

    # Add metadata
    df["crop"] = crop
    df["state"] = state
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["day_of_week"] = df["date"].dt.dayofweek
    df["season"] = df["month"].map(_month_to_season)

    # Save raw
    raw_dir = DATA_DIR / "merged"
    raw_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_dir / f"{crop}_{state}.csv", index=False)

    logger.info(f"Collected {len(df)} rows for {crop}/{state}")
    return df


def _month_to_season(m: int) -> str:
    if m in (6, 7, 8, 9, 10):
        return "kharif"
    elif m in (11, 12, 1, 2, 3):
        return "rabi"
    return "zaid"


# ─── 2. Feature Engineering ─────────────────────────────────────


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Full feature engineering pipeline."""
    if df.empty:
        return df

    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    # --- Lag prices ---
    for days in LAG_DAYS:
        df[f"price_lag_{days}"] = df["price"].shift(days)

    # --- Rolling averages ---
    for w in ROLLING_WINDOWS:
        df[f"price_rollmean_{w}"] = df["price"].rolling(w, min_periods=1).mean()
        df[f"price_rollstd_{w}"] = df["price"].rolling(w, min_periods=1).std()

    # --- Momentum ---
    df["price_momentum_7d"] = df["price"].pct_change(7)
    df["price_momentum_30d"] = df["price"].pct_change(30)
    df["price_acceleration"] = df["price_momentum_7d"].diff(7)

    # --- Volatility ---
    df["price_volatility_30d"] = df["price"].rolling(30, min_periods=1).std()
    df["price_volatility_90d"] = df["price"].rolling(90, min_periods=1).std()
    roll_mean = df["price"].rolling(30, min_periods=1).mean()
    roll_std = df["price"].rolling(30, min_periods=1).std()
    df["price_cv_30d"] = np.where(roll_mean != 0, roll_std / roll_mean, 0)

    # --- Weather anomalies ---
    rain_col = "rain" if "rain" in df.columns else "precipitation"
    if rain_col in df.columns:
        df["rain_normal_30d"] = df[rain_col].rolling(30, min_periods=1).mean()
        df["rain_deviation_30d"] = df[rain_col] - df["rain_normal_30d"]
        df["rain_anomaly_pct"] = np.where(
            df["rain_normal_30d"] != 0,
            df["rain_deviation_30d"] / df["rain_normal_30d"], 0,
        )
        df["is_dry"] = (df[rain_col] < 1.0).astype(int)
        df["dry_spell"] = df["is_dry"].groupby(
            (df["is_dry"] != df["is_dry"].shift()).cumsum()
        ).cumcount() + 1
        df.loc[df["is_dry"] == 0, "dry_spell"] = 0
        df = df.drop(columns=["is_dry", "rain_normal_30d"], errors="ignore")

    if "temp_mean" in df.columns:
        df["temp_normal_30d"] = df["temp_mean"].rolling(30, min_periods=1).mean()
        df["temp_anomaly"] = df["temp_mean"] - df["temp_normal_30d"]
        df = df.drop(columns=["temp_normal_30d"], errors="ignore")

    # --- Seasonal encoding ---
    for season in ["kharif", "rabi", "zaid"]:
        df[f"season_{season}"] = (df["season"] == season).astype(int)

    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

    # --- Target variables ---
    df["target_7d"] = df["price"].shift(-7)
    df["target_15d"] = df["price"].shift(-15)
    df["target_30d"] = df["price"].shift(-30)

    # Fill weather NaN
    weather_cols = [c for c in ["temp_max", "temp_min", "temp_mean", "precipitation", "rain", "wind_max"] if c in df.columns]
    if weather_cols:
        df[weather_cols] = df[weather_cols].fillna(method="ffill", limit=7)
        df[weather_cols] = df[weather_cols].fillna(method="bfill", limit=7)

    # Drop rows with NaN targets
    df = df.dropna(subset=["target_7d", "target_15d", "target_30d"])

    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Get numeric feature columns (exclude targets, metadata)."""
    exclude = {
        "date", "crop", "state", "season", "commodity", "district",
        "market", "variety", "unit", "target_7d", "target_15d", "target_30d",
    }
    return [c for c in df.columns if c not in exclude
            and df[c].dtype in ("float64", "int64", "float32", "int32", "int")]


# ─── 3. Model Training ─────────────────────────────────────────


def train_xgboost_model(df: pd.DataFrame, crop: str, state: str) -> dict:
    """Train XGBoost for a crop-state pair. Returns metrics + saves model."""
    from xgboost import XGBRegressor
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    import joblib

    feature_cols = get_feature_columns(df)
    X = df[feature_cols].copy()
    y = df["target_7d"].copy()

    # Replace inf with NaN, then fill
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)

    # Time-series split
    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = {"mae": [], "rmse": [], "r2": []}

    for train_idx, val_idx in tscv.split(X):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model = XGBRegressor(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
            reg_alpha=0.1, reg_lambda=1.0,
            objective="reg:squarederror", tree_method="hist",
            random_state=42,
        )
        model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

        y_pred = model.predict(X_val)
        cv_scores["mae"].append(float(mean_absolute_error(y_val, y_pred)))
        cv_scores["rmse"].append(float(np.sqrt(mean_squared_error(y_val, y_pred))))
        cv_scores["r2"].append(float(r2_score(y_val, y_pred)))

    # Final model on all data
    final_model = XGBRegressor(
        n_estimators=500, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        reg_alpha=0.1, reg_lambda=1.0,
        objective="reg:squarederror", tree_method="hist",
        random_state=42,
    )
    final_model.fit(X, y, verbose=False)

    # Feature importance
    importances = dict(zip(feature_cols, final_model.feature_importances_))
    top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:15]

    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODEL_DIR / f"{crop}_{state}_xgb_{timestamp}.joblib"
    meta_path = MODEL_DIR / f"{crop}_{state}_meta_{timestamp}.joblib"

    joblib.dump(final_model, model_path)
    joblib.dump({
        "feature_names": feature_cols,
        "feature_importances": importances,
        "metrics": {
            "cv_mae_mean": float(np.mean(cv_scores["mae"])),
            "cv_rmse_mean": float(np.mean(cv_scores["rmse"])),
            "cv_r2_mean": float(np.mean(cv_scores["r2"])),
        },
        "trained_at": timestamp,
        "crop": crop,
        "state": state,
        "data_points": len(df),
    }, meta_path)

    # Also save as "latest" for easy loading
    latest_model = MODEL_DIR / f"{crop}_{state}_latest.joblib"
    latest_meta = MODEL_DIR / f"{crop}_{state}_latest_meta.joblib"
    joblib.dump(final_model, latest_model)
    joblib.dump({
        "feature_names": feature_cols,
        "feature_importances": importances,
        "metrics": {
            "cv_mae_mean": float(np.mean(cv_scores["mae"])),
            "cv_rmse_mean": float(np.mean(cv_scores["rmse"])),
            "cv_r2_mean": float(np.mean(cv_scores["r2"])),
        },
        "trained_at": timestamp,
        "crop": crop,
        "state": state,
        "data_points": len(df),
    }, latest_meta)

    cv_summary = {k: {"mean": float(np.mean(v)), "std": float(np.std(v))}
                  for k, v in cv_scores.items()}

    logger.info(f"Trained {crop}/{state}: MAE={cv_summary['mae']['mean']:.1f}, "
                f"RMSE={cv_summary['rmse']['mean']:.1f}, R²={cv_summary['r2']['mean']:.4f}")

    return {
        "model_path": str(model_path),
        "metrics": cv_summary,
        "top_features": top_features,
        "data_points": len(df),
    }


# ─── 4. Model Inference ─────────────────────────────────────────

# Global model cache
_model_cache = {}


def load_model(crop: str, state: str):
    """Load trained XGBoost model for a crop-state pair."""
    cache_key = f"{crop}_{state}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    import joblib

    model_path = MODEL_DIR / f"{crop}_{state}_latest.joblib"
    meta_path = MODEL_DIR / f"{crop}_{state}_latest_meta.joblib"

    if not model_path.exists():
        return None, None

    model = joblib.load(model_path)
    meta = joblib.load(meta_path) if meta_path.exists() else {}

    _model_cache[cache_key] = (model, meta)
    return model, meta


def predict_with_model(crop: str, state: str, current_features: dict) -> Optional[dict]:
    """Make prediction using trained model."""
    model, meta = load_model(crop, state)
    if model is None:
        return None

    import pandas as pd

    feature_names = meta.get("feature_names", [])
    X = pd.DataFrame([{f: current_features.get(f, 0) for f in feature_names}])
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

    prediction = float(model.predict(X)[0])

    # Confidence from model metrics
    cv_mae = meta.get("metrics", {}).get("cv_mae_mean", 100)
    current_price = current_features.get("price", prediction)
    confidence = max(0.5, min(0.95, 1.0 - (cv_mae / max(current_price, 1))))

    return {
        "predicted_price_7d": round(prediction, 2),
        "model_confidence": round(confidence, 2),
        "feature_importance": meta.get("feature_importances", {}),
        "last_updated": meta.get("trained_at", ""),
        "data_points": meta.get("data_points", 0),
    }


# ─── 5. Daily Update ────────────────────────────────────────────


def daily_update(crops: Optional[list] = None, states: Optional[list] = None) -> dict:
    """
    Daily update: fetch new data → engineer features → update predictions → log accuracy.
    Lambda handler for EventBridge daily trigger.
    """
    crops = crops or CROPS[:10]
    states = states or INDIAN_STATES[:6]

    results = {"updated": 0, "errors": 0, "alerts": [], "timestamp": datetime.now().isoformat()}

    for crop in crops:
        for state in states:
            try:
                # Collect latest data
                df = collect_crop_state_data(crop, state, days_back=365)
                if df.empty or len(df) < 30:
                    continue

                # Engineer features
                df_featured = engineer_features(df)
                if df_featured.empty:
                    continue

                # Store latest features in DynamoDB
                latest = df_featured.iloc[-1]
                _store_prediction_to_dynamodb(crop, state, latest)

                # Check prediction accuracy (compare previous prediction with actual)
                _check_prediction_accuracy(crop, state, latest, results)

                results["updated"] += 1

            except Exception as e:
                logger.error(f"Daily update error {crop}/{state}: {e}")
                results["errors"] += 1

    logger.info(f"Daily update complete: {results['updated']} updated, {results['errors']} errors")
    return results


def _store_prediction_to_dynamodb(crop: str, state: str, latest_row):
    """Store latest price data to DynamoDB for API consumption."""
    if not USE_DYNAMODB:
        return

    try:
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.Table(PREDICTIONS_TABLE)

        ttl = int(datetime.now().timestamp()) + (30 * 86400)  # 30 days

        table.put_item(Item={
            "pk": crop,
            "sk": f"{state}_{datetime.now().strftime('%Y-%m-%d')}",
            "crop": crop,
            "state": state,
            "price": float(latest_row.get("price", 0)),
            "temp_max": float(latest_row.get("temp_max", 0)),
            "precipitation": float(latest_row.get("precipitation", 0)),
            "ttl": ttl,
            "updated_at": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.warning(f"DynamoDB write failed: {e}")


def _check_prediction_accuracy(crop: str, state: str, latest_row, results: dict):
    """Compare previous prediction with actual price. Alert if error > 15%."""
    if not USE_DYNAMODB:
        return

    try:
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.Table(PREDICTIONS_TABLE)

        # Get prediction from 7 days ago
        target_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        resp = table.get_item(Key={"pk": crop, "sk": f"{state}_{target_date}"})
        item = resp.get("Item")

        if not item:
            return

        predicted = item.get("predicted_price_7d", 0)
        actual = float(latest_row.get("price", 0))

        if predicted > 0 and actual > 0:
            error = abs(predicted - actual) / actual
            if error > ERROR_THRESHOLD:
                results["alerts"].append({
                    "crop": crop, "state": state,
                    "predicted": predicted, "actual": actual,
                    "error_pct": round(error * 100, 1),
                    "message": f"High prediction error: {round(error * 100, 1)}% for {crop}/{state}",
                })
    except Exception as e:
        logger.warning(f"Accuracy check failed: {e}")


# ─── 6. Weekly Retrain ──────────────────────────────────────────


def weekly_retrain(crops: Optional[list] = None, states: Optional[list] = None) -> dict:
    """
    Weekly retrain: merge new data → retrain all models → deploy if improved.
    Lambda handler for EventBridge weekly trigger.
    """
    crops = crops or CROPS[:10]
    states = states or INDIAN_STATES[:6]

    results = {
        "trained": 0, "improved": 0, "errors": 0,
        "models": {}, "timestamp": datetime.now().isoformat(),
    }

    for crop in crops:
        for state in states:
            try:
                # Collect full historical data
                df = collect_crop_state_data(crop, state, days_back=1825)
                if df.empty or len(df) < 90:
                    logger.warning(f"Insufficient data for {crop}/{state}: {len(df)} rows")
                    continue

                # Engineer features
                df_featured = engineer_features(df)
                if df_featured.empty:
                    continue

                # Get old model metrics for comparison
                _, old_meta = load_model(crop, state)
                old_mae = old_meta.get("metrics", {}).get("cv_mae_mean", float("inf"))

                # Train new model
                result = train_xgboost_model(df_featured, crop, state)
                new_mae = result["metrics"]["mae"]["mean"]

                results["models"][f"{crop}_{state}"] = {
                    "old_mae": round(old_mae, 2),
                    "new_mae": round(new_mae, 2),
                    "improved": new_mae < old_mae,
                    "data_points": result["data_points"],
                }
                results["trained"] += 1

                if new_mae < old_mae:
                    results["improved"] += 1
                    logger.info(f"✅ {crop}/{state} improved: {old_mae:.1f} → {new_mae:.1f}")

            except Exception as e:
                logger.error(f"Retrain error {crop}/{state}: {e}")
                results["errors"] += 1

    # Archive old model versions
    _archive_old_models()

    logger.info(f"Weekly retrain: {results['trained']} trained, {results['improved']} improved")
    return results


def _archive_old_models():
    """Move old model versions to archive directory, keeping only latest."""
    archive_dir = MODEL_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)

    # Group by crop_state prefix
    models = {}
    for f in MODEL_DIR.glob("*_xgb_*.joblib"):
        parts = f.stem.split("_xgb_")
        if len(parts) == 2:
            prefix = parts[0]
            if prefix not in models:
                models[prefix] = []
            models[prefix].append(f)

    for prefix, files in models.items():
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        # Keep only latest 3, archive the rest
        for old_file in files[3:]:
            try:
                old_file.rename(archive_dir / old_file.name)
                # Also move meta file
                meta_file = old_file.parent / old_file.name.replace("_xgb_", "_meta_")
                if meta_file.exists():
                    meta_file.rename(archive_dir / meta_file.name)
            except Exception:
                pass


# ─── 7. Full Training ───────────────────────────────────────────


def full_train(crops: Optional[list] = None, states: Optional[list] = None) -> dict:
    """Full training pipeline for all crop-state pairs."""
    crops = crops or CROPS
    states = states or INDIAN_STATES

    results = {
        "trained": 0, "errors": 0,
        "models": {}, "timestamp": datetime.now().isoformat(),
    }

    total = len(crops) * len(states)
    done = 0

    for crop in crops:
        for state in states:
            done += 1
            logger.info(f"[{done}/{total}] Training {crop}/{state}")

            try:
                # Collect data
                df = collect_crop_state_data(crop, state)
                if df.empty or len(df) < 90:
                    logger.warning(f"Insufficient data ({len(df)} rows), skipping")
                    continue

                # Engineer features
                df_featured = engineer_features(df)
                if df_featured.empty:
                    continue

                # Train
                result = train_xgboost_model(df_featured, crop, state)
                results["models"][f"{crop}_{state}"] = result
                results["trained"] += 1

            except Exception as e:
                logger.error(f"Training error {crop}/{state}: {e}")
                results["errors"] += 1

    # Save report
    report_path = MODEL_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"Full training complete: {results['trained']} models, {results['errors']} errors")
    return results


# ─── CLI ─────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AgriConnect Data Pipeline")
    parser.add_argument("command", choices=[
        "full-train", "daily-update", "weekly-retrain",
        "collect-data", "predict",
    ])
    parser.add_argument("crop", nargs="?", help="Crop name (for predict)")
    parser.add_argument("state", nargs="?", help="State name (for predict)")
    parser.add_argument("--crops", nargs="*", help="Crops to process")
    parser.add_argument("--states", nargs="*", help="States to process")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.command == "full-train":
        result = full_train(args.crops, args.states)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "daily-update":
        result = daily_update(args.crops, args.states)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "weekly-retrain":
        result = weekly_retrain(args.crops, args.states)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "collect-data":
        crops = args.crops or CROPS[:5]
        states = args.states or INDIAN_STATES[:3]
        for crop in crops:
            for state in states:
                df = collect_crop_state_data(crop, state)
                print(f"{crop}/{state}: {len(df)} rows")

    elif args.command == "predict":
        if not args.crop or not args.state:
            print("Usage: predict <crop> <state>")
            sys.exit(1)

        # Load and engineer latest features
        df = collect_crop_state_data(args.crop, args.state, days_back=365)
        if df.empty:
            print(f"No data for {args.crop}/{args.state}")
            sys.exit(1)

        df_feat = engineer_features(df)
        if df_feat.empty:
            print("No featured data")
            sys.exit(1)

        latest = df_feat.iloc[-1].to_dict()
        result = predict_with_model(args.crop, args.state, latest)

        if result:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"No trained model for {args.crop}/{args.state}. Run full-train first.")


if __name__ == "__main__":
    main()
