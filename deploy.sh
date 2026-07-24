#!/bin/bash
# deploy.sh
# Usage: ./deploy.sh               # extractor + dbt + restart dashboard
# Usage: ./deploy.sh --skip-extract # only dbt + dashboard
# Usage: ./deploy.sh --skip-dbt     # only extractor + dashboard
# Usage: ./deploy.sh --skip-all     # only restart dashboard
#
# Requires: docker compose, psql, pip, ~/.dbt/profiles.yml, .env.prod

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${BASE_DIR}/log"
EXTRACTOR_LOG="${LOG_DIR}/extractor.log"
DBT_LOG="${LOG_DIR}/dbt.log"

mkdir -p "$LOG_DIR"

echo "========================================"
echo " ErasOpera Deploy — $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# ─── Step 1: Pull latest code ────────────────────────────────────────────
echo "[1/4] Pulling latest code from git..."
cd "$BASE_DIR"
git pull origin master 2>&1 | tail -2

# ─── Step 2: Run extractor (Docker) ────────────────────────────────────────
if [ "${1:-}" != "--skip-extract" ] && [ "${1:-}" != "--skip-all" ]; then
    echo "[2/4] Running extractor (Docker)..."
    # Ensure .env exists
    if [ ! -f "${BASE_DIR}/extractor/.env" ]; then
        cp "${BASE_DIR}/extractor/.env.prod" "${BASE_DIR}/extractor/.env"
        echo "  → Created extractor/.env from .env.prod"
    fi
    docker compose -f docker-compose.prod.yml run --rm extractor python -m src \
        >> "$EXTRACTOR_LOG" 2>&1
    echo "  → Extractor done. Log: ${EXTRACTOR_LOG}"
else
    echo "[2/4] Skipping extractor."
fi

# ─── Step 3: Run dbt ─────────────────────────────────────────────────────
if [ "${1:-}" != "--skip-dbt" ] && [ "${1:-}" != "--skip-all" ]; then
    echo "[3/4] Running dbt..."
    cd "${BASE_DIR}/eras_dbt"

    # Ensure venv exists
    if [ ! -d "venv" ]; then
        echo "  → Creating Python venv..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -q dbt-core dbt-postgres
        deactivate
    fi

    source venv/bin/activate
    dbt build --target prod --profiles-dir ~/.dbt >> "$DBT_LOG" 2>&1
    deactivate
    echo "  → dbt done. Log: ${DBT_LOG}"
else
    echo "[3/4] Skipping dbt."
fi

# ─── Step 4: Restart dashboard (streamlit) ────────────────────────────────
echo "[4/4] Restarting dashboard..."
# Find and kill existing streamlit process for this project
DASHBOARD_PID=$(pgrep -f "streamlit run.*eras_opera" || true)
if [ -n "$DASHBOARD_PID" ]; then
    kill "$DASHBOARD_PID" 2>/dev/null || true
    sleep 2
    echo "  → Killed old dashboard (PID $DASHBOARD_PID)"
fi

# Start new dashboard session (runs in background, survives SSH logout via nohup)
DASHBOARD_DIR="${BASE_DIR}/dashboard_v2"
if [ -f "${DASHBOARD_DIR}/app.py" ]; then
    cd "$DASHBOARD_DIR"
    nohup streamlit run app.py --server.port 8501 > "${LOG_DIR}/dashboard.log" 2>&1 &
    echo "  → Dashboard started on port 8501 (PID $!)"
else
    echo "  → WARNING: dashboard_v2/app.py not found at ${DASHBOARD_DIR}"
fi

echo "========================================"
echo " Deploy complete — $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
