"""
quant/supres.py — Support/Resistance (WR TERTINGGI, dengan Fix Lengkap).

Metode (dari backtest 30M+ touch di 900 saham):
- SUPPORT    : Swing Low W=5 (91.1% WR mantul, 1.29M touch)
              Fallback: Donchian-55 low (81.9% WR)
- RESISTANCE : Dual role:
                * Breakout trigger: Swing High W=5 (87.3% breakout)
                * Breakout fallback: Donchian-55 high (65.9% breakout)
                * Reversal warning: Round-100 (64.1% mantul)

FIX:
- Normalisasi kolom (Open/openprice, High/highprice, dll)
- Filter MAX_DISTANCE_PCT untuk semua resistance
- Filter MIN_DISTANCE_PCT untuk semua level
- Cek duplikat antar metode

Field per zona:
- role: 'buy_limit' | 'stop_buy' | 'avoid'
- source: metode yang deteksi
- backtest_wr: WR historis dari backtest
"""

import math
import numpy as np
import pandas as pd
from quant.parquet_loader import load_parquet_safe


# ============================================================
# KONFIGURASI
# ============================================================
SWING_WINDOW = 5        # window swing pivot (5 = 91.1% WR)
DONCHIAN_PERIOD = 55    # fallback 55-bar high/low (81.9% WR support)
ROUND_STEP = 100        # round number step (64.1% WR resistance)
MIN_DISTANCE_PCT = 0.5  # minimal jarak level dari harga (0.5%)
MAX_DISTANCE_PCT = 15.0 # maksimal jarak level dari harga (15%)
BAND_PCT = 0.005        # lebar band zona (0.5% tiap sisi)


# ============================================================
# SAFE DIVISION
# ============================================================
def _safe_div(a, b, default=0.0):
    """Pembagian aman: handle 0, NaN, inf, None."""
    try:
        if b is None or b == 0:
            return default
        r = a / b
        if isinstance(r, float) and (np.isnan(r) or np.isinf(r)):
            return default
        return r
    except (TypeError, ZeroDivisionError, ValueError):
        return default


# ============================================================
# LOAD DATA (dengan normalisasi kolom)
# ============================================================
def _load_ohlcv(kode):
    """
    Ambil OHLCV satu saham dari parquet — dengan normalisasi kolom.

    Handle kasus:
    - Kolom 'Open' NaN tapi 'openprice' valid
    - Kolom 'High' vs 'high' vs 'highprice'
    - Kolom 'Date' vs 'date' vs 'tanggal'
    - Harga 0 atau NaN di baris tertentu
    """
    df_all = load_parquet_safe()
    if df_all is None:
        print("[supres] parquet is None")
        return None

    if "Kode" not in df_all.columns:
        print(f"[supres] no Kode column, have: {list(df_all.columns)}")
        return None

    # Normalize kode
    df_all["Kode"] = df_all["Kode"].astype(str).str.strip().str.upper()
    kode = str(kode).strip().upper()
    df = df_all[df_all["Kode"] == kode].copy()

    if df.empty:
        print(f"[supres] {kode} not found in parquet")
        return None

    # ============================================================
    # NORMALISASI KOLOM — handle nama alternatif
    # ============================================================
    col_aliases = {
        "Open":   ["Open", "open", "openprice", "open_price", "OpenPrice"],
        "High":   ["High", "high", "highprice", "high_price", "HighPrice"],
        "Low":    ["Low", "low", "lowprice", "low_price", "LowPrice"],
        "Close":  ["Close", "close", "closeprice", "close_price", "ClosePrice", "last"],
        "Date":   ["Date", "date", "tanggal", "Tanggal", "datetime"],
        "Volume": ["Volume", "volume", "vol", "Vol", "volumes"],
    }

    for target, candidates in col_aliases.items():
        # Skip kalau kolom target sudah ada & valid
        if target in df.columns:
            test = (
                pd.to_numeric(df[target], errors="coerce")
                if target != "Date"
                else pd.to_datetime(df[target], errors="coerce")
            )
            if test.notna().sum() > 0:
                continue

        # Cari kolom alternatif yang valid
        found = False
        for alt in candidates:
            if alt == target:
                continue
            if alt not in df.columns:
                continue
            if target == "Date":
                test = pd.to_datetime(df[alt], errors="coerce")
                if test.notna().sum() > 0:
                    df["Date"] = test
                    found = True
                    break
            else:
                test = pd.to_numeric(df[alt], errors="coerce")
                if test.notna().sum() > 0 and (test.dropna() > 0).any():
                    df[target] = test
                    found = True
                    break

        if not found and target in ["Open", "High", "Low", "Close"]:
            # Fallback: kalau Open tidak ada tapi High & Low ada, pakai (H+L)/2
            if (
                target == "Open"
                and "High" in df.columns
                and "Low" in df.columns
            ):
                df["Open"] = (df["High"] + df["Low"]) / 2
                continue
            print(f"[supres] {kode}: no valid '{target}' column")
            return None

    # Parse Date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["Date"])
    if len(df) == 0:
        print(f"[supres] {kode}: {before} rows, all Date invalid")
        return None

    # Cast numerik untuk OHLC
    for c in ["Open", "High", "Low", "Close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Filter NaN & harga <= 0
    before = len(df)
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[
        (df["Open"] > 0)
        & (df["High"] > 0)
        & (df["Low"] > 0)
        & (df["Close"] > 0)
    ]

    if len(df) == 0:
        print(f"[supres] {kode}: {before} rows, 0 valid after OHLC filter")
        return None

    # Sort by date
    df = df.sort_values("Date").reset_index(drop=True)

    if len(df) < 60:
        print(f"[supres] {kode}: only {len(df)} valid rows (need 60+)")
        return None

    return df


# ============================================================
# ATR
# ============================================================
def _atr(df, n=14):
    """Average True Range."""
    prev = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev).abs(),
            (df["Low"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(n, min_periods=n).mean()
    if atr.empty or pd.isna(atr.iloc[-1]):
        return 0.0
    return float(atr.iloc[-1])


# ============================================================
# SWING DETECTION
# ============================================================
def _find_swings(df, window=5):
    """
    Cari semua swing high & swing low.
    Swing = titik yang lebih tinggi/rendah dari `window` bar di kiri & kanannya.

    Return: (swing_lows, swing_highs) — masing-masing list of dict
            {idx: int, price: float}
    """
    highs = df["High"].values
    lows = df["Low"].values
    n = len(df)

    swing_lows = []
    swing_highs = []

    for i in range(window, n - window):
        left_h = highs[i - window : i]
        right_h = highs[i + 1 : i + 1 + window]
        left_l = lows[i - window : i]
        right_l = lows[i + 1 : i + 1 + window]

        if len(left_h) < window or len(right_h) < window:
            continue
        if len(left_l) < window or len(right_l) < window:
            continue

        # Swing low: low[i] < semua low di kiri & kanan
        if lows[i] > 0 and lows[i] < left_l.min() and lows[i] < right_l.min():
            swing_lows.append({"idx": i, "price": float(lows[i])})

        # Swing high: high[i] > semua high di kiri & kanan
        if highs[i] > 0 and highs[i] > left_h.max() and highs[i] > right_h.max():
            swing_highs.append({"idx": i, "price": float(highs[i])})

    return swing_lows, swing_highs


# ============================================================
# ZONE HELPER
# ============================================================
def _band(price, pct=BAND_PCT):
    """Buat band di sekitar level (default 0.5% tiap sisi)."""
    b = price * pct
    return round(price - b, 2), round(price + b, 2)


def _make_zone(
    level,
    side,
    role,
    strategy,
    score,
    strength,
    source,
    backtest_wr,
    df,
    last_idx,
    note,
    distance_pct=0.0,
):
    """
    Buat dict zona standar.

    Args:
        level        : harga level zona
        side         : "support" atau "resistance"
        role         : "buy_limit" | "stop_buy" | "avoid"
        strategy     : "limit_buy" | "stop_buy" | "avoid"
        score        : 0-10
        strength     : "WEAK" | "MODERATE" | "STRONG"
        source       : nama metode (e.g., "swing_w5")
        backtest_wr  : WR historis dari backtest
        df           : dataframe untuk ambil last_touch
        last_idx     : index bar touch terakhir
        note         : keterangan untuk UI
        distance_pct : % jarak dari harga sekarang
    """
    lower, upper = _band(level)
    days_since = (df["Date"].iloc[-1] - df["Date"].iloc[last_idx]).days

    return {
        "level": round(level, 2),
        "lower": lower,
        "upper": upper,
        "type": side,
        "role": role,
        "strategy": strategy,
        "original_type": side,
        "flip": False,
        "is_elite": False,
        "width_pct": 1.0,
        "n_touches": 1,
        "last_touch": df["Date"].iloc[last_idx],
        "days_since_last": days_since,
        "score": round(score, 2),
        "strength": strength,
        "bounces": 0,
        "source": source,
        "backtest_wr": backtest_wr,
        "distance_pct": round(distance_pct, 2),
        "note": note,
    }


# ============================================================
# SUPPORT ZONES
# ============================================================
def _build_supports(df, current, swing_lows):
    """
    Bangun list support dari swing_w5 + fallback donchian_55.

    Support = untuk BUY LIMIT (harga turun menyentuh level → beli).
    """
    supports = []

    # ----------------------------------------
    # PRIORITY 1: Swing Low W=5 (91.1% WR)
    # ----------------------------------------
    candidates = [
        s
        for s in swing_lows
        if s["price"] < current
        and MIN_DISTANCE_PCT
        <= (current - s["price"]) / current * 100
        <= MAX_DISTANCE_PCT
    ]
    # Sort: terdekat dulu (harga paling tinggi di bawah current)
    candidates.sort(key=lambda s: -s["price"])
    candidates = candidates[:2]  # ambil maksimal 2 terdekat

    for i, s in enumerate(candidates):
        level = s["price"]
        dist = (level / current - 1) * 100
        score = 8.5 - i * 0.5  # terdekat skor 8.5, berikutnya 8.0
        strength = "STRONG" if i == 0 else "MODERATE"

        supports.append(
            _make_zone(
                level=level,
                side="support",
                role="buy_limit",
                strategy="limit_buy",
                score=score,
                strength=strength,
                source=f"swing_w{SWING_WINDOW}",
                backtest_wr=91.1,
                df=df,
                last_idx=s["idx"],
                note=f"Swing low W={SWING_WINDOW} (WR 91.1% mantul)",
                distance_pct=dist,
            )
        )

    # ----------------------------------------
    # FALLBACK: Donchian-55 low (81.9% WR)
    # ----------------------------------------
    if len(supports) < 2 and len(df) >= DONCHIAN_PERIOD:
        tail = df["Low"].tail(DONCHIAN_PERIOD)
        lo55 = float(tail.min())
        lo_idx = int(tail.idxmin())

        # Cek duplikat
        existing_levels = [s["level"] for s in supports]
        is_duplicate = any(
            abs(lo55 - lv) / lv * 100 < 0.3 for lv in existing_levels
        )

        # Cek jarak
        dist_pct_check = (lo55 / current - 1) * 100 if lo55 < current else 0

        if (
            lo55 > 0
            and lo55 < current
            and not is_duplicate
            and MIN_DISTANCE_PCT <= abs(dist_pct_check) <= MAX_DISTANCE_PCT
        ):
            supports.append(
                _make_zone(
                    level=lo55,
                    side="support",
                    role="buy_limit",
                    strategy="limit_buy",
                    score=8.0,
                    strength="STRONG",
                    source="donchian_55",
                    backtest_wr=81.9,
                    df=df,
                    last_idx=lo_idx,
                    note="55-bar low (WR 81.9% mantul)",
                    distance_pct=dist_pct_check,
                )
            )

    # Sort: level tertinggi dulu (terdekat dari harga)
    supports.sort(key=lambda z: -z["level"])
    return supports


# ============================================================
# RESISTANCE ZONES
# ============================================================
def _build_resistances(df, current, swing_highs):
    """
    Bangun list resistance dengan DUAL ROLE:
    1. breakout_trigger (swing_high / donchian high) → STOP BUY
    2. reversal_warning (round_100) → AVOID BUY
    """
    resistances = []

    # ----------------------------------------
    # A1: Swing High W=5 (87.3% breakout rate)
    # ----------------------------------------
    swing_candidates = [
        s
        for s in swing_highs
        if s["price"] > current
        and MIN_DISTANCE_PCT
        <= (s["price"] - current) / current * 100
        <= MAX_DISTANCE_PCT
    ]
    swing_candidates.sort(key=lambda s: s["price"])  # terdekat dulu
    swing_candidates = swing_candidates[:1]  # ambil 1 terdekat saja

    for s in swing_candidates:
        level = s["price"]
        dist = (level / current - 1) * 100

        resistances.append(
            _make_zone(
                level=level,
                side="resistance",
                role="breakout_trigger",
                strategy="stop_buy",
                score=8.0,
                strength="STRONG",
                source=f"swing_w{SWING_WINDOW}",
                backtest_wr=87.3,
                df=df,
                last_idx=s["idx"],
                note=f"Swing high W={SWING_WINDOW} (87.3% breakout)",
                distance_pct=dist,
            )
        )

    # ----------------------------------------
    # A2: Donchian-55 high (65.9% breakout rate)
    # 🔧 FIX: filter MAX_DISTANCE_PCT — skip kalau terlalu jauh
    # ----------------------------------------
    if len(df) >= DONCHIAN_PERIOD:
        tail = df["High"].tail(DONCHIAN_PERIOD)
        hi55 = float(tail.max())
        hi_idx = int(tail.idxmax())

        existing_levels = [z["level"] for z in resistances]
        is_duplicate = any(
            abs(hi55 - lv) / lv * 100 < 0.3 for lv in existing_levels
        )

        # 🔧 FIX: hitung jarak dan filter
        dist_pct_check = (hi55 / current - 1) * 100 if hi55 > current else 0

        if (
            hi55 > current
            and not is_duplicate
            and MIN_DISTANCE_PCT <= dist_pct_check <= MAX_DISTANCE_PCT
        ):
            resistances.append(
                _make_zone(
                    level=hi55,
                    side="resistance",
                    role="breakout_trigger",
                    strategy="stop_buy",
                    score=7.0,
                    strength="STRONG",
                    source="donchian_55",
                    backtest_wr=65.9,
                    df=df,
                    last_idx=hi_idx,
                    note="55-bar high (65.9% breakout)",
                    distance_pct=dist_pct_check,
                )
            )

    # ----------------------------------------
    # B: Round-100 (64.1% reversal rate)
    # 🔧 FIX: filter MAX_DISTANCE_PCT juga
    # ----------------------------------------
    base = math.ceil(current / ROUND_STEP) * ROUND_STEP
    if base <= current:
        base += ROUND_STEP

    round_added = 0
    i = 0
    while round_added < 2 and i < 5:  # maksimal 5 iterasi, ambil 2 level valid
        r = base + i * ROUND_STEP
        dist = (r / current - 1) * 100

        # 🔧 FIX: hanya tambahkan kalau dalam range MIN-MAX
        if MIN_DISTANCE_PCT <= dist <= MAX_DISTANCE_PCT:
            resistances.append(
                _make_zone(
                    level=r,
                    side="resistance",
                    role="reversal_warning",
                    strategy="avoid",
                    score=6.0 - round_added * 0.5,
                    strength="MODERATE" if round_added == 0 else "WEAK",
                    source="round_100",
                    backtest_wr=64.1,
                    df=df,
                    last_idx=len(df) - 1,
                    note=f"Round {r:,.0f} (64.1% mantul — avoid buy)",
                    distance_pct=dist,
                )
            )
            round_added += 1

        i += 1

    # Sort: level terendah dulu (terdekat dari harga)
    resistances.sort(key=lambda z: z["level"])
    return resistances


# ============================================================
# MAIN API
# ============================================================
def get_support_resistance(kode, timeframe="daily", **kwargs):
    """
    Hitung support & resistance untuk satu saham.

    Returns:
        dict dengan key: kode, current_price, atr, tolerance,
                         n_bars, supports, resistances
        atau None kalau data tidak cukup / error.
    """
    try:
        return _impl(kode, timeframe)
    except Exception as e:
        print(f"[supres] gagal hitung {kode}: {e}")
        return None


def _impl(kode, timeframe):
    """Implementasi utama."""
    df = _load_ohlcv(kode)
    if df is None or len(df) < 60:
        return None

    current = float(df["Close"].iloc[-1])
    if current <= 0 or pd.isna(current):
        return None

    atr = _atr(df, 14)

    # Deteksi semua swing points
    swing_lows, swing_highs = _find_swings(df, window=SWING_WINDOW)

    # Bangun zona support & resistance
    supports = _build_supports(df, current, swing_lows)
    resistances = _build_resistances(df, current, swing_highs)

    return {
        "kode": kode,
        "timeframe": timeframe,
        "current_price": current,
        "atr": atr,
        "tolerance": round(max(atr * 0.5, current * 0.005), 2),
        "n_bars": len(df),
        "scales": {"simple": 2},
        "supports": supports,
        "resistances": resistances,
    }