#!/usr/bin/env python3
"""
run_matrix_5k_hyperopts.py
===========================
Executes a 5,000-epoch hyperoptimization across 5 core institutional liquidation strategies
and 3 key timeframes (15m, 5m, 1m).

Strategies:
  1. LiqVwapWallStrategy      (Anchored VWAP + Dominant Wall Proximity & Clear Runway)
  2. LiqVwapBreakoutStrategy  (Anchored VWAP + Liquidation Squeeze/Cascade Breakout)
  3. LiquidationFlipStrategy  (Continuous Liquidation Impulse Signal Flip)
  4. LiqCapitulationLong      (Long Capitulation Rebound Engine)
  5. LiqExhaustionShort       (Short Exhaustion Reversal Engine)

Timeframes:
  - 15m (Primary institutional horizon, highest SNR)
  - 5m  (Intraday momentum impulse)
  - 1m  (Microstructure execution)

Each run uses:
  --epochs 5000
  --spaces buy sell roi stoploss trailing
  --hyperopt-loss SharpeHyperOptLossDaily
  -j -1 (all available CPU cores)
"""

import argparse
import glob
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MatrixHyperopt")

BASE_DIR = "/root/Dev/screencoins/freqtrade"
USER_DATA_HOST = os.path.join(BASE_DIR, "user_data")
STRATEGIES_DIR = os.path.join(USER_DATA_HOST, "strategies")
STATUS_FILE = os.path.join(BASE_DIR, "pipeline_status.json")
RESULTS_DIR = os.path.join(USER_DATA_HOST, "hyperopt_results")
SUMMARY_MD = os.path.join(BASE_DIR, "hyperopt_matrix_5k_results.md")

DOCKER_IMAGE = "freqtradeorg/freqtrade:develop"
CONFIG_PATH = "/freqtrade/user_data/config_research.json"
TIMERANGE = "20260801-20261003"
EPOCHS = 5000
LOSS_FUNCTION = "SharpeHyperOptLossDaily"
SPACES = "buy sell roi stoploss trailing"

ALL_STRATEGIES = [
    "LiqVwapWallStrategy",
    "LiqVwapBreakoutStrategy",
    "LiquidationFlipStrategy",
    "LiqCapitulationLong",
    "LiqExhaustionShort",
]

ALL_TIMEFRAMES = ["15m", "5m", "1m"]

current_container_name = None


def signal_handler(sig, frame):
    logger.warning("Interrupt signal received. Cleaning up active container...")
    if current_container_name:
        subprocess.run(["docker", "rm", "-f", current_container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    update_pipeline_status(running=False, note="Terminated by user or interrupt signal")
    sys.exit(1)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def update_pipeline_status(**kwargs):
    status = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                status = json.load(f)
        except Exception:
            status = {}
    status.update(kwargs)
    status["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)


def init_summary_file():
    if not os.path.exists(SUMMARY_MD):
        header = """# 5,000-Epoch Hyperopt & Backtest Matrix Leaderboard
Timeframe sweeps across 15m, 5m, and 1m for 5 core institutional liquidation strategies.
Optimization target: **5,000 Epochs** per cell | Loss: **SharpeHyperOptLossDaily** | Concurrency: **max_open_trades = 1** | Asset: **BTC/USDT:USDT**

| Strategy | Timeframe | Epochs | Trades | Win Rate | Net Profit USDT | Net Profit % | Max Drawdown | Sharpe | Win/Loss Days | Completed At |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
        with open(SUMMARY_MD, "w") as f:
            f.write(header)


def append_summary_row(row: dict):
    line = (
        f"| **{row['strategy']}** | `{row['timeframe']}` | {row['epochs']} | "
        f"{row.get('trades', 'N/A')} | **{row.get('win_rate', 'N/A')}** | "
        f"{row.get('profit_usdt', 'N/A')} | **{row.get('profit_pct', 'N/A')}** | "
        f"{row.get('drawdown', 'N/A')} | **{row.get('sharpe', 'N/A')}** | "
        f"{row.get('days_win_loss', 'N/A')} | {row.get('timestamp', 'N/A')} |\n"
    )
    with open(SUMMARY_MD, "a") as f:
        f.write(line)


def extract_best_fthypt(strategy: str, target_json: str):
    """Extract best params from latest .fthypt result file into target_json."""
    pattern = os.path.join(RESULTS_DIR, f"strategy_{strategy}_*.fthypt")
    files = glob.glob(pattern)
    if not files:
        logger.warning(f"No .fthypt files found for {strategy}")
        return False
    
    latest_file = max(files, key=os.path.getmtime)
    logger.info(f"Extracting best trial from: {latest_file}")
    
    best_loss = float("inf")
    best_trial = None
    
    with open(latest_file, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                trial = json.loads(line)
                loss = trial.get("loss", float("inf"))
                if loss < best_loss:
                    best_loss = loss
                    best_trial = trial
            except Exception:
                continue

    if not best_trial:
        logger.warning("No valid trials found in .fthypt file")
        return False
        
    metrics = best_trial.get("results_metrics", {})
    wr = metrics.get('winrate', 0) * 100
    trades = metrics.get('total_trades', 0)
    profit = metrics.get('profit_total_abs', 0)
    sharpe = metrics.get('sharpe', 0)
    dd = metrics.get('max_drawdown_account', 0) * 100
    
    logger.info(f"Best Trial Found (Loss={best_loss:.4f}): Trades={trades}, WR={wr:.1f}%, Profit=+{profit:.2f} USDT, DD={dd:.2f}%, Sharpe={sharpe:.2f}")
    
    params_details = best_trial.get("params_details", {})
    data = {
        "strategy_name": strategy,
        "params": {
            "max_open_trades": {"max_open_trades": 1}
        },
        "ft_stratparam_v": 1,
        "export_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00:00")
    }
    
    for space in SPACES.split():
        if space in params_details and params_details[space]:
            data["params"][space] = params_details[space]
            
    with open(target_json, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved optimized params to {target_json}")
    return True


def parse_backtest_output(output: str) -> dict:
    metrics = {
        "trades": "N/A",
        "win_rate": "N/A",
        "profit_usdt": "N/A",
        "profit_pct": "N/A",
        "drawdown": "N/A",
        "sharpe": "N/A",
        "days_win_loss": "N/A",
    }
    lines = output.splitlines()
    for line in lines:
        if "│" in line and any(strat in line for strat in ALL_STRATEGIES):
            parts = [p.strip() for p in line.split("│") if p.strip()]
            if len(parts) >= 8:
                try:
                    metrics["trades"] = parts[1]
                    metrics["profit_usdt"] = parts[3] + " USDT"
                    metrics["profit_pct"] = parts[4] + "%"
                    wdl_parts = parts[6].split()
                    if wdl_parts:
                        metrics["win_rate"] = wdl_parts[-1] + "%"
                    metrics["drawdown"] = parts[7]
                except Exception:
                    pass

        if "Sharpe (daily wallet balance)" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                metrics["sharpe"] = parts[2].strip()

        if "Days win/draw/lose" in line:
            parts = line.split("│")
            if len(parts) >= 3:
                metrics["days_win_loss"] = parts[2].strip()

    return metrics


def run_hyperopt(strategy: str, timeframe: str, epochs: int):
    global current_container_name
    container_name = f"hyperopt_5k_{strategy}_{timeframe}"
    current_container_name = container_name

    logger.info(f"===> Starting Hyperopt: {strategy} [{timeframe}] for {epochs} epochs")
    log_file = os.path.join(USER_DATA_HOST, "logs", f"{container_name}.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    cmd = [
        "docker", "run",
        "--name", container_name,
        "--rm",
        "-v", f"{USER_DATA_HOST}:/freqtrade/user_data",
        DOCKER_IMAGE,
        "hyperopt",
        "--strategy", strategy,
        "--config", CONFIG_PATH,
        "--timeframe", timeframe,
        "--timerange", TIMERANGE,
        "--spaces", *SPACES.split(),
        "--epochs", str(epochs),
        "-j", "-1",
        "--hyperopt-loss", LOSS_FUNCTION,
    ]

    with open(log_file, "w") as out:
        proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT)
        proc.wait()

    current_container_name = None
    if proc.returncode != 0:
        logger.error(f"Hyperopt failed with return code {proc.returncode}. See {log_file}")
        return False
    logger.info(f"===> Hyperopt Finished: {strategy} [{timeframe}]")
    return True


def save_and_backtest(strategy: str, timeframe: str, epochs: int):
    logger.info(f"===> Running Backtest Verification for {strategy} [{timeframe}]")
    dest_json = os.path.join(STRATEGIES_DIR, f"{strategy}_{timeframe}_5k_optimized.json")
    default_json = os.path.join(STRATEGIES_DIR, f"{strategy}.json")

    # Extract best trial from fthypt directly into dest_json
    extracted = extract_best_fthypt(strategy, dest_json)
    if not extracted and os.path.exists(default_json):
        shutil.copyfile(default_json, dest_json)

    # Backup default_json if running non-15m timeframe
    backup_json = default_json + ".matrix_bak"
    if os.path.exists(default_json):
        shutil.copyfile(default_json, backup_json)

    # Temporarily set strategy.json to our optimized json for backtesting
    if os.path.exists(dest_json):
        shutil.copyfile(dest_json, default_json)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{USER_DATA_HOST}:/freqtrade/user_data",
        DOCKER_IMAGE,
        "backtesting",
        "--strategy", strategy,
        "--config", CONFIG_PATH,
        "--timeframe", timeframe,
        "--timerange", TIMERANGE,
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    metrics = parse_backtest_output(res.stdout)

    # Restore original default_json if this wasn't 15m
    if timeframe != "15m" and os.path.exists(backup_json):
        shutil.copyfile(backup_json, default_json)
        os.remove(backup_json)
    elif os.path.exists(backup_json):
        os.remove(backup_json)

    row = {
        "strategy": strategy,
        "timeframe": timeframe,
        "epochs": epochs,
        "trades": metrics["trades"],
        "win_rate": metrics["win_rate"],
        "profit_usdt": metrics["profit_usdt"],
        "profit_pct": metrics["profit_pct"],
        "drawdown": metrics["drawdown"],
        "sharpe": metrics["sharpe"],
        "days_win_loss": metrics["days_win_loss"],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    append_summary_row(row)
    logger.info(f"Result for {strategy} [{timeframe}]: WR={row['win_rate']}, Profit={row['profit_pct']}, DD={row['drawdown']}, Sharpe={row['sharpe']}")
    return row


def main():
    parser = argparse.ArgumentParser(description="Matrix 5K Hyperopt Runner")
    parser.add_argument("--strategies", nargs="+", default=ALL_STRATEGIES, help="Strategies to run")
    parser.add_argument("--timeframes", nargs="+", default=ALL_TIMEFRAMES, help="Timeframes to run")
    parser.add_argument("--epochs", type=int, default=EPOCHS, help="Number of epochs per cell")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip if 5k json already exists")
    args = parser.parse_args()

    init_summary_file()

    total_jobs = len(args.timeframes) * len(args.strategies)
    job_idx = 0

    logger.info(f"Starting 5K Matrix Sweep: {len(args.strategies)} strategies x {len(args.timeframes)} timeframes = {total_jobs} total jobs")

    for tf in args.timeframes:
        for strat in args.strategies:
            job_idx += 1
            dest_json = os.path.join(STRATEGIES_DIR, f"{strat}_{tf}_5k_optimized.json")
            
            if args.skip_existing and os.path.exists(dest_json):
                logger.info(f"[{job_idx}/{total_jobs}] Skipping already completed {strat} [{tf}] ({dest_json} exists)")
                continue

            update_pipeline_status(
                running=True,
                strategy=strat,
                timeframe=tf,
                current_index=job_idx,
                total_items=total_jobs,
                stage_name=f"Running 5,000-Epoch Hyperopt [{tf}]",
                target_epochs=args.epochs,
                loss=LOSS_FUNCTION,
                spaces=SPACES,
                completed_all=False,
            )

            success = run_hyperopt(strat, tf, args.epochs)
            if success:
                row = save_and_backtest(strat, tf, args.epochs)
                update_pipeline_status(
                    last_completed=f"{strat} [{tf}]",
                    last_metrics=row,
                )
            else:
                logger.warning(f"Failed job for {strat} [{tf}]")

    update_pipeline_status(
        running=False,
        completed_all=True,
        stage_name="Matrix 5,000-Epoch Hyperopt Completed",
        note=f"All {total_jobs} jobs finished.",
    )
    logger.info("All matrix hyperopt jobs completed successfully!")


if __name__ == "__main__":
    main()
