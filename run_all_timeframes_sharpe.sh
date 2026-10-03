#!/usr/bin/env bash
set -e

# Sequential SharpeHyperOptLoss Runner across Timeframes
# Timeframes: 5m, 15m, 1h, 1m
# Using SharpeHyperOptLoss to optimize risk-adjusted returns and penalize drawdown.

BASE_DIR="/freqtrade/user_data"
LOG_DIR="${BASE_DIR}/logs"
mkdir -p "${LOG_DIR}"

TIMEFRAMES=("5m" "15m" "1h" "1m")
EPOCHS=5000

echo "================================================================="
echo "Starting Sequential Multi-Timeframe Sharpe Hyperopt Sweep"
echo "Loss Function: SharpeHyperOptLoss"
echo "Epochs per TF: ${EPOCHS}"
echo "Timeframes: ${TIMEFRAMES[*]}"
echo "================================================================="

for TF in "${TIMEFRAMES[@]}"; do
    STRAT="LiquidationRegime${TF}"
    LOG_FILE="${LOG_DIR}/hyperopt_${TF}_sharpe.log"
    echo ""
    echo "================================================================="
    echo ">>> Starting Hyperopt for ${STRAT} (${TF}) at $(date -u)"
    echo ">>> Log: ${LOG_FILE}"
    echo "================================================================="

    freqtrade hyperopt \
        --strategy "${STRAT}" \
        --config "${BASE_DIR}/config_research.json" \
        --timeframe "${TF}" \
        --timerange 20260731-20260913 \
        --spaces buy sell roi stoploss trailing \
        --epochs "${EPOCHS}" \
        -j -1 \
        --hyperopt-loss SharpeHyperOptLoss \
        --logfile "${LOG_FILE}"

    # Backup the exported parameters specifically for Sharpe
    SRC_JSON="${BASE_DIR}/strategies/${STRAT}.json"
    DST_JSON="${BASE_DIR}/strategies/${STRAT}_Sharpe.json"
    if [ -f "${SRC_JSON}" ]; then
        cp "${SRC_JSON}" "${DST_JSON}"
        echo ">>> Successfully exported ${DST_JSON}"
    fi

    echo ">>> Finished ${STRAT} (${TF}) at $(date -u)"
done

echo ""
echo "================================================================="
echo "All multi-timeframe Sharpe hyperopt runs have completed!"
echo "================================================================="
