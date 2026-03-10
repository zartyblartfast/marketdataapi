# Retirement Data API

A lightweight REST API that provides real-time market benchmarks, inflation rates, and interest rates for retirement income planning applications.

## Purpose

This API serves as a **data abstraction layer** for the Retirement Income Planner web app. It replaces manual growth assumptions with live market data, enabling:

- **Auto-fill** projected growth rates from real benchmark returns
- **Performance monitoring** — compare predicted vs actual market returns
- **Drawdown alerts** — signal when to adjust withdrawal amounts

All personal financial data stays in the browser; this API only serves **public reference data**.

## Data Sources

| Data Type | Source | Update Frequency |
|-----------|--------|------------------|
| Equity & Bond benchmarks | [Tiingo](https://www.tiingo.com) | Daily |
| US inflation (CPI) | [FRED](https://fred.stlouisfed.org) | Monthly |
| Global inflation (UK, EU, CA, AU) | [OECD](https://data.oecd.org) | Monthly |
| Interest rates (all nations) | [FRED](https://fred.stlouisfed.org) | Daily |

### Benchmark ETFs

| Asset Class | Ticker | Description |
|-------------|--------|-------------|
| Developed Equity | VTI | Vanguard Total Stock Market |
| Emerging Equity | VWO | Vanguard Emerging Markets |
| Global Bonds | BND | Vanguard Total Bond Market |
| Global Small-Cap | VSS | Vanguard FTSE All-World ex-US Small-Cap |
| Global Property | VNQ | Vanguard Real Estate |

## API Endpoints

Base URL: `http://YOUR_SERVER/api/v1`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/v1/benchmarks` | GET | Trailing 1-year returns for all benchmarks |
| `/api/v1/benchmarks?nation=US` | GET | Filter by nation |
| `/api/v1/inflation` | GET | Year-on-year inflation rates |
| `/api/v1/inflation?nation=UK` | GET | Filter by nation |
| `/api/v1/interest_rates` | GET | Current central bank / 10-year rates |
| `/api/v1/interest_rates?nation=AU` | GET | Filter by nation |

### Example Response

```json
{
  "status": "ok",
  "fetched_at": "2026-03-07T14:32:06Z",
  "benchmarks": {
    "developed_equity": {
      "ticker": "VTI",
      "name": "Vanguard Total Stock Market ETF",
      "price": 331.41,
      "return_1y": 0.1895,
      "currency": "USD"
    },
    "global_smallcap": {
      "ticker": "VSS",
      "name": "Vanguard FTSE All-World ex-US Small-Cap ETF",
      "price": 150.10,
      "return_1y": 0.3248,
      "currency": "USD"
    }
  }
}
```

## Quick Start (Development)

```bash
# Clone and enter project
cd retirement-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your Tiingo and FRED API keys

# Create directories
mkdir -p data logs

# Fetch initial data
source .env
python scripts/update_all.py

# Run development server
python wsgi.py
# API available at http://localhost:5000
```

## Production Deployment (VPS)

```bash
# On your VPS (Debian/Ubuntu), as root:
sudo bash deploy/setup-vps.sh
```

This will:
1. Install system packages (Python, Nginx)
2. Create virtualenv and install dependencies
3. Install systemd service (Gunicorn on port 8000)
4. Install systemd timer (daily data refresh at 06:00 UTC)
5. Configure Nginx reverse proxy with rate limiting
6. Run initial data fetch

### Post-deployment

```bash
# Check service status
systemctl status retirement-api

# View logs
journalctl -u retirement-api -f

# Check timer schedule
systemctl list-timers retirement-api-update.timer

# Manual data refresh
sudo -u www-data /opt/retirement-api/venv/bin/python /opt/retirement-api/scripts/update_all.py

# SSL certificate
sudo certbot --nginx -d your-domain.com
```

## Project Structure

```
retirement-api/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration (CORS, paths)
│   ├── fetchers/            # Data source integrations
│   │   ├── benchmarks.py    # Tiingo ETF returns
│   │   ├── inflation.py     # FRED + OECD CPI data
│   │   └── interest_rates.py# FRED interest rates
│   ├── routes/
│   │   ├── health.py        # /health endpoint
│   │   └── v1.py            # /api/v1/* endpoints
│   ├── services/
│   │   └── storage.py       # Atomic JSON read/write
│   └── utils/
│       └── logging_setup.py # Structured logging
├── data/                    # JSON data files (auto-generated)
├── deploy/                  # Deployment configs
│   ├── nginx-retirement-api.conf
│   ├── retirement-api.service
│   ├── retirement-api-update.service
│   ├── retirement-api-update.timer
│   └── setup-vps.sh
├── logs/                    # Application logs
├── scripts/
│   ├── update_all.py        # Data refresh orchestrator
│   └── run_update.sh        # Cron/shell wrapper
├── .env.example             # Environment template
├── gunicorn.conf.py         # Gunicorn settings
├── requirements.txt         # Python dependencies
├── wsgi.py                  # WSGI entry point
└── README.md
```

## Supported Nations

| Code | Country | Inflation Source | Rate Source |
|------|---------|-----------------|-------------|
| US | United States | FRED (CPIAUCSL) | FRED (DGS10) |
| UK | United Kingdom | OECD | FRED (IRLTLT01GBM156N) |
| EU | Euro Area | OECD | FRED (IRLTLT01EZM156N) |
| CA | Canada | OECD | FRED (IRLTLT01CAM156N) |
| AU | Australia | OECD | FRED (IRLTLT01AUM156N) |

## Security

- **No personal data** — API serves only public market data
- **CORS** configured for frontend access
- **Rate limiting** via Nginx (10 req/s per IP)
- **Stale data detection** — responses include `fetched_at` timestamps
- **Atomic writes** — prevents serving partial JSON files

## License

Private — for use with the Retirement Income Planner application.

