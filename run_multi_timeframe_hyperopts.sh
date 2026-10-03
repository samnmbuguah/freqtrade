#!/usr/bin/env bash
set -e

USER_DATA="/root/Dev/screencoins/freqtrade/user_data"
CONFIG="/freqtrade/user_data/config_research.json"
TIMERANGE="20260731-20260913"
SPACES="buy sell roi stoploss trailing"
LOSS="OnlyProfitHyperOptLoss"
EPOCHS=10000

mkdir -p "${USER_DATA}/logs"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting multi-timeframe hyperopt suite..." | tee -a "${USER_DATA}/logs/hyperopt_suite.log"

# --- 1. 1 Hour Timeframe ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> Starting Phase 1: 1h Timeframe (${EPOCHS} epochs) <<<" | tee -a "${USER_DATA}/logs/hyperopt_suite.log"
docker run --rm \
  -v "${USER_DATA}:/freqtrade/user_data" \
  freqtradeorg/freqtrade:develop hyperopt \
  --strategy LiquidationRegime1h \
  --config "${CONFIG}" \
  --timeframe 1h \
  --timerange "${TIMERANGE}" \
  --spaces ${SPACES} \
  --epochs ${EPOCHS} \
  -j -1 \
  --hyperopt-loss "${LOSS}" \
  --logfile "/freqtrade/user_data/logs/hyperopt_1h.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_suite.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Phase 1 (1h) completed! Results dumped to LiquidationRegime1h.json" | tee -a "${USER_DATA}/logs/hyperopt_suite.log"

# --- 1.5. 15 Minute Timeframe ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> Starting Phase 2: 15m Timeframe (${EPOCHS} epochs) <<<" | tee -a "${USER_DATA}/logs/hyperopt_suite.log"
docker run --rm \
  -v "${USER_DATA}:/freqtrade/user_data" \
  freqtradeorg/freqtrade:develop hyperopt \
  --strategy LiquidationRegime15m \
  --config "${CONFIG}" \
  --timeframe 15m \
  --timerange "${TIMERANGE}" \
  --spaces ${SPACES} \
  --epochs ${EPOCHS} \
  -j -1 \
  --hyperopt-loss "${LOSS}" \
  --logfile "/freqtrade/user_data/logs/hyperopt_15m.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_suite.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Phase 2 (15m) completed! Results dumped to LiquidationRegime15m.json" | tee -a "${USER_DATA}/logs/hyperopt_suite.log"

# --- 2. 5 Minute Timeframe ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> Starting Phase 3: 5m Timeframe (${EPOCHS} epochs) <<<" | tee -a "${USER_DATA}/logs/hyperopt_suite.log"
docker run --rm \
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
  --logfile "/freqtrade/user_data/logs/hyperopt_5m.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_suite.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Phase 2 (5m) completed! Results dumped to LiquidationRegime5m.json" | tee -a "${USER_DATA}/logs/hyperopt_suite.log"

# --- 3. 1 Minute Timeframe ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> Starting Phase 3: 1m Timeframe (${EPOCHS} epochs) <<<" | tee -a "${USER_DATA}/logs/hyperopt_suite.log"
docker run --rm \
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
  --logfile "/freqtrade/user_data/logs/hyperopt_1m.log" 2>&1 | tee -a "${USER_DATA}/logs/hyperopt_suite.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Multi-timeframe hyperopt suite finished successfully!" | tee -a "${USER_DATA}/logs/hyperopt_suite.log"
