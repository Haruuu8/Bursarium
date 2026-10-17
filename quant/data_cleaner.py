"""
Bersihkan panel: validasi, filter universe, tandai kualitas data.
"""

import pandas as pd
import numpy as np
from .config import MIN_HARI_TRADING, MIN_HARGA, MIN_RATA_VOLUME


def validate_basic(df: pd.DataFrame) -> pd.DataFrame:
    """Validasi dasar: harga positif, high >= low, volume >= 0."""
    n0 = len(df)

    # High harus >= Low
    mask_valid = (
        (df["high"] >= df["low"]) &
        (df["high"] >= df["close"]) &
        (df["low"] <= df["close"]) &
        (df["close"] > 0) &
        (df["volume"] >= 0)
    )
    df = df[mask_valid].copy()

    # Buang duplikat (kode, date)
    df = df.drop_duplicates(subset=["kode", "date"], keep="last")

    print(f"  validate_basic: {n0} → {len(df)} baris ({n0 - len(df)} dibuang)")
    return df


def add_derived_basic(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan kolom dasar: return harian, range, dll."""
    df = df.sort_values(["kode", "date"]).reset_index(drop=True)

    # Return close-to-close
    df["ret_1d"] = df.groupby("kode")["close"].pct_change()

    # Range harian
    df["range"] = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
    df["body"] = (df["close"] - df["open"]).abs() / df["close"].replace(0, np.nan)

    # Gap
    df["gap"] = (df["open"] - df["prev_close"]) / df["prev_close"].replace(0, np.nan)

    # Value per transaction (rata-rata ukuran transaksi)
    df["avg_trade_size"] = df["value"] / df["frequency"].replace(0, np.nan)

    # Foreign net
    if "foreign_buy" in df.columns and "foreign_sell" in df.columns:
        df["foreign_net"] = df["foreign_buy"] - df["foreign_sell"]
        # Normalisasi ke value untuk comparable across stocks
        df["foreign_net_pct"] = df["foreign_net"] / df["value"].replace(0, np.nan)

    return df


def filter_universe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter saham yang layak dianalisis:
    - Cukup hari trading
    - Harga minimum
    - Volume rata-rata minimum
    """
    stats = df.groupby("kode").agg(
        n_hari=("date", "count"),
        harga_median=("close", "median"),
        volume_mean=("volume", "mean"),
    )
    layak = stats[
        (stats["n_hari"] >= MIN_HARI_TRADING) &
        (stats["harga_median"] >= MIN_HARGA) &
        (stats["volume_mean"] >= MIN_RATA_VOLUME)
    ].index

    n_saham_awal = df["kode"].nunique()
    df = df[df["kode"].isin(layak)].copy()
    n_saham_akhir = df["kode"].nunique()

    print(f"  filter_universe: {n_saham_awal} → {n_saham_akhir} saham "
          f"({n_saham_awal - n_saham_akhir} dibuang)")

    # Simpan statistik untuk audit
    stats.to_csv("quant/output/universe_stats.csv")

    return df


def clean_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline pembersihan lengkap."""
    print("Membersihkan panel:")
    df = validate_basic(df)
    df = add_derived_basic(df)
    df = filter_universe(df)
    return df


if __name__ == "__main__":
    from .data_loader import load_panel_from_gabungan
    panel = load_panel_from_gabungan()
    clean = clean_panel(panel)
    print(f"\nHasil akhir: {clean.shape}")
    print(f"Kolom: {list(clean.columns)}")