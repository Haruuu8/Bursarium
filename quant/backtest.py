import os
import sys
import logging
import pandas as pd
import numpy as np
import warnings
from multiprocessing import Pool

# Menyembunyikan warning Streamlit agar terminal bersih
logging.getLogger('streamlit').setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Menggunakan loader bawaan Anda
from quant.parquet_loader import load_parquet_safe

GLOBAL_DF = None

def load_all_data():
    print("Memuat data dari Parquet...")
    # Menggunakan loader bawaan agar tidak salah path
    df = load_parquet_safe()
    if df is None or df.empty:
        print("❌ Gagal memuat data. Pastikan data parquet tersedia.")
        sys.exit()
        
    df = df.dropna(subset=["Date"]).sort_values(["Kode", "Date"]).reset_index(drop=True)
    return df

def calculate_rsi(close_series, period):
    delta = close_series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def simulate_trades(df, signal_col, sl_pct, tp_pct):
    trades = []
    in_position = False
    
    lows = df['Low'].values
    highs = df['High'].values
    closes = df['Close'].values
    signals = signal_col.values
    
    for i in range(50, len(df)):
        if not in_position and signals[i]:
            in_position = True
            entry_price = closes[i]
            sl_price = entry_price * (1 - sl_pct)
            tp_price = entry_price * (1 + tp_pct)
            
        elif in_position:
            if lows[i] <= sl_price:
                trades.append(-sl_pct * 100)
                in_position = False
            elif highs[i] >= tp_price:
                trades.append(tp_pct * 100)
                in_position = False
                
    return trades

def process_chunk(kode):
    df_stock = GLOBAL_DF[GLOBAL_DF["Kode"] == kode].copy()
    if len(df_stock) < 100: return []

    closes = df_stock['Close']
    volumes = df_stock['Volume']
    
    sma_periods = [10, 20, 50, 100, 200]
    smas = {p: closes.rolling(p).mean() for p in sma_periods}
    
    rsi_periods = [7, 14, 21]
    rsis = {p: calculate_rsi(closes, p) for p in rsi_periods}
    
    high_periods = [5, 10, 20, 50, 100]
    highs_n = {p: df_stock['High'].rolling(p).max().shift(1) for p in high_periods}
    
    vol_ma = volumes.rolling(20).mean()

    sl_list = [0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040, 0.045, 0.050] 
    tp_list = [0.020, 0.025, 0.030, 0.035, 0.040, 0.045, 0.050, 0.060, 0.070, 0.080, 0.090, 0.100, 0.120, 0.150, 0.180, 0.200, 0.250, 0.300, 0.350, 0.400]
    
    rsi_levels = [20, 25, 30, 35, 40, 45, 50]
    
    local_results = []

    # --- A. STRATEGI BUY ON SUPPORT ---
    for sma_p in sma_periods:
        for rsi_p in rsi_periods:
            for rsi_lv in rsi_levels:
                signal = (closes < smas[sma_p]) & (rsis[rsi_p] < rsi_lv)
                for sl in sl_list:
                    for tp in tp_list:
                        pnls = simulate_trades(df_stock, signal, sl, tp)
                        if pnls:
                            wr = (sum(1 for x in pnls if x > 0) / len(pnls)) * 100
                            local_results.append({
                                "Strategy": "SUPPORT", "P1": sma_p, "P2": f"RSI{rsi_p}<{rsi_lv}",
                                "SL": sl * 100, "TP": tp * 100,
                                "Trades": len(pnls), "WR": wr, "PnL": sum(pnls)
                            })

    # --- B. STRATEGI BREAKOUT + VOLUME ---
    for high_p in high_periods:
        signal = (closes > highs_n[high_p]) & (volumes > (vol_ma * 1.5))
        for sl in sl_list:
            for tp in tp_list:
                pnls = simulate_trades(df_stock, signal, sl, tp)
                if pnls:
                    wr = (sum(1 for x in pnls if x > 0) / len(pnls)) * 100
                    local_results.append({
                        "Strategy": "BREAKOUT_VOL", "P1": high_p, "P2": "Vol>1.5x",
                        "SL": sl * 100, "TP": tp * 100,
                        "Trades": len(pnls), "WR": wr, "PnL": sum(pnls)
                    })
                    
    return local_results

def init_worker(df):
    global GLOBAL_DF
    GLOBAL_DF = df

def main():
    print("=== 🚀 THE ULTIMATE HOLY GRAIL SEARCH (20 WORKERS) ===")
    df_all = load_all_data()
    
    tickers = df_all["Kode"].unique()
    print(f"Menguji pada SELURUH {len(tickers)} saham. Ini akan memakan waktu beberapa menit.")
    
    results = []
    with Pool(processes=20, initializer=init_worker, initargs=(df_all,)) as pool:
        for i, res in enumerate(pool.imap_unordered(process_chunk, tickers, chunksize=1), 1):
            results.extend(res)
            if i % 10 == 0 or i == len(tickers):
                print(f"\rProgress: {i}/{len(tickers)} saham selesai.", end="", flush=True)

    print("\n\n✅ Selesai! Mengolah JUTAAN hasil simulasi...")
    df_res = pd.DataFrame(results)

    agg = df_res.groupby(["Strategy", "P1", "P2", "SL", "TP"]).agg(
        Total_Trades=("Trades", "sum"),
        Avg_WR=("WR", "mean"),
        Total_PnL=("PnL", "sum")
    ).reset_index()

    # FILTER: Profit Positif, WR di atas 50%, dan minimal 100 trade
    valid = agg[(agg["Total_PnL"] > 0) & (agg["Avg_WR"] >= 50.0) & (agg["Total_Trades"] >= 100)].copy()
    
    if valid.empty:
        print("❌ Tidak ada strategi yang mencapai WR >= 50% sekaligus Profit > 0.")
        print("Menampilkan 10 strategi dengan WR tertinggi (Profit Positif)...")
        valid = agg[(agg["Total_PnL"] > 0) & (agg["Total_Trades"] >= 100)].sort_values("Avg_WR", ascending=False).head(10)
    else:
        valid["Holy_Grail_Score"] = (valid["Avg_WR"] * valid["Total_PnL"]) / 100
        valid = valid.sort_values("Holy_Grail_Score", ascending=False)

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    print("\n" + "="*100)
    print("👑 TOP 20 STRATEGI TERBAIK (WR > 50% & PROFIT POSITIF)")
    print("="*100)
    top = valid.head(20)
    print(top.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

if __name__ == "__main__":
    main()