#!/usr/bin/env python3
"""
evaluate_all_9_oos.py
Runs automated Out-of-Sample backtests on the unseen window (Sept 13, 2026 to Oct 2, 2026)
for all 9 hyperoptimized strategy-timeframe combinations:
  - LiqCapitulationLong: 15m, 5m, 1h
  - LiqExhaustionShort:  15m, 5m, 1h
  - DailyOutlierAnchor:  15m, 5m, 1h
"""

import os
import sys
import json
import time
import shutil
import subprocess

BASE_DIR = "/root/Dev/screencoins/freqtrade"
USER_DATA = os.path.join(BASE_DIR, "user_data")
STRATEGIES_DIR = os.path.join(USER_DATA, "strategies")
CONFIG_FILE = "/freqtrade/user_data/config_research.json"
OOS_TIMERANGE = "20260913-20261002"

JOBS = [
    # 15m Timeframe
    {"strategy": "LiqCapitulationLong", "tf": "15m"},
    {"strategy": "LiqExhaustionShort",  "tf": "15m"},
    {"strategy": "DailyOutlierAnchor",  "tf": "15m"},

    # 5m Timeframe
    {"strategy": "LiqCapitulationLong", "tf": "5m"},
    {"strategy": "LiqExhaustionShort",  "tf": "5m"},
    {"strategy": "DailyOutlierAnchor",  "tf": "5m"},

    # 1h Timeframe
    {"strategy": "LiqCapitulationLong", "tf": "1h"},
    {"strategy": "LiqExhaustionShort",  "tf": "1h"},
    {"strategy": "DailyOutlierAnchor",  "tf": "1h"},
]

def parse_backtest_output(output: str):
    metrics = {
        "trades": 0, "wins": 0, "losses": 0, "winrate": 0.0,
        "profit_usdt": 0.0, "profit_pct": 0.0, "drawdown_usdt": 0.0, "drawdown_pct": 0.0,
        "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0
    }
    for line in output.splitlines():
        if "Total/Daily Avg Trades" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                val = parts[2].strip().split("/")[0].strip()
                try: metrics["trades"] = int(val)
                except: pass
        elif "Win  Draw  Loss  Win%" in line:
            pass
        elif "Absolute profit" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                val = parts[2].strip().replace("USDT", "").strip()
                try: metrics["profit_usdt"] = float(val)
                except: pass
        elif "Total profit %" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                val = parts[2].strip().replace("%", "").strip()
                try: metrics["profit_pct"] = float(val)
                except: pass
        elif "Absolute drawdown" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                val = parts[2].strip()
                if "USDT" in val:
                    p1 = val.split("USDT")[0].strip()
                    try: metrics["drawdown_usdt"] = float(p1)
                    except: pass
                if "(" in val and "%)" in val:
                    p2 = val.split("(")[1].split("%")[0].strip()
                    try: metrics["drawdown_pct"] = float(p2)
                    except: pass
        elif "Sharpe (closed trades)" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                try: metrics["sharpe"] = float(parts[2].strip())
                except: pass
        elif "Sortino (closed trades)" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                try: metrics["sortino"] = float(parts[2].strip())
                except: pass
        elif "Calmar (closed trades)" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                try: metrics["calmar"] = float(parts[2].strip())
                except: pass

    # Summary table parsing for exact wins/draws/losses
    for line in output.splitlines():
        if "│" in line and not line.startswith("┏") and not line.startswith("┗") and not line.startswith("┡"):
            parts = [p.strip() for p in line.split("│") if p.strip()]
            if len(parts) >= 8 and parts[0] in ["LiqCapitulationLong", "LiqExhaustionShort", "DailyOutlierAnchor"]:
                try:
                    wdl = parts[6].split()
                    if len(wdl) >= 4:
                        metrics["wins"] = int(wdl[0])
                        metrics["losses"] = int(wdl[2])
                        metrics["winrate"] = float(wdl[3])
                except:
                    pass

    return metrics

def run_job(strategy: str, tf: str):
    opt_file = os.path.join(STRATEGIES_DIR, f"{strategy}_{tf}_optimized.json")
    target_file = os.path.join(STRATEGIES_DIR, f"{strategy}.json")
    backup_file = os.path.join(STRATEGIES_DIR, f"{strategy}.json.bak_eval")

    if not os.path.exists(opt_file):
        print(f"[Error] Optimized file not found: {opt_file}")
        return None

    # Backup current target json
    if os.path.exists(target_file):
        shutil.copyfile(target_file, backup_file)

    try:
        shutil.copyfile(opt_file, target_file)
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{USER_DATA}:/freqtrade/user_data",
            "-v", f"{BASE_DIR}/freqtrade:/freqtrade/freqtrade",
            "freqtradeorg/freqtrade:develop",
            "backtesting",
            "--strategy", strategy,
            "--config", CONFIG_FILE,
            "--timeframe", tf,
            "--timerange", OOS_TIMERANGE
        ]
        start_t = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        dur = time.time() - start_t
        metrics = parse_backtest_output(res.stdout)
        metrics["duration"] = dur
        return metrics
    finally:
        # Restore original target json
        if os.path.exists(backup_file):
            shutil.move(backup_file, target_file)

def main():
    print("=" * 80)
    print(f"ScreenCoins Out-of-Sample Evaluation Suite (9 Hyperoptimized Jobs)")
    print(f"Window: {OOS_TIMERANGE} (Sept 13 to Oct 02, 2026)")
    print("=" * 80)

    results = []
    for i, job in enumerate(JOBS, 1):
        strat = job["strategy"]
        tf = job["tf"]
        print(f"\n[{i}/9] Running OOS Backtest: {strat} on {tf} ...", flush=True)
        m = run_job(strat, tf)
        if m:
            print(f"    Trades: {m['trades']} | WinRate: {m['winrate']:.1f}% | Profit: {m['profit_usdt']:+.2f} USDT ({m['profit_pct']:+.2f}%) | DD: {m['drawdown_pct']:.2f}% | Sortino: {m['sortino']:.2f} | Sharpe: {m['sharpe']:.2f} ({m['duration']:.1f}s)")
            results.append({"strategy": strat, "timeframe": tf, **m})
        else:
            print(f"    Failed to run {strat} on {tf}")

    report_path = os.path.join(USER_DATA, "all_9_strategies_oos_report.md")
    with open(report_path, "w") as f:
        f.write("# ScreenCoins 9-Strategy Out-of-Sample (OOS) Performance Report\n\n")
        f.write(f"**Period:** `September 13, 2026` to `October 2, 2026` (19 Unseen Days)\n")
        f.write(f"**Pair:** `BTC/USDT:USDT` (Isolated Futures)\n")
        f.write(f"**Parameters:** Fully Hyperoptimized (Stage 1 + Stage 2 Optuna)\n\n")
        f.write("| Strategy | Timeframe | Trades | Wins | Losses | Win Rate | Profit (USDT) | Profit % | Max DD % | Sortino | Sharpe |\n")
        f.write("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")
        for r in results:
            f.write(f"| **{r['strategy']}** | `{r['timeframe']}` | {r['trades']} | {r['wins']} | {r['losses']} | **{r['winrate']:.1f}%** | **{r['profit_usdt']:+.2f}** | **{r['profit_pct']:+.2f}%** | {r['drawdown_pct']:.2f}% | **{r['sortino']:.2f}** | {r['sharpe']:.2f} |\n")

    print("\n" + "=" * 80)
    print(f"Report saved to: {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
