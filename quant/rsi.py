"""Modul RSI + filter saham hidup.

Dipakai oleh Watchlist, scanner, dan halaman Technical.
"""

import os
import numpy as np
import pandas as pd

OHLCV_DIR = "data_ohlcv_idx"


# ============================================================
# RSI
# ============================================================
def hitung_rsi(series, periode=14):
    """RSI dengan metode Wilder (EMA alpha=1/periode)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/periode, adjust=False,
                        min_periods=periode).mean()
    avg_loss = loss.ewm(alpha=1/periode, adjust=False,
                        min_periods=periode).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ============================================================
# FILTER SAHAM HIDUP
# ============================================================
def _cek_df_hidup(df, min_hari=10, min_vol_hari=10):
    """
    Cek DataFrame — False kalau saham flat/suspended/delisting.

    Kriteria "mati":
      - Harga flat total selama `min_hari` hari terakhir (nunique <= 1)
      - Volume rata-rata `min_vol_hari` hari terakhir <= 0
      - Data terlalu pendek (< min_hari + 20 bar)
    """
    if df is None or len(df) < min_hari + 20:
        return False

    # Cari kolom Close
    close_col = None
    for c in df.columns:
        if str(c).strip().lower() in ("close", "closeprice", "close_price"):
            close_col = c
            break
    if close_col is None:
        return False

    tail = pd.to_numeric(df[close_col], errors="coerce").tail(min_hari).dropna()
    if len(tail) < min_hari:
        return False
    if tail.nunique() <= 1:
        return False

    # Cek Volume
    vol_col = None
    for c in df.columns:
        if str(c).strip().lower() == "volume":
            vol_col = c
            break
    if vol_col is not None:
        vol = pd.to_numeric(df[vol_col], errors="coerce").tail(min_vol_hari).dropna()
        if len(vol) > 0 and vol.mean() <= 0:
            return False

    return True


def saham_hidup(kode, min_hari=10, min_vol_hari=10):
    """Return True kalau saham masih aktif bergerak."""
    path = os.path.join(OHLCV_DIR, f"{kode}.csv")
    if not os.path.exists(path):
        return False
    try:
        df = pd.read_csv(path)
        return _cek_df_hidup(df, min_hari, min_vol_hari)
    except Exception:
        return False


def filter_saham_hidup(daftar_kode, min_hari=10):
    """Filter list kode → hanya yang masih hidup."""
    return [k for k in daftar_kode if saham_hidup(k, min_hari=min_hari)]