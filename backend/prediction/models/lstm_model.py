"""
LSTM Model for Crop Price Time Series Prediction
Captures sequential patterns in price data
"""
import numpy as np
import pandas as pd
import os
import json
from datetime import datetime

# Use TensorFlow/Keras for LSTM
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
    from tensorflow.keras.optimizers import Adam
    HAS_TF = True
except ImportError:
    HAS_TF = False


class LSTMPricePredictor:
    """LSTM-based time series price prediction model."""

    def __init__(self, sequence_length=30, model_dir="models/saved"):
        if not HAS_TF:
            raise ImportError(
                "TensorFlow is required for LSTM. Install with: pip install tensorflow"
            )
        self.sequence_length = sequence_length
        self.model_dir = model_dir
        self.model = None
        self.scaler_params = None
        self.metrics = {}

    def _build_model(self, n_features, lstm_units=None):
        """Build LSTM architecture."""
        if lstm_units is None:
            lstm_units = [128, 64]

        model = Sequential()

        # First LSTM layer
        model.add(LSTM(
            units=lstm_units[0],
            return_sequences=True if len(lstm_units) > 1 else False,
            input_shape=(self.sequence_length, n_features),
        ))
        model.add(BatchNormalization())
        model.add(Dropout(0.2))

        # Additional LSTM layers
        for i, units in enumerate(lstm_units[1:], 1):
            return_seq = i < len(lstm_units) - 1
            model.add(LSTM(units=units, return_sequences=return_seq))
            model.add(BatchNormalization())
            model.add(Dropout(0.2))

        # Output layers
        model.add(Dense(32, activation="relu"))
        model.add(Dropout(0.1))
        model.add(Dense(3))  # Predict 7d, 15d, 30d ahead

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss="huber",
            metrics=["mae"],
        )
        return model

    def create_sequences(self, data, targets=None):
        """Create input sequences for LSTM."""
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            if targets is not None:
                y.append(targets[i + self.sequence_length])
        return np.array(X), np.array(y) if targets is not None else np.array(X)

    def train(self, X_train, y_train, X_val=None, y_val=None,
              epochs=100, batch_size=32, lstm_units=None):
        """Train LSTM model with callbacks."""
        n_features = X_train.shape[2]
        self.model = self._build_model(n_features, lstm_units)

        callbacks = [
            EarlyStopping(
                monitor="val_loss" if X_val is not None else "loss",
                patience=15,
                restore_best_weights=True,
            ),
            ReduceLROnPlateau(
                monitor="val_loss" if X_val is not None else "loss",
                factor=0.5,
                patience=5,
                min_lr=1e-6,
            ),
        ]

        validation_data = (X_val, y_val) if X_val is not None else None

        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=1,
        )

        # Metrics
        y_pred_train = self.model.predict(X_train, verbose=0)
        self.metrics["train_mae"] = float(np.mean(np.abs(y_train - y_pred_train)))
        self.metrics["train_rmse"] = float(np.sqrt(np.mean((y_train - y_pred_train) ** 2)))

        if X_val is not None and y_val is not None:
            y_pred_val = self.model.predict(X_val, verbose=0)
            self.metrics["val_mae"] = float(np.mean(np.abs(y_val - y_pred_val)))
            self.metrics["val_rmse"] = float(np.sqrt(np.mean((y_val - y_pred_val) ** 2)))

        self.metrics["epochs_trained"] = len(history.history["loss"])
        return self.metrics

    def predict(self, X):
        """Make predictions. Returns array of shape (n, 3) for [7d, 15d, 30d]."""
        if self.model is None:
            raise ValueError("Model not trained yet.")
        return self.model.predict(X, verbose=0)

    def predict_single(self, sequence):
        """Predict from a single sequence of shape (seq_len, n_features)."""
        if sequence.ndim == 2:
            sequence = np.expand_dims(sequence, axis=0)
        pred = self.predict(sequence)
        return {
            "predicted_price_7d": float(pred[0][0]),
            "predicted_price_15d": float(pred[0][1]),
            "predicted_price_30d": float(pred[0][2]),
        }

    def save(self, crop, state):
        """Save LSTM model and metadata."""
        os.makedirs(self.model_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{crop}_{state}"

        model_path = os.path.join(self.model_dir, f"{prefix}_lstm_{timestamp}")
        self.model.save(model_path)

        meta_path = os.path.join(self.model_dir, f"{prefix}_lstm_meta_{timestamp}.json")
        meta = {
            "sequence_length": self.sequence_length,
            "metrics": self.metrics,
            "trained_at": timestamp,
            "model_path": model_path,
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        return {"model_path": model_path, "meta_path": meta_path}

    def load(self, model_path):
        """Load a saved LSTM model."""
        self.model = load_model(model_path)
        meta_path = model_path.replace("_lstm_", "_lstm_meta_").replace("/", "/")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            self.sequence_length = meta.get("sequence_length", self.sequence_length)
            self.metrics = meta.get("metrics", {})
        return self


def prepare_lstm_data(df, target_col="modal_price", sequence_length=30, forecast_horizons=[7, 15, 30]):
    """Prepare data sequences for LSTM training."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if target_col in numeric_cols:
        numeric_cols.remove(target_col)

    feature_cols = [target_col] + numeric_cols[:10]  # Limit features for LSTM

    scaler_min = df[feature_cols].min()
    scaler_max = df[feature_cols].max()
    scaler_range = scaler_max - scaler_min
    scaler_range[scaler_range == 0] = 1

    data_scaled = (df[feature_cols] - scaler_min) / scaler_range

    # Create targets: price at future horizons
    target_values = df[target_col].values
    targets = []
    for horizon in forecast_horizons:
        if horizon < len(target_values):
            shifted = np.full(len(target_values), np.nan)
            shifted[:-horizon] = target_values[horizon:]
            targets.append(shifted)
        else:
            targets.append(np.full(len(target_values), np.nan))

    targets_array = np.column_stack(targets)

    # Drop rows with NaN targets
    valid_mask = ~np.isnan(targets_array).any(axis=1) & ~np.isnan(data_scaled.values).any(axis=1)
    data_valid = data_scaled.values[valid_mask]
    targets_valid = targets_array[valid_mask]

    scaler_info = {
        "min": scaler_min.to_dict(),
        "max": scaler_max.to_dict(),
    }

    return data_valid, targets_valid, scaler_info
