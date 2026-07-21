#!/bin/bash
# =============================================================
# run-dbt.sh
# Chạy dbt transformation trên production server.
# dbt chạy native (không qua Docker) vì nó chỉ cần kết nối DB.
#
# Cài đặt trên server:
#   sudo cp deploy/scripts/run-dbt.sh /opt/eras-opera/run-dbt.sh
#   sudo chmod +x /opt/eras-opera/run-dbt.sh
# =============================================================

set -euo pipefail

# --- Config ---
APP_DIR="/opt/eras-opera"
DBT_DIR="$APP_DIR/eras_dbt"
LOG_DIR="/var/log/eras-opera"
LOG_FILE="$LOG_DIR/dbt-$(date +%Y%m%d-%H%M%S).log"
VENV_DBT="$DBT_DIR/venv"

# --- Tạo log dir nếu chưa có ---
mkdir -p "$LOG_DIR"

echo "========================================" | tee -a "$LOG_FILE"
echo "dbt started at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

cd "$DBT_DIR"
source "$VENV_DBT/bin/activate"

# dbt run — build tất cả models
echo "" | tee -a "$LOG_FILE"
echo "--- dbt run ---" | tee -a "$LOG_FILE"
dbt run --target prod --profiles-dir "$DBT_DIR" 2>&1 | tee -a "$LOG_FILE"
RUN_EXIT=$?

# dbt test — chạy tests nếu run thành công
if [ $RUN_EXIT -eq 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "--- dbt test ---" | tee -a "$LOG_FILE"
    dbt test --target prod --profiles-dir "$DBT_DIR" 2>&1 | tee -a "$LOG_FILE"
    TEST_EXIT=$?
else
    echo "dbt run failed — skipping tests" | tee -a "$LOG_FILE"
    TEST_EXIT=1
fi

deactivate

echo "" | tee -a "$LOG_FILE"
FINAL_EXIT=$(( RUN_EXIT + TEST_EXIT ))
if [ $FINAL_EXIT -eq 0 ]; then
    echo "dbt finished successfully at $(date)" | tee -a "$LOG_FILE"
else
    echo "dbt FAILED at $(date) (run_exit=$RUN_EXIT, test_exit=$TEST_EXIT)" | tee -a "$LOG_FILE"
fi

echo "Log: $LOG_FILE"
exit $FINAL_EXIT
