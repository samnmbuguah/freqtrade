#!/usr/bin/env bash
set -e

USER_DATA="/root/Dev/screencoins/freqtrade/user_data"
CONFIG="/freqtrade/user_data/config_research.json"
TIMERANGE="20260731-20260913"
SPACES="buy sell roi stoploss trailing"
LOSS="OnlyProfitHyperOptLoss"
EPOCHS=10000

mkdir -p "${USER_DATA}/logs"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===================================================" | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting 10,000-Epoch Optuna Runs for 5m & 1m" | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===================================================" | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"

# --- Phase 1: 5 Minute Timeframe (10,000 epochs) ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> Starting 5m Timeframe (${EPOCHS} epochs) <<<" | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"
docker run --name hyperopt_5m_10k --rm \
  -v "${USER_DATA}:/freqtrade/user_data" \
  freqtradeorg/freqtrade:develop hyperopt \
  --strategy LiquidationRegime5m \
  --config "${CONFIG}" \
  --timeframe 5m \
  --timerange "${TIMERANGE}" \
  --spaces ${SPACES} \
  --epochs ${EPOCHS} \
  -j -1 \
  --hyperopt-loss "${LOSS}" \
  --logfile "/freqtrade/user_data/logs/hyperopt_5m.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 5m 10,000-epoch hyperopt completed! Dumped to LiquidationRegime5m.json" | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"

# --- Phase 2: 1 Minute Timeframe (10,000 epochs) ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> Starting 1m Timeframe (${EPOCHS} epochs) <<<" | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"
docker run --name hyperopt_1m_10k --rm \
  -v "${USER_DATA}:/freqtrade/user_data" \
  freqtradeorg/freqtrade:develop hyperopt \
  --strategy LiquidationRegime1m \
  --config "${CONFIG}" \
  --timeframe 1m \
  --timerange "${TIMERANGE}" \
  --spaces ${SPACES} \
  --epochs ${EPOCHS} \
  -j -1 \
  --hyperopt-loss "${LOSS}" \
  --logfile "/freqtrade/user_data/logs/hyperopt_1m.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 1m 10,000-epoch hyperopt completed! Dumped to LiquidationRegime1m.json" | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] All 5m and 1m 10k hyperopts finished successfully!" | tee -a "${USER_DATA}/logs/hyperopt_5m_1m.log"
