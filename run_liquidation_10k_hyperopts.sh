#!/usr/bin/env bash
set -e

USER_DATA="/root/Dev/screencoins/freqtrade/user_data"
CONFIG="/freqtrade/user_data/config_research.json"
TIMERANGE="20260801-20261003"
SPACES="buy sell"
LOSS="SharpeHyperOptLoss"
EPOCHS=10000
STRATEGY="LiquidationFlipStrategy"
STATUS_FILE="/root/Dev/screencoins/freqtrade/pipeline_status.json"

mkdir -p "${USER_DATA}/logs"
mkdir -p "${USER_DATA}/hyperopt_results"

update_status() {
    local idx="$1"
    local tf="$2"
    local running="$3"
    cat <<EOF > "${STATUS_FILE}"
{
  "running": ${running},
  "current_index": ${idx},
  "total_items": 3,
  "strategy": "${STRATEGY}",
  "timeframe": "${tf}",
  "stage": 1,
  "stage_name": "10,000 Epochs Asymmetric Buy/Sell Optimization",
  "spaces": "${SPACES}",
  "loss": "${LOSS}",
  "target_epochs": ${EPOCHS},
  "start_time": "$(date -u '+%Y-%m-%d %H:%M:%S UTC')",
  "completed_all": false
}
EOF
}

echo "=========================================================================="
echo " Starting 10,000-Epoch Sharpe Hyperopt Pipeline for LiquidationFlipStrategy"
echo " Timeframes: 15m -> 5m -> 1m"
echo " Spaces: ${SPACES} | Loss: ${LOSS} | Workers: all (-j -1)"
echo "=========================================================================="

# ── PHASE 1: 15m TIMEFRAME (10,000 EPOCHS) ────────────────────────────────────
echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] >>> Starting Phase 1: 15m (${EPOCHS} epochs) <<<"
rm -f "${USER_DATA}/strategies/${STRATEGY}.json"
update_status 1 "15m" "true"

docker run --name "hyperopt_${STRATEGY}_15m_10k" --rm \
  -v "${USER_DATA}:/freqtrade/user_data" \
  freqtradeorg/freqtrade:develop hyperopt \
  --strategy "${STRATEGY}" \
  --config "${CONFIG}" \
  --timeframe 15m \
  --timerange "${TIMERANGE}" \
  --spaces ${SPACES} \
  --epochs ${EPOCHS} \
  -j -1 \
  --hyperopt-loss "${LOSS}" \
  --logfile "/freqtrade/user_data/logs/hyperopt_${STRATEGY}_15m_10k.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_pipeline.log"

if [ -f "${USER_DATA}/strategies/${STRATEGY}.json" ]; then
    cp "${USER_DATA}/strategies/${STRATEGY}.json" "${USER_DATA}/strategies/${STRATEGY}_15m_10k.json"
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Phase 1 complete! Saved to ${STRATEGY}_15m_10k.json"
fi

# ── PHASE 2: 5m TIMEFRAME (10,000 EPOCHS) ─────────────────────────────────────
echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] >>> Starting Phase 2: 5m (${EPOCHS} epochs) <<<"
rm -f "${USER_DATA}/strategies/${STRATEGY}.json"
update_status 2 "5m" "true"

docker run --name "hyperopt_${STRATEGY}_5m_10k" --rm \
  -v "${USER_DATA}:/freqtrade/user_data" \
  freqtradeorg/freqtrade:develop hyperopt \
  --strategy "${STRATEGY}" \
  --config "${CONFIG}" \
  --timeframe 5m \
  --timerange "${TIMERANGE}" \
  --spaces ${SPACES} \
  --epochs ${EPOCHS} \
  -j -1 \
  --hyperopt-loss "${LOSS}" \
  --logfile "/freqtrade/user_data/logs/hyperopt_${STRATEGY}_5m_10k.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_pipeline.log"

if [ -f "${USER_DATA}/strategies/${STRATEGY}.json" ]; then
    cp "${USER_DATA}/strategies/${STRATEGY}.json" "${USER_DATA}/strategies/${STRATEGY}_5m_10k.json"
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Phase 2 complete! Saved to ${STRATEGY}_5m_10k.json"
fi

# ── PHASE 3: 1m TIMEFRAME (10,000 EPOCHS) ─────────────────────────────────────
echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] >>> Starting Phase 3: 1m (${EPOCHS} epochs) <<<"
rm -f "${USER_DATA}/strategies/${STRATEGY}.json"
update_status 3 "1m" "true"

docker run --name "hyperopt_${STRATEGY}_1m_10k" --rm \
  -v "${USER_DATA}:/freqtrade/user_data" \
  freqtradeorg/freqtrade:develop hyperopt \
  --strategy "${STRATEGY}" \
  --config "${CONFIG}" \
  --timeframe 1m \
  --timerange "${TIMERANGE}" \
  --spaces ${SPACES} \
  --epochs ${EPOCHS} \
  -j -1 \
  --hyperopt-loss "${LOSS}" \
  --logfile "/freqtrade/user_data/logs/hyperopt_${STRATEGY}_1m_10k.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_pipeline.log"

if [ -f "${USER_DATA}/strategies/${STRATEGY}.json" ]; then
    cp "${USER_DATA}/strategies/${STRATEGY}.json" "${USER_DATA}/strategies/${STRATEGY}_1m_10k.json"
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Phase 3 complete! Saved to ${STRATEGY}_1m_10k.json"
fi

cat <<EOF > "${STATUS_FILE}"
{
  "running": false,
  "completed_all": true,
  "strategy": "${STRATEGY}",
  "end_time": "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
}
EOF

echo "=========================================================================="
echo " All 10,000-Epoch Hyperopts (15m, 5m, 1m) completed successfully!"
echo "=========================================================================="
