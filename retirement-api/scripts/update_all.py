#!/usr/bin/env python3
"""Daily data refresh script for the Retirement Data API."""
import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from app.utils.logging_setup import log
from app.services.storage import write_json


def update_benchmarks() -> bool:
    try:
        from app.fetchers.benchmarks import fetch_benchmarks
        log.info("Fetching benchmarks...")
        data = fetch_benchmarks()
        write_json("benchmarks.json", data)
        count = len(data.get("benchmarks", {}))
        log.info(f"Benchmarks updated: {count} series, status={data['status']}")
        return data["status"] == "ok"
    except Exception as e:
        log.error(f"Benchmark update failed: {e}")
        return False


def update_inflation() -> bool:
    try:
        from app.fetchers.inflation import fetch_inflation
        log.info("Fetching inflation data...")
        data = fetch_inflation()
        write_json("inflation.json", data)
        count = len(data.get("nations", {}))
        log.info(f"Inflation updated: {count} nations, status={data['status']}")
        return data["status"] == "ok"
    except Exception as e:
        log.error(f"Inflation update failed: {e}")
        return False


def update_interest_rates() -> bool:
    try:
        from app.fetchers.interest_rates import fetch_interest_rates
        log.info("Fetching interest rates...")
        data = fetch_interest_rates()
        write_json("interest_rates.json", data)
        count = len(data.get("nations", {}))
        log.info(f"Interest rates updated: {count} nations, status={data['status']}")
        return data["status"] == "ok"
    except Exception as e:
        log.error(f"Interest rate update failed: {e}")
        return False


def main():
    log.info("=" * 60)
    log.info("Starting daily data refresh")
    log.info("=" * 60)

    start = time.time()
    results = {}

    results["benchmarks"] = update_benchmarks()
    results["inflation"] = update_inflation()
    results["interest_rates"] = update_interest_rates()

    elapsed = time.time() - start
    success = all(results.values())
    failed = [k for k, v in results.items() if not v]

    log.info("=" * 60)
    if success:
        log.info(f"All updates completed successfully in {elapsed:.1f}s")
    else:
        log.warning(
            f"Updates completed with errors in {elapsed:.1f}s. "
            f"Failed: {', '.join(failed)}"
        )
    log.info("=" * 60)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
