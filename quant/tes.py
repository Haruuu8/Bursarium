# quant/backtest_valuasi.py
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARQUET_FILE = "ohlcv_idx_2026_all.parquet"

def load_price_data():
    print("Memuat data harga lokal (Parquet)...")
    df = pd.read_parquet(PARQUET_FILE)
    df["Kode"] = df["Kode"].astype(str).str.strip().str.upper()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["Date"])
    df.columns = [str(c).strip().lower() for c in df.columns]
    if 'openprice' in df.columns:
        df['open'] = df['open'].fillna(df['openprice'])
    df = df.rename(columns={"date": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume", "kode": "Kode"})
    
    # Ambil daftar saham unik, buang IHSG
    kodes = [k for k in df["Kode"].unique() if k not in ("IHSG", "JKSE", "^JKSE")]
    return df, kodes

def get_historical_fund_yf(kode, target_year):
    """Menarik data fundamental (EPS, BV, ROE, DER) dari tahun tertentu via yfinance"""
    try:
        t = yf.Ticker(f"{kode}.JK")
        
        # Ambil data income statement & balance sheet (tahunan)
        inc = t.income_stmt
        bs = t.balance_sheet
        
        if inc is None or bs is None or inc.empty or bs.empty:
            return None
            
        # Cari kolom tahun target (misal target_year = 2023)
        cols = [c for c in inc.columns if str(target_year) in str(c)]
        if not cols:
            return None
            
        col = cols[0]
        
        # EPS
        try:
            net_income = inc.loc["Net Income", col]
            shares = bs.loc["Ordinary Shares Number", col]
            if shares > 0:
                eps = net_income / shares
            else:
                eps = inc.loc["Basic EPS", col]
        except:
            return None

        # Book Value per Share
        try:
            equity = bs.loc["Stockholders Equity", col]
            shares = bs.loc["Ordinary Shares Number", col]
            if shares > 0:
                bv = equity / shares
            else:
                bv = 0
        except:
            bv = 0

        # ROE & DER
        try:
            roe = (net_income / equity) * 100
            total_liab = bs.loc["Total Liabilities Net Minority Interest", col]
            der = total_liab / equity
        except:
            roe = 0
            der = 99

        if eps > 0 and bv > 0 and 5.0 < roe < 50.0 and der < 2.0:
            return {"eps": eps, "bv": bv, "roe": roe, "der": der}
            
    except Exception:
        pass
    return None

def run_scenario(df_price, kodes, target_year, hold_years, label):
    print(f"\n{'='*70}")
    print(f"SKENARIO: {label}")
    print(f"Data Fundamental: Tahun {target_year} | Periode Hold: {hold_years} Tahun")
    print(f"{'='*70}")
    
    buy_date_str = f"{target_year}-12-31"
    sell_date_str = f"{target_year + hold_years}-12-31"
    
    # Cek IHSG
    ihsg = df_price[df_price["Kode"].isin(["IHSG", "JKSE"])].sort_values("Date")
    ihsg_buy = ihsg[ihsg["Date"] <= buy_date_str]["Close"].iloc[-1] if not ihsg[ihsg["Date"] <= buy_date_str].empty else 0
    ihsg_sell = ihsg[ihsg["Date"] <= sell_date_str]["Close"].iloc[-1] if not ihsg[ihsg["Date"] <= sell_date_str].empty else 0
    
    if ihsg_buy == 0 or ihsg_sell == 0:
        print("Data IHSG tidak mencukupi untuk periode ini.")
        return
        
    ihsg_ret = ((ihsg_sell / ihsg_buy) - 1) * 100
    print(f"Return IHSG ({hold_years} Tahun): {ihsg_ret:+.2f}%")

    winners = []
    losers = []
    
    # Batasi sampel agar tidak terlalu lama (maksimal 150 saham berkapitalisasi besar/menengah)
    # Kita urutkan kodes berdasarkan likuiditas atau alfabetis sebagai sampel
    sample_kodes = kodes[:150] 
    
    print(f"Menganalisa {len(sample_kodes)} saham...")
    
    for i, kode in enumerate(sample_kodes):
        df_stock = df_price[df_price["Kode"] == kode].sort_values("Date")
        if df_stock.empty: continue
        
        past_buy = df_stock[df_stock["Date"] <= buy_date_str]
        past_sell = df_stock[df_stock["Date"] <= sell_date_str]
        if past_buy.empty or past_sell.empty: continue
        
        price_buy = past_buy["Close"].iloc[-1]
        price_sell = past_sell["Close"].iloc[-1]
        
        if price_buy <= 0 or price_sell <= 0: continue
        
        # Ambil data fundamental historis
        fund = get_historical_fund_yf(kode, target_year)
        if not fund: continue
        
        eps = fund["eps"]
        bv = fund["bv"]
        
        # --- HITUNG FAIR VALUE (Sama seperti aplikasi Valuation Anda) ---
        # Graham: sqrt(22.5 * EPS * BV)
        fv_graham = np.sqrt(22.5 * eps * bv)
        # PE-based: EPS x Target PE 10 x Diskon 0.9
        fv_pe = eps * (10 * 0.9) 
        # PB-based: BV x Target PB 1.5 x Diskon 0.9
        fv_pb = bv * (1.5 * 0.9)
        
        fv_raw = (0.4 * fv_graham) + (0.3 * fv_pe) + (0.3 * fv_pb)
        fv = fv_raw * 0.85 # Margin of Safety 15%
        
        potential = ((fv - price_buy) / price_buy) * 100
        pe_buy = price_buy / eps
        
        # FILTER: Undervalued (Potential > 0) & PE Wajar (2 - 15)
        if potential > 0 and 2.0 < pe_buy < 15.0:
            # Buang data anomali
            if potential > 300: continue
            
            ret = ((price_sell / price_buy) - 1) * 100
            
            res = {
                "Kode": kode, "Buy": price_buy, "Sell": price_sell,
                "FV": round(fv, 0), "Potential": round(potential, 1),
                "ROE": round(fund["roe"], 1), "Return": round(ret, 1)
            }
            
            if ret > 0: winners.append(res)
            else: losers.append(res)

    total = len(winners) + len(losers)
    if total == 0:
        print("Tidak ada saham yang memenuhi kriteria Undervalued & Sehat.")
        return
        
    win_rate = (len(winners) / total) * 100
    avg_ret = np.mean([w["Return"] for w in winners] + [l["Return"] for l in losers])
    
    print(f"Saham Terpilih : {total}")
    print(f"Win Rate       : {win_rate:.1f}%")
    print(f"Avg Return     : {avg_ret:+.2f}%")
    print(f"Alpha vs IHSG  : {avg_ret - ihsg_ret:+.2f}%")
    
    print(f"\nTop 3 Cuan:")
    winners.sort(key=lambda x: x["Return"], reverse=True)
    for w in winners[:3]:
        print(f"  {w['Kode']:<5} | Ret: {w['Return']:+6.1f}% | Pot: {w['Potential']:+5.1f}% | ROE: {w['ROE']}%")

    print(f"\nTop 3 Buntung:")
    losers.sort(key=lambda x: x["Return"])
    for l in losers[:3]:
        print(f"  {l['Kode']:<5} | Ret: {l['Return']:+6.1f}% | Pot: {l['Potential']:+5.1f}% | ROE: {l['ROE']}%")

def main():
    df_price, kodes = load_price_data()
    
    # Jalankan 3 Skenario
    run_scenario(df_price, kodes, 2021, 3, "BULL MARKET (Beli 2021, Jual 2024)")
    run_scenario(df_price, kodes, 2022, 2, "SIDEWAYS (Beli 2022, Jual 2024)")
    run_scenario(df_price, kodes, 2023, 1, "BEAR MARKET (Beli 2023, Jual 2024)")

if __name__ == "__main__":
    main()