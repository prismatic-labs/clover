#!/usr/bin/env python3
"""
fetch-data.py — Weekly data refresh for prismatic-labs/clover

Updates data/stressors.json with:
  - Current economic indicators from FRED, OECD, World Bank
  - Recalculated pressure_index for each stressor based on current data

Also archives a snapshot to data/history/YYYY-MM-DD.json.

Run manually:  python3 scripts/fetch-data.py
In CI:         Called by .github/workflows/update-data.yml

Dependencies: requests
Optional:     pydantic (for response validation)

Environment:  FRED_API_KEY (required for FRED data; free at https://fred.stlouisfed.org/docs/api/api_key.html)
"""

import json
import logging
import math
import os
import random
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ─── Paths ─────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).parent.parent
DATA_FILE   = REPO_ROOT / "data" / "stressors.json"
HISTORY_DIR = REPO_ROOT / "data" / "history"

# ─── Model constants ────────────────────────────────────────────────────────
MONTE_CARLO_RUNS    = 500   # iterations for uncertainty band
WEIGHT_NOISE        = 0.20  # ±20% uniform noise on driver weights
BASELINE_PERIOD     = "2019-2020"

# ─── Severity bands ─────────────────────────────────────────────────────────
def severity_from_pct(pct: int) -> str:
    if pct >= 60: return "extreme"
    if pct >= 40: return "high"
    if pct >= 20: return "moderate"
    return "low"

# ─── FRED API ───────────────────────────────────────────────────────────────
# Free key from https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"

# FRED series IDs mapped to our indicator keys
FRED_SERIES = {
    "UNRATE":        "unemployment_rate_pct",        # Unemployment rate
    "U6RATE":        "underemployment_rate_pct",     # U-6 underemployment
    "MORTGAGE30US":  "mortgage_rate_30yr_pct",       # 30-year fixed mortgage rate
    "CPIAUCSL":      "cpi_all_items",                # CPI All Items
    "CUSR0000SAF11": "cpi_food_energy",              # CPI Food + Energy (proxy)
    "UMCSENT":       "consumer_sentiment",           # U of Michigan Consumer Sentiment
    "DRCCLACBS":     "credit_delinquency_rate_pct",  # Credit card delinquency rate
    "TDSP":          "debt_service_ratio_pct",       # Household debt service ratio
}

# ─── Baselines (pre-pandemic 2019-2020 average, US-centric for seed) ───────
BASELINES = {
    "unemployment_rate_pct": 3.7,
    "underemployment_rate_pct": 7.0,
    "mortgage_rate_30yr_pct": 3.7,
    "cpi_all_items": 258.8,
    "cpi_food_energy": 252.1,
    "consumer_sentiment": 96.0,
    "credit_delinquency_rate_pct": 2.3,
    "debt_service_ratio_pct": 9.7,
    "rent_to_income_ratio": 0.29,
    "gini_index": 0.389,
    "median_mean_wage_ratio": 0.76,
    "real_wage_growth_pct": 1.5,
    "household_debt_to_income": 1.35,
}

# ─── Stressor definitions ──────────────────────────────────────────────────
# Each stressor has drivers with weights (from published evidence) and
# a mapping to indicator keys.

STRESSOR_CONFIGS = {
    "housing_cost_burden": {
        "sensitivity": 1.15,   # calibration coefficient
        "drivers": [
            {"key": "rent_to_income_ratio", "weight": 0.50, "baseline_key": "rent_to_income_ratio"},
            {"key": "mortgage_rate_30yr_pct", "weight": 0.30, "baseline_key": "mortgage_rate_30yr_pct"},
            # Housing supply gap is not easily fetched from FRED; use a slower-moving proxy
        ],
    },
    "unemployment": {
        "sensitivity": 1.10,
        "drivers": [
            {"key": "unemployment_rate_pct", "weight": 0.45, "baseline_key": "unemployment_rate_pct"},
            # Long-term unemployment share — derived from BLS, not directly on FRED as a simple series
            {"key": "underemployment_rate_pct", "weight": 0.25, "baseline_key": "underemployment_rate_pct"},
        ],
    },
    "inflation_pressure": {
        "sensitivity": 1.05,
        "drivers": [
            {"key": "cpi_food_energy", "weight": 0.50, "baseline_key": "cpi_food_energy"},
            # Real wage growth — computed as nominal wage growth - CPI change
            {"key": "consumer_sentiment", "weight": 0.15, "baseline_key": "consumer_sentiment", "invert": True},
        ],
    },
    "consumer_debt": {
        "sensitivity": 1.08,
        "drivers": [
            {"key": "debt_service_ratio_pct", "weight": 0.45, "baseline_key": "debt_service_ratio_pct"},
            {"key": "credit_delinquency_rate_pct", "weight": 0.35, "baseline_key": "credit_delinquency_rate_pct"},
        ],
    },
    "income_inequality": {
        "sensitivity": 0.95,
        "drivers": [
            {"key": "gini_index", "weight": 0.40, "baseline_key": "gini_index"},
            # Inequality data moves very slowly; mostly uses seed values
        ],
    },
}


def load_existing() -> dict[str, Any]:
    """Load current stressors.json."""
    with open(DATA_FILE, encoding="utf-8") as fh:
        return json.load(fh)


# ─── Fetch functions ────────────────────────────────────────────────────────

def fetch_fred_series(series_id: str) -> float | None:
    """Fetch the most recent value for a FRED series."""
    if not FRED_API_KEY:
        log.warning("FRED_API_KEY not set — skipping %s", series_id)
        return None
    try:
        resp = requests.get(FRED_API_BASE, params={
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 5,
        }, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        observations = data.get("observations", [])
        for obs in observations:
            val = obs.get("value")
            if val is not None and val != ".":
                return float(val)
        log.warning("FRED %s: no valid observations", series_id)
        return None
    except Exception as e:
        log.warning("FRED %s failed: %s", series_id, e)
        return None


def fetch_all_indicators() -> dict[str, float]:
    """Fetch all available indicators from FRED. Returns key→value dict."""
    indicators: dict[str, float] = {}
    for series_id, key in FRED_SERIES.items():
        val = fetch_fred_series(series_id)
        if val is not None:
            indicators[key] = val
            log.info("  %s (%s) = %.4f", key, series_id, val)
    return indicators


# ─── Computation ────────────────────────────────────────────────────────────

def compute_change_pct(current: float, baseline: float, invert: bool = False) -> float:
    """Compute percentage change from baseline. If invert, a drop is positive pressure."""
    if baseline == 0:
        return 0.0
    pct = ((current - baseline) / abs(baseline)) * 100
    return -pct if invert else pct


def compute_pressure_index(
    stressor_id: str,
    indicators: dict[str, float],
    floor_pct: float,
    weight_noise: float = 0.0,
) -> float:
    """
    Compute the pressure index for a stressor.
    Compute the pressure index for a stressor from its drivers.
    """
    config = STRESSOR_CONFIGS.get(stressor_id)
    if not config:
        return 0.0

    sensitivity = config["sensitivity"]
    drivers = config["drivers"]

    total_weight = 0.0
    weighted_sum = 0.0

    for d in drivers:
        key = d["key"]
        baseline_key = d["baseline_key"]
        weight = d["weight"]
        invert = d.get("invert", False)

        current = indicators.get(key)
        baseline = BASELINES.get(baseline_key)

        if current is None or baseline is None:
            continue

        # Apply optional weight noise for Monte Carlo
        if weight_noise > 0:
            noise = random.uniform(-weight_noise, weight_noise)
            weight = max(0.01, weight * (1 + noise))

        change = compute_change_pct(current, baseline, invert)
        # Clamp individual driver changes to reasonable range
        change = max(-50, min(200, change))

        weighted_sum += weight * abs(change)
        total_weight += weight

    if total_weight == 0:
        return 0.0

    normalised = weighted_sum / total_weight
    raw = normalised * sensitivity

    # Apply local resilience floor
    max_pressure = 100 - floor_pct
    clamped = max(1.0, min(max_pressure, raw))
    return clamped


def run_monte_carlo(
    stressor_id: str,
    indicators: dict[str, float],
    floor_pct: float,
    runs: int = MONTE_CARLO_RUNS,
) -> tuple[int, int, int]:
    """
    Run Monte Carlo simulation for uncertainty bands.
    Returns (point_estimate, low_10th, high_90th).
    """
    point = compute_pressure_index(stressor_id, indicators, floor_pct, weight_noise=0.0)

    samples = []
    for _ in range(runs):
        s = compute_pressure_index(stressor_id, indicators, floor_pct, weight_noise=WEIGHT_NOISE)
        samples.append(s)

    samples.sort()
    p10 = samples[int(runs * 0.10)]
    p90 = samples[int(runs * 0.90)]

    return round(point), round(p10), round(p90)


def update_stressor_data(data: dict, indicators: dict[str, float], stale: list[str]) -> dict:
    """Recalculate all stressor pressure indices with current indicators."""

    # Merge fetched indicators with existing source values
    sources = data.get("sources", {})
    for key, val in indicators.items():
        sources[key] = round(val, 4)
    data["sources"] = sources

    # Track stale sources
    if stale:
        data["stale_sources"] = stale

    # Update tipping points
    tp = sources.get("tipping_points", {})
    rent = indicators.get("rent_to_income_ratio", sources.get("rent_to_income_ratio", 0))
    tp["housing_affordability_crisis"] = rent > 0.30
    tp["housing_current_ratio"] = round(rent, 3) if rent else tp.get("housing_current_ratio", 0)
    unemp = indicators.get("unemployment_rate_pct", sources.get("unemployment_rate_pct", 0))
    tp["unemployment_stress_risk"] = unemp > 6.0
    tp["unemployment_current_pct"] = round(unemp, 1) if unemp else tp.get("unemployment_current_pct", 0)
    sources["tipping_points"] = tp

    # Recalculate each stressor
    for stressor in data.get("stressors", []):
        sid = stressor["id"]
        floor = stressor.get("local_resilience_floor_pct", 30)

        point, low, high = run_monte_carlo(sid, indicators, floor)
        stressor["pressure_index"] = point
        stressor["pressure_low"] = low
        stressor["pressure_high"] = high
        stressor["severity"] = severity_from_pct(point)

        # Update driver change_pct values
        config = STRESSOR_CONFIGS.get(sid, {})
        config_drivers = {d["key"]: d for d in config.get("drivers", [])}
        for driver in stressor.get("drivers", []):
            # Try to match by input name to config key
            for cfg_key, cfg_d in config_drivers.items():
                if cfg_key in driver.get("source", "").lower() or cfg_key.replace("_", " ") in driver.get("input", "").lower():
                    current = indicators.get(cfg_key)
                    baseline = BASELINES.get(cfg_d["baseline_key"])
                    if current is not None and baseline is not None:
                        invert = cfg_d.get("invert", False)
                        driver["change_pct"] = round(compute_change_pct(current, baseline, invert))
                    break

    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return data


def archive_snapshot(data: dict) -> None:
    """Save a dated snapshot to data/history/."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    date_str = data["last_updated"]
    dest = HISTORY_DIR / f"{date_str}.json"
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    log.info("Archived snapshot to %s", dest)


def main() -> None:
    log.info("=== Clover data update ===")
    log.info("Loading existing data from %s", DATA_FILE)

    data = load_existing()
    stale: list[str] = []

    # Fetch indicators
    log.info("Fetching indicators from FRED...")
    indicators = fetch_all_indicators()

    if not indicators:
        log.warning("No indicators fetched — keeping existing values")
        stale.append("FRED (all series)")
    else:
        log.info("Fetched %d indicators", len(indicators))

    # Merge in values that aren't from FRED (slower-moving, from seed data)
    existing_sources = data.get("sources", {})
    for key in BASELINES:
        if key not in indicators and key in existing_sources:
            indicators[key] = existing_sources[key]

    # Recalculate
    log.info("Recalculating pressure indices...")
    data = update_stressor_data(data, indicators, stale)

    # Write
    log.info("Writing updated data to %s", DATA_FILE)
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    # Archive
    archive_snapshot(data)

    # Summary
    log.info("=== Summary ===")
    for s in data.get("stressors", []):
        log.info(
            "  %s: %d%% [%d–%d] (%s)",
            s["name"], s["pressure_index"], s["pressure_low"], s["pressure_high"], s["severity"]
        )
    if stale:
        log.warning("Stale sources: %s", ", ".join(stale))

    log.info("Done.")


if __name__ == "__main__":
    main()
