"""
AgriConnect — Weather Data Collection
Fetches historical weather from Open-Meteo Archive API.
Daily temperature, rainfall, humidity per state.
"""

import csv
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from config import DATA_DIR, INDIAN_STATES, STATE_COORDS, OPEN_METEO_ARCHIVE

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def fetch_weather_archive(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Fetch daily weather archive for a location."""
    url = f"{OPEN_METEO_ARCHIVE}/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "rain_sum",
            "et0_fao_evapotranspiration",
            "wind_speed_10m_max",
        ]),
        "timezone": "Asia/Kolkata",
    }

    client = httpx.Client(timeout=30)
    try:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return _parse_daily(data)
    except Exception as e:
        log.warning("Weather API error for (%.2f, %.2f): %s", lat, lon, e)
        return []
    finally:
        client.close()


def _parse_daily(data: dict) -> list[dict]:
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    records = []
    for i, date in enumerate(dates):
        records.append({
            "date": date,
            "temp_max": daily.get("temperature_2m_max", [None])[i],
            "temp_min": daily.get("temperature_2m_min", [None])[i],
            "temp_mean": daily.get("temperature_2m_mean", [None])[i],
            "precipitation": daily.get("precipitation_sum", [None])[i],
            "rain": daily.get("rain_sum", [None])[i],
            "evapotranspiration": daily.get("et0_fao_evapotranspiration", [None])[i],
            "wind_max": daily.get("wind_speed_10m_max", [None])[i],
        })
    return records


def save_weather_csv(records: list[dict], state: str) -> Path:
    out_dir = DATA_DIR / "weather"
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / f"{state}.csv"

    fieldnames = [
        "date", "temp_max", "temp_min", "temp_mean",
        "precipitation", "rain", "evapotranspiration", "wind_max",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    log.info("Saved %d weather records → %s", len(records), filepath)
    return filepath


def collect_all_weather(
    states: list[str] | None = None,
    start_date: str = "2015-01-01",
    end_date: str | None = None,
) -> list[Path]:
    """Collect weather for all states.  Splits into yearly chunks for reliability."""
    states = states or INDIAN_STATES
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    files: list[Path] = []

    for state in states:
        coords = STATE_COORDS.get(state)
        if not coords:
            log.warning("No coords for %s — skipping", state)
            continue

        lat, lon = coords
        log.info("Fetching weather for %s (%.2f, %.2f)", state, lat, lon)

        # Split into yearly chunks to avoid API timeouts
        all_records: list[dict] = []
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])

        for year in range(start_year, end_year + 1):
            chunk_start = f"{year}-01-01" if year > start_year else start_date
            chunk_end = f"{year}-12-31" if year < end_year else end_date
            records = fetch_weather_archive(lat, lon, chunk_start, chunk_end)
            all_records.extend(records)
            time.sleep(0.3)

        if all_records:
            f = save_weather_csv(all_records, state)
            files.append(f)

    log.info("Weather collection complete. %d files.", len(files))
    return files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Collect Open-Meteo weather data")
    parser.add_argument("--states", nargs="*", help="States (default: all)")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    collect_all_weather(states=args.states, start_date=args.start, end_date=args.end)
