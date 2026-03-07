from flask import Blueprint, jsonify, request
from pathlib import Path
import json
from datetime import datetime, timedelta
from app.config import Config
from app.utils.logging_setup import log

bp = Blueprint("v1", __name__)

DATA_DIR = Config.DATA_DIR
STALE_HOURS = 48  # Data older than this is flagged as stale


def _load_data(filename: str) -> tuple[dict, int]:
    """
    Load a JSON data file. Returns (data, http_status).
    Adds a _meta field with freshness info.
    Returns 503 if file missing, 200 otherwise.
    """
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return {
            "error": f"Data not yet available. File {filename} not found.",
            "hint": "Data is refreshed daily. Please try again later.",
        }, 503

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log.error(f"Failed to read {filename}: {e}")
        return {
            "error": f"Data file corrupted: {filename}",
        }, 500

    # Add freshness metadata
    as_of = data.get("as_of", "")
    stale = False
    if as_of:
        try:
            data_date = datetime.fromisoformat(as_of)
            age = datetime.now() - data_date
            stale = age > timedelta(hours=STALE_HOURS)
        except ValueError:
            pass

    data["_meta"] = {
        "stale": stale,
        "served_at": datetime.utcnow().isoformat() + "Z",
    }

    return data, 200


@bp.route("/benchmarks")
def get_benchmarks():
    """Return benchmark ETF data with trailing 1-year returns."""
    data, status = _load_data("benchmarks.json")
    return jsonify(data), status


@bp.route("/inflation")
def get_inflation():
    """Return inflation rates for all configured nations."""
    nation = request.args.get("nation", "").upper()
    data, status = _load_data("inflation.json")

    if status != 200:
        return jsonify(data), status

    # Filter by nation if requested
    if nation and "nations" in data:
        if nation in data["nations"]:
            filtered = {
                "as_of": data["as_of"],
                "status": data["status"],
                "nations": {nation: data["nations"][nation]},
                "_meta": data["_meta"],
            }
            return jsonify(filtered), 200
        else:
            return jsonify({
                "error": f"Nation '{nation}' not found",
                "available": list(data["nations"].keys()),
            }), 404

    return jsonify(data), status


@bp.route("/interest-rates")
@bp.route("/interest_rates")
def get_interest_rates():
    """Return interest/policy rates for all configured nations."""
    nation = request.args.get("nation", "").upper()
    data, status = _load_data("interest_rates.json")

    if status != 200:
        return jsonify(data), status

    # Filter by nation if requested
    if nation and "nations" in data:
        if nation in data["nations"]:
            filtered = {
                "as_of": data["as_of"],
                "status": data["status"],
                "nations": {nation: data["nations"][nation]},
                "_meta": data["_meta"],
            }
            return jsonify(filtered), 200
        else:
            return jsonify({
                "error": f"Nation '{nation}' not found",
                "available": list(data["nations"].keys()),
            }), 404

    return jsonify(data), status


@bp.route("/reference-data")
@bp.route("/reference_data")
def get_reference_data():
    """
    Combined endpoint: returns benchmarks, inflation, and interest rates
    in a single response. This is the primary endpoint for the planner app.
    Optional ?nation= filter for inflation and interest rates.
    """
    nation = request.args.get("nation", "").upper()

    benchmarks, b_status = _load_data("benchmarks.json")
    inflation, i_status = _load_data("inflation.json")
    rates, r_status = _load_data("interest_rates.json")

    # Filter by nation if requested
    if nation:
        if i_status == 200 and "nations" in inflation:
            inflation["nations"] = {
                k: v for k, v in inflation["nations"].items() if k == nation
            }
        if r_status == 200 and "nations" in rates:
            rates["nations"] = {
                k: v for k, v in rates["nations"].items() if k == nation
            }

    # Determine overall status
    statuses = [b_status, i_status, r_status]
    if all(s == 200 for s in statuses):
        overall_status = "ok"
        http_status = 200
    elif any(s == 200 for s in statuses):
        overall_status = "partial"
        http_status = 200
    else:
        overall_status = "error"
        http_status = 503

    combined = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d"),
        "status": overall_status,
        "benchmarks": benchmarks if b_status == 200 else {"error": benchmarks.get("error")},
        "inflation": inflation if i_status == 200 else {"error": inflation.get("error")},
        "interest_rates": rates if r_status == 200 else {"error": rates.get("error")},
    }

    return jsonify(combined), http_status
