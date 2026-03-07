# Retirement Planner — Market Data API
## Developer Implementation Guide

**Version:** 2.0  
**Date:** 2026-03-07  
**Target:** Linux VPS (Hostinger)  
**Purpose:** Step-by-step implementation guide for the Market Data API service.

---

## 1. Goal

Build a lightweight VPS service that:

- Fetches **4 global benchmark series** with trailing 1-year annualized returns
- Fetches **country-specific inflation** (UK, US, EU, CA, AU)
- Fetches **country-specific interest rates** (UK, US, EU, CA, AU)
- Caches all data as **local JSON files**
- Exposes simple **JSON endpoints** with CORS for the browser-based Retirement Income Planner
- Stores **no user data whatsoever**

The primary consumer is the Retirement Income Planner, which uses the benchmark return data to auto-fill DC pot growth rate assumptions and provide drawdown guidance.

---

## 2. Prerequisites

### 2.1 API Accounts Required

Create these accounts and obtain API keys **before starting development**:

| Provider | URL | Key Required | Purpose |
|---|---|---|---|
| Tiingo | https://www.tiingo.com | Yes | Benchmark ETF prices (VTI, VWO, BND, VSS, VNQ) |
| FRED | https://fred.stlouisfed.org/docs/api/api_key.html | Yes | US inflation (CPI) and interest rate (Fed Funds) |

The following are public APIs with no key required:

| Provider | Purpose |
|---|---|
| ONS (api.ons.gov.uk) | UK inflation (CPIH) |
| OECD (sdmx.oecd.org) | EU/CA/AU inflation and interest rates |
| Bank of England | UK base rate |

### 2.2 VPS Requirements

- Ubuntu 22.04+ or similar Linux
- Python 3.11+
- Nginx installed
- A domain name pointed at the VPS (for HTTPS)

---

## 3. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| API Framework | Flask |
| WSGI Server | Gunicorn |
| Reverse Proxy | Nginx |
| Scheduler | Cron |
| Data Storage | Local JSON files |
| Secrets | `.env` file + python-dotenv |
| TLS | Certbot / Let's Encrypt |
| CORS | flask-cors |

---

## 4. Project Structure

```text
retirement-api/
├── app/
│   ├── __init__.py
│   ├── api.py                    # Flask app and endpoint definitions
│   ├── config.py                 # Configuration and environment loading
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── benchmarks.py         # Tiingo: prices + 1-year return calculation
│   │   ├── inflation.py          # FRED (US), ONS (UK), OECD (EU/CA/AU)
│   │   └── interest_rates.py     # FRED (US), BoE (UK), OECD (EU/CA/AU)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage.py            # Atomic JSON read/write
│   │   └── combine.py            # Build combined reference_data.json
│   └── utils/
│       ├── __init__.py
│       └── logging_setup.py      # Logging configuration
├── data/                         # Cached JSON files (created at runtime)
├── scripts/
│   └── update_all.py             # Single update script for cron
├── requirements.txt
├── .env                          # API keys (not committed to git)
├── .env.example                  # Template for .env
├── .gitignore
├── gunicorn.conf.py
└── README.md
```

---

## 5. Configuration

### 5.1 `.env.example`

```bash
# Data provider API keys
TIINGO_API_KEY=your_tiingo_key_here
FRED_API_KEY=your_fred_key_here

# Application settings
DATA_DIR=/opt/retirement-api/data
LOG_DIR=/var/log/retirement-api
FLASK_ENV=production
PORT=8000

# CORS - comma-separated allowed origins
CORS_ORIGINS=https://your-planner-domain.com
```

### 5.2 `app/config.py`

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    TIINGO_API_KEY: str = os.getenv("TIINGO_API_KEY", "")
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))
    CORS_ORIGINS: list = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "*").split(",")
    ]
    PORT: int = int(os.getenv("PORT", "8000"))

    @classmethod
    def validate(cls) -> list[str]:
        issues = []
        if not cls.TIINGO_API_KEY:
            issues.append("TIINGO_API_KEY not set")
        if not cls.FRED_API_KEY:
            issues.append("FRED_API_KEY not set")
        return issues
```

### 5.3 `requirements.txt`

```text
Flask==3.1.0
flask-cors==5.0.1
requests==2.32.3
gunicorn==23.0.0
python-dotenv==1.1.0
```

---

## 6. Logging

### 6.1 `app/utils/logging_setup.py`

```python
import logging
import sys
from pathlib import Path
from app.config import Config


def setup_logging(name: str = "retirement-api") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    log_dir = Config.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "api.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


log = setup_logging()
```

---

## 7. Storage Service

### 7.1 `app/services/storage.py`

Atomic writes prevent serving partial JSON if the process is interrupted.

```python
import json
import tempfile
from pathlib import Path
from typing import Any
from app.config import Config
from app.utils.logging_setup import log


def get_data_dir() -> Path:
    path = Config.DATA_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(filename: str, payload: Any) -> None:
    """Write JSON atomically: write to temp file then rename."""
    target = get_data_dir() / filename
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=get_data_dir(), suffix=".tmp"
        )
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        Path(tmp_path).rename(target)
        log.info(f"Written {filename}")
    except Exception as e:
        log.error(f"Failed to write {filename}: {e}")
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
        raise


def read_json(filename: str) -> Any:
    """Read a cached JSON file. Returns None if missing."""
    path = get_data_dir() / filename
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

---

## 8. Benchmark Fetcher (Tiingo)

This fetcher retrieves historical daily prices for each ETF proxy and calculates the trailing 1-year annualized return.

### 8.1 `app/fetchers/benchmarks.py`

```python
import requests
from datetime import date, timedelta
from app.config import Config
from app.utils.logging_setup import log

SERIES = {
    "developed_equity": {
        "ticker": "VTI",
        "label": "Developed Market Equity",
    },
    "emerging_equity": {
        "ticker": "VWO",
        "label": "Emerging Market Equity",
    },
    "global_bonds": {
        "ticker": "BND",
        "label": "Global Bonds",
    },
    "global_smallcap": {
        "ticker": "VSS",
        "label": "Global Small-Cap Equity",
    },
    "global_property": {
        "ticker": "VNQ",
        "label": "Global Property / REITs",
    },
}

TIINGO_BASE = "https://api.tiingo.com/tiingo/daily"


def _tiingo_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Token {Config.TIINGO_API_KEY}",
    }


def _fetch_price_history(ticker: str, days: int = 400) -> list[dict]:
    """
    Fetch daily price history for a ticker.
    We request ~400 days to ensure we have at least 1 year
    of trading days even accounting for weekends/holidays.
    """
    start = (date.today() - timedelta(days=days)).isoformat()
    url = f"{TIINGO_BASE}/{ticker}/prices"
    params = {
        "startDate": start,
        "resampleFreq": "daily",
    }
    resp = requests.get(
        url, headers=_tiingo_headers(), params=params, timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def _calc_return_1y(prices: list[dict]) -> float | None:
    """
    Calculate trailing 1-year return from daily price data.
    Uses adjClose for dividend-adjusted returns.
    Finds the price closest to 12 months ago.
    """
    if len(prices) < 2:
        return None

    latest = prices[-1]
    latest_price = float(latest["adjClose"])
    latest_date = latest["date"][:10]  # "YYYY-MM-DD"

    # Find price closest to 1 year ago
    target_date = date.fromisoformat(latest_date) - timedelta(days=365)

    best = None
    best_diff = 999
    for p in prices:
        p_date = date.fromisoformat(p["date"][:10])
        diff = abs((p_date - target_date).days)
        if diff < best_diff:
            best_diff = diff
            best = p

    if best is None or best_diff > 30:
        return None  # No price close enough to 1 year ago

    old_price = float(best["adjClose"])
    if old_price <= 0:
        return None

    return round((latest_price / old_price) - 1, 6)


def fetch_benchmarks() -> dict:
    """
    Fetch all benchmark series. Returns full benchmark payload.
    On per-ticker failure, that ticker is skipped with a warning.
    """
    result = {
        "as_of": str(date.today()),
        "status": "ok",
        "benchmarks": {},
    }

    errors = []

    for key, meta in SERIES.items():
        ticker = meta["ticker"]
        try:
            prices = _fetch_price_history(ticker)
            if not prices:
                raise ValueError(f"No price data returned for {ticker}")

            latest = prices[-1]
            latest_price = float(latest["adjClose"])
            price_date = latest["date"][:10]
            return_1y = _calc_return_1y(prices)

            result["benchmarks"][key] = {
                "label": meta["label"],
                "latest_price": round(latest_price, 4),
                "return_1y": return_1y,
                "price_date": price_date,
                "proxy": ticker,
                "source": "tiingo",
            }
            log.info(
                f"Benchmark {key} ({ticker}): "
                f"price={latest_price:.2f}, "
                f"return_1y={return_1y}"
            )

        except Exception as e:
            log.error(f"Failed to fetch benchmark {key} ({ticker}): {e}")
            errors.append(key)

    if errors:
        result["status"] = "partial"
        result["errors"] = errors

    return result
```

---

## 9. Inflation Fetcher

Fetches inflation data from three sources: FRED (US), ONS (UK), and OECD (EU, CA, AU).

### 9.1 `app/fetchers/inflation.py`

```python
import requests
from datetime import date
from app.config import Config
from app.utils.logging_setup import log


def _fetch_fred_cpi() -> dict | None:
    """
    Fetch US CPI 12-month percentage change from FRED.
    Series: CPIAUCSL (CPI for All Urban Consumers).
    Uses the pc1 unit transformation for year-over-year percent change.
    """
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "CPIAUCSL",
            "api_key": Config.FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
            "units": "pc1",  # Percent change from year ago
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        obs = data.get("observations", [])
        if not obs:
            return None

        latest = obs[0]
        rate = float(latest["value"]) / 100  # Convert percent to decimal
        return {
            "rate": round(rate, 4),
            "label": "US CPI 12-month rate",
            "source": "fred",
            "period": latest["date"],
        }
    except Exception as e:
        log.error(f"FRED CPI fetch failed: {e}")
        return None


def _fetch_ons_cpih() -> dict | None:
    """
    Fetch UK CPIH 12-month rate from ONS.
    Series ID: L55O (CPIH annual rate).
    """
    try:
        url = "https://api.ons.gov.uk/timeseries/L55O/dataset/MM23/data"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Get the most recent month
        months = data.get("months", [])
        if not months:
            return None

        latest = months[-1]
        rate = float(latest["value"]) / 100  # Convert percent to decimal
        return {
            "rate": round(rate, 4),
            "label": "UK CPIH 12-month rate",
            "source": "ons",
            "period": latest.get("date", ""),
        }
    except Exception as e:
        log.error(f"ONS CPIH fetch failed: {e}")
        return None


def _fetch_oecd_cpi(country_code: str, country_label: str) -> dict | None:
    """
    Fetch CPI inflation from OECD SDMX API.
    Uses the Prices dataset for year-over-year growth rate.
    country_code: OECD code (EA20, CAN, AUS)
    """
    try:
        url = (
            f"https://sdmx.oecd.org/public/rest/data/"
            f"OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
            f"{country_code}.M.N.CPI.PA._T.N.GY"
            f"?lastNObservations=1"
            f"&dimensionAtObservation=AllDimensions"
        )
        headers = {"Accept": "application/vnd.sdmx.data+json;version=2.0.0"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Navigate SDMX JSON structure to extract the value
        datasets = data.get("data", {}).get("dataSets", [{}])
        if not datasets:
            return None

        observations = datasets[0].get("observations", {})
        if not observations:
            return None

        # Get the first (only) observation
        first_key = next(iter(observations))
        value = observations[first_key][0]

        rate = round(float(value) / 100, 4)
        return {
            "rate": rate,
            "label": f"{country_label}",
            "source": "oecd",
        }
    except Exception as e:
        log.error(f"OECD CPI fetch failed for {country_code}: {e}")
        return None


def fetch_inflation() -> dict:
    """
    Fetch inflation data for all supported countries.
    """
    result = {
        "as_of": str(date.today()),
        "status": "ok",
        "inflation": {},
    }
    errors = []

    # US from FRED
    us = _fetch_fred_cpi()
    if us:
        result["inflation"]["US"] = us
    else:
        errors.append("US")

    # UK from ONS
    uk = _fetch_ons_cpih()
    if uk:
        result["inflation"]["UK"] = uk
    else:
        errors.append("UK")

    # EU, CA, AU from OECD
    oecd_countries = {
        "EU": ("EA20", "Euro Area HICP 12-month rate"),
        "CA": ("CAN", "Canada CPI 12-month rate"),
        "AU": ("AUS", "Australia CPI 12-month rate"),
    }
    for code, (oecd_code, label) in oecd_countries.items():
        data = _fetch_oecd_cpi(oecd_code, label)
        if data:
            result["inflation"][code] = data
        else:
            errors.append(code)

    if errors:
        result["status"] = "partial"
        result["errors"] = errors

    return result
```

---

## 10. Interest Rate Fetcher

Fetches central bank policy rates from FRED (US), Bank of England (UK), and OECD (EU, CA, AU).

### 10.1 `app/fetchers/interest_rates.py`

```python
import requests
from datetime import date
from app.config import Config
from app.utils.logging_setup import log


def _fetch_fred_fedfunds() -> dict | None:
    """
    Fetch US Federal Funds Effective Rate from FRED.
    Series: FEDFUNDS
    """
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "FEDFUNDS",
            "api_key": Config.FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        obs = data.get("observations", [])
        if not obs:
            return None

        latest = obs[0]
        rate = float(latest["value"]) / 100  # Percent to decimal
        return {
            "rate": round(rate, 4),
            "label": "Federal Funds Effective Rate",
            "source": "fred",
            "period": latest["date"],
        }
    except Exception as e:
        log.error(f"FRED FEDFUNDS fetch failed: {e}")
        return None


def _fetch_boe_base_rate() -> dict | None:
    """
    Fetch Bank of England Base Rate.
    Uses the BoE Statistical Interactive Database CSV export.
    Series: IUDBEDR (Official Bank Rate)
    """
    try:
        url = (
            "https://www.bankofengland.co.uk/boeapps/database/"
            "_iadb-fromshowcolumns.asp"
            "?csv.x=yes"
            "&Datefrom=01/Jan/2024"
            "&Dateto=now"
            "&SeriesCodes=IUDBEDR"
            "&CSVF=TN"
        )
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        # Parse CSV response — last non-empty line has the latest rate
        lines = resp.text.strip().split("\n")
        data_lines = [
            line for line in lines[1:]
            if line.strip() and not line.startswith("DATE")
        ]
        if not data_lines:
            return None

        last_line = data_lines[-1]
        parts = last_line.split(",")
        rate = float(parts[-1].strip()) / 100  # Percent to decimal
        return {
            "rate": round(rate, 4),
            "label": "Bank of England Base Rate",
            "source": "boe",
            "period": parts[0].strip(),
        }
    except Exception as e:
        log.error(f"BoE base rate fetch failed: {e}")
        return None


def _fetch_oecd_rate(country_code: str, country_label: str) -> dict | None:
    """
    Fetch short-term interest rate from OECD.
    Uses MEI (Main Economic Indicators) dataset.
    """
    try:
        url = (
            f"https://sdmx.oecd.org/public/rest/data/"
            f"OECD.SDD.STES,DSD_KEI@DF_KEI,4.0/"
            f"{country_code}.M.IR3TIB.PA"
            f"?lastNObservations=1"
            f"&dimensionAtObservation=AllDimensions"
        )
        headers = {"Accept": "application/vnd.sdmx.data+json;version=2.0.0"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        datasets = data.get("data", {}).get("dataSets", [{}])
        if not datasets:
            return None

        observations = datasets[0].get("observations", {})
        if not observations:
            return None

        first_key = next(iter(observations))
        value = observations[first_key][0]

        rate = round(float(value) / 100, 4)
        return {
            "rate": rate,
            "label": country_label,
            "source": "oecd",
        }
    except Exception as e:
        log.error(f"OECD rate fetch failed for {country_code}: {e}")
        return None


def fetch_interest_rates() -> dict:
    """
    Fetch interest rates for all supported countries.
    """
    result = {
        "as_of": str(date.today()),
        "status": "ok",
        "interest_rates": {},
    }
    errors = []

    # US from FRED
    us = _fetch_fred_fedfunds()
    if us:
        result["interest_rates"]["US"] = us
    else:
        errors.append("US")

    # UK from Bank of England
    uk = _fetch_boe_base_rate()
    if uk:
        result["interest_rates"]["UK"] = uk
    else:
        errors.append("UK")

    # EU, CA, AU from OECD
    oecd_countries = {
        "EU": ("EA20", "ECB Deposit Facility Rate"),
        "CA": ("CAN", "Bank of Canada Policy Rate"),
        "AU": ("AUS", "RBA Cash Rate"),
    }
    for code, (oecd_code, label) in oecd_countries.items():
        data = _fetch_oecd_rate(oecd_code, label)
        if data:
            result["interest_rates"][code] = data
        else:
            errors.append(code)

    if errors:
        result["status"] = "partial"
        result["errors"] = errors

    return result
```

---

## 11. Combine Service

### 11.1 `app/services/combine.py`

Builds the simplified `reference_data.json` for the frontend.

```python
from datetime import date


def build_reference_data(
    benchmarks: dict, inflation: dict, interest_rates: dict
) -> dict:
    """
    Build the combined reference_data.json payload.
    Extracts only the values the frontend needs.
    """
    combined = {
        "as_of": str(date.today()),
        "benchmarks": {},
        "inflation": {},
        "interest_rates": {},
    }

    # Benchmarks: extract price, return, and proxy
    for key, val in benchmarks.get("benchmarks", {}).items():
        combined["benchmarks"][key] = {
            "latest_price": val.get("latest_price"),
            "return_1y": val.get("return_1y"),
            "proxy": val.get("proxy"),
        }

    # Inflation: extract just the rate
    for key, val in inflation.get("inflation", {}).items():
        combined["inflation"][key] = val.get("rate")

    # Interest rates: extract just the rate
    for key, val in interest_rates.get("interest_rates", {}).items():
        combined["interest_rates"][key] = val.get("rate")

    return combined
```

---

## 12. Flask Application

### 12.1 `app/__init__.py`

```python
# Package marker
```

### 12.2 `app/api.py`

```python
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import Config
from app.services.storage import read_json
from app.utils.logging_setup import log


def create_app() -> Flask:
    app = Flask(__name__)

    # CORS — allow the planner frontend to call the API
    CORS(app, origins=Config.CORS_ORIGINS)

    @app.get("/api/v1/health")
    def health():
        """Health check with data freshness info."""
        freshness = {}
        for name in ["benchmarks", "inflation", "interest_rates"]:
            data = read_json(f"{name}.json")
            if data:
                freshness[name] = {
                    "as_of": data.get("as_of", "unknown"),
                    "status": data.get("status", "unknown"),
                }
            else:
                freshness[name] = {
                    "as_of": "missing",
                    "status": "missing",
                }

        overall = "ok"
        if any(v["status"] != "ok" for v in freshness.values()):
            overall = "degraded"

        return jsonify({
            "status": overall,
            "data_freshness": freshness,
        })

    @app.get("/api/v1/benchmarks/latest")
    def benchmarks_latest():
        data = read_json("benchmarks.json")
        if data is None:
            return jsonify(
                {"status": "missing", "message": "No data available"}
            ), 503
        return jsonify(data)

    @app.get("/api/v1/inflation")
    def inflation():
        data = read_json("inflation.json")
        if data is None:
            return jsonify(
                {"status": "missing", "message": "No data available"}
            ), 503
        return jsonify(data)

    @app.get("/api/v1/interest-rates")
    def interest_rates():
        data = read_json("interest_rates.json")
        if data is None:
            return jsonify(
                {"status": "missing", "message": "No data available"}
            ), 503
        return jsonify(data)

    @app.get("/api/v1/reference-data")
    def reference_data():
        data = read_json("reference_data.json")
        if data is None:
            return jsonify(
                {"status": "missing", "message": "No data available"}
            ), 503
        return jsonify(data)

    log.info("Flask app created")
    return app


app = create_app()
```

---

## 13. Update Script

### 13.1 `scripts/update_all.py`

This is the **single script** called by cron. It fetches all data, writes individual files, and rebuilds the combined file.

```python
#!/usr/bin/env python3
"""Fetch all data sources and rebuild cached JSON files."""

import sys
import datetime
from pathlib import Path

# Ensure the project root is on the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.config import Config
from app.utils.logging_setup import log
from app.services.storage import write_json, read_json
from app.services.combine import build_reference_data
from app.fetchers.benchmarks import fetch_benchmarks
from app.fetchers.inflation import fetch_inflation
from app.fetchers.interest_rates import fetch_interest_rates


def update_with_fallback(name: str, fetch_fn, filename: str) -> dict:
    """
    Attempt to fetch fresh data. On failure, keep existing cached data
    and mark it as stale.
    """
    try:
        data = fetch_fn()
        write_json(filename, data)
        log.info(f"{name}: updated successfully")
        return data
    except Exception as e:
        log.error(f"{name}: fetch failed — {e}")
        cached = read_json(filename)
        if cached:
            cached["status"] = "stale"
            cached["stale_since"] = str(datetime.date.today())
            log.warning(f"{name}: serving stale cached data")
            return cached
        else:
            log.error(f"{name}: no cached data available")
            return {"status": "error", "message": f"No data for {name}"}


def main():
    log.info("=" * 60)
    log.info("Starting data update")

    # Validate config
    issues = Config.validate()
    if issues:
        for issue in issues:
            log.error(f"Config issue: {issue}")
        log.error("Aborting update due to config issues")
        sys.exit(1)

    # Fetch all data with fallback
    benchmarks = update_with_fallback(
        "Benchmarks", fetch_benchmarks, "benchmarks.json"
    )
    inflation = update_with_fallback(
        "Inflation", fetch_inflation, "inflation.json"
    )
    interest_rates = update_with_fallback(
        "Interest Rates", fetch_interest_rates, "interest_rates.json"
    )

    # Build combined reference data
    try:
        combined = build_reference_data(
            benchmarks, inflation, interest_rates
        )
        write_json("reference_data.json", combined)
        log.info("Combined reference_data.json rebuilt")
    except Exception as e:
        log.error(f"Failed to build combined data: {e}")

    log.info("Data update complete")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
```

---

## 14. Gunicorn Configuration

### 14.1 `gunicorn.conf.py`

```python
bind = "127.0.0.1:8000"
workers = 2
timeout = 30
accesslog = "-"
errorlog = "-"
```

Run command:
```bash
gunicorn -c gunicorn.conf.py app.api:app
```

---

## 15. VPS Deployment

### 15.1 Install System Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx
```

### 15.2 Create Application Directory

```bash
sudo mkdir -p /opt/retirement-api
sudo chown -R $USER:$USER /opt/retirement-api
cd /opt/retirement-api
```

### 15.3 Clone or Upload Project Files

Copy the project structure into `/opt/retirement-api/`.

### 15.4 Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 15.5 Create `.env` File

```bash
cp .env.example .env
nano .env
# Fill in your actual API keys
```

### 15.6 Create Data and Log Directories

```bash
sudo mkdir -p /opt/retirement-api/data
sudo mkdir -p /var/log/retirement-api
sudo chown -R $USER:$USER /opt/retirement-api/data
sudo chown -R $USER:$USER /var/log/retirement-api
```

### 15.7 Run Initial Data Fetch

```bash
cd /opt/retirement-api
source venv/bin/activate
python scripts/update_all.py
```

Verify the data files were created:
```bash
ls -la data/
cat data/reference_data.json | python3 -m json.tool
```

### 15.8 Test Flask Locally

```bash
gunicorn -c gunicorn.conf.py app.api:app
# In another terminal:
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/reference-data
```

---

## 16. Systemd Service

Create `/etc/systemd/system/retirement-api.service`:

```ini
[Unit]
Description=Retirement Planner Market Data API
After=network.target

[Service]
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/opt/retirement-api
EnvironmentFile=/opt/retirement-api/.env
ExecStart=/opt/retirement-api/venv/bin/gunicorn -c gunicorn.conf.py app.api:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Important:** Replace `YOUR_USERNAME` with the actual user that owns `/opt/retirement-api`. Do **not** use `www-data` unless you change directory ownership to match.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable retirement-api
sudo systemctl start retirement-api
sudo systemctl status retirement-api
```

---

## 17. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/retirement-api`:

```nginx
# Rate limiting zone: 10 requests/second per IP
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Block all non-API paths
    location / {
        return 404;
    }
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/retirement-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 18. HTTPS with Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Certbot will automatically modify the Nginx config to add TLS.

---

## 19. Cron Job

Open crontab for the application user:

```bash
crontab -e
```

Add a single entry:

```cron
# Market Data API: daily refresh at 02:00 UTC
0 2 * * * cd /opt/retirement-api && /opt/retirement-api/venv/bin/python scripts/update_all.py >> /var/log/retirement-api/cron.log 2>&1
```

This single job fetches all data (benchmarks, inflation, interest rates) and rebuilds the combined file. Inflation data only changes monthly at source, but fetching it daily is harmless and avoids a separate cron entry.

---

## 20. `.gitignore`

```text
.env
data/
logs/
venv/
__pycache__/
*.pyc
*.tmp
```

---

## 21. Frontend Integration

The browser app calls a single endpoint:

```javascript
const API_BASE = "https://your-domain.com";

async function fetchReferenceData() {
    const resp = await fetch(`${API_BASE}/api/v1/reference-data`);
    if (!resp.ok) throw new Error("Failed to fetch reference data");
    return resp.json();
}
```

Usage in the planner:

```javascript
const data = await fetchReferenceData();

// Auto-fill growth rate for a DC pot with "developed equity" allocation
const marketReturn = data.benchmarks.developed_equity.return_1y;
// e.g., 0.082 = 8.2%

// User can override if their specific fund differs
let assumedGrowth = marketReturn;  // default to market
// assumedGrowth = 0.065;          // user override example

// Compare actual pot growth vs market
const potGrowth = (currentValue / previousValue) - 1;  // from user entries
const potVsMarket = potGrowth - marketReturn;

// Compare market vs assumption for drawdown guidance
const marketVsAssumption = marketReturn - assumedGrowth;
```

---

## 22. Failure Handling Summary

| Scenario | Behaviour |
|---|---|
| Provider API returns error | Log error, keep cached data, mark as stale |
| Provider API times out | Same as above (30s timeout) |
| One ticker fails, others succeed | Partial status, successful tickers still updated |
| No cached data exists and fetch fails | Endpoint returns 503 with error message |
| Data file is missing on disk | Endpoint returns 503 with error message |
| Cron job fails entirely | Previous data files remain, served as-is |

---

## 23. Testing Checklist

Before going live, verify:

- [ ] `.env` contains valid Tiingo and FRED API keys
- [ ] `python scripts/update_all.py` completes without errors
- [ ] `data/` contains all 4 JSON files
- [ ] `curl /api/v1/health` returns `{"status": "ok"}`
- [ ] `curl /api/v1/reference-data` returns valid benchmark data with `return_1y` values
- [ ] CORS headers present in response (`Access-Control-Allow-Origin`)
- [ ] HTTPS works via browser
- [ ] Cron job runs and log file updates
- [ ] Systemd service restarts after reboot

---

## 24. Development Order (Step by Step)

1. **Create provider accounts** — Tiingo and FRED (do this first, keys may take a few minutes)
2. **Set up project structure** — directories, `.env`, `requirements.txt`
3. **Implement `config.py`** — environment loading and validation
4. **Implement `storage.py`** — atomic JSON read/write
5. **Implement `logging_setup.py`** — file + console logging
6. **Implement `benchmarks.py`** — Tiingo fetcher with return calculation
7. **Test benchmarks** — run fetcher standalone, verify JSON output
8. **Implement `inflation.py`** — FRED + ONS + OECD fetchers
9. **Implement `interest_rates.py`** — FRED + BoE + OECD fetchers
10. **Implement `combine.py`** — build reference_data.json
11. **Implement `update_all.py`** — orchestration with fallback
12. **Implement `api.py`** — Flask app with all endpoints
13. **Test locally** — run Gunicorn, test all endpoints
14. **Deploy to VPS** — systemd, Nginx, HTTPS, cron
15. **Verify end-to-end** — cron runs, data refreshes, endpoints respond

---

## 25. Summary

This service is deliberately small and focused. It provides:

- **4 global benchmark return rates** (the primary value for the planner)
- **Country-specific inflation rates** (for spending projections)
- **Country-specific interest rates** (for discount rate modelling)
- **Simple JSON endpoints** with CORS, rate limiting, and HTTPS

The browser-based Retirement Income Planner uses this data to:

- Auto-fill DC pot growth rate assumptions from real market data
- Compare actual pot performance against market averages
- Alert when market conditions deviate from plan assumptions
- Guide drawdown adjustments to protect pot longevity to the target age

All personal financial data remains in the browser. The API serves only public reference data.
