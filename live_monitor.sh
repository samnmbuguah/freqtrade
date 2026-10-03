#!/usr/bin/env bash

TARGET_DIR="/root/Dev/screencoins/freqtrade/user_data/hyperopt_results"
STATUS_FILE="/root/Dev/screencoins/freqtrade/pipeline_status.json"

python3 -c "
import json, glob, os, time, sys

def get_status():
    if os.path.exists('${STATUS_FILE}'):
        try:
            with open('${STATUS_FILE}', 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def get_latest_file(strat=None):
    if strat:
        files = glob.glob(f'${TARGET_DIR}/strategy_{strat}_*.fthypt')
        if files:
            return max(files, key=os.path.getmtime)
    files = glob.glob('${TARGET_DIR}/*.fthypt')
    if not files:
        return None
    return max(files, key=os.path.getmtime)

while True:
    status = get_status()
    active_strat = status.get('strategy', 'LiqCapitulationLong')
    active_tf = status.get('timeframe', '15m')
    current_idx = status.get('current_index', 1)
    total_items = status.get('total_items', 9)
    stage_num = status.get('stage', 1)
    stage_name = status.get('stage_name', 'Stage 1: Buy & Sell Space')
    target_epochs = status.get('target_epochs', 1500)
    spaces = status.get('spaces', 'buy sell')

    fpath = get_latest_file(active_strat)
    if not fpath:
        print('Waiting for hyperopt to generate trial results...')
        time.sleep(3)
        continue

    best_loss = 999
    best = None
    count = 0
    size_mb = os.path.getsize(fpath) / (1024 * 1024)

    try:
        with open(fpath, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                count += 1
                d = json.loads(line)
                loss = d.get('loss', 999)
                if loss < best_loss:
                    best_loss = loss
                    best = d
    except Exception as e:
        time.sleep(2)
        continue

    # Clear terminal screen
    sys.stdout.write('\033[H\033[J')
    pct = min((count / float(target_epochs)) * 100.0, 100.0) if target_epochs else 0.0
    bar_len = 35
    filled = int(bar_len * (pct / 100.0))
    bar = '=' * filled + '-' * (bar_len - filled)

    print('=' * 70)
    print('       SCREENCOINS TWO-STAGE SORTINO HYPEROPT MONITOR')
    print('=' * 70)
    print(f'Active Task:     [{current_idx}/{total_items}] {active_strat} ({active_tf})')
    print(f'Current Phase:   Stage {stage_num}: {stage_name}')
    print(f'Spaces:          {spaces}')
    print(f'Progress:        [{bar}] {count}/{target_epochs} ({pct:.1f}%)')
    print(f'Results File:    {os.path.basename(fpath)} ({size_mb:.1f} MB)')
    print('-' * 70)

    if best:
        m = best.get('results_metrics', {})
        trades = m.get('total_trades', 0)
        wins = m.get('wins', 0)
        losses = m.get('losses', 0)
        wr = m.get('winrate', 0) * 100
        p_abs = m.get('profit_total_abs', 0)
        dd = m.get('max_drawdown_account', 0) * 100
        pf = m.get('profit_factor', 0)
        sortino = m.get('sortino', 0)
        sharpe = m.get('sharpe', 0)

        print(f'  >>> CURRENT BEST TRIAL PERFORMANCE <<<')
        print(f'  * Total Trades:   {trades} trades')
        print(f'  * Win Rate:       {wr:.1f}% ({wins} Wins / {losses} Losses)')
        print(f'  * Absolute Gain:  +{p_abs:.2f} USDT (+{p_abs:.2f}%)')
        print(f'  * Max Drawdown:   {dd:.2f}%')
        print(f'  * Profit Factor:  {pf:.2f}')
        print(f'  * Sortino Ratio:  {sortino:.2f} | Sharpe: {sharpe:.2f}')
        print('-' * 70)

        p = best.get('params_dict', {})
        p_det = best.get('params_details', {})
        print('  >>> KEY OPTIMIZED PARAMETERS <<<')
        if 'leverage_num' in p:
            print(f'  * Leverage:          {p.get(\"leverage_num\")}x')
        if 'z_liq_threshold' in p:
            print(f'  * Z-Liq Trigger:     {p.get(\"z_liq_threshold\")} sigma')
        if 'long_tp_disp' in p:
            print(f'  * Long Take Profit:  {p.get(\"long_tp_disp\")} ({p.get(\"long_tp_disp\")*100:.2f}%)')
        if 'short_tp_disp' in p:
            print(f'  * Short Take Profit: {p.get(\"short_tp_disp\")} ({p.get(\"short_tp_disp\")*100:.2f}%)')
        if 'target_tp_disp' in p:
            print(f'  * Outlier Target TP: {p.get(\"target_tp_disp\")} ({p.get(\"target_tp_disp\")*100:.2f}%)')
        if 'stoploss' in p:
            print(f'  * Stoploss:          {p.get(\"stoploss\", 0)*100:.2f}% on margin')
        if 'long_max_holding_min' in p:
            print(f'  * Max Holding Time:  {p.get(\"long_max_holding_min\")} min')

    print('=' * 70)
    print('  (Updating live every 3s... Press Ctrl+C to exit monitor)')
    time.sleep(3)
"
