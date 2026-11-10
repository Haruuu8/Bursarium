import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from quant.parquet_loader import load_parquet_safe

def debug():
    print("Mengecek isi Parquet...")
    d = load_parquet_safe()
    
    if d is None:
        print("Data kosong!")
        return

    print("Kolom yang ada di data:", d.columns.tolist())
    print(f"Total saham awal: {d['Kode'].nunique()}")
    print(f"Total baris awal: {len(d):,}\n")

    # 1. Cek Konversi Tanggal
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce").dt.normalize()
    d_date = d.dropna(subset=["Date"])
    print(f"Setelah filter Tanggal (Date valid): {d_date['Kode'].nunique()} saham")

    # 2. Cek Konversi Numerik (Open, Close, Volume, dll)
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in d_date.columns:
            d_date[c] = pd.to_numeric(d_date[c], errors="coerce")

    d_num = d_date.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    print(f"Setelah dropna (OHLCV valid): {d_num['Kode'].nunique()} saham\n")

    # 3. Cek Siapa Saja yang Hilang
    kodes_awal = set(d['Kode'].unique())
    kodes_akhir = set(d_num['Kode'].unique())
    hilang = list(kodes_awal - kodes_akhir)
    
    if hilang:
        print(f"ADA {len(hilang)} SAHAM YANG HILANG DI FILTER.")
        print(f"Contoh saham yang hilang: {hilang[:10]}")
        
        contoh = hilang[0]
        print(f"\n--- Isi Data Mentah untuk Saham {contoh} ---")
        print(d[d['Kode'] == contoh].tail(3).to_string())
    else:
        print("Tidak ada saham yang hilang di filter dropna.")

if __name__ == "__main__":
    debug()