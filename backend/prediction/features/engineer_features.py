"""
AgriConnect — Feature Engineering Pipeline
Transforms preprocessed crop data into ML-ready features:
  • Lag prices (1m, 3m, 6m)
  • Rolling averages (3m, 6m, 12m)
  • Price momentum & volatility
  • Weather anomalies (rainfall deviation)
  • Seasonal encoding
  • State-wise demand-supply gap proxy
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    PROCESSED_DIR,
    LAG_PERIODS,
    ROLLING_WINDOWS,
    CROP_SEASON_MAP,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── Price Features ─────────────────────────────────────────

def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lagged price columns: price_lag_30, price_lag_90, price_lag_180."""
    df = df.copy()
    for days in LAG_PERIODS:
        df[f"price_lag_{days}"] = df["price"].shift(days)
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling mean and std for 3m, 6m, 12m windows."""
    df = df.copy()
    for days in ROLLING_WINDOWS:
        df[f"price_rollmean_{days}"] = df["price"].rolling(window=days, min_periods=1).mean()
        df[f"price_rollstd_{days}"] = df["price"].rolling(window=days, min_periods=1).std()
    return df


def add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    """Price momentum: rate of change over 7d and 30d."""
    df = df.copy()
    df["price_momentum_7d"] = df["price"].pct_change(7)
    df["price_momentum_30d"] = df["price"].pct_change(30)
    # Acceleration (second derivative)
    df["price_acceleration"] = df["price_momentum_7d"].diff(7)
    return df


def add_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling standard deviation as volatility proxy + coefficient of variation."""
    df = df.copy()
    df["price_volatility_30d"] = df["price"].rolling(30, min_periods=1).std()
    df["price_volatility_90d"] = df["price"].rolling(90, min_periods=1).std()
    # Coefficient of variation
    roll_mean = df["price"].rolling(30, min_periods=1).mean()
    roll_std = df["price"].rolling(30, min_periods=1).std()
    df["price_cv_30d"] = np.where(roll_mean != 0, roll_std / roll_mean, 0)
    return df


# ── Weather Features ───────────────────────────────────────

def add_weather_anomaly_features(df: pd.DataFrame) -> pd.DataFrame:
    """Rainfall deviation from normal, temperature anomaly, dry/wet spell indicators."""
    df = df.copy()

    if "rain" not in df.columns and "precipitation" not in df.columns:
        df["rain"] = np.nan
        df["temp_mean"] = np.nan

    rain_col = "rain" if "rain" in df.columns else "precipitation"

    # 30-day rolling normal rainfall
    df["rain_normal_30d"] = df[rain_col].rolling(30, min_periods=1).mean()
    df["rain_deviation_30d"] = df[rain_col] - df["rain_normal_30d"]
    df["rain_anomaly_pct"] = np.where(
        df["rain_normal_30d"] != 0,
        df["rain_deviation_30d"] / df["rain_normal_30d"],
        0,
    )

    # Consecutive dry days
    df["is_dry"] = (df[rain_col] < 1.0).astype(int)
    df["dry_spell"] = df["is_dry"].groupby(
        (df["is_dry"] != df["is_dry"].shift()).cumsum()
    ).cumcount() + 1
    df.loc[df["is_dry"] == 0, "dry_spell"] = 0

    # Temperature anomaly
    if "temp_mean" in df.columns:
        df["temp_normal_30d"] = df["temp_mean"].rolling(30, min_periods=1).mean()
        df["temp_anomaly"] = df["temp_mean"] - df["temp_normal_30d"]
    else:
        df["temp_anomaly"] = 0

    # Drop helper columns
    df = df.drop(columns=["is_dry", "rain_normal_30d"], errors="ignore")
    return df


# ── Seasonal Features ──────────────────────────────────────

def add_seasonal_features(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode seasons + cyclical month encoding."""
    df = df.copy()

    # One-hot seasons
    for season in ["kharif", "rabi", "zaid"]:
        df[f"season_{season}"] = (df["season"] == season).astype(int)

    # Cyclical month encoding
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # Day of year cyclical
    df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

    # Harvest proximity (days until typical harvest for crop's season)
    df["days_to_harvest"] = df.apply(_days_to_harvest, axis=1)

    return df


def _days_to_harvest(row) -> int:
    crop = row.get("crop", "")
    month = row.get("month", 1)
    season = CROP_SEASON_MAP.get(crop, "kharif")

    harvest_months = {"kharif": 10, "rabi": 3, "zaid": 6}
    harvest_month = harvest_months.get(season, 10)

    diff = (harvest_month - month) % 12
    return diff * 30  # approximate days


# ── Demand-Supply Proxy ────────────────────────────────────

def add_demand_supply_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Proxy for state-wise demand-supply gap using arrival quantity trends.
    Higher arrivals → oversupply → price pressure downward.
    """
    df = df.copy()

    if "arrival_qty" in df.columns:
        df["arrival_qty_30d_avg"] = df["arrival_qty"].rolling(30, min_periods=1).mean()
        df["arrival_qty_90d_avg"] = df["arrival_qty"].rolling(90, min_periods=1).mean()
        # Supply surplus index: recent vs. longer-term average
        df["supply_surplus_index"] = np.where(
            df["arrival_qty_90d_avg"] != 0,
            df["arrival_qty_30d_avg"] / df["arrival_qty_90d_avg"],
            1.0,
        )
    else:
        df["arrival_qty_30d_avg"] = 0
        df["arrival_qty_90d_avg"] = 0
        df["supply_surplus_index"] = 1.0

    return df


# ── Target Variables ───────────────────────────────────────

def add_target_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Create target columns: price in 7, 15, 30 days."""
    df = df.copy()
    df["target_7d"] = df["price"].shift(-7)
    df["target_15d"] = df["price"].shift(-15)
    df["target_30d"] = df["price"].shift(-30)
    return df


# ── Full Pipeline ──────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full feature engineering pipeline on a preprocessed DataFrame."""
    if df.empty:
        return df

    log.info("Engineering features for %d rows …", len(df))

    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_momentum_features(df)
    df = add_volatility_features(df)
    df = add_weather_anomaly_features(df)
    df = add_seasonal_features(df)
    df = add_demand_supply_features(df)
    df = add_target_columns(df)

    # Drop rows where target is NaN (trailing rows)
    before = len(df)
    df = df.dropna(subset=["target_7d", "target_15d", "target_30d"])
    log.info("Dropped %d rows with NaN targets. %d rows remaining.", before - len(df), len(df))

    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return the list of feature columns (exclude targets, metadata, dates)."""
    exclude = {
        "date", "crop", "state", "season", "commodity", "district",
        "market", "variety", "unit",
        "target_7d", "target_15d", "target_30d",
    }
    return [c for c in df.columns if c not in exclude and df[c].dtype in ("float64", "int64", "float32", "int32", "int")]


def engineer_and_save(
    processed_path: Optional[str] = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Load processed data, engineer features, save, and return (df, feature_cols)."""
    if processed_path is None:
        processed_path = str(PROCESSED_DIR / "combined.parquet")

    path = Path(processed_path)
    if not path.exists():
        log.error("Processed file not found: %s", path)
        return pd.DataFrame(), []

    df = pd.read_parquet(path)
    df = engineer_features(df)

    # Save featured dataset
    out_path = PROCESSED_DIR / "featured.parquet"
    df.to_parquet(out_path, index=False)
    log.info("Featured dataset saved → %s (%d rows, %d columns)", out_path, len(df), len(df.columns))

    feature_cols = get_feature_columns(df)
    log.info("Feature columns (%d): %s", len(feature_cols), feature_cols[:10])

    return df, feature_cols


if __name__ == "__main__":
    df, features = engineer_and_save()
    print(f"Dataset: {len(df)} rows, {len(features)} features")
