#!/bin/bash
# =============================================================
# run-extractor.sh
# Chạy extractor container một lần (one-shot), log kết quả.
# Được gọi bởi cron job trên production server.
#
# Cài đặt trên server:
#   sudo cp deploy/scripts/run-extractor.sh /opt/eras-opera/run-extractor.sh
#   sudo chmod +x /opt/eras-opera/run-extractor.sh
# =============================================================

set -euo pipefail

# --- Config ---
APP_DIR="/opt/eras-opera"
LOG_DIR="/var/log/eras-opera"
LOG_FILE="$LOG_DIR/extractor-$(date +%Y%m%d-%H%M%S).log"
COMPOSE_FILE="$APP_DIR/docker-compose.prod.yml"

# --- Tạo log dir nếu chưa có ---
mkdir -p "$LOG_DIR"

echo "========================================" | tee -a "$LOG_FILE"
echo "Extractor started at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

cd "$APP_DIR"

# Build image nếu chưa có (lần đầu hoặc sau git pull)
docker compose -f "$COMPOSE_FILE" build extractor >> "$LOG_FILE" 2>&1

# Chạy extractor — one-shot, tự thoát sau khi xong
# --rm: xóa container sau khi chạy xong
# --no-deps: không cần khởi động service khác
docker compose -f "$COMPOSE_FILE" run --rm --no-deps extractor >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "" | tee -a "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "Extractor finished successfully at $(date)" | tee -a "$LOG_FILE"
else
    echo "Extractor FAILED with exit code $EXIT_CODE at $(date)" | tee -a "$LOG_FILE"
fi

echo "Log: $LOG_FILE"
exit $EXIT_CODE
