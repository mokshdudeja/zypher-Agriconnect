"""
AgriConnect — Data Preprocessing Pipeline
Loads raw mandi + weather CSVs, merges by date + state,
handles missing values, and produces a clean dataset.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config import DATA_DIR, PROCESSED_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── Loaders ────────────────────────────────────────────────

def load_mandi(crop: str, state: str) -> pd.DataFrame:
    filepath = DATA_DIR / "mandi" / f"{crop}_{state}.csv"
    if not filepath.exists():
        log.warning("No mandi data for %s / %s", crop, state)
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Use modal price as primary; fill from avg of min/max
    df["price"] = df["modal_price"]
    mask = df["price"] == 0
    df.loc[mask, "price"] = (df.loc[mask, "min_price"] + df.loc[mask, "max_price"]) / 2

    return df


def load_weather(state: str) -> pd.DataFrame:
    filepath = DATA_DIR / "weather" / f"{state}.csv"
    if not filepath.exists():
        log.warning("No weather data for %s", state)
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ── Merge & Clean ──────────────────────────────────────────

def merge_mandi_weather(mandi: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Left-join mandi prices with weather on date."""
    if mandi.empty:
        return pd.DataFrame()
    if weather.empty:
        # Return mandi data with NaN weather columns
        for col in ["temp_max", "temp_min", "temp_mean", "precipitation", "rain", "wind_max"]:
            mandi[col] = np.nan
        return mandi

    merged = pd.merge_asof(
        mandi.sort_values("date"),
        weather.sort_values("date"),
        on="date",
        direction="nearest",
        tolerance=pd.Timedelta("2D"),
    )
    return merged


def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill then back-fill small gaps; drop rows with no price."""
    if df.empty:
        return df

    # Forward-fill weather gaps up to 7 days
    weather_cols = [c for c in ["temp_max", "temp_min", "temp_mean", "precipitation", "rain", "wind_max"] if c in df.columns]
    if weather_cols:
        df[weather_cols] = df[weather_cols].fillna(method="ffill", limit=7)
        df[weather_cols] = df[weather_cols].fillna(method="bfill", limit=7)

    # Interpolate remaining numeric gaps
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].interpolate(method="linear", limit=5)

    # Drop rows where price is still missing
    df = df.dropna(subset=["price"])

    return df


def add_basic_features(df: pd.DataFrame, crop: str, state: str) -> pd.DataFrame:
    """Add calendar and metadata columns."""
    df = df.copy()
    df["crop"] = crop
    df["state"] = state
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["day_of_week"] = df["date"].dt.dayofweek

    # Season encoding (Kharif=6-10, Rabi=11-3, Zaid=3-6)
    df["season"] = df["month"].map(_month_to_season)

    return df


def _month_to_season(m: int) -> str:
    if m in (6, 7, 8, 9, 10):
        return "kharif"
    elif m in (11, 12, 1, 2, 3):
        return "rabi"
    else:
        return "zaid"


# ── Pipeline ───────────────────────────────────────────────

def preprocess_crop_state(
    crop: str,
    state: str,
    save: bool = True,
) -> pd.DataFrame:
    """Full preprocessing pipeline for one crop × state pair."""
    mandi = load_mandi(crop, state)
    if mandi.empty:
        return pd.DataFrame()

    weather = load_weather(state)
    df = merge_mandi_weather(mandi, weather)
    df = handle_missing(df)
    df = add_basic_features(df, crop, state)

    if save and not df.empty:
        out_dir = PROCESSED_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{crop}_{state}.parquet"
        df.to_parquet(out_path, index=False)
        log.info("Saved processed data → %s (%d rows)", out_path, len(df))

    return df


def preprocess_all(
    crops: Optional[list[str]] = None,
    states: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Preprocess all crop × state pairs and concatenate."""
    from config import CROPS, INDIAN_STATES

    crops = crops or CROPS
    states = states or INDIAN_STATES
    frames: list[pd.DataFrame] = []

    total = len(crops) * len(states)
    done = 0

    for crop in crops:
        for state in states:
            done += 1
            df = preprocess_crop_state(crop, state, save=True)
            if not df.empty:
                frames.append(df)
                log.info("[%d/%d] %s / %s — %d rows", done, total, crop, state, len(df))
            else:
                log.info("[%d/%d] %s / %s — no data", done, total, crop, state)

    if frames:
        combined = pd.concat(frames, ignore_index=True)
        out_path = PROCESSED_DIR / "combined.parquet"
        combined.to_parquet(out_path, index=False)
        log.info("Combined dataset saved → %s (%d rows)", out_path, len(combined))
        return combined

    log.warning("No data found for any crop × state pair.")
    return pd.DataFrame()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Preprocess mandi + weather data")
    parser.add_argument("--crops", nargs="*")
    parser.add_argument("--states", nargs="*")
    args = parser.parse_args()

    preprocess_all(crops=args.crops, states=args.states)
