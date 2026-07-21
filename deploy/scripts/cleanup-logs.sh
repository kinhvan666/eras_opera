#!/bin/bash
# =============================================================
# cleanup-logs.sh
# Xóa log files cũ hơn 30 ngày.
# Chạy hàng tuần qua cron.
# =============================================================

LOG_DIR="/var/log/eras-opera"
KEEP_DAYS=30

find "$LOG_DIR" -type f -name "*.log" -mtime +$KEEP_DAYS -delete
echo "Log cleanup done at $(date) — removed files older than $KEEP_DAYS days"
