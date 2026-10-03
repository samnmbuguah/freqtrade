#!/usr/bin/env python3
"""
ScreenCoins Multi-Strategy Multi-Timeframe Two-Stage Sortino Hyperopt Pipeline
Runs coarse-stepped Bayesian optimization across:
  - Timeframes: 15m -> 5m -> 1h
  - Strategies: LiqCapitulationLong -> LiqExhaustionShort -> DailyOutlierAnchor
  - Two-Stage Execution:
      Stage 1: --spaces buy sell (1,500 epochs)
      Stage 2: --spaces roi stoploss trailing (1,200 epochs)
"""

import os
import sys
import time
import glob
import json
import signal
import subprocess
from datetime import datetime, timezone

BASE_DIR = "/root/Dev/screencoins/freqtrade"
USER_DATA = os.path.join(BASE_DIR, "user_data")
RESULTS_DIR = os.path.join(USER_DATA, "hyperopt_results")
STATUS_FILE = os.path.join(BASE_DIR, "pipeline_status.json")
SUMMARY_FILE = os.path.join(USER_DATA, "hyperopt_pipeline_summary.md")
CONTAINER_NAME = "hyperopt_pipeline_runner"

SCHEDULE = [
    # 1. 15m Timeframe (Live Bot & Primary Timeframe)
    {"strategy": "LiqCapitulationLong", "timeframe": "15m", "timerange": "20260731-20260913"},
    {"strategy": "LiqExhaustionShort",  "timeframe": "15m", "timerange": "20260731-20260913"},
    {"strategy": "DailyOutlierAnchor",  "timeframe": "15m", "timerange": "20260731-20260913"},

    # 2. 5m Timeframe (Fast Scalp Engine)
    {"strategy": "LiqCapitulationLong", "timeframe": "5m",  "timerange": "20260731-20260913"},
    {"strategy": "LiqExhaustionShort",  "timeframe": "5m",  "timerange": "20260731-20260913"},
    {"strategy": "DailyOutlierAnchor",  "timeframe": "5m",  "timerange": "20260731-20260913"},

    # 3. 1h Timeframe (Macro Swing Engine)
    {"strategy": "LiqCapitulationLong", "timeframe": "1h",  "timerange": "20260731-20260913"},
    {"strategy": "LiqExhaustionShort",  "timeframe": "1h",  "timerange": "20260731-20260913"},
    {"strategy": "DailyOutlierAnchor",  "timeframe": "1h",  "timerange": "20260731-20260913"},
]

STAGE1_EPOCHS = 1500
STAGE2_EPOCHS = 1200

current_proc = None

def signal_handler(sig, frame):
    print("\n[Pipeline] Termination signal received. Stopping Docker container...")
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    update_status(running=False, error="Terminated by user")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def update_status(**kwargs):
    status = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                status = json.load(f)
        except Exception:
            pass
    status.update(kwargs)
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def get_latest_fthypt(strategy: str) -> str:
    pattern = os.path.join(RESULTS_DIR, f"strategy_{strategy}_*.fthypt")
    files = glob.glob(pattern)
    if not files:
        files = glob.glob(os.path.join(RESULTS_DIR, "*.fthypt"))
    return max(files, key=os.path.getmtime) if files else ""

def append_to_summary(strategy: str, timeframe: str, stage: int, metrics: dict, params: dict):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    os.makedirs(os.path.dirname(SUMMARY_FILE), exist_ok=True)
    
    is_new = not os.path.exists(SUMMARY_FILE)
    with open(SUMMARY_FILE, "a") as f:
        if is_new:
            f.write("# ScreenCoins Two-Stage Multi-Timeframe Hyperopt Results\n\n")
            f.write("| Timestamp | Strategy | TF | Stage | Trades | Win Rate | Total Profit | Max DD | Sortino | Sharpe |\n")
            f.write("|---|---|---|---|---|---|---|---|---|---|\n")
            
        wr = metrics.get('winrate', 0) * 100
        trades = metrics.get('total_trades', 0)
        p_abs = metrics.get('profit_total_abs', 0)
        dd = metrics.get('max_drawdown_account', 0) * 100
        sortino = metrics.get('sortino', 0)
        sharpe = metrics.get('sharpe', 0)
        
        f.write(f"| {now_str} | **{strategy}** | `{timeframe}` | Stage {stage} | {trades} | **{wr:.1f}%** | **+{p_abs:.2f} USDT** | {dd:.2f}% | **{sortino:.2f}** | {sharpe:.2f} |\n")

def run_hyperopt_stage(strategy: str, timeframe: str, timerange: str, stage: int, spaces: str, epochs: int, index: int, total: int):
    stage_desc = "Stage 1: Buy & Sell Space" if stage == 1 else "Stage 2: ROI, Stoploss & Trailing"
    print("\n" + "=" * 70)
    print(f"[{index}/{total}] Starting {strategy} on {timeframe} - {stage_desc}")
    print(f"Spaces: {spaces} | Epochs: {epochs} | Loss: SortinoHyperOptLoss")
    print("=" * 70)

    # Clean previous container
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    update_status(
        running=True,
        current_index=index,
        total_items=total,
        strategy=strategy,
        timeframe=timeframe,
        stage=stage,
        stage_name=stage_desc,
        spaces=spaces,
        target_epochs=epochs,
        start_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        error=None
    )

    log_file = f"/freqtrade/user_data/logs/hyperopt_{strategy}_{timeframe}_stage{stage}.log"
    cmd = [
        "docker", "run",
        "--name", CONTAINER_NAME,
        "-v", f"{USER_DATA}:/freqtrade/user_data",
        "-v", f"{BASE_DIR}/freqtrade:/freqtrade/freqtrade",
        "freqtradeorg/freqtrade:develop",
        "hyperopt",
        "--strategy", strategy,
        "--config", "/freqtrade/user_data/config_research.json",
        "--timeframe", timeframe,
        "--timerange", timerange,
        "--spaces", *spaces.split(),
        "--epochs", str(epochs),
        "-j", "-1",
        "--hyperopt-loss", "SortinoHyperOptLoss",
        "--logfile", log_file
    ]

    print(f"Executing: {' '.join(cmd)}")
    start_t = time.time()
    res = subprocess.run(cmd)
    dur = (time.time() - start_t) / 60.0

    if res.returncode != 0:
        print(f"Warning: Hyperopt exited with code {res.returncode}")
        # Clean container
        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False

    # Apply best trial to strategy JSON
    target_json = os.path.join(USER_DATA, "strategies", f"{strategy}.json")
    pattern = os.path.join(RESULTS_DIR, f"strategy_{strategy}_*.fthypt")
    spaces_csv = ",".join(spaces.split())

    apply_cmd = [
        "python3",
        os.path.join(BASE_DIR, "apply_hyperopt_best.py"),
        strategy,
        spaces_csv,
        pattern,
        target_json
    ]
    subprocess.run(apply_cmd)

    # Read latest metrics to record
    latest_fthypt = get_latest_fthypt(strategy)
    best_trial = None
    if latest_fthypt and os.path.exists(latest_fthypt):
        with open(latest_fthypt, "r") as f:
            best_loss = float("inf")
            for line in f:
                if line.strip():
                    t = json.loads(line)
                    if t.get("loss", float("inf")) < best_loss:
                        best_loss = t.get("loss")
                        best_trial = t
                        
    if best_trial:
        m = best_trial.get("results_metrics", {})
        p = best_trial.get("params_details", {})
        append_to_summary(strategy, timeframe, stage, m, p)

    # If Stage 2 completed, also save a permanent copy for this specific timeframe
    if stage == 2:
        archived_json = os.path.join(USER_DATA, "strategies", f"{strategy}_{timeframe}_optimized.json")
        subprocess.run(["cp", target_json, archived_json])
        print(f"Archived full multi-stage strategy config to: {archived_json}")

    print(f"Done stage in {dur:.1f} minutes.")
    return True

def main():
    total_tasks = len(SCHEDULE)
    print("=" * 70)
    print(f"Starting Multi-Strategy Two-Stage Hyperopt Pipeline ({total_tasks} Strategy-TF Jobs)")
    print("=" * 70)

    for i, item in enumerate(SCHEDULE, 1):
        strat = item["strategy"]
        tf = item["timeframe"]
        tr = item["timerange"]

        # Stage 1: Buy & Sell Space
        success1 = run_hyperopt_stage(strat, tf, tr, stage=1, spaces="buy sell", epochs=STAGE1_EPOCHS, index=i, total=total_tasks)
        if not success1:
            print(f"Failed Stage 1 for {strat} ({tf}). Skipping to next...")
            continue

        # Stage 2: ROI, Stoploss & Trailing Space
        success2 = run_hyperopt_stage(strat, tf, tr, stage=2, spaces="roi stoploss trailing", epochs=STAGE2_EPOCHS, index=i, total=total_tasks)
        if not success2:
            print(f"Failed Stage 2 for {strat} ({tf}). Continuing...")

    print("\n" + "=" * 70)
    print("ALL PIPELINE TASKS COMPLETED SUCCESSFULLY!")
    print(f"Summary ledger available at: {SUMMARY_FILE}")
    print("=" * 70)
    update_status(running=False, completed_all=True)

if __name__ == "__main__":
    main()
