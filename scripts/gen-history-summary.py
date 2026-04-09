#!/usr/bin/env python3
"""
gen-history-summary.py — Aggregate daily snapshots into a summary for sparklines.

Reads data/history/*.json and produces data/history-summary.json with:
  {
    "dates": ["2026-04-01", "2026-04-08", ...],
    "history": {
      "housing_cost_burden": [68, 69, ...],
      "unemployment": [42, 41, ...],
      ...
    }
  }

Run: python3 scripts/gen-history-summary.py
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT   = Path(__file__).parent.parent
HISTORY_DIR = REPO_ROOT / "data" / "history"
SUMMARY_FILE = REPO_ROOT / "data" / "history-summary.json"


def main() -> None:
    snapshots = sorted(HISTORY_DIR.glob("*.json"))
    if not snapshots:
        log.warning("No history snapshots found in %s", HISTORY_DIR)
        return

    dates: list[str] = []
    history: dict[str, list[int]] = {}

    for snap_path in snapshots:
        date_str = snap_path.stem
        dates.append(date_str)

        with open(snap_path, encoding="utf-8") as fh:
            snap = json.load(fh)

        for stressor in snap.get("stressors", []):
            sid = stressor["id"]
            pct = stressor.get("pressure_index", 0)
            if sid not in history:
                history[sid] = []
            history[sid].append(pct)

    # Pad shorter series with None (in case a stressor was added later)
    max_len = len(dates)
    for sid in history:
        while len(history[sid]) < max_len:
            history[sid].insert(0, None)

    summary = {"dates": dates, "history": history}

    with open(SUMMARY_FILE, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    log.info("Wrote history summary: %d dates, %d stressors", len(dates), len(history))


if __name__ == "__main__":
    main()
