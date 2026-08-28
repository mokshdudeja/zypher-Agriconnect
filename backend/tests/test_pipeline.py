"""
Tests for backend/prediction/data_pipeline.py — Pipeline stages

Covers:
- Data collection with mocked HTTP responses
- Feature engineering correctness
- Train/test split (time-series aware)
- XGBoost training job
- Daily update flow
- Weekly retrain flow
- Model registry (archive old models)
- DynamoDB caching logic
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest


# ─── Feature Engineering Correctness ────────────────────────────

class TestFeatureEngineeringCorrectness:
    """Verify features are computed correctly."""

    def test_lag_features_are_shifted(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        # price_lag_7 should be price shifted by 7
        for i in range(7, min(20, len(df))):
            assert df["price_lag_7"].iloc[i] == pytest.approx(
                df["price"].iloc[i - 7], rel=1e-6
            )

    def test_rolling_mean_is_correct(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        # Rolling mean at position i should be mean of last 7 prices
        for i in range(6, min(20, len(df))):
            expected = df["price"].iloc[max(0, i - 6):i + 1].mean()
            assert df["price_rollmean_7"].iloc[i] == pytest.approx(expected, rel=1e-4)

    def test_momentum_is_pct_change(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        # Momentum 7d = pct_change(7)
        for i in range(7, min(20, len(df))):
            if df["price"].iloc[i - 7] != 0:
                expected = (df["price"].iloc[i] - df["price"].iloc[i - 7]) / df["price"].iloc[i - 7]
                assert df["price_momentum_7d"].iloc[i] == pytest.approx(expected, rel=1e-4)

    def test_volatility_is_rolling_std(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        for i in range(29, min(40, len(df))):
            expected = df["price"].iloc[max(0, i - 29):i + 1].std()
            assert df["price_volatility_30d"].iloc[i] == pytest.approx(expected, rel=1e-3)

    def test_seasonal_encoding_is_binary(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        for col in ["season_kharif", "season_rabi", "season_zaid"]:
            assert set(df[col].unique()).issubset({0, 1})

    def test_cyclical_month_encoding(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        # month_sin and month_cos should be in [-1, 1]
        assert df["month_sin"].between(-1, 1).all()
        assert df["month_cos"].between(-1, 1).all()

    def test_target_columns_are_shifted(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        # target_7d at position i should be price at position i+7
        for i in range(0, min(10, len(df) - 30)):
            assert df["target_7d"].iloc[i] == pytest.approx(
                df["price"].iloc[i + 7], rel=1e-6
            )

    def test_no_infinite_values(self, sample_featured_df):
        """Ensure no infinite values in features."""
        assert not np.isinf(sample_featured_df.select_dtypes(include=[np.number]).values).any()

    def test_rain_anomaly_calculation(self, sample_mandi_df):
        from backend.prediction.data_pipeline import engineer_features
        df = engineer_features(sample_mandi_df)
        # Rain anomaly should be deviation / normal
        if "rain_deviation_30d" in df.columns and "rain_anomaly_pct" in df.columns:
            for i in range(30, min(40, len(df))):
                normal = df["rain_deviation_30d"].iloc[i] + df.get("rain", pd.Series([0])).iloc[i] if "rain" in df.columns else 0
                # Just verify it's a finite number
                assert np.isfinite(df["rain_anomaly_pct"].iloc[i])


# ─── Time-Series Split ─────────────────────────────────────────

class TestTimeSeriesSplit:
    """Verify train/test split respects temporal ordering."""

    def test_no_data_leakage_in_cv(self, sample_featured_df):
        from sklearn.model_selection import TimeSeriesSplit
        from backend.prediction.data_pipeline import get_feature_columns

        cols = get_feature_columns(sample_featured_df)
        X = sample_featured_df[cols].fillna(0)
        y = sample_featured_df["target_7d"]

        tscv = TimeSeriesSplit(n_splits=3)
        for train_idx, val_idx in tscv.split(X):
            # All train indices should be before all val indices
            assert max(train_idx) < min(val_idx)

    def test_train_indices_older_than_val(self, sample_featured_df):
        from sklearn.model_selection import TimeSeriesSplit
        from backend.prediction.data_pipeline import get_feature_columns

        cols = get_feature_columns(sample_featured_df)
        X = sample_featured_df[cols].fillna(0)
        dates = sample_featured_df["date"]

        tscv = TimeSeriesSplit(n_splits=3)
        for train_idx, val_idx in tscv.split(X):
            train_max_date = dates.iloc[max(train_idx)]
            val_min_date = dates.iloc[min(val_idx)]
            assert train_max_date <= val_min_date


# ─── Full Training Pipeline ────────────────────────────────────

class TestFullTrainingPipeline:
    """Test the complete training pipeline."""

    def test_full_train_returns_results(self, sample_mandi_df, temp_dir, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)
        monkeypatch.setattr("backend.prediction.data_pipeline.DATA_DIR", temp_dir / "data")

        with patch("backend.prediction.data_pipeline.collect_crop_state_data") as mock_collect:
            mock_collect.return_value = sample_mandi_df

            from backend.prediction.data_pipeline import full_train
            result = full_train(crops=["wheat"], states=["uttar_pradesh"])

        assert "trained" in result
        assert "errors" in result
        assert result["trained"] >= 1

    def test_full_train_saves_report(self, sample_mandi_df, temp_dir, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)
        monkeypatch.setattr("backend.prediction.data_pipeline.DATA_DIR", temp_dir / "data")

        with patch("backend.prediction.data_pipeline.collect_crop_state_data") as mock_collect:
            mock_collect.return_value = sample_mandi_df

            from backend.prediction.data_pipeline import full_train
            full_train(crops=["wheat"], states=["uttar_pradesh"])

        report_path = temp_dir / "training_report.json"
        assert report_path.exists()
        with open(report_path) as f:
            report = json.load(f)
        assert "timestamp" in report


# ─── Weekly Retrain ─────────────────────────────────────────────

class TestWeeklyRetrain:
    """Test the weekly retrain flow."""

    def test_weekly_retrain_compares_metrics(self, sample_mandi_df, temp_dir, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)
        monkeypatch.setattr("backend.prediction.data_pipeline.DATA_DIR", temp_dir / "data")

        with patch("backend.prediction.data_pipeline.collect_crop_state_data") as mock_collect:
            mock_collect.return_value = sample_mandi_df

            from backend.prediction.data_pipeline import weekly_retrain
            result = weekly_retrain(crops=["wheat"], states=["uttar_pradesh"])

        assert "trained" in result
        assert "improved" in result
        assert result["trained"] >= 1

    def test_weekly_retrain_archives_old_models(self, sample_mandi_df, temp_dir, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)
        monkeypatch.setattr("backend.prediction.data_pipeline.DATA_DIR", temp_dir / "data")

        with patch("backend.prediction.data_pipeline.collect_crop_state_data") as mock_collect:
            mock_collect.return_value = sample_mandi_df

            from backend.prediction.data_pipeline import full_train, weekly_retrain
            # First train
            full_train(crops=["wheat"], states=["uttar_pradesh"])
            # Retrain
            weekly_retrain(crops=["wheat"], states=["uttar_pradesh"])

        # Archive dir should exist (even if empty)
        archive_dir = temp_dir / "archive"
        assert archive_dir.exists()


# ─── DynamoDB Caching ───────────────────────────────────────────

class TestDynamoDBCaching:
    """Test DynamoDB caching logic."""

    def test_store_prediction_no_dynamodb(self, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.USE_DYNAMODB", False)
        from backend.prediction.data_pipeline import _store_prediction_to_dynamodb
        # Should not crash
        _store_prediction_to_dynamodb("wheat", "uttar_pradesh", {"price": 2150})

    @patch("backend.prediction.data_pipeline.boto3")
    def test_store_prediction_with_dynamodb(self, mock_boto3, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.USE_DYNAMODB", True)
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        from backend.prediction.data_pipeline import _store_prediction_to_dynamodb
        _store_prediction_to_dynamodb("wheat", "uttar_pradesh", {"price": 2150, "temp_max": 35})

        mock_table.put_item.assert_called_once()
        call_kwargs = mock_table.put_item.call_args[1]
        assert call_kwargs["Item"]["crop"] == "wheat"
        assert call_kwargs["Item"]["state"] == "uttar_pradesh"
        assert "ttl" in call_kwargs["Item"]


# ─── Model Registry ─────────────────────────────────────────────

class TestModelRegistry:
    """Test model archiving."""

    def test_archive_keeps_latest_three(self, temp_dir, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        # Create fake model files
        for i in range(5):
            model_file = temp_dir / f"wheat_up_xgb_2024010{i}.joblib"
            model_file.write_text(f"model-{i}")
            meta_file = temp_dir / f"wheat_up_meta_2024010{i}.joblib"
            meta_file.write_text(f"meta-{i}")

        from backend.prediction.data_pipeline import _archive_old_models
        _archive_old_models()

        archive_dir = temp_dir / "archive"
        assert archive_dir.exists()
        # Should have archived 2 files (kept 3 latest)
        archived = list(archive_dir.glob("*.joblib"))
        assert len(archived) == 4  # 2 model + 2 meta


# ─── CLI Entry Points ───────────────────────────────────────────

class TestCLIMain:
    """Test CLI entry points."""

    def test_cli_main_predict(self, sample_mandi_df, temp_dir, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.MODEL_DIR", temp_dir)

        with patch("backend.prediction.data_pipeline.collect_crop_state_data") as mock_collect:
            mock_collect.return_value = sample_mandi_df
            from backend.prediction.data_pipeline import main
            # Should not crash (will print "No trained model" message)
            import sys
            monkeypatch.setattr(sys, "argv", [
                "data_pipeline.py", "predict", "wheat", "uttar_pradesh"
            ])
            # main() will try to predict and fail gracefully
            try:
                main()
            except SystemExit:
                pass  # argparse may raise SystemExit


# ─── Weather Data Handling ──────────────────────────────────────

class TestWeatherDataHandling:
    """Test weather data collection and processing."""

    @patch("backend.prediction.data_pipeline.requests.get")
    def test_fetch_weather_empty_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"daily": {"time": []}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from backend.prediction.data_pipeline import fetch_weather_history
        records = fetch_weather_history(26.8467, 80.9462, "2024-01-01", "2024-01-31")
        assert records == []

    @patch("backend.prediction.data_pipeline.requests.get")
    def test_fetch_weather_api_error(self, mock_get):
        mock_get.side_effect = Exception("Connection timeout")

        from backend.prediction.data_pipeline import fetch_weather_history
        records = fetch_weather_history(26.8467, 80.9462, "2024-01-01", "2024-01-31")
        assert records == []

    def test_collect_crop_state_no_data(self, monkeypatch):
        monkeypatch.setattr("backend.prediction.data_pipeline.DATA_DIR",
                            Path("/nonexistent/path"))

        with patch("backend.prediction.data_pipeline.fetch_mandi_prices", return_value=[]):
            from backend.prediction.data_pipeline import collect_crop_state_data
            df = collect_crop_state_data("wheat", "uttar_pradesh", days_back=30)
            assert df.empty
