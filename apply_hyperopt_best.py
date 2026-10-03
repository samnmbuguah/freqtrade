#!/usr/bin/env python3
"""
apply_hyperopt_best.py
Finds the best trial from a hyperopt .fthypt result file and injects the
optimized spaces into the strategy's JSON configuration.
"""
import sys
import os
import glob
import json
from datetime import datetime, timezone

def apply_best(strategy_name: str, spaces: list, fthypt_pattern: str, target_json: str):
    files = glob.glob(fthypt_pattern)
    if not files:
        print(f"No .fthypt files found matching pattern: {fthypt_pattern}")
        sys.exit(1)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Reading results from: {latest_file}")
    
    best_loss = float("inf")
    best_trial = None
    
    with open(latest_file, "r") as f:
        for line in f:
            if not line.strip():
                continue
            trial = json.loads(line)
            loss = trial.get("loss", float("inf"))
            if loss < best_loss:
                best_loss = loss
                best_trial = trial
                
    if not best_trial:
        print("No valid trials found!")
        sys.exit(1)
        
    metrics = best_trial.get("results_metrics", {})
    wr = metrics.get('winrate', 0) * 100
    trades = metrics.get('total_trades', 0)
    profit = metrics.get('profit_total_abs', 0)
    sortino = metrics.get('sortino', 0)
    sharpe = metrics.get('sharpe', 0)
    dd = metrics.get('max_drawdown_account', 0) * 100
    
    print(f"Best Trial Found (Loss={best_loss:.4f}):")
    print(f"  Trades: {trades}, WinRate: {wr:.1f}%, Profit: +{profit:.2f} USDT, DD: {dd:.2f}%, Sortino: {sortino:.2f}, Sharpe: {sharpe:.2f}")
    
    params_details = best_trial.get("params_details", {})
    
    # Read existing target json or create structure
    if os.path.exists(target_json):
        with open(target_json, "r") as f:
            data = json.load(f)
    else:
        data = {
            "strategy_name": strategy_name,
            "params": {},
            "ft_stratparam_v": 1
        }
        
    if "params" not in data:
        data["params"] = {}
        
    for space in spaces:
        if space in params_details and params_details[space]:
            data["params"][space] = params_details[space]
            print(f"  -> Updated space '{space}': {params_details[space]}")
            
    data["strategy_name"] = strategy_name
    data["ft_stratparam_v"] = 1
    data["export_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f+00:00")
    
    with open(target_json, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"Successfully saved optimized params to {target_json}\n")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 apply_hyperopt_best.py <strategy_name> <comma_separated_spaces> <fthypt_pattern> <target_json>")
        sys.exit(1)
        
    strat = sys.argv[1]
    sp = [s.strip() for s in sys.argv[2].split(",") if s.strip()]
    pattern = sys.argv[3]
    dest = sys.argv[4]
    apply_best(strat, sp, pattern, dest)
