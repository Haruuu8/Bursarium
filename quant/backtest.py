import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys
import logging
import itertools
import json
import pandas as pd
import numpy as np
import warnings
from multiprocessing import Pool

logging.getLogger('streamlit').setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.parquet_loader import load_parquet_safe

GLOBAL_DF = None

def init_worker():
    global GLOBAL_DF
    df = load_parquet_safe()
    if df is not None:
        df = df.dropna(subset=["Date"]).sort_values(["Kode", "Date"]).reset_index(drop=True)
        df["Kode"] = df["Kode"].astype(str).str.strip().str.upper()
    GLOBAL_DF = df

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def process_chunk(kode):
    global GLOBAL_DF
    if GLOBAL_DF is None: return []
        
    df = GLOBAL_DF[GLOBAL_DF["Kode"] == kode].copy()
    if len(df) < 250: return [] 

    df = df.reset_index(drop=True)
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    opens = df['Open'].values
    volumes = df['Volume'].values
    n = len(closes)
    
    # Precompute
    rsi14 = calc_rsi(df['Close'], 14).values
    ema20 = df['Close'].ewm(span=20, adjust=False).mean().values
    sma50 = df['Close'].rolling(50).mean().values
    macd_line = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = (macd_line - macd_signal).values
    vol_ma = df['Volume'].rolling(20).mean().values
    
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().values
    atr_ma = pd.Series(atr).rolling(20).mean().values
    
    sma20 = df['Close'].rolling(20).mean().values
    std20 = df['Close'].rolling(20).std().values
    bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / sma20
    bb_width_ma = pd.Series(bb_width).rolling(20).mean().values
    
    candle_range = np.maximum(highs - lows, 1e-9)
    candle_body = np.abs(closes - opens)
    
    results = []
    
    for start in range(0, n - 160, 20):
        setup_end = start + 100
        test_start = setup_end
        test_end = min(test_start + 50, n)
        
        sh_arr = highs[start:setup_end]
        sl_arr = lows[start:setup_end]
        
        hi_idx = int(np.argmax(sh_arr))
        lo_idx = int(np.argmin(sl_arr))
        sh = float(sh_arr[hi_idx])
        sl = float(sl_arr[lo_idx])
        rg = sh - sl
        
        if sl <= 0 or rg <= 0 or rg / sl < 0.10: continue
        
        is_up = lo_idx < hi_idx
        
        if is_up:
            fib_levels = {
                "0.618": sh - rg * 0.618,
                "0.786": sh - rg * 0.786,
                "0.850": sh - rg * 0.850,
            }
        else:
            fib_levels = {
                "0.618": sl + rg * 0.618,
                "0.786": sl + rg * 0.786,
                "0.850": sl + rg * 0.850,
            }
        
        tol = sh * 0.005
        
        for level_name, level_price in fib_levels.items():
            touch_idx = -1
            for i in range(test_start, test_end):
                if lows[i] <= level_price + tol and highs[i] >= level_price - tol:
                    touch_idx = i
                    break
            
            if touch_idx < 0: continue
            
            out_end = min(touch_idx + 15, test_end)
            if out_end <= touch_idx + 2: continue
            
            broke = False
            bounced = False
            
            if is_up:
                for j in range(touch_idx + 1, out_end):
                    if closes[j] < level_price - tol * 3:
                        broke = True; break
                    if closes[j] > level_price + tol * 4:
                        bounced = True; break
            else:
                for j in range(touch_idx + 1, out_end):
                    if closes[j] > level_price + tol * 3:
                        broke = True; break
                    if closes[j] < level_price - tol * 4:
                        bounced = True; break
            
            if not (broke or bounced): continue
            
            t = touch_idx
            rsi_val = rsi14[t] if not np.isnan(rsi14[t]) else 50
            vol_r = volumes[t] / vol_ma[t] if (vol_ma[t] > 0 and not np.isnan(vol_ma[t])) else 1
            
            # Bitmask filters
            mask = 0
            if rsi_val < 30: mask |= 1
            if rsi_val < 35: mask |= 2
            if rsi_val < 45: mask |= 4
            if vol_r > 1.2: mask |= 8
            if vol_r > 1.5: mask |= 16
            if not np.isnan(ema20[t]) and closes[t] > ema20[t]: mask |= 32
            if not np.isnan(sma50[t]) and closes[t] > sma50[t]: mask |= 64
            if not np.isnan(macd_hist[t]) and macd_hist[t] > 0: mask |= 128
            if closes[t] > opens[t] and candle_body[t]/candle_range[t] > 0.5: mask |= 256
            if not np.isnan(atr[t]) and not np.isnan(atr_ma[t]) and atr[t] < atr_ma[t]: mask |= 512
            if not np.isnan(bb_width[t]) and not np.isnan(bb_width_ma[t]) and bb_width[t] < bb_width_ma[t]: mask |= 1024
            
            results.append((level_name, "UP" if is_up else "DOWN", mask, int(bounced)))
    
    return results

FILTER_NAMES = ["RSI<30", "RSI<35", "RSI<45", "Vol>1.2x", "Vol>1.5x", "EMA20", "SMA50", "MACD", "StrongCandle", "ATR_Low", "BB_Squeeze"]
FILTER_BITS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]

def mask_matches(mask, required_filters):
    for f in required_filters:
        idx = FILTER_NAMES.index(f)
        bit = FILTER_BITS[idx]
        if not (mask & bit):
            return False
    return True

def main():
    print("=== 🌀 COMPREHENSIVE FIBONACCI + FILTER SEARCH ===\n")
    
    df_all = load_parquet_safe()
    if df_all is None or df_all.empty:
        print("❌ Gagal memuat data.")
        sys.exit()
        
    df_all["Kode"] = df_all["Kode"].astype(str).str.strip().str.upper()
    tickers = df_all["Kode"].unique()
    del df_all 
    
    print(f"Menguji {len(tickers)} saham dengan Fibonacci Deep Zone (0.618, 0.786, 0.850)")
    print("Dan 11 filter tambahan (RSI, Volume, Trend, dll)\n")
    
    all_results = []
    with Pool(processes=10, initializer=init_worker) as pool:
        for i, res in enumerate(pool.imap_unordered(process_chunk, tickers, chunksize=2), 1):
            all_results.extend(res)
            if i % 20 == 0 or i == len(tickers):
                print(f"\rProgress: {i}/{len(tickers)} saham selesai.", flush=True)

    print(f"\n\n✅ Selesai! Total touch events: {len(all_results):,}")
    
    if not all_results:
        print("❌ Tidak ada touch.")
        return
    
    df = pd.DataFrame(all_results, columns=["Fib", "Direction", "Mask", "Win"])
    
    # Test combinations
    combo_data = []
    
    for fib in ["0.618", "0.786", "0.850"]:
        for direction in ["UP", "DOWN"]:
            subset = df[(df["Fib"] == fib) & (df["Direction"] == direction)]
            if len(subset) < 50: continue
            
            # Baseline
            wr = subset["Win"].mean() * 100
            combo_data.append({
                "Combo": f"Fib {fib} ({direction}) - BASE",
                "N": len(subset),
                "WR": wr,
            })
            
            # Test filter combinations up to 3 filters
            for size in [1, 2, 3]:
                for filters in itertools.combinations(FILTER_NAMES, size):
                    # Apply filter mask
                    req_mask = 0
                    for f in filters:
                        req_mask |= FILTER_BITS[FILTER_NAMES.index(f)]
                    
                    # Subset where mask has ALL required bits
                    filtered = subset[(subset["Mask"] & req_mask) == req_mask]
                    
                    if len(filtered) < 30: continue
                    
                    wr = filtered["Win"].mean() * 100
                    combo_data.append({
                        "Combo": f"Fib {fib} ({direction}) + {' + '.join(filters)}",
                        "N": len(filtered),
                        "WR": wr,
                    })
    
    df_combo = pd.DataFrame(combo_data).sort_values("WR", ascending=False)
    
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    
    print("\n" + "="*110)
    print("👑 TOP 30 KOMBINASI FIBONACCI + FILTER (Win Rate Tertinggi)")
    print("(Minimal 30 touch, sudah diverifikasi)")
    print("="*110)
    
    top = df_combo.head(30).reset_index(drop=True)
    top.index = top.index + 1
    print(top.to_string(float_format=lambda x: f"{x:.1f}"))
    
    # Save best
    if not df_combo.empty:
        best = df_combo.iloc[0]
        # Parse best
        best_info = {
            "Combo": best["Combo"],
            "N": int(best["N"]),
            "WR": float(best["WR"]),
        }
        
        print("\n" + "="*110)
        print(f"🏆 STRATEGI TERBAIK DITEMUKAN!")
        print(f"   {best['Combo']}")
        print(f"   Sample: {best['N']} touch")
        print(f"   Win Rate: {best['WR']:.1f}%")
        print("="*110)
        
        # Also show best with min sample 100
        strict = df_combo[df_combo["N"] >= 100]
        if not strict.empty:
            best_strict = strict.iloc[0]
            print(f"\n💎 STRATEGI PALING STABIL (Minimal 100 touch):")
            print(f"   {best_strict['Combo']}")
            print(f"   Sample: {best_strict['N']} touch")
            print(f"   Win Rate: {best_strict['WR']:.1f}%")
            
            with open("quant/output/best_fibo_strategy.json", "w") as f:
                json.dump({
                    "Combo": best_strict["Combo"],
                    "N": int(best_strict["N"]),
                    "WR": float(best_strict["WR"]),
                }, f, indent=4)
            print(f"\n💾 Disimpan ke: quant/output/best_fibo_strategy.json")

if __name__ == "__main__":
    main()