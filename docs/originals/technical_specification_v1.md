Retirement Planner Benchmark & Macro Data API
Technical Specification (Markdown Version)

Version: 1.1
Author: System Design Specification
Target Deployment: Linux VPS (Hostinger)
Purpose: Provide benchmark and macroeconomic data for the browser-based Retirement Income Planner.

1. System Overview

The Retirement Income Planner will run entirely in the user's browser using JavaScript and local storage for all personal financial data.

A small server-side service hosted on a Linux VPS will provide non-personal reference data, including:

global market benchmarks

country-specific inflation

country-specific interest rates

The service will expose simple JSON endpoints consumed by the browser application.

This architecture ensures:

no personal data stored on servers

minimal GDPR exposure

low infrastructure cost

reliable external data aggregation

2. System Architecture
                +---------------------+
                |  External Data APIs |
                |                     |
                | Tiingo / marketstack|
                | FRED / OECD / ONS   |
                +----------+----------+
                           |
                           |
                    (daily refresh)
                           |
                           v
                +----------------------+
                | Benchmark Aggregator |
                | Linux VPS Service    |
                | Python / Node        |
                +----------+-----------+
                           |
                    JSON endpoints
                           |
                           v
               +------------------------+
               | Retirement Planner App |
               | Browser (JavaScript)   |
               | User Data Local Only   |
               +------------------------+
3. Core Data Categories

The service publishes three types of data.

3.1 Global Market Benchmarks

These represent global capital markets and are not country specific.

Four benchmark series are used to approximate most retirement portfolios.

Benchmark	Purpose
Developed Equity	Global developed stock markets
Emerging Equity	Emerging market equities
Global Bonds	Global bond markets
Global Property	Global REIT/property market

Example ETF proxies:

Asset Class	Proxy ETF
Developed Equity	VTI / VT
Emerging Equity	VWO
Global Bonds	BND
Global Property	VNQ
3.2 Inflation Data (Country Specific)

Inflation is used to adjust retirement spending projections.

Inflation series are maintained per country.

Example countries supported initially:

United Kingdom

United States

Euro Area

Canada

Australia

Inflation should represent 12-month CPI change.

3.3 Interest Rates (Country Specific)

Interest rates are used to estimate:

risk-free return

bond yield environment

discount rates for projections

Rates represent central bank policy rates or similar proxies.

Example:

Country	Source
UK	Bank of England Base Rate
US	Federal Funds Rate
EU	ECB Deposit Rate
4. Data Providers

The service aggregates data from existing financial APIs.

4.1 Market Data Providers

Recommended primary providers:

Provider	Notes
Tiingo	Reliable end-of-day market data
marketstack	Large exchange coverage
Financial Modeling Prep	Broad financial dataset
Alpha Vantage	Widely used but tighter limits
EOD Historical Data	Large dataset option

Recommended default: Tiingo

4.2 Economic Data Providers

Used for inflation and interest rates.

Provider	Purpose
FRED	US macroeconomic data
ONS API	UK inflation and statistics
OECD	International inflation datasets
World Bank	Global fallback data
5. VPS Service Design
5.1 Technology Stack

Recommended stack:

Component	Technology
OS	Linux
Language	Python or Node.js
Scheduler	Cron
Output Format	JSON
Web Server	Nginx
5.2 Refresh Frequency

Market and macro data should be refreshed periodically.

Recommended schedule:

Data	Frequency
Market benchmarks	Daily
Inflation	Monthly
Interest rates	Daily

Cron example:

0 2 * * * update_benchmarks.py
6. API Endpoints

The VPS will expose simple HTTP endpoints.

Latest Benchmark Data
GET /api/benchmarks/latest

Example response:

{
  "as_of": "2026-03-07",
  "benchmarks": {
    "developed_equity": 281.42,
    "emerging_equity": 41.18,
    "global_bonds": 73.51,
    "global_property": 89.42
  }
}
Inflation Data
GET /api/inflation

Example response:

{
  "as_of": "2026-03-01",
  "inflation": {
    "UK": 0.039,
    "US": 0.031,
    "EU": 0.028,
    "CA": 0.032,
    "AU": 0.034
  }
}
Interest Rate Data
GET /api/interest-rates

Example response:

{
  "as_of": "2026-03-07",
  "rates": {
    "UK": 0.0425,
    "US": 0.045,
    "EU": 0.035,
    "CA": 0.04,
    "AU": 0.0375
  }
}
7. Combined Data Endpoint

A combined endpoint reduces browser requests.

GET /api/reference-data

Example:

{
  "as_of": "2026-03-07",

  "benchmarks": {
    "developed_equity": 281.42,
    "emerging_equity": 41.18,
    "global_bonds": 73.51,
    "global_property": 89.42
  },

  "inflation": {
    "UK": 0.039,
    "US": 0.031,
    "EU": 0.028
  },

  "interest_rates": {
    "UK": 0.0425,
    "US": 0.045,
    "EU": 0.035
  }
}
8. Browser Integration

The frontend JavaScript application will:

Fetch reference data at startup

Cache results locally

Map user portfolios to benchmark categories

Calculate synthetic portfolio benchmark returns

Example fetch:

const data = await fetch("/api/reference-data").then(r => r.json());
9. Security & Privacy

The VPS must never store user data.

Only public benchmark and macroeconomic data should be hosted.

Security practices:

store API keys in environment variables

enable HTTPS

limit outbound API calls

implement caching

10. Data Storage

The service should store cached data locally for reliability.

Recommended files:

data/
    benchmarks.json
    inflation.json
    interest_rates.json
11. Failure Handling

If an upstream data source fails:

use last successful cached value

mark dataset as stale

log error

Example response flag:

{
  "status": "stale",
  "last_successful_update": "2026-03-06"
}
12. Implementation Phases
Phase 1

Implement:

benchmark data

VPS API service

daily refresh

Phase 2

Add:

inflation data

interest rate data

combined endpoint

Phase 3

Enhancements:

historical benchmark series

volatility metrics

exchange rates

additional countries

13. Benefits

This design provides:

realistic market benchmarking

country-specific inflation assumptions

interest rate environment awareness

privacy-preserving architecture

minimal infrastructure requirements

The system can support most retirement portfolio scenarios while keeping the application lightweight and scalable.