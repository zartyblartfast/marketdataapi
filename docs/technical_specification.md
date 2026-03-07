# Retirement Planner — Market Data API
## Technical Specification

**Version:** 2.0  
**Date:** 2026-03-07  
**Target Deployment:** Linux VPS (Hostinger)  
**Purpose:** Provide market benchmark growth rates and macroeconomic reference data for the browser-based Retirement Income Planner.

---

## 1. Purpose & Context

### 1.1 The Problem

The Retirement Income Planner models DC pension pot sustainability to a target end-of-life age (e.g., 90). Each DC pot has an asset allocation (equity, bonds, property, etc.) with an **assumed annual growth rate** that drives the projection.

Currently these growth rates are **manually entered guesses**. The Market Data API replaces them with **real market-average returns** per asset class.

### 1.2 What the API Enables

| Function | Description |
|---|---|
| **Auto-fill growth rates** | The planner auto-populates projected growth rates with trailing market returns per asset class from the API. The user can override if their specific fund consistently differs from the market average. |
| **Market performance monitoring** | Compare actual market returns against the user's assumed growth rates. Alert when the market is significantly over- or under-performing assumptions. |
| **Pot-level performance monitoring** | Compare the user's actual pot growth (calculated from successive manual value entries) against the market average for that asset class. |
| **Drawdown guidance** | Advise the user to increase drawdown if the market is outperforming or decrease drawdown if underperforming, to protect pot longevity. |
| **Macro data capture** | Serve country-specific inflation and interest rates for future use in spending projections and discount rate modelling. |

### 1.3 Architecture Principle

- **All personal financial data stays in the browser** (local storage).
- **The API serves only public reference data** — no user accounts, no personal data, no GDPR exposure.
- **Comparison and alerting logic runs in the browser**, not on the server.

---

## 2. System Architecture

```
+---------------------+
|  External Data APIs |
|                     |
| Tiingo              |
| FRED / ONS / OECD   |
+----------+----------+
           |
    (scheduled refresh)
           |
           v
+----------------------+
| Market Data API      |
| Linux VPS (Flask)    |
| Fetchers → JSON cache|
+----------+-----------+
           |
    JSON endpoints
    (HTTPS + CORS)
           |
           v
+------------------------+
| Retirement Planner App |
| Browser (JavaScript)   |
| All user data local    |
+------------------------+
```

---

## 3. Data Categories

The API publishes three categories of data.

### 3.1 Global Market Benchmarks

Four benchmark series representing the major asset classes found in retirement portfolios. These are **global** (not country-specific).

| Internal Key | Asset Class | ETF Proxy | Source |
|---|---|---|---|
| `developed_equity` | Developed market equities | VTI | Tiingo |
| `emerging_equity` | Emerging market equities | VWO | Tiingo |
| `global_bonds` | Global bond markets | BND | Tiingo |
| `global_property` | Global property / REITs | VNQ | Tiingo |

For each benchmark the API provides:

| Field | Description |
|---|---|
| `latest_price` | Most recent adjusted closing price |
| `return_1y` | Trailing 1-year annualized return (decimal, e.g., 0.082 = 8.2%) |
| `price_date` | Date of the latest price |
| `proxy` | ETF ticker used as proxy |
| `source` | Data provider name |

**How returns are calculated:**

The fetcher retrieves at least 13 months of monthly closing prices. The 1-year return is:

```
return_1y = (latest_price / price_12_months_ago) - 1
```

### 3.2 Inflation Data (Country-Specific)

Annual CPI inflation rate (12-month percentage change) per country. Used for adjusting spending projections in the planner.

| Country | Code | Source | Series |
|---|---|---|---|
| United Kingdom | UK | ONS | CPIH 12-month rate |
| United States | US | FRED | CPIAUCSL (calculated) |
| Euro Area | EU | OECD | HICP |
| Canada | CA | OECD | CPI |
| Australia | AU | OECD | CPI |

### 3.3 Interest Rates (Country-Specific)

Central bank policy rates or close proxies. Used for risk-free return estimation and discount rate modelling.

| Country | Code | Source | Series |
|---|---|---|---|
| United Kingdom | UK | Bank of England | Base Rate |
| United States | US | FRED | FEDFUNDS |
| Euro Area | EU | ECB / OECD | Deposit Facility Rate |
| Canada | CA | OECD | Policy Rate |
| Australia | AU | OECD | Cash Rate |

---

## 4. Data Providers

### 4.1 Market Data — Tiingo (Primary)

- **What:** End-of-day ETF prices and historical daily prices.
- **Free tier:** 500 requests/day, sufficient for 4 tickers daily.
- **Account required:** Yes — https://www.tiingo.com
- **API key:** Provided on registration.

### 4.2 US Economic Data — FRED

- **What:** US CPI, Federal Funds Rate, and other macro series.
- **Free tier:** 120 requests/minute, more than sufficient.
- **Account required:** Yes — https://fred.stlouisfed.org/docs/api/api_key.html
- **API key:** Provided on registration.

### 4.3 UK Economic Data — ONS

- **What:** UK CPI/CPIH inflation.
- **Free tier:** Public API, no key required.
- **Endpoint:** ONS API v1 — time series datasets.

### 4.4 International Data — OECD

- **What:** Inflation and interest rates for EU, CA, AU, and fallback for others.
- **Free tier:** Public API, no key required.
- **Endpoint:** OECD SDMX REST API.

### 4.5 UK Interest Rate — Bank of England

- **What:** Bank Rate (base rate).
- **Free tier:** Public statistical database, no key required.
- **Endpoint:** BoE Statistical Interactive Database.

### 4.6 Provider Priority

| Data | Primary | Fallback |
|---|---|---|
| Benchmark prices | Tiingo | — (cache serves stale) |
| US inflation | FRED | OECD |
| US interest rate | FRED | OECD |
| UK inflation | ONS | OECD |
| UK interest rate | BoE | OECD |
| EU / CA / AU macro | OECD | — (cache serves stale) |

---

## 5. API Endpoints

All endpoints are prefixed with `/api/v1`.

### 5.1 Health Check

```
GET /api/v1/health
```

Response:
```json
{
  "status": "ok",
  "data_freshness": {
    "benchmarks": {"as_of": "2026-03-07", "status": "ok"},
    "inflation": {"as_of": "2026-03-01", "status": "ok"},
    "interest_rates": {"as_of": "2026-03-07", "status": "ok"}
  }
}
```

### 5.2 Benchmark Data

```
GET /api/v1/benchmarks/latest
```

Response:
```json
{
  "as_of": "2026-03-07",
  "status": "ok",
  "benchmarks": {
    "developed_equity": {
      "label": "Developed Market Equity",
      "latest_price": 281.42,
      "return_1y": 0.082,
      "price_date": "2026-03-06",
      "proxy": "VTI",
      "source": "tiingo"
    },
    "emerging_equity": {
      "label": "Emerging Market Equity",
      "latest_price": 41.18,
      "return_1y": 0.045,
      "price_date": "2026-03-06",
      "proxy": "VWO",
      "source": "tiingo"
    },
    "global_bonds": {
      "label": "Global Bonds",
      "latest_price": 73.51,
      "return_1y": 0.031,
      "price_date": "2026-03-06",
      "proxy": "BND",
      "source": "tiingo"
    },
    "global_property": {
      "label": "Global Property / REITs",
      "latest_price": 89.42,
      "return_1y": 0.056,
      "price_date": "2026-03-06",
      "proxy": "VNQ",
      "source": "tiingo"
    }
  }
}
```

### 5.3 Inflation Data

```
GET /api/v1/inflation
```

Response:
```json
{
  "as_of": "2026-03-01",
  "status": "ok",
  "inflation": {
    "UK": {"rate": 0.039, "label": "UK CPIH 12-month rate", "source": "ons"},
    "US": {"rate": 0.031, "label": "US CPI 12-month rate", "source": "fred"},
    "EU": {"rate": 0.028, "label": "Euro Area HICP 12-month rate", "source": "oecd"},
    "CA": {"rate": 0.032, "label": "Canada CPI 12-month rate", "source": "oecd"},
    "AU": {"rate": 0.034, "label": "Australia CPI 12-month rate", "source": "oecd"}
  }
}
```

### 5.4 Interest Rate Data

```
GET /api/v1/interest-rates
```

Response:
```json
{
  "as_of": "2026-03-07",
  "status": "ok",
  "interest_rates": {
    "UK": {"rate": 0.0425, "label": "Bank of England Base Rate", "source": "boe"},
    "US": {"rate": 0.045, "label": "Federal Funds Rate", "source": "fred"},
    "EU": {"rate": 0.035, "label": "ECB Deposit Facility Rate", "source": "oecd"},
    "CA": {"rate": 0.040, "label": "Bank of Canada Policy Rate", "source": "oecd"},
    "AU": {"rate": 0.0375, "label": "RBA Cash Rate", "source": "oecd"}
  }
}
```

### 5.5 Combined Reference Data (Primary Frontend Endpoint)

```
GET /api/v1/reference-data
```

Response:
```json
{
  "as_of": "2026-03-07",
  "benchmarks": {
    "developed_equity": {"latest_price": 281.42, "return_1y": 0.082, "proxy": "VTI"},
    "emerging_equity": {"latest_price": 41.18, "return_1y": 0.045, "proxy": "VWO"},
    "global_bonds": {"latest_price": 73.51, "return_1y": 0.031, "proxy": "BND"},
    "global_property": {"latest_price": 89.42, "return_1y": 0.056, "proxy": "VNQ"}
  },
  "inflation": {
    "UK": 0.039, "US": 0.031, "EU": 0.028, "CA": 0.032, "AU": 0.034
  },
  "interest_rates": {
    "UK": 0.0425, "US": 0.045, "EU": 0.035, "CA": 0.040, "AU": 0.0375
  }
}
```

---

## 6. Technology Stack

| Component | Technology |
|---|---|
| OS | Ubuntu 22.04+ (Hostinger VPS) |
| Language | Python 3.11+ |
| API Framework | Flask |
| WSGI Server | Gunicorn |
| Reverse Proxy | Nginx (with CORS + rate limiting) |
| Scheduler | Cron |
| Data Storage | Local JSON files |
| Secrets | Environment variables (`.env` file) |
| TLS | Certbot / Let's Encrypt |

---

## 7. Refresh Schedule

A single cron job runs `update_all.py` which fetches all data sources and rebuilds all JSON files.

| Data | Refresh Frequency | Rationale |
|---|---|---|
| Market benchmarks | Daily (02:00 UTC) | End-of-day prices update overnight |
| Interest rates | Daily (02:00 UTC) | Policy rates can change at any meeting |
| Inflation | Monthly (2nd of month, 03:00 UTC) | CPI data published monthly |

Cron entry:
```
0 2 * * * cd /opt/retirement-api && /opt/retirement-api/venv/bin/python scripts/update_all.py >> /var/log/retirement-api/update.log 2>&1
```

Inflation is fetched in every run but only changes monthly at source. This avoids a separate cron entry.

---

## 8. Data Storage

```
data/
├── benchmarks.json          # Full benchmark detail (prices + returns)
├── inflation.json           # Full inflation detail (rates + labels + sources)
├── interest_rates.json      # Full interest rate detail
└── reference_data.json      # Simplified combined file for frontend
```

All files are overwritten atomically (write to temp file, then rename) to prevent serving partial data.

---

## 9. Failure Handling

If an upstream provider fails during a refresh:

1. **Keep the last successful cached JSON** — do not overwrite with empty/partial data.
2. **Set status to `stale`** in the affected JSON file.
3. **Log the error** with timestamp, provider, HTTP status, and error message.
4. **The API continues serving** the cached data — endpoints never return errors to the frontend.

Stale response example:
```json
{
  "as_of": "2026-03-06",
  "status": "stale",
  "stale_since": "2026-03-07T02:00:00Z",
  "message": "Using last successful cached data"
}
```

The `/api/v1/health` endpoint reports staleness so it can be monitored.

---

## 10. Security & Privacy

| Requirement | Implementation |
|---|---|
| No user data on server | API serves only public reference data |
| API keys protected | Stored in `.env`, never in code or git |
| HTTPS | TLS via Certbot / Let's Encrypt |
| CORS | Configured to allow only the planner's domain |
| Rate limiting | Nginx `limit_req_zone` (e.g., 10 req/s per IP) |
| File permissions | Data directory owned by the service user |

---

## 11. Frontend Integration Summary

The browser-based Retirement Income Planner will:

1. **Fetch** `/api/v1/reference-data` on startup (and cache locally).
2. **Auto-fill** each DC pot's projected growth rate with the `return_1y` value for the matching asset class.
3. **Allow the user to override** the growth rate if their specific fund differs from the market average.
4. **Calculate actual pot growth** from successive manual value entries (pot value and "value as of" date).
5. **Compare three values** per pot:
   - User's assumed growth rate (auto-filled or overridden)
   - Market-average return from API (`return_1y`)
   - Actual pot growth (calculated from value entries)
6. **Display simple alerts** when significant deviation is detected.
7. **Suggest drawdown adjustments** to protect pot longevity to the target age.

All comparison logic, alerting, and drawdown calculations run **entirely in the browser**.

---

## 12. Implementation Phases

### Phase 1 — MVP

- Flask API with `/api/v1/reference-data` endpoint
- Benchmark fetcher (Tiingo) with trailing 1-year return calculation
- Inflation fetcher (FRED for US, ONS for UK, OECD for EU/CA/AU)
- Interest rate fetcher (FRED for US, BoE for UK, OECD for EU/CA/AU)
- JSON file caching with atomic writes
- Error handling and stale fallback
- Logging
- Cron-based daily refresh
- Nginx reverse proxy with CORS and HTTPS
- Systemd service

### Phase 2 — Enhancements

- Trailing 3-year and 5-year annualized returns
- Monthly historical price series endpoint
- Provider fallback chains (e.g., if Tiingo fails, try Alpha Vantage)
- Additional countries for inflation/interest rates

### Phase 3 — Future

- Exchange rates
- Volatility metrics
- Benchmark definitions/metadata endpoint
- Country metadata endpoint

---

## 13. Accounts Required

Before development begins, create accounts and obtain API keys for:

| Provider | URL | Key Required | Free Tier |
|---|---|---|---|
| Tiingo | https://www.tiingo.com | Yes | 500 req/day |
| FRED | https://fred.stlouisfed.org/docs/api/api_key.html | Yes | 120 req/min |
| ONS | https://api.ons.gov.uk | No | Public |
| OECD | https://data.oecd.org | No | Public |
| Bank of England | https://www.bankofengland.co.uk/statistics | No | Public |
