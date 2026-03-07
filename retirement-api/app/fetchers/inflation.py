import requests
from datetime import date, timedelta
from app.config import Config
from app.utils.logging_setup import log

# ─── FRED (US CPI) ───────────────────────────────────────────────

def _fetch_fred_cpi() -> dict:
    """
    Fetch US CPI-U (CPIAUCSL) from FRED.
    Calculate YoY inflation rate from the last 13 monthly observations.
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "CPIAUCSL",
        "api_key": Config.FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 15,  # extra buffer for revisions
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    obs = resp.json().get("observations", [])

    # Filter out any non-numeric values (FRED uses "." for missing)
    valid = [(o["date"], float(o["value"])) for o in obs if o["value"] != "."]
    if len(valid) < 13:
        raise ValueError(f"Not enough CPI observations: {len(valid)}")

    latest_date, latest_val = valid[0]
    year_ago_date, year_ago_val = valid[12]

    if year_ago_val <= 0:
        raise ValueError("Invalid year-ago CPI value")

    yoy = round((latest_val / year_ago_val) - 1, 6)

    return {
        "nation": "US",
        "label": "US CPI-U (YoY)",
        "rate": yoy,
        "period": latest_date,
        "prior_period": year_ago_date,
        "source": "fred",
        "series": "CPIAUCSL",
    }


# ─── OECD (UK, EU, CA, AU) ───────────────────────────────────────

OECD_NATIONS = {
    "UK": {"code": "GBR", "label": "UK CPI (YoY)"},
    "EU": {"code": "EA20", "label": "Eurozone HICP (YoY)"},
    "CA": {"code": "CAN", "label": "Canada CPI (YoY)"},
    "AU": {"code": "AUS", "label": "Australia CPI (YoY)"},
}


def _fetch_oecd_cpi(nation_key: str) -> dict:
    """
    Fetch CPI inflation from OECD SDMX REST API.
    Uses PRICES_CPI dataset, measure CPI, unit PA (percent per annum),
    transformation GY (growth rate over 1 year).
    Tries monthly first, falls back to quarterly.
    """
    meta = OECD_NATIONS[nation_key]
    loc = meta["code"]

    for freq in ["M", "Q"]:
        url = (
            f"https://sdmx.oecd.org/public/rest/data/"
            f"OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
            f"{loc}.{freq}.N.CPI.PA._T.N.GY.?lastNObservations=1"
            f"&dimensionAtObservation=AllDimensions"
        )
        headers = {"Accept": "application/vnd.sdmx.data+json;version=2.0.0"}

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()

            # Navigate SDMX-JSON 2.0 structure
            datasets = data.get("data", {}).get("dataSets", [])
            if not datasets:
                continue

            observations = datasets[0].get("observations", {})
            if not observations:
                continue

            # Get the first (and only) observation
            obs_key = list(observations.keys())[0]
            obs_val = observations[obs_key][0]

            # Get time period from dimensions
            structures = data.get("data", {}).get("structures", [{}])
            obs_dims = structures[0].get("dimensions", {}).get("observation", [])
            time_dim = None
            for d in obs_dims:
                if d.get("id") == "TIME_PERIOD":
                    time_dim = d
                    break

            period = "unknown"
            if time_dim:
                # For AllDimensions, the key is like "0:0:0:0:0:0:0:0:0"
                # The last index corresponds to TIME_PERIOD
                indices = obs_key.split(":")
                time_idx = len(obs_dims) - 1  # TIME_PERIOD is last dimension
                idx = int(indices[time_idx]) if time_idx < len(indices) else 0
                vals = time_dim.get("values", [])
                if vals and idx < len(vals):
                    period = vals[idx].get("id", "unknown")

            return {
                "nation": nation_key,
                "label": meta["label"],
                "rate": round(float(obs_val) / 100, 6),
                "period": period,
                "frequency": freq,
                "source": "oecd",
            }

        except requests.exceptions.HTTPError:
            continue

    raise ValueError(f"Could not fetch OECD CPI for {nation_key} ({loc})")


# ─── Main entry point ─────────────────────────────────────────────

def fetch_inflation() -> dict:
    """
    Fetch inflation data for all configured nations.
    US via FRED, UK/EU/CA/AU via OECD.
    Returns full inflation payload with per-nation results.
    """
    result = {
        "as_of": str(date.today()),
        "status": "ok",
        "nations": {},
    }
    errors = []

    # US via FRED
    try:
        result["nations"]["US"] = _fetch_fred_cpi()
        log.info(f"Inflation US: {result['nations']['US']['rate']*100:.2f}%")
    except Exception as e:
        log.error(f"Failed to fetch US inflation: {e}")
        errors.append("US")

    # UK, EU, CA, AU via OECD
    for nation in ["UK", "EU", "CA", "AU"]:
        try:
            result["nations"][nation] = _fetch_oecd_cpi(nation)
            log.info(f"Inflation {nation}: {result['nations'][nation]['rate']*100:.2f}%")
        except Exception as e:
            log.error(f"Failed to fetch {nation} inflation: {e}")
            errors.append(nation)

    if errors:
        result["status"] = "partial" if result["nations"] else "error"
        result["errors"] = errors

    return result
