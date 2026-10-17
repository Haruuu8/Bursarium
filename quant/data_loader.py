"""
Loader data mentah dari hasil scraper — UNIVERSAL.
Handle 2 format:
  - Format baru (6-7 kolom): Kode, Date, Open, High, Low, Close, Volume
  - Format lama (30 kolom):  StockCode, OpenPrice, Previous, Value, Frequency, dll
Auto-fill kolom yang hilang agar data_cleaner tidak error.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from .config import (
    RAW_CSV_GABUNGAN, RAW_CSV_PER_SAHAM, DAFTAR_SAHAM_CSV, IHSG_CSV,
)


def _norm(c):
    """Normalisasi nama kolom: lowercase, hilangkan titik/spasi/underscore."""
    return str(c).lower().strip().rstrip(".").replace(" ", "").replace("_", "")


COL_MAP = {
    "date": "date", "tanggal": "date",
    "stockcode": "kode", "kode": "kode", "ticker": "kode", "code": "kode",
    "openprice": "open", "open": "open",
    "high": "high", "highprice": "high",
    "low": "low", "lowprice": "low",
    "close": "close", "closeprice": "close",
    "previous": "prev_close", "prevclose": "prev_close",
    "volume": "volume", "vol": "volume",
    "value": "value",
    "frequency": "frequency",
    "foreignbuy": "foreign_buy",
    "foreignsell": "foreign_sell",
    "listedshares": "listed_shares",
    "tradebleshares": "tradeable_shares",
}


def _rename_columns(df):
    ren = {}
    for c in df.columns:
        nc = _norm(c)
        if nc in COL_MAP:
            target = COL_MAP[nc]
            if c != target:
                ren[c] = target
    if ren:
        df = df.rename(columns=ren)
    # Buang kolom duplikat
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    return df


def load_panel_from_gabungan() -> pd.DataFrame:
    if not RAW_CSV_GABUNGAN.exists():
        raise FileNotFoundError(
            f"File gabungan tidak ditemukan: {RAW_CSV_GABUNGAN}\n"
            "Jalankan ticker.py atau gabung.py dulu."
        )

    from pathlib import Path
    _pq = Path(str(RAW_CSV_GABUNGAN).replace(".csv", ".parquet"))
    if _pq.exists():
        df = pd.read_parquet(_pq)
    else:
        df = pd.read_csv(RAW_CSV_GABUNGAN)
    df = _rename_columns(df)

    # Kolom wajib (OHLCV)
    required = ["date", "kode", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Kolom wajib tidak ditemukan: {missing}\n"
            f"Kolom yang ada: {df.columns.tolist()}"
        )

    # Konversi Date — handle format campuran
    df["date"] = pd.to_datetime(
        df["date"], format="mixed", errors="coerce", utc=True
    ).dt.tz_localize(None)
    df = df.dropna(subset=["date"])

    # Kode upper
    df["kode"] = df["kode"].astype(str).str.upper().str.strip()

    # Urutkan (penting untuk shift)
    df = df.sort_values(["kode", "date"]).reset_index(drop=True)

    # === AUTO-FILL kolom yang hilang ===

    # prev_close: dari close.shift(1) per kode
    if "prev_close" not in df.columns:
        df["prev_close"] = df.groupby("kode")["close"].shift(1)

    # value: estimasi = close × volume (proxy)
    if "value" not in df.columns:
        df["value"] = df["close"] * df["volume"]

    # frequency: tidak bisa dihitung → NaN
    if "frequency" not in df.columns:
        df["frequency"] = np.nan

    # foreign_buy / foreign_sell: tidak ada → NaN
    for col in ["foreign_buy", "foreign_sell"]:
        if col not in df.columns:
            df[col] = np.nan

    # Konversi kolom numerik
    for col in df.columns:
        if col in ("date", "kode"):
            continue
        if df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_ihsg() -> pd.DataFrame:
    if not IHSG_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(IHSG_CSV)
    df = _rename_columns(df)

    # Rename khusus IHSG
    ren = {}
    for c in df.columns:
        cl = _norm(c)
        if cl in ("close", "closeprice", "ihsgclose", "ihsg"):
            ren[c] = "ihsg_close"
        elif cl in ("open", "openprice"):
            ren[c] = "ihsg_open"
        elif cl in ("high", "highprice"):
            ren[c] = "ihsg_high"
        elif cl in ("low", "lowprice"):
            ren[c] = "ihsg_low"
        elif cl == "volume":
            ren[c] = "ihsg_volume"
    df = df.rename(columns=ren)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(
            df["date"], format="mixed", errors="coerce", utc=True
        ).dt.tz_localize(None)
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    return df
