from flask import Blueprint, jsonify
from datetime import datetime

bp = Blueprint("health", __name__)


@bp.route("/health")
def health_check():
    """Simple health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "retirement-data-api",
        "version": "1.0.0",
    })
