#!/usr/bin/env bash
set -e

CONTAINER_NAME="hyperopt_liq_long_sortino"

docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

echo "=== Starting LiqCapitulationLong Hyperopt with Sortino Loss ==="

docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  -v /root/Dev/screencoins/freqtrade/user_data:/freqtrade/user_data \
  -v /root/Dev/screencoins/freqtrade/freqtrade:/freqtrade/freqtrade \
  freqtradeorg/freqtrade:develop \
  hyperopt \
  --strategy LiqCapitulationLong \
  --config /freqtrade/user_data/config_research.json \
  --timeframe 15m \
  --timerange 20260731-20260913 \
  --spaces buy sell roi stoploss trailing \
  --epochs 10000 \
  -j -1 \
  --hyperopt-loss SortinoHyperOptLoss \
  --logfile /freqtrade/user_data/logs/hyperopt_liq_long_sortino.log

echo "Container ${CONTAINER_NAME} started!"
echo "Follow live progress:"
echo "  docker logs -f ${CONTAINER_NAME}"
