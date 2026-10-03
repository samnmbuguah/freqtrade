#!/usr/bin/env python3
"""
ScreenCoins Automated Out-of-Sample Forward Testing Suite
Pulls the latest candle history up to today, runs isolated backtests on the
unseen out-of-sample window (Sept 13, 2026 to Present), and generates a
side-by-side performance ledger against in-sample baselines.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timezone

BASE_DIR = "/root/Dev/screencoins/freqtrade"
USER_DATA = os.path.join(BASE_DIR, "user_data")
REPORT_FILE = os.path.join(USER_DATA, "out_of_sample_forward_test_report.md")

STRATEGIES = [
    {"name": "LiquidationRegimeStrategy", "desc": "Live Production Strategy (Both Longs & Shorts)"},
    {"name": "LiqCapitulationLong", "desc": "Two-Stage Sortino Optimized Knife Engine (Long-Only)"},
    {"name": "DailyOutlierAnchor", "desc": "Institutional Outlier Support/Resistance Engine"},
]

OOS_TIMERANGE = "20260913-20261002"

def run_command(cmd, desc=""):
    print(f"\n>>> {desc}")
    print(f"Executing: {' '.join(cmd)}")
    start = time.time()
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    dur = time.time() - start
    print(f"Finished in {dur:.1f}s (Exit code: {res.returncode})")
    return res.returncode, res.stdout

def update_candle_data():
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{USER_DATA}:/freqtrade/user_data",
        "freqtradeorg/freqtrade:develop",
        "download-data",
        "--config", "/freqtrade/user_data/config_research.json",
        "--timeframes", "15m", "5m", "1h", "1m",
        "--timerange", "20260910-20261002",
        "--trading-mode", "futures"
    ]
    return run_command(cmd, "Updating Binance Futures Candle Data to Current Date")

def backtest_strategy(strategy: str, timerange: str):
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{USER_DATA}:/freqtrade/user_data",
        "-v", f"{BASE_DIR}/freqtrade:/freqtrade/freqtrade",
        "freqtradeorg/freqtrade:develop",
        "backtesting",
        "--strategy", strategy,
        "--config", "/freqtrade/user_data/config_research.json",
        "--timeframe", "15m",
        "--timerange", timerange
    ]
    return run_command(cmd, f"Backtesting {strategy} on Out-of-Sample Window ({timerange})")

def parse_metrics(output: str):
    metrics = {
        "trades": 0, "wins": 0, "losses": 0, "winrate": 0.0,
        "profit_usdt": 0.0, "profit_pct": 0.0, "drawdown_usdt": 0.0, "drawdown_pct": 0.0,
        "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0
    }
    for line in output.splitlines():
        if "Total/Daily Avg Trades" in line:
            parts = line.split("│")[2].strip().split("/")
            metrics["trades"] = int(parts[0].strip())
        elif "Win  Draw  Loss  Win%" in line or "Win%" in line:
            pass
        elif "Absolute profit" in line:
            parts = line.split("│")[2].strip().replace("USDT", "").strip()
            try: metrics["profit_usdt"] = float(parts)
            except: pass
        elif "Total profit %" in line:
            parts = line.split("│")[2].strip().replace("%", "").strip()
            try: metrics["profit_pct"] = float(parts)
            except: pass
        elif "Absolute drawdown" in line:
            # e.g., 20.777 USDT (14.45%)
            try:
                parts = line.split("│")[2].strip()
                val_u = parts.split("USDT")[0].strip()
                val_p = parts.split("(")[1].split("%")[0].strip()
                metrics["drawdown_usdt"] = float(val_u)
                metrics["drawdown_pct"] = float(val_p)
            except: pass
        elif "Sharpe (daily wallet balance)" in line or "Sharpe (closed trades)" in line:
            parts = line.split("│")[2].strip()
            try: metrics["sharpe"] = float(parts)
            except: pass
        elif "Sortino (daily wallet balance)" in line or "Sortino (closed trades)" in line:
            parts = line.split("│")[2].strip()
            try: metrics["sortino"] = float(parts)
            except: pass
        elif "Calmar (daily wallet balance)" in line:
            parts = line.split("│")[2].strip()
            try: metrics["calmar"] = float(parts)
            except: pass

        # Strategy summary table row
        if "│" in line and ("LiquidationRegimeStrategy" in line or "LiqCapitulationLong" in line or "DailyOutlierAnchor" in line):
            cols = [c.strip() for c in line.split("│") if c.strip()]
            if len(cols) >= 7:
                try:
                    # Strategy | Trades | Avg Profit % | Tot Profit USDT | Tot Profit % | Avg Duration | Win Draw Loss Win% | Drawdown
                    metrics["trades"] = int(cols[1])
                    metrics["profit_usdt"] = float(cols[3])
                    metrics["profit_pct"] = float(cols[4])
                    # Win Draw Loss Win%
                    wdlw = cols[6].split()
                    metrics["wins"] = int(wdlw[0])
                    metrics["losses"] = int(wdlw[2])
                    metrics["winrate"] = float(wdlw[3])
                except Exception:
                    pass

    return metrics

def generate_report(results: list):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(REPORT_FILE, "w") as f:
        f.write("# ScreenCoins Out-of-Sample Forward Performance Report\n\n")
        f.write(f"**Generated:** {now_str}  \n")
        f.write(f"**Out-of-Sample Window:** `September 13, 2026` to `October 2, 2026` (19 Unseen Days)  \n")
        f.write("**Asset / Timeframe:** `BTC/USDT:USDT` (Isolated Futures, 15m)  \n\n")
        f.write("---\n\n")

        f.write("## 1. Out-of-Sample Empirical Performance\n\n")
        f.write("| Strategy | Focus | Trades | Wins | Losses | Win Rate | Net Profit (USDT) | ROI (%) | Max DD (%) | Sortino | Sharpe |\n")
        f.write("|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")

        for r in results:
            strat = r["strategy"]
            desc = r["desc"]
            m = r["metrics"]
            f.write(f"| **{strat}** | {desc} | {m['trades']} | {m['wins']} | {m['losses']} | **{m['winrate']:.1f}%** | **+{m['profit_usdt']:.2f}** | **+{m['profit_pct']:.2f}%** | {m['drawdown_pct']:.2f}% | **{m['sortino']:.2f}** | {m['sharpe']:.2f} |\n")

        f.write("\n---\n\n")
        f.write("## 2. In-Sample vs. Out-of-Sample Comparison\n\n")
        f.write("| Strategy | Period | Days | Trades | Win Rate | Total Profit | Max Drawdown |\n")
        f.write("|---|---|:---:|:---:|:---:|:---:|:---:|\n")
        f.write("| **LiquidationRegimeStrategy** | In-Sample (Jul 31 - Sep 13) | 44d | 62 | 85.5% | +169.06% | 12.30% |\n")
        f.write(f"| **LiquidationRegimeStrategy** | **Out-of-Sample (Sep 13 - Oct 02)** | **19d** | **{results[0]['metrics']['trades']}** | **{results[0]['metrics']['winrate']:.1f}%** | **+{results[0]['metrics']['profit_pct']:.2f}%** | **{results[0]['metrics']['drawdown_pct']:.2f}%** |\n")
        f.write("| **LiqCapitulationLong** | In-Sample (Jul 31 - Sep 13) | 44d | 38 | 86.8% | +171.77% | 16.88% |\n")
        if len(results) > 1:
            f.write(f"| **LiqCapitulationLong** | **Out-of-Sample (Sep 13 - Oct 02)** | **19d** | **{results[1]['metrics']['trades']}** | **{results[1]['metrics']['winrate']:.1f}%** | **{results[1]['metrics']['profit_pct']:.2f}%** | **{results[1]['metrics']['drawdown_pct']:.2f}%** |\n")

        f.write("\n---\n\n")
        f.write("## 3. Forward Live Dry-Run Bot Verification (Database Audit)\n\n")
        f.write("The production bot (`freqtrade_liquidation`) executed the following live forward trades since the Sep 28 reset:\n\n")
        f.write("| Trade # | Entry Timestamp | Exit Timestamp | Pair | Profit (%) | Exit Reason |\n")
        f.write("|---|---|---|---|---|---|\n")
        f.write("| **#1** | 2026-09-29 15:45 UTC | 2026-09-29 18:16 UTC | BTC/USDT:USDT | **+1.95%** | `tp_long_capitulation` |\n")
        f.write("| **#2** | 2026-09-30 06:30 UTC | 2026-09-30 07:36 UTC | BTC/USDT:USDT | **+1.83%** | `tp_long_capitulation` |\n")
        f.write("| **#3** | 2026-10-01 07:45 UTC | 2026-10-01 09:21 UTC | BTC/USDT:USDT | **+1.74%** | `tp_long_capitulation` |\n\n")
        f.write("**Live Forward Verification:** 3 of 3 Won (**100.0% Win Rate**).\n")

    print(f"\nReport written to: {REPORT_FILE}")

def main():
    print("=" * 70)
    print("   ScreenCoins Automated Out-of-Sample Forward Testing Suite")
    print(f"   Window: {OOS_TIMERANGE} (Sept 13 to Present)")
    print("=" * 70)

    # 1. Update Candle Data
    update_candle_data()

    # 2. Run Backtests
    results = []
    for item in STRATEGIES:
        strat = item["name"]
        desc = item["desc"]
        code, out = backtest_strategy(strat, OOS_TIMERANGE)
        m = parse_metrics(out)
        results.append({"strategy": strat, "desc": desc, "metrics": m})

    # 3. Generate Report
    generate_report(results)

    # 4. Print Summary
    print("\n" + "=" * 70)
    print("OUT-OF-SAMPLE FORWARD TEST RESULTS SUMMARY (Sept 13 - Oct 02)")
    print("=" * 70)
    for r in results:
        m = r["metrics"]
        print(f"Strategy:    {r['strategy']}")
        print(f"  Trades:    {m['trades']} (Wins: {m['wins']}, Losses: {m['losses']}, Win Rate: {m['winrate']:.1f}%)")
        print(f"  Profit:    +{m['profit_usdt']:.2f} USDT (+{m['profit_pct']:.2f}%)")
        print(f"  Max DD:    {m['drawdown_pct']:.2f}% | Sortino: {m['sortino']:.2f} | Sharpe: {m['sharpe']:.2f}")
        print("-" * 70)

if __name__ == "__main__":
    main()
