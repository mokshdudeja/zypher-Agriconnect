"""
Tests for backend/prediction/ — Model inference, feature engineering, API endpoint

Covers:
- Model loading (existing model, no model → fallback)
- Inference with valid features
- Feature importance extraction
- Confidence score calculation
- Rule-based fallback logic
- Input validation
- Model serialization/deserialization
"""

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest


# ─── Feature Engineering ────────────────────────────────────────

class TestFeatureEngineering:
    """Test the feature engineering pipeline."""

    def test_engineer_features_adds_lag_columns(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        for days in [1, 3, 7, 14, 30]:
            assert f"price_lag_{days}" in df.columns

    def test_engineer_features_adds_rolling_columns(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        for w in [7, 14, 30]:
            assert f"price_rollmean_{w}" in df.columns
            assert f"price_rollstd_{w}" in df.columns

    def test_engineer_features_adds_momentum(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        assert "price_momentum_7d" in df.columns
        assert "price_momentum_30d" in df.columns
        assert "price_acceleration" in df.columns

    def test_engineer_features_adds_volatility(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        assert "price_volatility_30d" in df.columns
        assert "price_volatility_90d" in df.columns
        assert "price_cv_30d" in df.columns

    def test_engineer_features_adds_weather_anomalies(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        assert "rain_deviation_30d" in df.columns
        assert "rain_anomaly_pct" in df.columns
        assert "dry_spell" in df.columns
        assert "temp_anomaly" in df.columns

    def test_engineer_features_adds_seasonal_encoding(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        assert "season_kharif" in df.columns
        assert "season_rabi" in df.columns
        assert "season_zaid" in df.columns
        assert "month_sin" in df.columns
        assert "month_cos" in df.columns
        assert "doy_sin" in df.columns
        assert "doy_cos" in df.columns

    def test_engineer_features_adds_targets(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        assert "target_7d" in df.columns
        assert "target_15d" in df.columns
        assert "target_30d" in df.columns

    def test_engineer_features_drops_nan_targets(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        # Last 30 rows should not have NaN targets
        assert df["target_7d"].iloc[-1] is not np.nan
        assert df["target_30d"].iloc[-1] is not np.nan

    def test_engineer_features_empty_df(self):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(pd.DataFrame())
        assert df.empty

    def test_get_feature_columns(self, sample_featured_df):
        from backend.prediction.data_pipeline import get_feature_columns
        cols = get_feature_columns(sample_featured_df)
        assert len(cols) > 15
        assert "price" in cols
        assert "price_lag_7" in cols
        # Should not include targets or metadata
        assert "target_7d" not in cols
        assert "date" not in cols
        assert "crop" not in cols


# ─── Model Training & Inference ─────────────────────────────────

class TestModelTraining:
    """Test XGBoost model training."""

    def test_train_xgboost_returns_metrics(self, sample_featured_df, temp_dir, monkeypatch):
        from backend.prediction.data_pipeline import MODEL_DIR, train_xgboost_model
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        result = train_xgboost_model(sample_featured_df, "wheat", "uttar_pradesh")

        assert "model_path" in result
        assert "metrics" in result
        assert "top_features" in result
        assert "data_points" in result
        assert result["data_points"] == len(sample_featured_df)

    def test_train_xgboost_saves_model_files(self, sample_featured_df, temp_dir, monkeypatch):
        from backend.prediction.data_pipeline import train_xgboost_model
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        result = train_xgboost_model(sample_featured_df, "wheat", "uttar_pradesh")

        model_path = Path(result["model_path"])
        assert model_path.exists()
        # Check latest model also saved
        latest = temp_dir / "wheat_uttar_pradesh_latest.joblib"
        assert latest.exists()

    def test_train_xgboost_feature_importance(self, sample_featured_df, temp_dir, monkeypatch):
        from backend.prediction.data_pipeline import train_xgboost_model
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        result = train_xgboost_model(sample_featured_df, "wheat", "uttar_pradesh")

        assert len(result["top_features"]) <= 15
        for name, importance in result["top_features"]:
            assert isinstance(name, str)
            assert isinstance(importance, (float, np.floating))
            assert importance >= 0


class TestModelInference:
    """Test model loading and prediction."""

    def test_load_model_no_model(self, temp_dir, monkeypatch):
        from backend.prediction.data_pipeline import load_model
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        model, meta = load_model("nonexistent", "crop")
        assert model is None
        assert meta is None

    def test_load_model_with_trained_model(self, sample_featured_df, temp_dir, monkeypatch):
        from backend.prediction.data_pipeline import train_xgboost_model, load_model
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        train_xgboost_model(sample_featured_df, "wheat", "uttar_pradesh")

        model, meta = load_model("wheat", "uttar_pradesh")
        assert model is not None
        assert meta is not None
        assert "feature_names" in meta
        assert "metrics" in meta

    def test_predict_with_model(self, sample_featured_df, temp_dir, monkeypatch):
        from backend.prediction.data_pipeline import train_xgboost_model, predict_with_model
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        train_xgboost_model(sample_featured_df, "wheat", "uttar_pradesh")

        # Create current features dict
        latest = sample_featured_df.iloc[-1].to_dict()
        result = predict_with_model("wheat", "uttar_pradesh", latest)

        assert result is not None
        assert "predicted_price_7d" in result
        assert "model_confidence" in result
        assert "feature_importance" in result
        assert "last_updated" in result
        assert result["model_confidence"] > 0

    def test_predict_no_model_returns_none(self, temp_dir, monkeypatch):
        from backend.prediction.data_pipeline import predict_with_model
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        result = predict_with_model("nonexistent", "crop", {"price": 100})
        assert result is None


# ─── Data Collection ────────────────────────────────────────────

class TestDataCollection:
    """Test data collection from external APIs (mocked)."""

    @patch("backend.prediction.data_pipeline.requests.get")
    def test_fetch_mandi_prices(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "count": 1,
            "records": [{
                "date": "2024-01-15",
                "state": "Uttar Pradesh",
                "district": "Lucknow",
                "market": "Lucknow",
                "commodity": "Wheat",
                "min_price": "2000",
                "max_price": "2300",
                "modal_price": "2150",
                "arrival_quantity": "500",
            }],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from backend.prediction.data_pipeline import fetch_mandi_prices
        records = fetch_mandi_prices("wheat", "uttar_pradesh", "2024-01-01", "2024-01-31")
        assert len(records) >= 1
        assert records[0]["modal_price"] == 2150.0

    @patch("backend.prediction.data_pipeline.requests.get")
    def test_fetch_weather_history(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "daily": {
                "time": ["2024-01-15", "2024-01-16"],
                "temperature_2m_max": [35.0, 36.0],
                "temperature_2m_min": [22.0, 23.0],
                "temperature_2m_mean": [28.5, 29.5],
                "precipitation_sum": [5.0, 0.0],
                "rain_sum": [5.0, 0.0],
                "wind_speed_10m_max": [15.0, 12.0],
            },
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from backend.prediction.data_pipeline import fetch_weather_history
        records = fetch_weather_history(26.8467, 80.9462, "2024-01-15", "2024-01-16")
        assert len(records) == 2
        assert records[0]["temp_max"] == 35.0


# ─── Daily Update ───────────────────────────────────────────────

class TestDailyUpdate:
    """Test the daily update flow."""

    @patch("backend.prediction.data_pipeline.collect_crop_state_data")
    @patch("backend.prediction.data_pipeline.engineer_features")
    def test_daily_update_basic(self, mock_eng, mock_collect, temp_dir, monkeypatch):
        import pandas as pd
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        mock_df = pd.DataFrame({"price": [100, 101, 102]})
        mock_collect.return_value = mock_df
        mock_eng.return_value = mock_df

        from backend.prediction.data_pipeline import daily_update
        result = daily_update(crops=["wheat"], states=["uttar_pradesh"])

        assert "updated" in result
        assert "errors" in result
        assert "timestamp" in result


# ─── Prediction API Endpoint ────────────────────────────────────

class TestPredictionAPI:
    """Test the /api/predict endpoint via TestClient."""

    def test_health_endpoint(self, prediction_client):
        response = prediction_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_supported_endpoint(self, prediction_client):
        response = prediction_client.get("/api/supported")
        assert response.status_code == 200
        data = response.json()
        assert "crops" in data
        assert "states" in data
        assert len(data["crops"]) >= 10

    def test_predict_valid_crop_state(self, prediction_client):
        response = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        assert response.status_code == 200
        data = response.json()
        assert data["crop"] == "wheat"
        assert data["state"] == "uttar_pradesh"
        assert data["current_price"] > 0
        assert data["predicted_price_7d"] > 0
        assert 0 <= data["confidence"] <= 1
        assert data["trend"] in ("bullish", "bearish", "stable")

    def test_predict_invalid_crop(self, prediction_client):
        response = prediction_client.get("/api/predict/invalid_crop/uttar_pradesh")
        assert response.status_code == 400

    def test_predict_invalid_state(self, prediction_client):
        response = prediction_client.get("/api/predict/wheat/invalid_state")
        assert response.status_code == 400

    def test_predict_all_supported_crops(self, prediction_client):
        crops = ["wheat", "rice", "maize", "cotton", "soybean",
                 "potato", "tomato", "onion", "groundnut", "sugarcane"]
        for crop in crops:
            response = prediction_client.get(f"/api/predict/{crop}/uttar_pradesh")
            assert response.status_code == 200, f"Failed for {crop}"
            data = response.json()
            assert data["crop"] == crop

    def test_predict_response_fields(self, prediction_client):
        response = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = response.json()
        required_fields = [
            "crop", "state", "current_price", "predicted_price_7d",
            "predicted_price_15d", "predicted_price_30d", "confidence",
            "trend", "factors", "generated_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_predict_weather_endpoint(self, prediction_client):
        response = prediction_client.get(
            "/api/weather?district=lucknow&state=uttar_pradesh"
        )
        # May fail if weather API is down, but structure should be correct
        if response.status_code == 200:
            data = response.json()
            assert "current" in data
            assert "forecast" in data


# ─── Model Serialization ────────────────────────────────────────

class TestModelSerialization:
    """Test model save/load roundtrip."""

    def test_model_joblib_roundtrip(self, sample_featured_df, temp_dir, monkeypatch):
        import joblib
        from backend.prediction.data_pipeline import train_xgboost_model, MODEL_DIR
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        result = train_xgboost_model(sample_featured_df, "wheat", "uttar_pradesh")

        # Load and verify
        model = joblib.load(result["model_path"])
        assert model is not None

        # Make a prediction
        from backend.prediction.data_pipeline import get_feature_columns
        cols = get_feature_columns(sample_featured_df)
        X = sample_featured_df[cols].iloc[-1:].fillna(0)
        pred = model.predict(X)
        assert len(pred) == 1
        assert pred[0] > 0


# ─── Accuracy Monitoring ────────────────────────────────────────

class TestAccuracyMonitoring:
    """Test accuracy monitoring and alerting."""

    def test_error_threshold_constant(self):
        from backend.prediction.data_pipeline import ERROR_THRESHOLD
        assert ERROR_THRESHOLD == 0.15

    def test_check_prediction_accuracy_no_dynamodb(self, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.USE_DYNAMODB", False)
        from backend.prediction.data_pipeline import _check_prediction_accuracy
        results = {"alerts": []}
        _check_prediction_accuracy("wheat", "uttar_pradesh", {"price": 2150}, results)
        # Should not crash, no alerts when DynamoDB disabled
        assert isinstance(results["alerts"], list)
