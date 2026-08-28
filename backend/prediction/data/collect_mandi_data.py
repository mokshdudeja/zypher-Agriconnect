"""
AgriConnect — Mandi Price Data Collection
Fetches historical crop prices from Agmarknet.gov.in via their public API.
Saves daily CSV per crop-state pair.
"""

import csv
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx

from config import (
    DATA_DIR, CROPS, INDIAN_STATES, AGMARKNET_CROPS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Agmarknet public API
AGMARKNET_API = "https://api.data.gov.in/resource"
AGMARKNET_RESOURCE_ID = "359856e0-2940-4db7-a518-bec053bd5301"  # mandi daily prices


def _agmarknet_params(
    commodity: str,
    start_date: str,
    end_date: str,
    state: Optional[str] = None,
    page: int = 1,
) -> dict:
    filters = [
        {"field": "commodity", "value": commodity, "operator": "=="},
        {"field": "date", "value": start_date, "operator": ">="},
        {"field": "date", "value": end_date, "operator": "<="},
    ]
    if state:
        filters.append({"field": "state", "value": state.title(), "operator": "=="})

    return {
        "api-key": "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b",
        "format": "json",
        "limit": 1000,
        "offset": (page - 1) * 1000,
        "filters": filters,
    }


def fetch_mandi_prices(
    crop: str,
    state: str,
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
) -> list[dict]:
    """Fetch mandi prices for a crop-state pair, paginating through results."""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    commodity = AGMARKNET_CROPS.get(crop, crop.title())
    all_records: list[dict] = []
    page = 1

    client = httpx.Client(timeout=30, follow_redirects=True)

    while True:
        params = _agmarknet_params(commodity, start_date, end_date, state, page)
        try:
            resp = client.get(AGMARKNET_API, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning("Agmarknet API error (page %d): %s", page, e)
            break

        records = data.get("records", [])
        if not records:
            break

        all_records.extend(records)
        log.info("  %s / %s — page %d: %d records", crop, state, page, len(records))

        total = int(data.get("count", 0))
        if page * 1000 >= total:
            break
        page += 1
        time.sleep(0.5)  # rate-limit courtesy

    client.close()
    return all_records


def normalize_record(rec: dict) -> dict:
    """Flatten an Agmarknet record into a clean schema."""
    return {
        "date": rec.get("date", ""),
        "state": rec.get("state", ""),
        "district": rec.get("district", ""),
        "market": rec.get("market", ""),
        "commodity": rec.get("commodity", ""),
        "variety": rec.get("variety", ""),
        "min_price": _safe_float(rec.get("min_price")),
        "max_price": _safe_float(rec.get("max_price")),
        "modal_price": _safe_float(rec.get("modal_price")),
        "arrival_qty": _safe_float(rec.get("arrival_quantity")),
        "unit": rec.get("unit", "Quintal"),
    }


def _safe_float(val) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def save_csv(records: list[dict], crop: str, state: str) -> Path:
    """Write records to a CSV file."""
    out_dir = DATA_DIR / "mandi"
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / f"{crop}_{state}.csv"

    fieldnames = [
        "date", "state", "district", "market", "commodity",
        "variety", "min_price", "max_price", "modal_price",
        "arrival_qty", "unit",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(normalize_record(rec))

    log.info("Saved %d records → %s", len(records), filepath)
    return filepath


def collect_all(
    crops: Optional[list[str]] = None,
    states: Optional[list[str]] = None,
    start_date: str = "2015-01-01",
) -> list[Path]:
    """Collect mandi prices for all crop × state combinations."""
    crops = crops or CROPS
    states = states or INDIAN_STATES
    files: list[Path] = []

    total = len(crops) * len(states)
    done = 0

    for crop in crops:
        for state in states:
            done += 1
            log.info("[%d/%d] Fetching %s — %s", done, total, crop, state)
            records = fetch_mandi_prices(crop, state, start_date)
            if records:
                f = save_csv(records, crop, state)
                files.append(f)
            time.sleep(1)  # be kind to the API

    log.info("Collection complete. %d files saved.", len(files))
    return files


# ── CLI entry point ────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Collect Agmarknet mandi prices")
    parser.add_argument("--crops", nargs="*", help="Crops to collect (default: all)")
    parser.add_argument("--states", nargs="*", help="States to collect (default: all)")
    parser.add_argument("--start", default="2015-01-01", help="Start date YYYY-MM-DD")
    args = parser.parse_args()

    collect_all(crops=args.crops, states=args.states, start_date=args.start)
