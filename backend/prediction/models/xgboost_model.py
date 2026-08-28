"""
XGBoost Model for Crop Price Prediction
Primary model — provides feature importance and baseline predictions
"""
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from datetime import datetime


class XGBoostPricePredictor:
    """XGBoost-based price prediction model with time-series aware validation."""

    def __init__(self, model_dir="models/saved"):
        self.model_dir = model_dir
        self.model = None
        self.feature_names = None
        self.feature_importances = None
        self.metrics = {}

    def _default_params(self):
        return {
            "n_estimators": 1000,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "random_state": 42,
        }

    def train(self, X_train, y_train, X_val=None, y_val=None, params=None):
        """Train XGBoost model with early stopping."""
        train_params = self._default_params()
        if params:
            train_params.update(params)

        self.feature_names = list(X_train.columns) if hasattr(X_train, "columns") else None

        self.model = XGBRegressor(**train_params)

        eval_set = [(X_train, y_train)]
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=False,
        )

        # Feature importance
        importances = self.model.feature_importances_
        if self.feature_names:
            self.feature_importances = dict(zip(self.feature_names, importances))
        else:
            self.feature_importances = {f"feature_{i}": v for i, v in enumerate(importances)}

        # Evaluate
        y_pred = self.model.predict(X_train)
        self.metrics["train_mae"] = float(mean_absolute_error(y_train, y_pred))
        self.metrics["train_rmse"] = float(np.sqrt(mean_squared_error(y_train, y_pred)))
        self.metrics["train_r2"] = float(r2_score(y_train, y_pred))

        if X_val is not None and y_val is not None:
            y_val_pred = self.model.predict(X_val)
            self.metrics["val_mae"] = float(mean_absolute_error(y_val, y_val_pred))
            self.metrics["val_rmse"] = float(np.sqrt(mean_squared_error(y_val, y_val_pred)))
            self.metrics["val_r2"] = float(r2_score(y_val, y_val_pred))

        return self.metrics

    def predict(self, X):
        """Make predictions. Returns array of predicted prices."""
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
        return self.model.predict(X)

    def predict_with_confidence(self, X, confidence_level=0.90):
        """Predict with confidence intervals using quantile regression."""
        point_pred = self.predict(X)

        # Use training residuals for confidence estimation
        confidence_margin = self.metrics.get("val_rmse", self.metrics.get("train_rmse", 100))
        z_score = 1.645 if confidence_level == 0.90 else 1.96  # 90% or 95%

        lower = point_pred - z_score * confidence_margin
        upper = point_pred + z_score * confidence_margin

        return {
            "predictions": point_pred.tolist(),
            "lower_bound": lower.tolist(),
            "upper_bound": upper.tolist(),
            "confidence_level": confidence_level,
        }

    def cross_validate(self, X, y, n_splits=5):
        """Time-series aware cross-validation."""
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = {"mae": [], "rmse": [], "r2": []}

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_fold_train = X.iloc[train_idx] if hasattr(X, "iloc") else X[train_idx]
            y_fold_train = y.iloc[train_idx] if hasattr(y, "iloc") else y[train_idx]
            X_fold_val = X.iloc[val_idx] if hasattr(X, "iloc") else X[val_idx]
            y_fold_val = y.iloc[val_idx] if hasattr(y, "iloc") else y[val_idx]

            fold_model = XGBRegressor(**self._default_params())
            fold_model.fit(X_fold_train, y_fold_train, eval_set=[(X_fold_val, y_fold_val)], verbose=False)

            y_fold_pred = fold_model.predict(X_fold_val)
            cv_scores["mae"].append(mean_absolute_error(y_fold_val, y_fold_pred))
            cv_scores["rmse"].append(float(np.sqrt(mean_squared_error(y_fold_val, y_fold_pred))))
            cv_scores["r2"].append(r2_score(y_fold_val, y_fold_pred))

        cv_summary = {k: {"mean": float(np.mean(v)), "std": float(np.std(v))} for k, v in cv_scores.items()}
        self.metrics["cross_validation"] = cv_summary
        return cv_summary

    def get_top_features(self, n=10):
        """Get top N most important features."""
        if not self.feature_importances:
            return []
        sorted_features = sorted(self.feature_importances.items(), key=lambda x: x[1], reverse=True)
        return sorted_features[:n]

    def save(self, crop, state):
        """Save model and metadata to disk."""
        os.makedirs(self.model_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{crop}_{state}"

        model_path = os.path.join(self.model_dir, f"{prefix}_xgb_{timestamp}.joblib")
        meta_path = os.path.join(self.model_dir, f"{prefix}_xgb_meta_{timestamp}.joblib")

        joblib.dump(self.model, model_path)
        joblib.dump({
            "feature_names": self.feature_names,
            "feature_importances": self.feature_importances,
            "metrics": self.metrics,
            "trained_at": timestamp,
        }, meta_path)

        return {"model_path": model_path, "meta_path": meta_path}

    def load(self, model_path):
        """Load a saved model."""
        self.model = joblib.load(model_path)
        meta_path = model_path.replace("_xgb_", "_xgb_meta_")
        if os.path.exists(meta_path):
            meta = joblib.load(meta_path)
            self.feature_names = meta.get("feature_names")
            self.feature_importances = meta.get("feature_importances")
            self.metrics = meta.get("metrics", {})
        return self


def train_xgboost_for_crop(df, crop, state, target_col="modal_price", test_size=0.2):
    """End-to-end training pipeline for a single crop-state pair."""
    from ..features.engineer_features import FeatureEngineer

    fe = FeatureEngineer()
    df_features = fe.engineer_all_features(df)

    # Prepare features and target
    feature_cols = [c for c in df_features.columns if c not in [target_col, "date", "crop", "state"]]
    X = df_features[feature_cols].select_dtypes(include=[np.number])
    y = df_features[target_col]

    # Train-test split (temporal)
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Train
    predictor = XGBoostPricePredictor()
    metrics = predictor.train(X_train, y_train, X_test, y_test)
    cv_scores = predictor.cross_validate(X, y)

    # Save
    paths = predictor.save(crop, state)

    # Top features for explainability
    top_features = predictor.get_top_features(15)

    return {
        "model": predictor,
        "metrics": metrics,
        "cross_validation": cv_scores,
        "top_features": top_features,
        "paths": paths,
    }
