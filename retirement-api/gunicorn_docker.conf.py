"""Gunicorn configuration for Docker deployment."""

bind = "0.0.0.0:8000"
workers = 2
timeout = 30
keepalive = 5

# Log to stdout/stderr for Docker log collection
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
