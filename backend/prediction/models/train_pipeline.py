"""
Training Pipeline — Orchestrates full model training for all crop-state pairs.
Run: python -m backend.prediction.models.train_pipeline
"""
import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime

from ..data.collect_mandi_data import MandiDataCollector
from ..data.collect_weather_data import WeatherDataCollector
from ..data.preprocess import DataPreprocessor
from ..features.engineer_features import FeatureEngineer
from ..config import CROP_MAPPING, STATES, DATA_DIR


def train_all_models(crops=None, states=None, output_dir="models/saved"):
    """
    Full training pipeline:
    1. Collect data for each crop-state pair
    2. Preprocess and engineer features
    3. Train XGBoost, LSTM, and Ensemble
    4. Save models and metrics
    """
    crops = crops or list(CROP_MAPPING.keys())
    states = states or STATES[:5]  # Top 5 states initially

    mandi_collector = MandiDataCollector()
    weather_collector = WeatherDataCollector()
    preprocessor = DataPreprocessor()
    fe = FeatureEngineer()

    results = {
        "trained_at": datetime.now().isoformat(),
        "models": {},
        "summary": {"total": 0, "success": 0, "failed": 0},
    }

    for crop in crops:
        for state in states:
            pair_key = f"{crop}_{state}"
            print(f"\n{'='*60}")
            print(f"Training: {crop} in {state}")
            print(f"{'='*60}")

            try:
                # 1. Collect mandi data
                print("  [1/5] Collecting mandi data...")
                mandi_df = mandi_collector.collect_historical_data(crop, state)

                if mandi_df is None or mandi_df.empty:
                    print(f"  ⚠ No mandi data for {crop} in {state}, skipping")
                    results["summary"]["failed"] += 1
                    continue

                # 2. Collect weather data
                print("  [2/5] Collecting weather data...")
                state_coords = _get_state_coords(state)
                weather_df = weather_collector.collect_historical_weather(
                    state_coords["lat"], state_coords["lon"],
                    mandi_df["date"].min(), mandi_df["date"].max()
                )

                # 3. Merge and preprocess
                print("  [3/5] Preprocessing...")
                if weather_df is not None and not weather_df.empty:
                    merged = preprocessor.merge_datasets(mandi_df, weather_df)
                else:
                    merged = mandi_df

                merged_clean = preprocessor.clean_price_data(merged)

                if len(merged_clean) < 90:  # Need at least 90 days
                    print(f"  ⚠ Not enough data ({len(merged_clean)} days), skipping")
                    results["summary"]["failed"] += 1
                    continue

                # 4. Engineer features
                print("  [4/5] Engineering features...")
                df_features = fe.engineer_all_features(merged_clean)

                # 5. Train models
                print("  [5/5] Training models...")

                # --- XGBoost ---
                from .xgboost_model import train_xgboost_for_crop
                xgb_result = train_xgboost_for_crop(df_features, crop, state)
                print(f"    XGBoost MAE: {xgb_result['metrics'].get('val_mae', 'N/A')}")

                # --- LSTM ---
                try:
                    from .lstm_model import LSTMPricePredictor, prepare_lstm_data
                    X_seq, y_seq, scaler_info = prepare_lstm_data(df_features)
                    split = int(len(X_seq) * 0.8)
                    lstm_model = LSTMPricePredictor(sequence_length=30)
                    lstm_model.train(
                        X_seq[:split], y_seq[:split],
                        X_seq[split:], y_seq[split:],
                        epochs=50, batch_size=16,
                    )
                    lstm_model.save(crop, state)
                    print(f"    LSTM MAE: {lstm_model.metrics.get('val_mae', 'N/A')}")
                except ImportError:
                    print("    ⚠ TensorFlow not installed, skipping LSTM")
                    lstm_model = None

                # --- Ensemble ---
                from .ensemble import EnsemblePricePredictor
                ensemble = EnsemblePricePredictor()
                # (Ensemble training needs predictions from base models on validation set)
                ensemble.save(crop, state)

                results["models"][pair_key] = {
                    "xgboost_metrics": xgb_result["metrics"],
                    "lstm_metrics": lstm_model.metrics if lstm_model else None,
                    "top_features": xgb_result["top_features"][:10],
                    "data_points": len(merged_clean),
                }
                results["summary"]["success"] += 1
                print(f"  ✅ {pair_key} trained successfully")

            except Exception as e:
                print(f"  ❌ Error training {pair_key}: {e}")
                results["summary"]["failed"] += 1
                results["models"][pair_key] = {"error": str(e)}

            results["summary"]["total"] += 1

    # Save training report
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "training_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"Training complete: {results['summary']}")
    print(f"Report saved to: {report_path}")
    print(f"{'='*60}")

    return results


def _get_state_coords(state):
    """Get approximate coordinates for Indian states."""
    coords = {
        "uttar_pradesh": {"lat": 26.8467, "lon": 80.9462},
        "maharashtra": {"lat": 19.7515, "lon": 75.7139},
        "madhya_pradesh": {"lat": 22.9734, "lon": 78.6569},
        "west_bengal": {"lat": 22.9868, "lon": 87.8550},
        "rajasthan": {"lat": 27.0238, "lon": 74.2179},
        "karnataka": {"lat": 15.3173, "lon": 75.7139},
        "andhra_pradesh": {"lat": 15.9129, "lon": 79.7400},
        "gujarat": {"lat": 22.2587, "lon": 71.1924},
        "punjab": {"lat": 31.1471, "lon": 75.3412},
        "tamil_nadu": {"lat": 11.1271, "lon": 78.6569},
    }
    return coords.get(state, {"lat": 20.5937, "lon": 78.9629})  # Center of India fallback


if __name__ == "__main__":
    train_all_models()
