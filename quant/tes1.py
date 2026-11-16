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

OHLCV_DIR = "data_ohlcv_idx"
GAP_MIN_PCT = 0.02
GAP_MAX_PCT = 0.20
ATR_MIN_PCT = 0.03
SL_PCT = -0.03
TRAIL_PCT = 0.005

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

def main():
    print("Memuat data panel...")
    panel = load_panel_from_gabungan()
    panel = clean_panel(panel)
    panel = build_features(panel)
    panel = detect_events(panel)
    
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel = panel[(panel["open"] > 0) & (panel["close"] > 0)].copy()
    panel = panel.sort_values(["kode", "date"]).reset_index(drop=True)

    if "atr_pct" not in panel.columns:
        g = panel.groupby("kode", group_keys=False)
        prev_c = g["close"].shift(1)
        tr = np.maximum(panel["high"] - panel["low"], np.maximum((panel["high"] - prev_c).abs(), (panel["low"] - prev_c).abs()))
        atr = tr.groupby(panel["kode"]).transform(lambda s: s.rolling(14).mean())
        panel["atr_pct"] = atr / panel["close"]

    g = panel.groupby("kode")
    panel["open_T1"] = g["open"].shift(-1)
    panel["close_T1"] = g["close"].shift(-1)
    panel["high_T1"] = g["high"].shift(-1)
    panel["low_T1"] = g["low"].shift(-1)
    
    # --- RULE HAKA PAGI (UNION ABC) ---
    m_a = (panel["ret_1d"] > 0.10) & (panel["ret_5d"] > 0.10) & (panel["px_vs_sma20"] > 0.10)
    m_b = (panel["ret_1d"] > 0.10) & (panel["ret_5d"] > 0.15) & (panel["range"] > 0.08) & (panel["vol_z_20"] > 1.5)
    m_c = (panel["ret_3d"] > 0.12) & (panel["px_vs_sma20"] > 0.15)
    m_q = (panel["atr_pct"] > ATR_MIN_PCT)
    
    mask_haka = (m_a | m_b | m_c) & m_q
    
    # Syarat Gap Up 2-20%
    panel["gap_pct"] = (panel["open_T1"] / panel["close"]) - 1
    mask_gap = (panel["gap_pct"] >= GAP_MIN_PCT) & (panel["gap_pct"] <= GAP_MAX_PCT)
    
    signals = panel[mask_haka & mask_gap].dropna(subset=["open_T1", "close_T1", "high_T1", "low_T1"]).copy()
    
    print(f"\nTotal Sinyal Haka Pagi + Gap Up (2-20%): {len(signals):,}")

    print("Memuat data OHLCV CSV...")
    df_ohlcv_map = {}
    for k in signals["kode"].unique():
        df_o = _load_ohlcv(k)
        if df_o is not None: df_ohlcv_map[k] = df_o

    print("Menghitung simulasi Hybrid (TP + Hold to Close)...")
    
    results = {
        "Trailing 0.5%": [],
        "TP 3% / Close": [],
        "TP 5% / Close": [],
        "TP 10% / Close": [],
        "TP 5% / Close + SL 3%": []
    }
    
    for _, row in signals.iterrows():
        kode = row["kode"]
        if kode not in df_ohlcv_map: continue
        
        entry = row["open_T1"]
        high = row["high_T1"]
        low = row["low_T1"]
        close = row["close_T1"]
        
        if pd.isna(entry) or entry <= 0: continue
        
        # --- 1. Trailing 0.5% (Optimis) ---
        df_o = df_ohlcv_map[kode]
        sig_dt = pd.Timestamp(row["date"]).normalize()
        m = df_o.index[df_o["Date"] == sig_dt].tolist()
        if m:
            sig_idx = m[0]
            entry_idx = sig_idx + 1
            if entry_idx < len(df_o):
                peak = entry
                sl_price = entry * (1 + SL_PCT)
                ret = (close / entry) - 1 # default
                for i in range(entry_idx, min(entry_idx + 30, len(df_o))):
                    h = df_o.iloc[i]["High"]
                    l = df_o.iloc[i]["Low"]
                    if pd.isna(h) or pd.isna(l): continue
                    if h > peak: peak = h
                    trail = peak * (1 - TRAIL_PCT)
                    if trail > entry and l <= trail:
                        ret = (trail / entry) - 1
                        break
                    if l <= sl_price:
                        ret = SL_PCT
                        break
                results["Trailing 0.5%"].append(ret)

        # --- 2. Hybrid: TP / Close ---
        # Skenario: Jika High menyentuh target, jual di target. Jika tidak, jual di Close.
        # Tanpa SL (dibiarkan turun sampai close).
        
        def get_tp_close_ret(tp_pct):
            target_price = entry * (1 + tp_pct)
            if high >= target_price:
                return tp_pct
            else:
                return (close / entry) - 1

        results["TP 3% / Close"].append(get_tp_close_ret(0.03))
        results["TP 5% / Close"].append(get_tp_close_ret(0.05))
        results["TP 10% / Close"].append(get_tp_close_ret(0.10))

        # --- 3. Hybrid + SL 3% (Konservatif: Cek SL dulu baru TP) ---
        # Jika Low menyentuh SL, jual di SL. Jika tidak, cek TP, jika tidak, jual di Close.
        tp_5 = entry * 1.05
        sl_3 = entry * 0.97
        if low <= sl_3:
            results["TP 5% / Close + SL 3%"].append(SL_PCT)
        elif high >= tp_5:
            results["TP 5% / Close + SL 3%"].append(0.05)
        else:
            results["TP 5% / Close + SL 3%"].append((close / entry) - 1)

    # --- CETAK HASIL ---
    def print_metrics(name, returns):
        n = len(returns)
        if n == 0: return
        wr = sum(1 for r in returns if r > 0) / n * 100
        avg = np.mean(returns) * 100
        tot = np.sum(returns) * 100
        max_win = np.max(returns) * 100 if n > 0 else 0
        max_loss = np.min(returns) * 100 if n > 0 else 0
        print(f"{name:<30} | {n:>5} | {wr:>6.1f}% | {avg:>+6.2f}% | {tot:>+9.2f}% | {max_win:>+6.1f}% | {max_loss:>+6.1f}%")

    print("\n" + "="*105)
    print("PERBANDINGAN METODE EXIT: TRAILING vs HYBRID (TP / HOLD TO CLOSE)")
    print("="*105)
    print(f"{'Metode Exit':<30} | {'N':<5} | {'WinRate':<7} | {'Avg P/L':<7} | {'Total P/L':<10} | {'Max Win':<7} | {'Max Loss'}")
    print("-" * 105)
    for key, val in results.items():
        print_metrics(key, val)
    print("="*105)
    print("Catatan:")
    print("- 'TP X% / Close' = Jika High menyentuh +X%, jual di +X%. Jika gagal, tahan sampai Close (Tanpa SL).")
    print("- 'TP 5% / Close + SL 3%' = Jika Low menyentuh -3%, cutloss. Jika tidak, cek TP 5%. Jika gagal, tahan sampai Close.")

if __name__ == "__main__":
    main()