# 5,000-Epoch Hyperopt & Backtest Matrix Leaderboard
Timeframe sweeps across 15m, 5m, and 1m for 5 core institutional liquidation strategies.
Optimization target: **5,000 Epochs** per cell | Loss: **SharpeHyperOptLossDaily** | Concurrency: **max_open_trades = 1** | Asset: **BTC/USDT:USDT**

| Strategy | Timeframe | Epochs | Trades | Win Rate | Net Profit USDT | Net Profit % | Max Drawdown | Sharpe | Win/Loss Days | Completed At |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **LiqVwapWallStrategy** | `15m` | 5000 | 27 | **81.5%** | 95.033 USDT | **95.03%** | 0.001 USDT  0.00% | **11.40** | 21 / 10 / 2 | 2026-10-21 13:22 UTC |
| **LiqVwapBreakoutStrategy** | `15m` | 5000 | 27 | **92.6%** | 71.331 USDT | **71.33%** | 0.001 USDT  0.00% | **11.34** | 20 / 11 / 2 | 2026-10-21 15:01 UTC |
| **LiquidationFlipStrategy** | `15m` | 5000 | 51 | **72.5%** | 95.203 USDT | **95.2%** | 15.632 USDT  11.42% | **8.06** | 25 / 6 / 2 | 2026-10-21 17:15 UTC |
| **LiqCapitulationLong** | `15m` | 5000 | 75 | **70.7%** | 97.210 USDT | **97.21%** | 18.296 USDT  17.98% | **7.37** | 37 / 12 / 14 | 2026-10-21 19:59 UTC |
| **LiqExhaustionShort** | `15m` | 5000 | 21 | **95.2%** | 62.816 USDT | **62.82%** | 0 USDT  0.00% | **10.78** | 19 / 43 / 1 | 2026-10-21 22:55 UTC |
| **LiqVwapWallStrategy** | `5m` | 5000 | 12 | **91.7%** | 29.045 USDT | **29.04%** | 0 USDT  0.00% | **7.73** | 10 / 19 / 1 | 2026-10-22 01:36 UTC |
| **LiqVwapBreakoutStrategy** | `5m` | 5000 | 29 | **69.0%** | 22.228 USDT | **22.23%** | 2.68 USDT  2.27% | **7.54** | 14 / 15 / 5 | 2026-10-22 04:29 UTC |
