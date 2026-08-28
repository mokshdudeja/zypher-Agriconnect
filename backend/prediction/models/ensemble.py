"""
Ensemble Model — Combines XGBoost + LSTM + Prophet predictions
Uses stacking/meta-learner to weight individual model outputs
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime

from .xgboost_model import XGBoostPricePredictor
from .lstm_model import LSTMPricePredictor


class EnsemblePricePredictor:
    """
    Ensemble that combines:
    - XGBoost (feature-based, tabular data)
    - LSTM (sequential patterns)
    - Prophet (seasonality and trends, optional)
    """

    def __init__(self, model_dir="models/saved"):
        self.model_dir = model_dir
        self.meta_learner = None
        self.xgb_predictor = None
        self.lstm_predictor = None
        self.weights = {}
        self.metrics = {}

    def _get_prophet_prediction(self, df, crop, state, forecast_days=30):
        """Generate prediction using Facebook Prophet (optional dependency)."""
        try:
            from prophet import Prophet

            prophet_df = df[["date", "modal_price"]].copy()
            prophet_df.columns = ["ds", "y"]
            prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                changepoint_prior_scale=0.05,
            )
            model.fit(prophet_df)

            future = model.make_future_dataframe(periods=forecast_days)
            forecast = model.predict(future)

            predicted = forecast.tail(30)["yhat"].values
            return {
                "7d": float(predicted[6]) if len(predicted) > 6 else None,
                "15d": float(predicted[14]) if len(predicted) > 14 else None,
                "30d": float(predicted[29]) if len(predicted) > 29 else None,
                "trend": "bullish" if predicted[-1] > predicted[0] else "bearish",
            }
        except ImportError:
            return None
        except Exception as e:
            print(f"Prophet prediction failed: {e}")
            return None

    def train_meta_learner(self, xgb_preds, lstm_preds, prophet_preds, actual_prices):
        """
        Train a Ridge regression meta-learner that combines base model predictions.

        Args:
            xgb_preds: array of XGBoost predictions
            lstm_preds: array of LSTM predictions
            prophet_preds: array of Prophet predictions (or None)
            actual_prices: ground truth prices
        """
        features = np.column_stack([
            xgb_preds,
            lstm_preds,
            prophet_preds if prophet_preds is not None else xgb_preds,
        ])

        self.meta_learner = Ridge(alpha=1.0)
        self.meta_learner.fit(features, actual_prices)

        # Learn weights
        coefs = self.meta_learner.coef_
        total = np.sum(np.abs(coefs))
        self.weights = {
            "xgboost": float(abs(coefs[0]) / total) if total > 0 else 0.33,
            "lstm": float(abs(coefs[1]) / total) if total > 0 else 0.33,
            "prophet": float(abs(coefs[2]) / total) if total > 0 else 0.34,
        }

        # Metrics
        ensemble_pred = self.meta_learner.predict(features)
        self.metrics["mae"] = float(mean_absolute_error(actual_prices, ensemble_pred))
        self.metrics["rmse"] = float(np.sqrt(mean_squared_error(actual_prices, ensemble_pred)))
        self.metrics["r2"] = float(r2_score(actual_prices, ensemble_pred))

        return self.metrics

    def predict(self, xgb_pred, lstm_pred, prophet_pred=None):
        """
        Make ensemble prediction from base model outputs.

        Returns dict with predicted prices and confidence info.
        """
        # Simple weighted average if no meta-learner trained
        if self.meta_learner is None:
            w = self.weights or {"xgboost": 0.4, "lstm": 0.35, "prophet": 0.25}
            if prophet_pred is None:
                w_total = w["xgboost"] + w["lstm"]
                pred = (xgb_pred * w["xgboost"] + lstm_pred * w["lstm"]) / w_total
            else:
                pred = (
                    xgb_pred * w["xgboost"]
                    + lstm_pred * w["lstm"]
                    + prophet_pred * w["prophet"]
                )
            return {
                "predicted_price": float(pred),
                "model_weights": w,
            }

        features = np.array([[
            xgb_pred,
            lstm_pred,
            prophet_pred if prophet_pred is not None else xgb_pred,
        ]])
        pred = self.meta_learner.predict(features)[0]

        return {
            "predicted_price": float(pred),
            "model_weights": self.weights,
        }

    def predict_horizons(self, xgb_model, lstm_model, df, sequence, crop, state):
        """
        Full prediction pipeline: get predictions from each model for 7/15/30 day horizons.

        Returns formatted output matching the API spec.
        """
        current_price = float(df["modal_price"].iloc[-1])

        # XGBoost predictions (single timestep forward)
        from ..features.engineer_features import FeatureEngineer
        fe = FeatureEngineer()
        df_feat = fe.engineer_all_features(df)
        feature_cols = [c for c in df_feat.columns
                        if c not in ["modal_price", "date", "crop", "state"]]
        X_latest = df_feat[feature_cols].select_dtypes(include=[np.number]).iloc[[-1]]

        xgb_pred = xgb_model.predict(X_latest)[0]

        # LSTM predictions (sequence-based)
        lstm_result = lstm_model.predict_single(sequence)

        # Prophet predictions
        prophet_result = self._get_prophet_prediction(df, crop, state)

        # Combine for each horizon
        results = {}
        horizon_map = {
            "7d": ("predicted_price_7d", 7),
            "15d": ("predicted_price_15d", 15),
            "30d": ("predicted_price_30d", 30),
        }

        for key, (field, days) in horizon_map.items():
            lstm_val = lstm_result.get(field, xgb_pred)
            prophet_val = prophet_result.get(key, xgb_pred) if prophet_result else None
            combined = self.predict(xgb_pred, lstm_val, prophet_val)
            results[field] = combined["predicted_price"]

        # Determine trend
        pred_7d = results["predicted_price_7d"]
        if pred_7d > current_price * 1.02:
            trend = "bullish"
        elif pred_7d < current_price * 0.98:
            trend = "bearish"
        else:
            trend = "stable"

        # Confidence based on model agreement
        preds = [results["predicted_price_7d"], results["predicted_price_15d"], results["predicted_price_30d"]]
        pred_std = np.std(preds) / np.mean(preds) if np.mean(preds) > 0 else 0
        confidence = max(0.5, min(0.99, 1.0 - pred_std * 5))

        # Determine contributing factors
        factors = []
        if "rainfall" in df.columns:
            recent_rain = df["rainfall"].tail(7).mean()
            normal_rain = df["rainfall"].mean()
            if recent_rain < normal_rain * 0.5:
                factors.append("low_rainfall")
            elif recent_rain > normal_rain * 1.5:
                factors.append("high_rainfall")

        if "modal_price" in df.columns:
            momentum = (df["modal_price"].iloc[-1] - df["modal_price"].iloc[-30]) / df["modal_price"].iloc[-30]
            if momentum > 0.1:
                factors.append("high_demand")
            elif momentum < -0.1:
                factors.append("low_demand")

        if not factors:
            factors.append("normal_market_conditions")

        return {
            "crop": crop,
            "state": state,
            "current_price": current_price,
            "predicted_price_7d": round(results["predicted_price_7d"], 2),
            "predicted_price_15d": round(results["predicted_price_15d"], 2),
            "predicted_price_30d": round(results["predicted_price_30d"], 2),
            "confidence": round(confidence, 2),
            "trend": trend,
            "factors": factors,
            "model_weights": self.weights,
        }

    def save(self, crop, state):
        """Save ensemble meta-learner."""
        os.makedirs(self.model_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{crop}_{state}"

        path = os.path.join(self.model_dir, f"{prefix}_ensemble_{timestamp}.joblib")
        joblib.dump({
            "meta_learner": self.meta_learner,
            "weights": self.weights,
            "metrics": self.metrics,
            "trained_at": timestamp,
        }, path)
        return path

    def load(self, path):
        """Load ensemble meta-learner."""
        data = joblib.load(path)
        self.meta_learner = data["meta_learner"]
        self.weights = data["weights"]
        self.metrics = data.get("metrics", {})
        return self
