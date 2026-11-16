# quant/cek_bulan_ini.py
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.data_loader import load_panel_from_gabungan
from quant.data_cleaner import clean_panel
from quant.feature_engineering import build_features
from quant.event_detector import detect_events

TRAIL_PCT = 0.005
SL_PCT = -0.03
MAX_HOLD_DAYS = 30
OHLCV_DIR = "data_ohlcv_idx"

_OHLCV_CACHE = {}

def _load_ohlcv(kode):
    if kode in _OHLCV_CACHE: return _OHLCV_CACHE[kode]
    path = os.path.join(OHLCV_DIR, f"{kode}.csv")
    if not os.path.exists(path): return None
    try:
        df = pd.read_csv(path)
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
        if any(c not in df.columns for c in ["Date", "Open", "High", "Low", "Close"]): return None
        df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
        df = df.sort_values("Date").reset_index(drop=True)
        for c in ["Open", "High", "Low", "Close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        _OHLCV_CACHE[kode] = df
        return df
    except Exception:
        return None

def simulate_trade(df_ohlcv, entry, tanggal_signal):
    # Mode Optimis (Cek High dulu baru Low)
    try:
        entry = float(entry)
        sig_dt = pd.Timestamp(tanggal_signal).normalize()
    except: return None, "SUSPENDED"
    if pd.isna(entry) or entry <= 0: return None, "SUSPENDED"

    m = df_ohlcv.index[df_ohlcv["Date"] == sig_dt].tolist()
    if m: sig_idx = m[0]
    else:
        v = df_ohlcv[df_ohlcv["Date"] >= sig_dt]
        if len(v) == 0: return None, "SUSPENDED"
        sig_idx = v.index[0]

    entry_idx = sig_idx + 1
    if entry_idx >= len(df_ohlcv): return None, "PENDING"

    sl_price = entry * (1 + SL_PCT)
    peak = entry
    end_idx = min(entry_idx + MAX_HOLD_DAYS, len(df_ohlcv))

    for i in range(entry_idx, end_idx):
        row = df_ohlcv.iloc[i]
        high = row["High"]
        low = row["Low"]
        if pd.isna(high) or pd.isna(low): continue

        if high > peak: peak = high
        trail_price = peak * (1 - TRAIL_PCT)
        
        if trail_price > entry and low <= trail_price:
            return (trail_price / entry - 1), "TRAIL"
        if low <= sl_price:
            return SL_PCT, "SL"

    last_close = float(df_ohlcv.iloc[end_idx - 1]["Close"])
    if pd.isna(last_close): return None, "SUSPENDED"
    return last_close / entry - 1, "HOLD"

def main():
    print("Memuat data panel...")
    panel = load_panel_from_gabungan()
    panel = clean_panel(panel)
    panel = build_features(panel)
    panel = detect_events(panel)
    
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel = panel[(panel["open"] > 0) & (panel["close"] > 0)].copy()
    panel = panel.sort_values(["kode", "date"]).reset_index(drop=True)

    g = panel.groupby("kode")
    if "rsi_14" not in panel.columns:
        delta = g["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        ag = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
        al = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
        rs = ag / al.replace(0, np.nan)
        panel["rsi_14"] = 100 - (100 / (1 + rs))

    panel["open_T1"] = g["open"].shift(-1)
    panel["date_T1"] = g["date"].shift(-1)
    
    # --- RULE 3 ---
    mask_rule3 = (
        (panel["ret_1d"] > 0.10) & 
        (panel["ret_5d"] > 0.20) & 
        (panel["rsi_14"] > 50)
    ).fillna(False)
    
    # --- SET TANGGAL UNTUK BULAN LALU (OKTOBER) ---
    last_date = pd.Timestamp(panel["date"].max())
    bulan_lalu_end = last_date.replace(day=1) - pd.Timedelta(days=1)
    bulan_lalu_start = bulan_lalu_end.replace(day=1)
    
    sub_bulan = panel[(panel["date"] >= bulan_lalu_start) & (panel["date"] <= bulan_lalu_end)].copy()
    signals = sub_bulan[mask_rule3].dropna(subset=["open_T1"]).copy()
    
    print("\n" + "="*95)
    print(f"LAPORAN TRADING BULAN LALU ({bulan_lalu_start.strftime('%B %Y')}) - RULE 3 + ENTRY GAP UP > 2%")
    print("="*95)
    
    if signals.empty:
        print("Tidak ada sinyal Rule 3 di bulan ini.")
        return

    print("Memuat data OHLCV CSV...")
    df_ohlcv_map = {}
    for k in signals["kode"].unique():
        df_o = _load_ohlcv(k)
        if df_o is not None: df_ohlcv_map[k] = df_o

    trades = []
    
    for _, row in signals.iterrows():
        kode = row["kode"]
        if kode not in df_ohlcv_map: continue
        
        # Cek Gap Up > 2%
        gap_pct = (row["open_T1"] / row["close"]) - 1
        
        if gap_pct > 0.02:
            # Eksekusi Trade
            ret, status = simulate_trade(df_ohlcv_map[kode], row["open_T1"], row["date"])
            
            if status in ("TRAIL", "SL", "HOLD"):
                trades.append({
                    "Tanggal Sinyal": row["date"].strftime('%d %b'),
                    "Kode": kode,
                    "Close T": row["close"],
                    "Gap %": gap_pct * 100,
                    "Entry T+1": row["open_T1"],
                    "Status": status,
                    "P/L %": ret * 100
                })

    # Print Hasil
    if not trades:
        print("Tidak ada saham yang lolos syarat Gap Up > 2% bulan ini.")
    else:
        n_exec = len(trades)
        n_win = sum(1 for t in trades if t["P/L %"] > 0)
        tot_pl = sum(t["P/L %"] for t in trades)
        avg_pl = tot_pl / n_exec
        
        print(f"Total Sinyal Rule 3     : {len(signals)}")
        print(f"Lolos Gap Up > 2%       : {n_exec}")
        print(f"Tidak Lolos (Skip)      : {len(signals) - n_exec}")
        print("-" * 50)
        print(f"Win Rate                : {n_win} / {n_exec} ({n_win/n_exec*100:.1f}%)")
        print(f"Total P/L (Optimis)     : {tot_pl:+.2f}%")
        print(f"Avg P/L per Trade       : {avg_pl:+.2f}%")
        
        print("\n" + "="*95)
        print("DETAIL TRADE (Bisa Anda Cross-Check)")
        print("="*95)
        print(f"{'Tgl Sinyal':<12} | {'Kode':<7} | {'Close':>7} | {'Gap %':>7} | {'Entry':>7} | {'Status':<6} | {'P/L %'}")
        print("-" * 75)
        for t in trades:
            print(f"{t['Tanggal Sinyal']:<12} | {t['Kode']:<7} | {t['Close T']:>7.0f} | {t['Gap %']:>+6.1f}% | {t['Entry T+1']:>7.0f} | {t['Status']:<6} | {t['P/L %']:>+6.2f}%")

if __name__ == "__main__":
    main()