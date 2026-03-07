#!/bin/bash
# Cron wrapper for the daily data update.
set -euo pipefail

PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -f "${PROJ_DIR}/.env" ]; then
    set -a
    source "${PROJ_DIR}/.env"
    set +a
fi

echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Starting data refresh"

if [ -f "${PROJ_DIR}/venv/bin/python" ]; then
    PYTHON="${PROJ_DIR}/venv/bin/python"
else
    PYTHON="python3"
fi

"${PYTHON}" "${PROJ_DIR}/scripts/update_all.py"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Data refresh completed successfully"
else
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Data refresh completed with errors (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
