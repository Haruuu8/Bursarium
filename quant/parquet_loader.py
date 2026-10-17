import os
import pandas as pd
import streamlit as st

PARQUET_FILE = "ohlcv_idx_2026_all.parquet"

@st.cache_data(ttl=1800)
def load_parquet_safe():
    """Fungsi super aman untuk membaca parquet dan membuang kolom duplikat."""
    if not os.path.exists(PARQUET_FILE):
        return None
        
    df = pd.read_parquet(PARQUET_FILE)
    
    # 1. Lowercase semua kolom
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    # 2. Buang kolom duplikat
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    
    # 3. Rename ke standar
    col_map = {
        "date": "Date", "tanggal": "Date",
        "open": "Open", "high": "High", "low": "Low", "close": "Close",
        "volume": "Volume", "vol": "Volume",
        "kode": "Kode"
    }
    df = df.rename(columns=col_map)
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    
    # 4. Konversi Date
    if "Date" in df.columns:
        date_col = df["Date"]
        if isinstance(date_col, pd.DataFrame):
            date_col = date_col.iloc[:, 0]
        df["Date"] = pd.to_datetime(date_col, errors="coerce").dt.tz_localize(None)
        
    return df