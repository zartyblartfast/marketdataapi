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
