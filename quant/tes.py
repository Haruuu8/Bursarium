# quant/bandingkan_rules.py
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.data_loader import load_panel_from_gabungan
from quant.data_cleaner import clean_panel
from quant.feature_engineering import build_features
from quant.event_detector import detect_events

def simulate_trade(df_ohlcv, entry, tanggal_signal, gap_min_pct, gap_max_pct):
    try:
        entry = float(entry)
        sig_dt = pd.Timestamp(tanggal_signal).normalize()
    except (ValueError, TypeError):
        return None, "SUSPENDED"

    if pd.isna(entry) or entry <= 0:
        return None, "SUSPENDED"

    m = df_ohlcv.index[df_ohlcv["Date"] == sig_dt].tolist()
    if m:
        sig_idx = m[0]
    else:
        v = df_ohlcv[df_ohlcv["Date"] >= sig_dt]
        if len(v) == 0:
            return None, "SUSPENDED"
        sig_idx = v.index[0]

    entry_idx = sig_idx + 1
    if entry_idx >= len(df_ohlcv):
        return None, "PENDING"

    signal_close = df_ohlcv.iloc[sig_idx]["Close"]
    open_t1 = df_ohlcv.iloc[entry_idx]["Open"]

    if pd.isna(open_t1) or open_t1 <= 0:
        return None, "SUSPENDED"

    gap_pct = (open_t1 / signal_close) - 1
    if gap_pct < gap_min_pct:
        return None, "SKIP_GAP_LOW"
    if gap_pct > gap_max_pct:
        return None, "SKIP_GAP_HIGH"

    SL_PCT = -0.03
    TRAIL_PCT = 0.005
    MAX_HOLD_DAYS = 30

    sl_price = entry * (1 + SL_PCT)
    peak = entry
    end_idx = min(entry_idx + MAX_HOLD_DAYS, len(df_ohlcv))

    for i in range(entry_idx, end_idx):
        row = df_ohlcv.iloc[i]
        high = row["High"]
        low = row["Low"]
        if pd.isna(high) or pd.isna(low):
            continue

        if high > peak:
            peak = high

        trail_price = peak * (1 - TRAIL_PCT)

        if trail_price > entry and low <= trail_price:
            return (trail_price / entry - 1), "TRAIL"

        if low <= sl_price:
            return SL_PCT, "SL"

    last_close = float(df_ohlcv.iloc[end_idx - 1]["Close"])
    if pd.isna(last_close):
        return None, "SUSPENDED"
    return last_close / entry - 1, "HOLD"

def load_all_data():
    print("Memuat data panel...")
    panel = load_panel_from_gabungan()
    panel = clean_panel(panel)
    panel = build_features(panel)
    panel = detect_events(panel)
    
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel = panel[(panel["open"] > 0) & (panel["close"] > 0)].copy()
    
    print("Menghitung MA200 & Forward Return...")
    panel["ma200"] = panel.groupby("kode")["close"].transform(lambda x: x.rolling(200, min_periods=100).mean())
    panel["px_vs_ma200"] = (panel["close"] / panel["ma200"]) - 1
    
    panel = panel.sort_values(["kode", "date"]).reset_index(drop=True)
    panel["open_T1"] = panel.groupby("kode")["open"].shift(-1)
    
    return panel

def apply_rules(panel):
    m_a = (panel["ret_1d"] > 0.10) & (panel["ret_5d"] > 0.10) & (panel["px_vs_sma20"] > 0.10)
    m_a_mid = (panel["ret_1d"] > 0.08) & (panel["ret_5d"] > 0.08) & (panel["px_vs_sma20"] > 0.08)
    m_b = (panel["ret_1d"] > 0.10) & (panel["ret_5d"] > 0.15) & (panel["range"] > 0.08) & (panel["vol_z_20"] > 1.5)
    m_ma200 = panel["px_vs_ma200"] > 0.10
    
    rule1 = m_b & m_a_mid & m_ma200
    rule2 = m_a & m_ma200
    
    print(f"\n--- TOTAL SINYAL SEBELUM GAP ---")
    print(f"Rule 1 (B ∩ A_Mid + MA200) : {rule1.sum()} kali")
    print(f"Rule 2 (A + MA200)         : {rule2.sum()} kali")
    print(f"--------------------------------\n")
    
    return rule1, rule2

def run_backtest(panel, mask, df_ohlcv_map, gap_min, gap_max):
    df_signals = panel[mask].copy()
    if df_signals.empty: return 0, 0, 0, {}
    
    n_exec = 0
    n_win = 0
    tot_ret = 0
    status_counts = {"TRAIL":0, "SL":0, "HOLD":0, "SKIP_GAP_LOW":0, "SKIP_GAP_HIGH":0, "SUSPENDED":0, "PENDING":0}
    
    for _, row in df_signals.iterrows():
        kode = row["kode"]
        if kode not in df_ohlcv_map: 
            status_counts["SUSPENDED"] += 1
            continue
        
        ret, status = simulate_trade(df_ohlcv_map[kode], row["open_T1"], row["date"], gap_min, gap_max)
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if status in ("TRAIL", "SL", "HOLD"):
            n_exec += 1
            tot_ret += ret
            if ret > 0:
                n_win += 1
                
    wr = (n_win / n_exec * 100) if n_exec > 0 else 0
    avg = (tot_ret / n_exec * 100) if n_exec > 0 else 0
    
    return n_exec, wr, avg, status_counts

def main():
    panel = load_all_data()
    rule1, rule2 = apply_rules(panel)
    
    print("Memuat data OHLCV individual (CSV)...")
    df_ohlcv_map = {}
    kodes = panel["kode"].unique()
    for k in kodes:
        path = os.path.join("data_ohlcv_idx", f"{k}.csv")
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                
                # FIX BUG: Normalisasi nama kolom persis seperti screen.py
                rename_map = {}
                for col in df.columns:
                    cl = str(col).lower().strip()
                    if cl in ("open", "openprice", "open_price"): rename_map[col] = "Open"
                    elif cl in ("high", "highprice", "high_price"): rename_map[col] = "High"
                    elif cl in ("low", "lowprice", "low_price"): rename_map[col] = "Low"
                    elif cl in ("close", "closeprice", "close_price"): rename_map[col] = "Close"
                    elif cl in ("date", "tanggal"): rename_map[col] = "Date"

                df = df.rename(columns=rename_map)
                df = df.loc[:, ~df.columns.duplicated(keep="first")]
                
                if all(c in df.columns for c in ["Date", "Open", "High", "Low", "Close"]):
                    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
                    df = df.sort_values("Date").reset_index(drop=True)
                    df_ohlcv_map[k] = df
            except:
                pass

    gaps_to_test = [(0.02, 0.10), (0.02, 0.15), (0.02, 0.20)]
    
    print("\n" + "="*95)
    print("BANDINGKAN RULE 1 vs RULE 2 (TRAIL 0.5%, SL 3%)")
    print("="*95)
    print(f"{'Rule':<10} | {'Gap Filter':<12} | {'N (Trade)':<10} | {'Win Rate':<10} | {'Avg P/L':<10} | {'Status Sinyal'}")
    print("-" * 95)
    
    for gmin, gmax in gaps_to_test:
        gap_str = f"{int(gmin*100)}-{int(gmax*100)}%"
        
        n1, wr1, avg1, st1 = run_backtest(panel, rule1, df_ohlcv_map, gmin, gmax)
        print(f"{'Rule 1':<10} | {gap_str:<12} | {n1:<10} | {wr1:>6.1f}%   | {avg1:>+6.2f}%   | SkipLow:{st1['SKIP_GAP_LOW']}, SkipHigh:{st1['SKIP_GAP_HIGH']}")
        
        n2, wr2, avg2, st2 = run_backtest(panel, rule2, df_ohlcv_map, gmin, gmax)
        print(f"{'Rule 2':<10} | {gap_str:<12} | {n2:<10} | {wr2:>6.1f}%   | {avg2:>+6.2f}%   | SkipLow:{st2['SKIP_GAP_LOW']}, SkipHigh:{st2['SKIP_GAP_HIGH']}")
        print("-" * 95)

if __name__ == "__main__":
    main()