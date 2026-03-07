import requests
from datetime import date
from app.config import Config
from app.utils.logging_setup import log

# All interest rates sourced from FRED for reliability and consistency.
# Each nation uses the most appropriate policy/reference rate series.

FRED_SERIES = {
    "US": {
        "series_id": "FEDFUNDS",
        "label": "US Federal Funds Rate",
    },
    "UK": {
        "series_id": "IUDSOIA",
        "label": "UK Sterling Overnight Index Average (SONIA)",
    },
    "EU": {
        "series_id": "ECBMRRFR",
        "label": "ECB Main Refinancing Rate",
    },
    "CA": {
        "series_id": "IRSTCI01CAM156N",
        "label": "Canada Immediate Interest Rate",
    },
    "AU": {
        "series_id": "IRSTCI01AUM156N",
        "label": "Australia Immediate Interest Rate",
    },
}


def _fetch_fred_rate(nation: str) -> dict:
    """
    Fetch the latest interest/policy rate for a nation from FRED.
    Returns rate as a decimal (e.g., 0.0364 for 3.64%).
    """
    meta = FRED_SERIES[nation]
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": meta["series_id"],
        "api_key": Config.FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    obs = resp.json().get("observations", [])

    # Filter out missing values (FRED uses "." for missing)
    valid = [(o["date"], float(o["value"])) for o in obs if o["value"] != "."]
    if not valid:
        raise ValueError(f"No valid observations for {meta['series_id']}")

    latest_date, latest_val = valid[0]

    return {
        "nation": nation,
        "label": meta["label"],
        "rate": round(latest_val / 100, 6),  # Convert percentage to decimal
        "period": latest_date,
        "source": "fred",
        "series": meta["series_id"],
    }


def fetch_interest_rates() -> dict:
    """
    Fetch interest/policy rates for all configured nations via FRED.
    Returns full interest rates payload with per-nation results.
    """
    result = {
        "as_of": str(date.today()),
        "status": "ok",
        "nations": {},
    }
    errors = []

    for nation in FRED_SERIES:
        try:
            result["nations"][nation] = _fetch_fred_rate(nation)
            rate = result["nations"][nation]["rate"]
            log.info(f"Interest rate {nation}: {rate*100:.2f}%")
        except Exception as e:
            log.error(f"Failed to fetch {nation} interest rate: {e}")
            errors.append(nation)

    if errors:
        result["status"] = "partial" if result["nations"] else "error"
        result["errors"] = errors

    return result
