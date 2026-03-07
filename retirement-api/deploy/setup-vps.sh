#!/bin/bash
# VPS deployment script for the Retirement Data API
# Run as root on a fresh Debian/Ubuntu VPS
#
# Usage: sudo bash deploy/setup-vps.sh

set -euo pipefail

APP_DIR="/opt/retirement-api"
APP_USER="www-data"

echo "=== Retirement Data API - VPS Setup ==="
echo

# 1. System packages
echo "[1/8] Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx certbot python3-certbot-nginx

# 2. Create app directory
echo "[2/8] Setting up application directory..."
mkdir -p "${APP_DIR}"
cp -r . "${APP_DIR}/"
cd "${APP_DIR}"

# 3. Python virtual environment
echo "[3/8] Creating Python virtual environment..."
python3 -m venv venv
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt

# 4. Create directories
echo "[4/8] Creating data and log directories..."
mkdir -p data logs

# 5. Set permissions
echo "[5/8] Setting file permissions..."
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
chmod 600 .env

# 6. Install systemd services
echo "[6/8] Installing systemd services..."
cp deploy/retirement-api.service /etc/systemd/system/
cp deploy/retirement-api-update.service /etc/systemd/system/
cp deploy/retirement-api-update.timer /etc/systemd/system/
systemctl daemon-reload

# 7. Install nginx config
echo "[7/8] Installing Nginx configuration..."
cp deploy/nginx-retirement-api.conf /etc/nginx/sites-available/retirement-api
ln -sf /etc/nginx/sites-available/retirement-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

# 8. Start services
echo "[8/8] Starting services..."
systemctl enable --now retirement-api
systemctl enable --now retirement-api-update.timer
systemctl reload nginx

# Initial data fetch
echo
echo "Running initial data fetch..."
sudo -u "${APP_USER}" venv/bin/python scripts/update_all.py

echo
echo "=== Setup Complete ==="
echo "API running at: http://localhost:8000"
echo "Nginx proxy at: http://YOUR_DOMAIN_OR_IP"
echo
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Update nginx config with your domain: /etc/nginx/sites-available/retirement-api"
echo "  3. Obtain SSL cert: sudo certbot --nginx -d YOUR_DOMAIN"
echo "  4. Restrict CORS origin in app/config.py"
echo "  5. Check status: systemctl status retirement-api"
echo "  6. View logs: journalctl -u retirement-api -f"
