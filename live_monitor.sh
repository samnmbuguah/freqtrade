#!/usr/bin/env bash

TARGET_DIR="/root/Dev/screencoins/freqtrade/user_data/hyperopt_results"
STATUS_FILE="/root/Dev/screencoins/freqtrade/pipeline_status.json"

python3 -c "
import json, glob, os, time, sys, re

def get_status():
    if os.path.exists('${STATUS_FILE}'):
        try:
            with open('${STATUS_FILE}', 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def get_latest_file(strat=None):
    # 1. Try from .last_result.json
    last_res_path = os.path.join('${TARGET_DIR}', '.last_result.json')
    if os.path.exists(last_res_path):
        try:
            with open(last_res_path, 'r') as f:
                lr = json.load(f)
                latest_name = lr.get('latest_hyperopt')
                if latest_name:
                    p = os.path.join('${TARGET_DIR}', latest_name)
                    if os.path.exists(p):
                        if not strat or f'_{strat}_' in latest_name:
                            return p
                        # If the specified strat doesn't match latest file, fallback to latest file if valid
                        return p
        except Exception:
            pass

    # 2. Check by strategy glob
    if strat:
        files = glob.glob(f'${TARGET_DIR}/strategy_{strat}_*.fthypt')
        if files:
            return max(files, key=os.path.getmtime)

    # 3. Fallback to newest .fthypt file
    files = glob.glob('${TARGET_DIR}/*.fthypt')
    if not files:
        return None
    return max(files, key=os.path.getmtime)

while True:
    status = get_status()
    active_strat = status.get('strategy')
    active_tf = status.get('timeframe', '15m')
    current_idx = status.get('current_index', 1)
    total_items = status.get('total_items', 3)
    stage_name = status.get('stage_name', 'Hyperopt Optimization')
    target_epochs = status.get('target_epochs', 200)
    spaces = status.get('spaces', 'buy sell')
    loss_name = status.get('loss', 'SharpeHyperOptLoss')

    fpath = get_latest_file(active_strat)
    if not fpath:
        print('Waiting for hyperopt to generate trial results...')
        time.sleep(3)
        continue

    # Extract strategy name from filename if not specified
    fname = os.path.basename(fpath)
    strat_match = re.search(r'strategy_([A-Za-z0-9]+)_', fname)
    displayed_strat = active_strat or (strat_match.group(1) if strat_match else 'Strategy')

    best_loss = 999999
    best = None
    count = 0
    size_mb = os.path.getsize(fpath) / (1024 * 1024)

    try:
        with open(fpath, 'r') as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                count += 1
                try:
                    d = json.loads(line_str)
                    loss = d.get('loss', 999999)
                    if loss < best_loss:
                        best_loss = loss
                        best = d
                except Exception:
                    continue
    except Exception as e:
        time.sleep(2)
        continue

    # Clear terminal screen
    sys.stdout.write('\033[H\033[J')
    pct = min((count / float(target_epochs)) * 100.0, 100.0) if target_epochs else 0.0
    bar_len = 35
    filled = int(bar_len * (pct / 100.0))
    bar = '=' * filled + '-' * (bar_len - filled)

    print('=' * 75)
    print('            SCREENCOINS HYPEROPT LIVE MONITOR')
    print('=' * 75)
    print(f'Active Task:     [{current_idx}/{total_items}] {displayed_strat} ({active_tf})')
    print(f'Phase & Loss:    {stage_name} | {loss_name}')
    print(f'Spaces:          {spaces}')
    print(f'Progress:        [{bar}] {count}/{target_epochs} ({pct:.1f}%)')
    print(f'Results File:    {fname} ({size_mb:.2f} MB)')
    print('-' * 75)

    if best:
        m = best.get('results_metrics', {})
        trades = m.get('total_trades', 0)
        wins = m.get('wins', 0)
        losses = m.get('losses', 0)
        draws = m.get('draws', 0)
        wr = m.get('winrate', 0) * 100
        p_abs = m.get('profit_total_abs', 0)
        p_pct = m.get('profit_total', 0) * 100
        dd = m.get('max_drawdown_account', 0) * 100
        pf = m.get('profit_factor', 0)
        sortino = m.get('sortino', 0)
        sharpe = m.get('sharpe', 0)

        print('  >>> CURRENT BEST TRIAL PERFORMANCE <<<')
        print(f'  * Total Trades:   {trades} trades ({wins} Wins / {draws} Draws / {losses} Losses)')
        print(f'  * Win Rate:       {wr:.1f}%')
        print(f'  * Profit:         +{p_abs:.2f} USDT (+{p_pct:.2f}%)')
        print(f'  * Max Drawdown:   {dd:.2f}%')
        print(f'  * Profit Factor:  {pf:.2f}')
        print(f'  * Sharpe Ratio:   {sharpe:.3f} | Sortino: {sortino:.3f}')
        print(f'  * Loss/Objective: {best_loss:.5f}')
        print('-' * 75)

        p = best.get('params_dict', {})
        print('  >>> KEY OPTIMIZED PARAMETERS <<<')

        # Buy space / Long params
        buy_keys = [k for k in p if k.startswith('long_') or k in ('leverage_num', 'z_liq_reversal', 'z_liq_cascade', 'wick_ratio_threshold', 'trend_ema_period')]
        sell_keys = [k for k in p if k.startswith('short_')]

        if buy_keys:
            print('  [Buy Space / Long Entries]')
            if 'long_leverage_num' in p:
                print(f'    - Long Leverage:     {p[\"long_leverage_num\"]}x')
            elif 'leverage_num' in p:
                print(f'    - Leverage:          {p[\"leverage_num\"]}x')
            if 'long_z_liq_cascade' in p:
                print(f'    - Long Cascade Z:    {p[\"long_z_liq_cascade\"]} σ')
            if 'long_z_liq_reversal' in p:
                print(f'    - Long Reversal Z:   {p[\"long_z_liq_reversal\"]} σ')
            if 'long_min_wall_dist' in p:
                print(f'    - Long Wall Runway:  {p[\"long_min_wall_dist\"]*100:.2f}%')
            if 'long_min_candle_pct' in p:
                print(f'    - Long Min Candle:   {p[\"long_min_candle_pct\"]*100:.2f}%')
            if 'long_wick_ratio_threshold' in p:
                print(f'    - Long Wick Ratio:   {p[\"long_wick_ratio_threshold\"]*100:.1f}%')

        if sell_keys:
            print('  [Sell Space / Short Entries]')
            if 'short_leverage_num' in p:
                print(f'    - Short Leverage:    {p[\"short_leverage_num\"]}x')
            if 'short_z_liq_cascade' in p:
                print(f'    - Short Cascade Z:   {p[\"short_z_liq_cascade\"]} σ')
            if 'short_z_liq_reversal' in p:
                print(f'    - Short Reversal Z:  {p[\"short_z_liq_reversal\"]} σ')
            if 'short_min_wall_dist' in p:
                print(f'    - Short Wall Runway: {p[\"short_min_wall_dist\"]*100:.2f}%')
            if 'short_min_candle_pct' in p:
                print(f'    - Short Min Candle:  {p[\"short_min_candle_pct\"]*100:.2f}%')
            if 'short_wick_ratio_threshold' in p:
                print(f'    - Short Wick Ratio:  {p[\"short_wick_ratio_threshold\"]*100:.1f}%')

        # Trailing Stop & Risk
        print('  [Risk & Dynamic Trailing Exits]')
        if 'trailing_stop_positive' in p:
            print(f'    - Trailing Stop:     {p[\"trailing_stop_positive\"]*100:.2f}%')
        if 'trailing_stop_positive_offset' in p:
            print(f'    - Trailing Offset:   {p[\"trailing_stop_positive_offset\"]*100:.2f}%')
        if 'stoploss' in p:
            print(f'    - Stoploss:          {p[\"stoploss\"]*100:.2f}%')

    print('=' * 75)
    print('  (Updating live every 3s... Press Ctrl+C to exit monitor)')
    time.sleep(3)
"
