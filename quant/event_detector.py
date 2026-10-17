"""
Deteksi event top gainer (bagian 2 ROLE.txt).
Semua event didefinisikan pada hari T berdasarkan data hari T.
Label forward-looking (MFE, future return) hanya untuk evaluasi, bukan fitur.
"""

import numpy as np
import pandas as pd
from .config import (
    DAILY_RANK_TOP_PCT, EXTREME_RETURN_THRESHOLDS,
    INTRADAY_HIGH_THRESHOLDS,
    MULTIDAY_HORIZONS, MULTIDAY_THRESHOLDS, MFE_HORIZONS,
)


# ============================================================
# A. DAILY RANK
# ============================================================
def add_daily_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Rank return harian cross-sectional per tanggal."""
    df = df.copy()
    df["ret_1d_rank_pct"] = df.groupby("date")["ret_1d"].rank(
        pct=True, ascending=False)

    for pct in DAILY_RANK_TOP_PCT:
        col = f"is_top_{int(pct*100)}pct"
        df[col] = (df["ret_1d_rank_pct"] <= pct).astype(int)

    return df


# ============================================================
# B. EXTREME RETURN (CLOSE-BASED)
# ============================================================
def add_extreme_return_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag return close-based >= threshold."""
    df = df.copy()
    for thr in EXTREME_RETURN_THRESHOLDS:
        col = f"is_up_{int(thr*100)}pct"
        df[col] = (df["ret_1d"] >= thr).astype(int)
    return df


# ============================================================
# B2. INTRADAY HIGH-BASED (MENYENTUH LEVEL)
# ============================================================
def add_intraday_high_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag event berdasarkan intraday high vs prev_close.
    Ini yang paling relevan untuk trading: apakah saham menyentuh +X%
    kapan pun dalam hari itu, terlepas dari close.
    """
    df = df.copy()
    # Ret dari prev_close ke high hari ini
    df["ret_to_high"] = df["high"] / df["prev_close"] - 1

    # Ret dari prev_close ke open (untuk cek gap)
    df["ret_to_open"] = df["open"] / df["prev_close"] - 1

    # Berapa % harga jatuh dari high ke close (indikasi distribusi)
    df["close_to_high_ratio"] = df["close"] / df["high"]

    for thr in INTRADAY_HIGH_THRESHOLDS:
        col = f"is_touch_{int(thr*100)}pct"
        df[col] = (df["ret_to_high"] >= thr).astype(int)

    return df


# ============================================================
# C. MULTI-DAY RETURN (FORWARD-LOOKING, HANYA UNTUK LABEL)
# ============================================================
def add_multiday_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Future returns (forward-looking, hanya untuk label)."""
    df = df.copy()
    for n in MULTIDAY_HORIZONS:
        df[f"fwd_ret_{n}d"] = (
            df.groupby("kode")["close"].shift(-n) / df["close"] - 1
        )
        for thr in MULTIDAY_THRESHOLDS:
            col = f"is_fwd_up_{int(thr*100)}pct_{n}d"
            df[col] = (df[f"fwd_ret_{n}d"] >= thr).astype(int)
    return df


# ============================================================
# D. MAXIMUM FAVORABLE / ADVERSE EXCURSION
# ============================================================
def add_mfe_mae(df: pd.DataFrame) -> pd.DataFrame:
    """
    MFE & MAE dalam horizon n hari ke depan, berdasarkan harga yang
    dapat dieksekusi. MFE diukur pakai 'high', MAE pakai 'low'.
    Forward-looking, hanya untuk label.
    """
    df = df.copy()
    for n in MFE_HORIZONS:
        # Rolling ke depan: untuk setiap baris, ambil max high dari
        # n baris berikutnya
        future_high = df.groupby("kode")["high"].transform(
            lambda s: s[::-1].rolling(n, min_periods=1).max()[::-1].shift(-1))
        future_low = df.groupby("kode")["low"].transform(
            lambda s: s[::-1].rolling(n, min_periods=1).min()[::-1].shift(-1))

        df[f"mfe_{n}d"] = future_high / df["close"] - 1
        df[f"mae_{n}d"] = future_low / df["close"] - 1

    return df


# ============================================================
# E. TARGET LABELS (ROLE.txt bagian 6)
# ============================================================
def add_target_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Target prediksi dari ROLE.txt bagian 6.
    Semua label di sini forward-looking, TIDAK boleh jadi fitur.
    """
    df = df.copy()

    # Target A: Top 5% besok
    df["target_A"] = df.groupby("date")["fwd_ret_1d"].transform(
        lambda s: (s.rank(pct=True, ascending=False) <= 0.05).astype(int))

    # Target B: naik >= 5% dalam 3 hari
    df["target_B"] = (df["fwd_ret_3d"] >= 0.05).astype(int)

    # Target C: naik >= 10% dalam 5 hari
    df["target_C"] = (df["fwd_ret_5d"] >= 0.10).astype(int)

    # Target D: naik >= 15% dalam 10 hari
    df["target_D"] = (df["fwd_ret_10d"] >= 0.15).astype(int)

    # Target E: MFE >= 10% sebelum MAE <= -5% dalam 10 hari
    df["target_E"] = ((df["mfe_10d"] >= 0.10) & (df["mae_10d"] > -0.05)).astype(int)

    return df


# ============================================================
# PIPELINE
# ============================================================
def detect_events(df: pd.DataFrame) -> pd.DataFrame:
    print("Mendeteksi event...")
    df = add_daily_rank(df)
    df = add_extreme_return_flags(df)
    df = add_intraday_high_flags(df)
    df = add_multiday_returns(df)
    df = add_mfe_mae(df)
    df = add_target_labels(df)

    # Ringkasan
    print("\nFrekuensi event:")
    event_cols = [
        "is_top_1pct", "is_top_5pct", "is_top_10pct",
        "is_up_5pct", "is_up_10pct", "is_up_15pct", "is_up_20pct",
        "is_touch_5pct", "is_touch_10pct", "is_touch_15pct", "is_touch_20pct",
        "target_A", "target_B", "target_C", "target_D", "target_E",
    ]
    for col in event_cols:
        if col in df.columns:
            n = df[col].sum()
            pct = n / len(df) * 100
            print(f"  {col:<18}: {n:>7,} ({pct:.3f}%)")

    return df


if __name__ == "__main__":
    from .data_loader import load_panel_from_gabungan
    from .data_cleaner import clean_panel

    panel = load_panel_from_gabungan()
    panel = clean_panel(panel)
    events = detect_events(panel)
    print(f"\nTotal baris: {len(events):,}")
    print(f"Total kolom: {events.shape[1]}")