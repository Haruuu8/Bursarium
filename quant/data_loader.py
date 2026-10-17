import os
import pandas as pd

PARQUET_FILE = "ohlcv_idx_2026_all.parquet"

def load_parquet_safe():
    """Fungsi super aman untuk membaca parquet dan membuang kolom duplikat."""
    if not os.path.exists(PARQUET_FILE):
        return None
        
    df = pd.read_parquet(PARQUET_FILE)
    
    # 1. Ubah semua nama kolom jadi huruf kecil
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    # 2. Buang kolom yang namanya persis sama
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    
    # 3. Ganti ke nama standar (Title Case)
    col_map = {
        "date": "Date", "tanggal": "Date",
        "open": "Open", "high": "High", "low": "Low", "close": "Close",
        "volume": "Volume", "vol": "Volume",
        "kode": "Kode"
    }
    df = df.rename(columns=col_map)
    
    # 4. Buang lagi jika ada yang dobel setelah di-rename
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    
    # 5. Konversi Date dengan super aman
    if "Date" in df.columns:
        date_col = df["Date"]
        if isinstance(date_col, pd.DataFrame):
            date_col = date_col.iloc[:, 0]
        df["Date"] = pd.to_datetime(date_col, errors="coerce").dt.tz_localize(None)
        
    return df