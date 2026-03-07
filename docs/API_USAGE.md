# Market Data API — Usage Guide

> **Base URL:** `https://marketdata.countdays.co.uk`  
> **Authentication:** None required — this API serves public reference data only  
> **Rate Limit:** 10 requests/second per IP (burst up to 20)  
> **CORS:** Enabled for browser-based access  
> **Data Refresh:** Daily at 06:00 UTC

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Endpoints Overview](#2-endpoints-overview)
3. [Health Check](#3-health-check)
4. [Benchmarks](#4-benchmarks---trailing-1-year-returns)
5. [Inflation](#5-inflation---year-on-year-cpi-rates)
6. [Interest Rates](#6-interest-rates---central-bank--policy-rates)
7. [Reference Data (Combined)](#7-reference-data---all-data-in-one-call)
8. [Filtering by Nation](#8-filtering-by-nation)
9. [Understanding the Response](#9-understanding-the-response)
10. [Error Handling](#10-error-handling)
11. [JavaScript Integration Examples](#11-javascript-integration-examples)
12. [Supported Nations](#12-supported-nations)
13. [Data Sources & Freshness](#13-data-sources--freshness)

---

## 1. Quick Start

Fetch all market data in a single call:

```bash
curl https://marketdata.countdays.co.uk/api/v1/reference-data
```

Or from JavaScript:

```javascript
const response = await fetch("https://marketdata.countdays.co.uk/api/v1/reference-data");
const data = await response.json();
console.log(data.benchmarks.benchmarks.developed_equity.return_1y); // e.g. 0.189487
console.log(data.inflation.nations.UK.rate);                        // e.g. 0.032
console.log(data.interest_rates.nations.US.rate);                   // e.g. 0.0364
```

---

## 2. Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health and version |
| `/api/v1/benchmarks` | GET | Trailing 1-year returns for equity, bond, small-cap & property ETFs |
| `/api/v1/inflation` | GET | Year-on-year CPI inflation rates by nation |
| `/api/v1/interest-rates` | GET | Current central bank / policy interest rates by nation |
| `/api/v1/reference-data` | GET | **Combined** — all benchmarks, inflation & interest rates |

All endpoints accept an optional `?nation=XX` query parameter (see [Section 8](#8-filtering-by-nation)).

---

## 3. Health Check

Use this endpoint to verify the API is running.

### Request

```bash
curl https://marketdata.countdays.co.uk/health
```

### Response

```json
{
    "service": "retirement-data-api",
    "status": "healthy",
    "timestamp": "2026-03-07T16:30:47.248102Z",
    "version": "1.0.0"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `service` | string | Service identifier |
| `status` | string | `"healthy"` when operational |
| `timestamp` | string | Current server time (ISO 8601 UTC) |
| `version` | string | API version |

---

## 4. Benchmarks — Trailing 1-Year Returns

Returns annualized 1-year total returns for five asset-class proxy ETFs. These represent broad market performance and can be used to **auto-fill growth rate assumptions** in the Retirement Income Planner.

### Request

```bash
curl https://marketdata.countdays.co.uk/api/v1/benchmarks
```

### Response

```json
{
    "_meta": {
        "served_at": "2026-03-07T16:30:45.850450Z",
        "stale": false
    },
    "as_of": "2026-03-07",
    "benchmarks": {
        "developed_equity": {
            "label": "Developed Market Equity",
            "latest_price": 331.41,
            "price_date": "2026-03-06",
            "proxy": "VTI",
            "return_1y": 0.189487,
            "source": "tiingo"
        },
        "emerging_equity": {
            "label": "Emerging Market Equity",
            "latest_price": 54.47,
            "price_date": "2026-03-06",
            "proxy": "VWO",
            "return_1y": 0.224302,
            "source": "tiingo"
        },
        "global_bonds": {
            "label": "Global Bonds",
            "latest_price": 74.24,
            "price_date": "2026-03-06",
            "proxy": "BND",
            "return_1y": 0.056228,
            "source": "tiingo"
        },
        "global_property": {
            "label": "Global Property / REITs",
            "latest_price": 93.55,
            "price_date": "2026-03-06",
            "proxy": "VNQ",
            "return_1y": 0.058513,
            "source": "tiingo"
        }
    },
    "status": "ok"
}
```

### Benchmark Fields

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Human-readable asset class name |
| `proxy` | string | ETF ticker symbol used as proxy |
| `return_1y` | float | **Trailing 1-year annualized return** (decimal, e.g. `0.189487` = 18.95%) |
| `latest_price` | float | Most recent closing price (USD) |
| `price_date` | string | Date of the latest price (YYYY-MM-DD) |
| `source` | string | Data provider (`"tiingo"`) |

### Asset Class Mapping

| Key | ETF | Asset Class | Use Case |
|-----|-----|-------------|----------|
| `developed_equity` | VTI | Developed Market Equity | Growth allocation |
| `emerging_equity` | VWO | Emerging Market Equity | Higher-risk growth |
| `global_bonds` | BND | Global Bonds | Conservative / income |
| `global_smallcap` | VSS | Global Small-Cap Equity | Small-cap growth / diversification |
| `global_property` | VNQ | Global Property / REITs | Real asset diversification |

### Converting Returns to Percentages

The `return_1y` value is a decimal. To display as a percentage:

```javascript
const pct = (data.benchmarks.developed_equity.return_1y * 100).toFixed(2);
// "18.95"
```

---

## 5. Inflation — Year-on-Year CPI Rates

Returns the latest year-on-year Consumer Price Index (CPI) inflation rate for each supported nation.

### Request

```bash
curl https://marketdata.countdays.co.uk/api/v1/inflation
```

### Response

```json
{
    "_meta": {
        "served_at": "2026-03-07T16:30:45.988765Z",
        "stale": false
    },
    "as_of": "2026-03-07",
    "nations": {
        "AU": {
            "frequency": "M",
            "label": "Australia CPI (YoY)",
            "nation": "AU",
            "period": "2026-01",
            "rate": 0.03843,
            "source": "oecd"
        },
        "CA": {
            "frequency": "M",
            "label": "Canada CPI (YoY)",
            "nation": "CA",
            "period": "2026-01",
            "rate": 0.022939,
            "source": "oecd"
        },
        "EU": {
            "frequency": "M",
            "label": "Eurozone HICP (YoY)",
            "nation": "EU",
            "period": "2025-12",
            "rate": 0.019,
            "source": "oecd"
        },
        "UK": {
            "frequency": "M",
            "label": "UK CPI (YoY)",
            "nation": "UK",
            "period": "2026-01",
            "rate": 0.032,
            "source": "oecd"
        },
        "US": {
            "frequency": "M",
            "label": "US CPI Urban (YoY)",
            "nation": "US",
            "period": "2026-01-01",
            "rate": 0.028319,
            "source": "fred"
        }
    },
    "status": "ok"
}
```

### Inflation Fields

| Field | Type | Description |
|-------|------|-------------|
| `nation` | string | Two-letter nation code |
| `label` | string | Human-readable description |
| `rate` | float | **Year-on-year inflation rate** (decimal, e.g. `0.032` = 3.2%) |
| `period` | string | Reference period for the data point |
| `frequency` | string | Data frequency (`"M"` = monthly) |
| `source` | string | Data provider (`"fred"` or `"oecd"`) |

---

## 6. Interest Rates — Central Bank / Policy Rates

Returns the current central bank or policy interest rate for each supported nation.

### Request

```bash
curl https://marketdata.countdays.co.uk/api/v1/interest-rates
```

### Response

```json
{
    "_meta": {
        "served_at": "2026-03-07T16:30:46.238939Z",
        "stale": false
    },
    "as_of": "2026-03-07",
    "nations": {
        "AU": {
            "label": "Australia Immediate Interest Rate",
            "nation": "AU",
            "period": "2026-01-01",
            "rate": 0.036,
            "series": "IRSTCI01AUM156N",
            "source": "fred"
        },
        "CA": {
            "label": "Canada Immediate Interest Rate",
            "nation": "CA",
            "period": "2026-01-01",
            "rate": 0.0225,
            "series": "IRSTCI01CAM156N",
            "source": "fred"
        },
        "EU": {
            "label": "ECB Main Refinancing Rate",
            "nation": "EU",
            "period": "2026-03-06",
            "rate": 0.0215,
            "series": "ECBMRRFR",
            "source": "fred"
        },
        "UK": {
            "label": "UK Sterling Overnight Index Average (SONIA)",
            "nation": "UK",
            "period": "2026-03-04",
            "rate": 0.037301,
            "series": "IUDSOIA",
            "source": "fred"
        },
        "US": {
            "label": "US Federal Funds Effective Rate",
            "nation": "US",
            "period": "2026-03-06",
            "rate": 0.0364,
            "series": "DFF",
            "source": "fred"
        }
    },
    "status": "ok"
}
```

### Interest Rate Fields

| Field | Type | Description |
|-------|------|-------------|
| `nation` | string | Two-letter nation code |
| `label` | string | Human-readable rate description |
| `rate` | float | **Current interest rate** (decimal, e.g. `0.0364` = 3.64%) |
| `period` | string | Date of the data point (YYYY-MM-DD) |
| `series` | string | FRED series identifier |
| `source` | string | Data provider (`"fred"`) |

---

## 7. Reference Data — All Data in One Call

Returns **benchmarks, inflation, and interest rates combined** in a single response. This is the recommended endpoint for the Retirement Income Planner to minimize API calls.

### Request

```bash
curl https://marketdata.countdays.co.uk/api/v1/reference-data
```

### Response Structure

```json
{
    "as_of": "2026-03-07",
    "benchmarks": {
        "_meta": { "served_at": "...", "stale": false },
        "as_of": "2026-03-07",
        "benchmarks": {
            "developed_equity": { ... },
            "emerging_equity": { ... },
            "global_bonds": { ... },
            "global_smallcap": { ... },
            "global_property": { ... }
        },
        "status": "ok"
    },
    "inflation": {
        "_meta": { "served_at": "...", "stale": false },
        "as_of": "2026-03-07",
        "nations": {
            "AU": { ... },
            "CA": { ... },
            "EU": { ... },
            "UK": { ... },
            "US": { ... }
        },
        "status": "ok"
    },
    "interest_rates": {
        "_meta": { "served_at": "...", "stale": false },
        "as_of": "2026-03-07",
        "nations": {
            "AU": { ... },
            "CA": { ... },
            "EU": { ... },
            "UK": { ... },
            "US": { ... }
        },
        "status": "ok"
    },
    "status": "ok"
}
```

### Accessing Nested Data

```javascript
const ref = await fetch("https://marketdata.countdays.co.uk/api/v1/reference-data")
    .then(r => r.json());

// Benchmark returns
const equityReturn = ref.benchmarks.benchmarks.developed_equity.return_1y;
const bondReturn   = ref.benchmarks.benchmarks.global_bonds.return_1y;

// Inflation for a specific nation
const ukInflation  = ref.inflation.nations.UK.rate;

// Interest rate for a specific nation
const usRate       = ref.interest_rates.nations.US.rate;
```

---

## 8. Filtering by Nation

All data endpoints accept an optional `nation` query parameter to return data for a single nation.

### Supported Nation Codes

| Code | Country |
|------|---------|
| `US` | United States |
| `UK` | United Kingdom |
| `EU` | Euro Area |
| `CA` | Canada |
| `AU` | Australia |

### Examples

```bash
# UK inflation only
curl "https://marketdata.countdays.co.uk/api/v1/inflation?nation=UK"

# Australian interest rate only
curl "https://marketdata.countdays.co.uk/api/v1/interest-rates?nation=AU"

# US benchmarks (returns all benchmarks — nation filter applies to macro data)
curl "https://marketdata.countdays.co.uk/api/v1/benchmarks?nation=US"
```

### Filtered Response Example (Inflation, UK only)

```json
{
    "_meta": {
        "served_at": "2026-03-07T16:30:45.988765Z",
        "stale": false
    },
    "as_of": "2026-03-07",
    "nations": {
        "UK": {
            "frequency": "M",
            "label": "UK CPI (YoY)",
            "nation": "UK",
            "period": "2026-01",
            "rate": 0.032,
            "source": "oecd"
        }
    },
    "status": "ok"
}
```

> **Note:** The `nation` parameter is case-sensitive. Use uppercase codes (`UK`, not `uk`).

---

## 9. Understanding the Response

### The `_meta` Object

Every response includes a `_meta` block:

```json
"_meta": {
    "served_at": "2026-03-07T16:30:45.850450Z",
    "stale": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `served_at` | string | Timestamp when the response was generated (ISO 8601 UTC) |
| `stale` | boolean | `true` if the cached data is older than 25 hours (data may be outdated) |

### Stale Data

Data is refreshed daily at **06:00 UTC**. If a refresh fails, the API continues serving the last successful data but marks it as **stale**:

```json
"_meta": {
    "served_at": "2026-03-08T10:00:00Z",
    "stale": true
}
```

Your application should check the `stale` flag and optionally display a warning to users.

### The `status` Field

Top-level responses include `"status": "ok"` when data was loaded successfully.

### Rate Values

All rates (returns, inflation, interest) are expressed as **decimals**:

| Decimal | Percentage | Meaning |
|---------|------------|----------|
| `0.189487` | 18.95% | Developed equity 1-year return |
| `0.032` | 3.20% | UK inflation rate |
| `0.0364` | 3.64% | US federal funds rate |
| `-0.02` | -2.00% | Hypothetical negative return |

To convert: `percentage = decimal × 100`

---

## 10. Error Handling

The API returns JSON error responses with appropriate HTTP status codes.

### 404 — Not Found

```json
{
    "error": "Not found",
    "status": 404
}
```

### 429 — Rate Limited

Returned when exceeding 10 requests/second:

```json
{
    "error": "Rate limit exceeded. Max 10 requests per second.",
    "status": 429
}
```

### 500 — Server Error

```json
{
    "error": "Internal server error",
    "status": 500
}
```

### Recommended Error Handling (JavaScript)

```javascript
async function fetchMarketData() {
    try {
        const response = await fetch(
            "https://marketdata.countdays.co.uk/api/v1/reference-data"
        );

        if (!response.ok) {
            if (response.status === 429) {
                console.warn("Rate limited — retrying in 2 seconds");
                await new Promise(r => setTimeout(r, 2000));
                return fetchMarketData(); // retry once
            }
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        // Check for stale data
        if (data.benchmarks?._meta?.stale) {
            console.warn("Market data may be outdated");
        }

        return data;
    } catch (error) {
        console.error("Failed to fetch market data:", error);
        return null; // fall back to manual assumptions
    }
}
```

---

## 11. JavaScript Integration Examples

### Auto-Fill Growth Rates in the Planner

```javascript
/**
 * Fetch market benchmark returns and auto-fill growth rate inputs.
 * Falls back to manual entry if the API is unavailable.
 */
async function autoFillGrowthRates() {
    const data = await fetchMarketData();
    if (!data) return; // API unavailable, keep manual inputs

    const benchmarks = data.benchmarks.benchmarks;

    // Map asset classes to form fields
    const mapping = {
        "developed_equity": "input-growth-equity",
        "emerging_equity":  "input-growth-emerging",
        "global_bonds":     "input-growth-bonds",
        "global_property":  "input-growth-property"
    };

    for (const [assetClass, inputId] of Object.entries(mapping)) {
        const input = document.getElementById(inputId);
        if (input && benchmarks[assetClass]) {
            const pct = (benchmarks[assetClass].return_1y * 100).toFixed(2);
            input.value = pct;
            input.dataset.source = "market"; // flag as auto-filled
        }
    }
}
```

### Get Inflation for a Specific Nation

```javascript
async function getInflationRate(nationCode = "UK") {
    const response = await fetch(
        `https://marketdata.countdays.co.uk/api/v1/inflation?nation=${nationCode}`
    );
    const data = await response.json();
    return data.nations[nationCode]?.rate ?? null;
}

// Usage
const ukInflation = await getInflationRate("UK");
console.log(`UK inflation: ${(ukInflation * 100).toFixed(1)}%`); // "UK inflation: 3.2%"
```

### Performance Monitoring — Compare Predicted vs Actual

```javascript
/**
 * Compare user's assumed growth rate against market benchmark.
 * Returns a traffic-light status for drawdown guidance.
 */
function assessPerformance(assumedRate, marketRate) {
    const diff = marketRate - assumedRate;
    const threshold = 0.02; // 2 percentage points

    if (diff > threshold) {
        return {
            status: "green",
            message: "Market is outperforming your assumption. " +
                     "You may be able to increase drawdown.",
            diff: diff
        };
    } else if (diff < -threshold) {
        return {
            status: "red",
            message: "Market is underperforming your assumption. " +
                     "Consider reducing drawdown to preserve your pot.",
            diff: diff
        };
    } else {
        return {
            status: "amber",
            message: "Market performance is in line with your assumption.",
            diff: diff
        };
    }
}

// Example usage
const assumed = 0.07;  // User assumed 7% growth
const market  = 0.189; // Market returned 18.9%
const result  = assessPerformance(assumed, market);
console.log(result.status);  // "green"
console.log(result.message); // "Market is outperforming..."
```

---

## 12. Supported Nations

| Code | Country | Inflation Source | Interest Rate Source | Rate Description |
|------|---------|-----------------|---------------------|------------------|
| US | United States | FRED (CPIAUCSL) | FRED (DFF) | Federal Funds Effective Rate |
| UK | United Kingdom | OECD | FRED (IUDSOIA) | Sterling Overnight Index Average |
| EU | Euro Area | OECD | FRED (ECBMRRFR) | ECB Main Refinancing Rate |
| CA | Canada | OECD | FRED (IRSTCI01CAM156N) | Immediate Interest Rate |
| AU | Australia | OECD | FRED (IRSTCI01AUM156N) | Immediate Interest Rate |

---

## 13. Data Sources & Freshness

| Data Type | Provider | Update Frequency | Typical Lag |
|-----------|----------|-----------------|-------------|
| Benchmark ETF prices | [Tiingo](https://www.tiingo.com) | Daily (market days) | 1 day |
| US inflation (CPI) | [FRED](https://fred.stlouisfed.org) | Monthly | ~2 weeks |
| Global inflation | [OECD](https://data.oecd.org) | Monthly | 1–2 months |
| Interest rates | [FRED](https://fred.stlouisfed.org) | Daily / Monthly | 1–2 days |

### Data Refresh Schedule

- The API server refreshes all data **daily at 06:00 UTC** via an automated systemd timer.
- Cached JSON files are served between refreshes for fast response times.
- If a refresh fails, the previous data continues to be served (marked as `stale: true`).

---

## curl Cheat Sheet

```bash
# Health check
curl https://marketdata.countdays.co.uk/health

# All benchmarks
curl https://marketdata.countdays.co.uk/api/v1/benchmarks

# All inflation rates
curl https://marketdata.countdays.co.uk/api/v1/inflation

# UK inflation only
curl "https://marketdata.countdays.co.uk/api/v1/inflation?nation=UK"

# All interest rates
curl https://marketdata.countdays.co.uk/api/v1/interest-rates

# US interest rate only
curl "https://marketdata.countdays.co.uk/api/v1/interest-rates?nation=US"

# Everything in one call
curl https://marketdata.countdays.co.uk/api/v1/reference-data

# Pretty-print with jq
curl -s https://marketdata.countdays.co.uk/api/v1/benchmarks | jq .
```
