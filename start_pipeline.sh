#!/usr/bin/env bash
set -e

DIR="/root/Dev/screencoins/freqtrade"
cd "$DIR"

echo "=== ScreenCoins Two-Stage Hyperopt Pipeline Launcher ==="

# Stop any running runner
pkill -f "python3.*pipeline_runner.py" 2>/dev/null || true
docker rm -f hyperopt_pipeline_runner 2>/dev/null || true
docker rm -f hyperopt_liq_long_sortino 2>/dev/null || true

mkdir -p "$DIR/user_data/logs"

echo "Starting pipeline in background..."
nohup python3 "$DIR/pipeline_runner.py" > "$DIR/user_data/logs/pipeline_runner.log" 2>&1 &
RUNNER_PID=$!

echo "Pipeline started with PID: ${RUNNER_PID}"
echo "To monitor live in terminal:"
echo "  bash ${DIR}/live_monitor.sh"
echo "Or check logs:"
echo "  tail -f ${DIR}/user_data/logs/pipeline_runner.log"
