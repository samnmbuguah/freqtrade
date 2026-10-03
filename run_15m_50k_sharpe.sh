#!/usr/bin/env bash
set -e

CONTAINER_NAME="hyperopt_15m_50k"

# Stop and remove any prior instance if exists
docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

echo "=== Starting 15m Optuna Hyperopt (50,000 Epochs - Sharpe Loss) ==="

docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  -v /root/Dev/screencoins/freqtrade/user_data:/freqtrade/user_data \
  -v /root/Dev/screencoins/freqtrade/freqtrade:/freqtrade/freqtrade \
  freqtradeorg/freqtrade:develop \
  hyperopt \
  --strategy LiquidationRegime15m \
  --config /freqtrade/user_data/config_research.json \
  --timeframe 15m \
  --timerange 20260731-20260913 \
  --spaces buy sell roi stoploss trailing \
  --epochs 50000 \
  -j -1 \
  --hyperopt-loss SharpeHyperOptLoss \
  --logfile /freqtrade/user_data/logs/hyperopt_15m_50k.log

echo "Container ${CONTAINER_NAME} is running in background across all CPU cores."
echo "Follow live progress with:"
echo "  docker logs -f ${CONTAINER_NAME}"
