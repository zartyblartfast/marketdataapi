"""Gunicorn configuration for the Retirement Data API."""
import multiprocessing

bind = "127.0.0.1:8000"
workers = 2
timeout = 30
keepalive = 5

# Logging
accesslog = "logs/gunicorn-access.log"
errorlog = "logs/gunicorn-error.log"
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
