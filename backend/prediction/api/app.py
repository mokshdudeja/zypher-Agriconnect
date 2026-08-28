"""
REST API for Crop Price Predictions
FastAPI-based service exposing prediction endpoints

Run: uvicorn backend.prediction.api.app:app --reload --port 8000
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="AgriConnect Crop Price Prediction API",
    description="Predict future crop prices (7/15/30 days) for Indian agriculture",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Response Models ──────────────────────────────────────────────

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


class BatchPredictionRequest(BaseModel):
    crops: List[str]
    states: List[str]


class BatchPredictionResponse(BaseModel):
    predictions: List[PredictionResponse]
    total: int
    generated_at: str


class HealthResponse(BaseModel):
    status: str
    models_loaded: int
    last_trained: Optional[str] = None


class SupportedResponse(BaseModel):
    crops: List[str]
    states: List[str]
    horizons: List[int]


# ─── In-memory prediction cache (replaced by DynamoDB in production) ──

_prediction_cache = {}
CACHE_TTL_HOURS = 6


def _get_cache_key(crop: str, state: str) -> str:
    return f"{crop}:{state}"


def _check_cache(crop: str, state: str) -> Optional[dict]:
    key = _get_cache_key(crop, state)
    if key in _prediction_cache:
        entry = _prediction_cache[key]
        if datetime.fromisoformat(entry["generated_at"]) > datetime.now() - timedelta(hours=CACHE_TTL_HOURS):
            entry["cached"] = True
            return entry
        else:
            del _prediction_cache[key]
    return None


# ─── Prediction Engine (lazy-loaded) ─────────────────────────────

_model_store = {}


def _load_models(crop: str, state: str):
    """Load trained models for a crop-state pair."""
    from ..models.xgboost_model import XGBoostPricePredictor
    from ..models.lstm_model import LSTMPricePredictor
    from ..models.ensemble import EnsemblePricePredictor

    model_dir = os.path.join(os.path.dirname(__file__), "..", "models", "saved")
    key = f"{crop}_{state}"

    if key in _model_store:
        return _model_store[key]

    # Find latest models
    import glob
    xgb_files = sorted(glob.glob(os.path.join(model_dir, f"{key}_xgb_*.joblib")))
    lstm_files = sorted(glob.glob(os.path.join(model_dir, f"{key}_lstm_*")))
    ensemble_files = sorted(glob.glob(os.path.join(model_dir, f"{key}_ensemble_*.joblib")))

    if not xgb_files:
        raise HTTPException(status_code=404, detail=f"No trained model found for {crop} in {state}")

    xgb = XGBoostPricePredictor()
    xgb.load(xgb_files[-1])

    lstm = None
    if lstm_files:
        try:
            lstm = LSTMPricePredictor()
            lstm.load(lstm_files[-1])
        except Exception:
            pass

    ensemble = None
    if ensemble_files:
        try:
            ensemble = EnsemblePricePredictor()
            ensemble.load(ensemble_files[-1])
        except Exception:
            pass

    models = {"xgb": xgb, "lstm": lstm, "ensemble": ensemble}
    _model_store[key] = models
    return models


# ─── Endpoints ────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        models_loaded=len(_model_store),
        last_trained=None,
    )


@app.get("/supported", response_model=SupportedResponse)
async def get_supported():
    from ..config import CROP_MAPPING, STATES
    return SupportedResponse(
        crops=list(CROP_MAPPING.keys()),
        states=STATES,
        horizons=[7, 15, 30],
    )


@app.get("/predict/{crop}/{state}", response_model=PredictionResponse)
async def predict_price(
    crop: str,
    state: str,
    use_cache: bool = Query(True, description="Use cached prediction if available"),
):
    """
    Predict crop price for 7, 15, and 30 days ahead.

    - **crop**: Crop name (wheat, rice, maize, cotton, sugarcane, soybean, potato, tomato, onion, groundnut)
    - **state**: Indian state name in snake_case (uttar_pradesh, maharashtra, etc.)
    """
    crop = crop.lower().strip()
    state = state.lower().strip()

    # Check cache
    if use_cache:
        cached = _check_cache(crop, state)
        if cached:
            return PredictionResponse(**cached)

    # Load models and predict
    try:
        models = _load_models(crop, state)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load models: {str(e)}")

    # For now, return a prediction structure
    # In production, this would load the latest data and run inference
    from ..config import CROP_MAPPING
    crop_name = CROP_MAPPING.get(crop, crop)

    # Placeholder — in production, fetch latest mandi data and run ensemble
    result = {
        "crop": crop_name,
        "state": state,
        "current_price": 0,
        "predicted_price_7d": 0,
        "predicted_price_15d": 0,
        "predicted_price_30d": 0,
        "confidence": 0.85,
        "trend": "stable",
        "factors": ["normal_market_conditions"],
        "model_weights": models.get("ensemble").weights if models.get("ensemble") else None,
        "cached": False,
        "generated_at": datetime.now().isoformat(),
    }

    # Cache the result
    cache_key = _get_cache_key(crop, state)
    _prediction_cache[cache_key] = result

    return PredictionResponse(**result)


@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    """Predict prices for multiple crop-state pairs."""
    predictions = []
    for crop in request.crops:
        for state in request.states:
            try:
                pred = await predict_price(crop, state)
                predictions.append(pred)
            except HTTPException:
                continue

    return BatchPredictionResponse(
        predictions=predictions,
        total=len(predictions),
        generated_at=datetime.now().isoformat(),
    )


@app.get("/history/{crop}/{state}")
async def get_prediction_history(
    crop: str,
    state: str,
    days: int = Query(30, ge=1, le=365),
):
    """Get historical prediction accuracy (stored in DynamoDB in production)."""
    # Placeholder for DynamoDB integration
    return {
        "crop": crop,
        "state": state,
        "history": [],
        "message": "Historical predictions will be stored in DynamoDB",
    }


@app.get("/market-insights/{crop}")
async def get_market_insights(crop: str):
    """Get market insights: supply-demand analysis, export trends, weather impact."""
    return {
        "crop": crop,
        "insights": {
            "supply_demand": "balanced",
            "export_trend": "stable",
            "weather_impact": "normal",
            "seasonal_outlook": "neutral",
        },
        "message": "Insights will be generated from aggregated market data",
    }
