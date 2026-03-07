# Retirement Planner VPS API
## Developer Implementation Guide

Version: 1.0  
Target: Linux VPS deployment  
Purpose: Implement a small server-side reference-data service for the browser-based Retirement Income Planner.

---

## 1. Goal

Build a lightweight VPS service that:

- fetches and caches **4 global benchmark series**
- fetches and caches **country-specific inflation**
- fetches and caches **country-specific interest rates**
- exposes simple **JSON endpoints** for the JavaScript frontend
- stores **no user financial data**

This service is not a user platform. It is only a public reference-data layer for the app.

---

## 2. Recommended Stack

- **OS:** Ubuntu 22.04+ or similar Linux VPS
- **Language:** Python 3.11+
- **API framework:** Flask
- **Scheduler:** cron
- **Web server / reverse proxy:** Nginx
- **WSGI server:** Gunicorn
- **Storage:** local JSON files on disk
- **Secrets:** environment variables in `.env`

Why Flask:

- simple
- lightweight
- familiar if the current planner began as Flask
- easy to deploy on a small VPS

---

## 3. Core Data Model

### 3.1 Global benchmark series

These are the four benchmark series to include initially:

1. **developed_equity**
2. **emerging_equity**
3. **global_bonds**
4. **global_property**

### 3.2 Suggested ETF proxies

These are practical proxy examples for the benchmark service:

| Internal series | Example proxy idea |
|---|---|
| developed_equity | VTI or VT-style developed/global equity proxy |
| emerging_equity | VWO-style emerging markets proxy |
| global_bonds | BND-style bond proxy |
| global_property | VNQ-style property / REIT proxy |

### 3.3 Country-specific macro data

Maintain separate datasets for:

- **inflation**
- **interest_rates**

Recommended starting countries:

- UK
- US
- EU
- CA
- AU

You can add more later.

---

## 4. Project Structure

```text
retirement-api/
├── app/
│   ├── __init__.py
│   ├── api.py
│   ├── config.py
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── benchmarks.py
│   │   ├── inflation.py
│   │   └── interest_rates.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage.py
│   │   └── combine.py
│   └── utils/
│       ├── __init__.py
│       └── logging_setup.py
├── data/
│   ├── benchmarks.json
│   ├── inflation.json
│   ├── interest_rates.json
│   └── reference_data.json
├── scripts/
│   ├── update_benchmarks.py
│   ├── update_inflation.py
│   ├── update_interest_rates.py
│   └── update_all.py
├── requirements.txt
├── .env
├── gunicorn.conf.py
└── README.md
```

---

## 5. Suggested API Endpoints

### 5.1 Health check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### 5.2 Latest benchmark data

```http
GET /api/benchmarks/latest
```

### 5.3 Inflation data

```http
GET /api/inflation
```

### 5.4 Interest rate data

```http
GET /api/interest-rates
```

### 5.5 Combined reference data

```http
GET /api/reference-data
```

This combined endpoint should be the main frontend endpoint.

---

## 6. Example JSON Output

### 6.1 `benchmarks.json`

```json
{
  "as_of": "2026-03-07",
  "status": "ok",
  "benchmarks": {
    "developed_equity": {
      "label": "Developed Market Equity",
      "value": 281.42,
      "source": "tiingo",
      "proxy": "VTI"
    },
    "emerging_equity": {
      "label": "Emerging Market Equity",
      "value": 41.18,
      "source": "tiingo",
      "proxy": "VWO"
    },
    "global_bonds": {
      "label": "Global Bonds",
      "value": 73.51,
      "source": "tiingo",
      "proxy": "BND"
    },
    "global_property": {
      "label": "Global Property",
      "value": 89.42,
      "source": "tiingo",
      "proxy": "VNQ"
    }
  }
}
```

### 6.2 `inflation.json`

```json
{
  "as_of": "2026-03-01",
  "status": "ok",
  "inflation": {
    "UK": {
      "rate": 0.039,
      "label": "United Kingdom CPI 12-month rate",
      "source": "ons"
    },
    "US": {
      "rate": 0.031,
      "label": "United States CPI 12-month rate",
      "source": "fred"
    },
    "EU": {
      "rate": 0.028,
      "label": "Euro Area CPI/HICP 12-month rate",
      "source": "oecd"
    }
  }
}
```

### 6.3 `interest_rates.json`

```json
{
  "as_of": "2026-03-07",
  "status": "ok",
  "interest_rates": {
    "UK": {
      "rate": 0.0425,
      "label": "Bank of England base rate",
      "source": "boe"
    },
    "US": {
      "rate": 0.045,
      "label": "Federal Funds Rate proxy",
      "source": "fred"
    },
    "EU": {
      "rate": 0.035,
      "label": "ECB policy rate proxy",
      "source": "oecd"
    }
  }
}
```

### 6.4 `reference_data.json`

```json
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
```

---

## 7. Environment Variables

Example `.env`:

```bash
FLASK_ENV=production
DATA_DIR=/opt/retirement-api/data
TIINGO_API_KEY=your_tiingo_key_here
FRED_API_KEY=your_fred_key_here
PORT=8000
```

Do not hardcode API keys in scripts.

---

## 8. Python Requirements

Example `requirements.txt`:

```text
Flask==3.0.2
requests==2.31.0
gunicorn==21.2.0
python-dotenv==1.0.1
```

Optional:

```text
pydantic==2.6.4
```

---

## 9. Basic Flask App

### 9.1 `app/api.py`

```python
from flask import Flask, jsonify
import json
from pathlib import Path
import os


def load_json(filename: str):
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    path = data_dir / filename
    if not path.exists():
        return {"status": "missing", "file": filename}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/benchmarks/latest")
    def benchmarks_latest():
        return jsonify(load_json("benchmarks.json"))

    @app.get("/api/inflation")
    def inflation():
        return jsonify(load_json("inflation.json"))

    @app.get("/api/interest-rates")
    def interest_rates():
        return jsonify(load_json("interest_rates.json"))

    @app.get("/api/reference-data")
    def reference_data():
        return jsonify(load_json("reference_data.json"))

    return app


app = create_app()
```

---

## 10. Storage Helper

### 10.1 `app/services/storage.py`

```python
import json
from pathlib import Path
import os
from typing import Any


def get_data_dir() -> Path:
    path = Path(os.getenv("DATA_DIR", "data"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(filename: str, payload: Any) -> None:
    path = get_data_dir() / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def read_json(filename: str) -> Any:
    path = get_data_dir() / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

---

## 11. Benchmark Fetcher Example

This is a simplified example. It assumes one provider for market proxy prices.

### 11.1 `app/fetchers/benchmarks.py`

```python
import os
from datetime import date
import requests

TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "")

SERIES = {
    "developed_equity": {"ticker": "VTI", "label": "Developed Market Equity"},
    "emerging_equity": {"ticker": "VWO", "label": "Emerging Market Equity"},
    "global_bonds": {"ticker": "BND", "label": "Global Bonds"},
    "global_property": {"ticker": "VNQ", "label": "Global Property"},
}


def fetch_latest_price(ticker: str) -> float:
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
    headers = {"Content-Type": "application/json"}
    params = {"token": TIINGO_API_KEY}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data:
        raise ValueError(f"No data returned for {ticker}")
    return float(data[-1]["adjClose"])


def fetch_benchmarks() -> dict:
    result = {
        "as_of": str(date.today()),
        "status": "ok",
        "benchmarks": {}
    }

    for key, meta in SERIES.items():
        price = fetch_latest_price(meta["ticker"])
        result["benchmarks"][key] = {
            "label": meta["label"],
            "value": price,
            "source": "tiingo",
            "proxy": meta["ticker"]
        }

    return result
```

---

## 12. Inflation Fetcher Example

Keep this layer abstract. One source per country is fine at first.

### 12.1 `app/fetchers/inflation.py`

```python
from datetime import date


def fetch_inflation() -> dict:
    # Replace these placeholder values with actual source fetch logic.
    return {
        "as_of": str(date.today()),
        "status": "ok",
        "inflation": {
            "UK": {
                "rate": 0.039,
                "label": "United Kingdom CPI 12-month rate",
                "source": "ons"
            },
            "US": {
                "rate": 0.031,
                "label": "United States CPI 12-month rate",
                "source": "fred"
            },
            "EU": {
                "rate": 0.028,
                "label": "Euro Area CPI/HICP 12-month rate",
                "source": "oecd"
            }
        }
    }
```

---

## 13. Interest Rate Fetcher Example

### 13.1 `app/fetchers/interest_rates.py`

```python
from datetime import date


def fetch_interest_rates() -> dict:
    # Replace these placeholder values with actual source fetch logic.
    return {
        "as_of": str(date.today()),
        "status": "ok",
        "interest_rates": {
            "UK": {
                "rate": 0.0425,
                "label": "Bank of England base rate",
                "source": "boe"
            },
            "US": {
                "rate": 0.045,
                "label": "Federal Funds Rate proxy",
                "source": "fred"
            },
            "EU": {
                "rate": 0.035,
                "label": "ECB policy rate proxy",
                "source": "oecd"
            }
        }
    }
```

---

## 14. Update Scripts

### 14.1 `scripts/update_benchmarks.py`

```python
from app.fetchers.benchmarks import fetch_benchmarks
from app.services.storage import write_json

payload = fetch_benchmarks()
write_json("benchmarks.json", payload)
```

### 14.2 `scripts/update_inflation.py`

```python
from app.fetchers.inflation import fetch_inflation
from app.services.storage import write_json

payload = fetch_inflation()
write_json("inflation.json", payload)
```

### 14.3 `scripts/update_interest_rates.py`

```python
from app.fetchers.interest_rates import fetch_interest_rates
from app.services.storage import write_json

payload = fetch_interest_rates()
write_json("interest_rates.json", payload)
```

### 14.4 `scripts/update_all.py`

```python
from app.services.storage import write_json, read_json
from app.fetchers.benchmarks import fetch_benchmarks
from app.fetchers.inflation import fetch_inflation
from app.fetchers.interest_rates import fetch_interest_rates

benchmarks = fetch_benchmarks()
inflation = fetch_inflation()
interest_rates = fetch_interest_rates()

write_json("benchmarks.json", benchmarks)
write_json("inflation.json", inflation)
write_json("interest_rates.json", interest_rates)

combined = {
    "as_of": benchmarks["as_of"],
    "benchmarks": {
        k: v["value"] for k, v in benchmarks["benchmarks"].items()
    },
    "inflation": {
        k: v["rate"] for k, v in inflation["inflation"].items()
    },
    "interest_rates": {
        k: v["rate"] for k, v in interest_rates["interest_rates"].items()
    }
}

write_json("reference_data.json", combined)
```

---

## 15. Initial VPS Setup

### 15.1 Install packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx
```

### 15.2 Create app directory

```bash
sudo mkdir -p /opt/retirement-api
sudo chown -R $USER:$USER /opt/retirement-api
cd /opt/retirement-api
```

### 15.3 Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 16. Gunicorn Run Command

From the project root:

```bash
gunicorn -w 2 -b 127.0.0.1:8000 app.api:app
```

For a small VPS, 2 workers is usually enough.

---

## 17. Systemd Service

Create `/etc/systemd/system/retirement-api.service`

```ini
[Unit]
Description=Retirement Planner Reference Data API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/retirement-api
Environment="DATA_DIR=/opt/retirement-api/data"
Environment="TIINGO_API_KEY=your_tiingo_key_here"
Environment="FRED_API_KEY=your_fred_key_here"
ExecStart=/opt/retirement-api/venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 app.api:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable retirement-api
sudo systemctl start retirement-api
sudo systemctl status retirement-api
```

---

## 18. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/retirement-api`

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/retirement-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 19. HTTPS

If the domain is public, enable TLS.

Example with Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 20. Cron Jobs

Open crontab:

```bash
crontab -e
```

Suggested schedule:

```cron
# Benchmarks: daily at 02:00
0 2 * * * cd /opt/retirement-api && /opt/retirement-api/venv/bin/python scripts/update_benchmarks.py

# Interest rates: daily at 02:10
10 2 * * * cd /opt/retirement-api && /opt/retirement-api/venv/bin/python scripts/update_interest_rates.py

# Inflation: monthly on day 2 at 03:00
0 3 2 * * cd /opt/retirement-api && /opt/retirement-api/venv/bin/python scripts/update_inflation.py

# Combined file rebuild: daily at 03:15
15 3 * * * cd /opt/retirement-api && /opt/retirement-api/venv/bin/python scripts/update_all.py
```

You can simplify this by calling only `update_all.py` if preferred.

---

## 21. Frontend Integration

The browser app should call only one endpoint if possible:

```javascript
const referenceData = await fetch("https://your-domain.com/api/reference-data")
  .then(r => r.json());
```

Example use:

```javascript
const ukInflation = referenceData.inflation.UK;
const ukRate = referenceData.interest_rates.UK;
const developed = referenceData.benchmarks.developed_equity;
```

The frontend then:

- maps each pension pot to benchmark weights
- computes synthetic benchmark movement
- applies guardrail messaging
- keeps all personal values in browser storage only

---

## 22. Failure Handling

If a provider fails:

- keep the last successful cached JSON
- add a stale status
- log the problem
- do not break the endpoint entirely

Example stale response:

```json
{
  "as_of": "2026-03-06",
  "status": "stale",
  "message": "Using last successful cached dataset"
}
```

---

## 23. Logging

At minimum, log:

- update start/end time
- provider used
- success/failure
- response status code
- stale fallback events

A simple file logger is sufficient initially.

---

## 24. Security Notes

- do not store user portfolio data on the VPS
- keep API keys in environment variables only
- restrict write permissions on the project directory
- enable HTTPS
- consider basic rate limiting at Nginx level if the endpoint becomes public

---

## 25. Suggested Development Order

### Phase 1

Implement:

- Flask API
- local JSON output
- benchmark fetcher
- `/api/reference-data`

### Phase 2

Add:

- inflation fetcher
- interest rate fetcher
- cron automation
- stale fallback handling

### Phase 3

Enhance:

- historical series output
- more countries
- exchange rates
- benchmark definitions endpoint

---

## 26. Minimal Viable Deliverable

The first working version should do only this:

1. fetch 4 benchmark proxy prices
2. fetch inflation for UK / US / EU
3. fetch interest rates for UK / US / EU
4. write `reference_data.json`
5. expose `GET /api/reference-data`

That is enough for the browser planner to start using dynamic benchmark and macro data.

---

## 27. Nice Future Additions

After the base service works, consider adding:

- exchange rates
- historical monthly returns
- volatility measures
- benchmark definitions endpoint
- country metadata endpoint

---

## 28. Summary

This VPS API service should remain deliberately small and focused.

Its role is to provide:

- **4 global benchmark series**
- **country-specific inflation**
- **country-specific interest rates**
- **simple JSON endpoints**

The browser app remains the place where:

- user data is stored
- retirement modelling happens
- benchmark matching is calculated
- guardrail logic is applied

That architecture gives a strong balance of:

- privacy
- simplicity
- low cost
- commercial practicality
- ease of deployment on a small Linux VPS
