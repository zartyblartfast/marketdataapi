from flask import Flask, jsonify
from flask_cors import CORS
from app.config import Config
from app.utils.logging_setup import log


def create_app() -> Flask:
    """Application factory for the Retirement Data API."""
    app = Flask(__name__)

    # CORS: allow browser access from configured origins
    allowed_origins = Config.CORS_ORIGINS
    CORS(app, origins=allowed_origins)
    log.info(f"CORS enabled for origins: {allowed_origins}")

    # Register blueprints
    from app.routes.v1 import bp as v1_bp
    app.register_blueprint(v1_bp, url_prefix="/api/v1")

    from app.routes.health import bp as health_bp
    app.register_blueprint(health_bp)

    # JSON error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "status": 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed", "status": 405}), 405

    @app.errorhandler(500)
    def internal_error(e):
        log.error(f"Internal server error: {e}")
        return jsonify({"error": "Internal server error", "status": 500}), 500

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({"error": "Rate limit exceeded", "status": 429}), 429

    log.info("Retirement Data API initialized")
    return app
