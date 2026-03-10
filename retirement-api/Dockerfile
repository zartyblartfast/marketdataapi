# Market Data API — Docker Image
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install cron for scheduled data refreshes
RUN apt-get update && apt-get install -y --no-install-recommends cron curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY wsgi.py .
COPY gunicorn_docker.conf.py gunicorn.conf.py
COPY app/ app/
COPY scripts/ scripts/
RUN chmod +x scripts/*.sh scripts/*.py

# Create persistent directories
RUN mkdir -p /app/data /app/logs

# Install cron job for daily data refresh at 06:00 UTC
RUN echo '0 6 * * * cd /app && /usr/local/bin/python scripts/update_all.py >> /app/logs/cron.log 2>&1' \
    | crontab -

# Expose API port
EXPOSE 8000

# Start cron in background, then Gunicorn in foreground
CMD cron && gunicorn --config gunicorn.conf.py wsgi:app
