"""
quant/supres_technical.py — Support/Resistance untuk Halaman Technical.

Berbeda dari supres.py (Watchlist) yang ketat swing_w5 saja:
- Multi-window swing (3, 5, 7)
- Donchian (20, 55, 100)
- Round numbers
- Previous week/month high/low
- Cluster semua level → skor berdasarkan confluence
- Selalu ada fallback (N-day high/low) supaya tidak kosong

Field output kompatibel dengan views/technical.py:
- supports[], resistances[]: {level, lower, upper, score, strength, 
                              n_touches, distance_pct, source, role,
                              last_touch, days_since_last, note}
"""

import math
import numpy as np
import pandas as pd
from quant.parquet_loader import load_parquet_safe


# ============================================================
# KONFIGURASI
# ============================================================
SWING_WINDOWS = [3, 5, 7]           # multi-window swing detection
DONCHIAN_PERIODS = [20, 55, 100]    # multi-period donchian
ROUND_STEPS = [50, 100, 500, 1000]  # round number levels

CLUSTER_TOLERANCE_ATR = 0.5         # toleransi cluster (0.5 ATR)
BAND_PCT = 0.005                    # lebar band zona (0.5% tiap sisi)

MAX_PER_SIDE = 5                    # maksimal 5 support & 5 resistance
MIN_SCORE = 2.0                     # minimal skor untuk tampil

FALLBACK_PERIODS = [20, 60, 120, 250]  # fallback N-day high/low


# ============================================================
# LOAD DATA
# ============================================================
def _load_ohlcv(kode):
    """Ambil OHLCV satu saham, normalisasi kolom alternatif."""
    df_all = load_parquet_safe()
    if df_all is None:
        return None
    if "Kode" not in df_all.columns:
        return None

    df_all["Kode"] = df_all["Kode"].astype(str).str.strip().str.upper()
    kode_clean = str(kode).strip().upper()
    df = df_all[df_all["Kode"] == kode_clean].copy()
    if df.empty:
        return None

    col_aliases = {
        "Open":  ["Open", "open", "openprice", "open_price", "OpenPrice"],
        "High":  ["High", "high", "highprice", "high_price", "HighPrice"],
        "Low":   ["Low", "low", "lowprice", "low_price", "LowPrice"],
        "Close": ["Close", "close", "closeprice", "close_price", "ClosePrice", "last"],
        "Date":  ["Date", "date", "tanggal", "Tanggal", "datetime"],
        "Volume": ["Volume", "volume", "vol", "Vol", "volumes"],
    }

    for target, candidates in col_aliases.items():
        if target in df.columns:
            if target == "Date":
                test = pd.to_datetime(df[target], errors="coerce")
            else:
                test = pd.to_numeric(df[target], errors="coerce")
            if test.notna().sum() > 0:
                continue
        found = False
        for alt in candidates:
            if alt == target or alt not in df.columns:
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
            if target == "Open" and "High" in df.columns and "Low" in df.columns:
                df["Open"] = (df["High"] + df["Low"]) / 2
                continue
            return None

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()
    if df.empty:
        return None

    for c in ["Open", "High", "Low", "Close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[(df["Open"] > 0) & (df["High"] > 0) & (df["Low"] > 0) & (df["Close"] > 0)]
    if df.empty:
        return None

    df = df.sort_values("Date").reset_index(drop=True)
    if len(df) < 30:
        return None

    if "Volume" not in df.columns:
        df["Volume"] = 0

    return df


# ============================================================
# ATR
# ============================================================
def _atr(df, n=14):
    prev = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev).abs(),
        (df["Low"] - prev).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(n, min_periods=max(1, n // 2)).mean()
    if atr.empty or pd.isna(atr.iloc[-1]):
        return float(df["Close"].iloc[-1]) * 0.02
    return float(atr.iloc[-1])


# ============================================================
# LEVEL DETECTORS — return list of (price, method, idx, side_hint)
# ============================================================
def _detect_swing_levels(df, window):
    """Swing high/low dari window tertentu."""
    levels = []
    highs = df["High"].values
    lows = df["Low"].values
    n = len(df)
    for i in range(window, n - window):
        left_h = highs[i - window:i]
        right_h = highs[i + 1:i + 1 + window]
        left_l = lows[i - window:i]
        right_l = lows[i + 1:i + 1 + window]
        if len(left_l) < window or len(right_l) < window:
            continue

        # Swing low
        if lows[i] > 0 and lows[i] < left_l.min() and lows[i] < right_l.min():
            levels.append({
                "price": float(lows[i]),
                "method": f"swing_w{window}_low",
                "idx": i,
                "side_hint": "support",
            })
        # Swing high
        if highs[i] > 0 and highs[i] > left_h.max() and highs[i] > right_h.max():
            levels.append({
                "price": float(highs[i]),
                "method": f"swing_w{window}_high",
                "idx": i,
                "side_hint": "resistance",
            })
    return levels


def _detect_donchian(df, period):
    """Donchian high/low (N-bar high & low)."""
    levels = []
    if len(df) < period:
        return levels

    tail_low = df["Low"].tail(period)
    tail_high = df["High"].tail(period)
    lo = float(tail_low.min())
    hi = float(tail_high.max())
    lo_idx = int(tail_low.idxmin())
    hi_idx = int(tail_high.idxmax())

    if lo > 0:
        levels.append({
            "price": lo,
            "method": f"donchian_{period}_low",
            "idx": lo_idx,
            "side_hint": "support",
        })
    if hi > 0:
        levels.append({
            "price": hi,
            "method": f"donchian_{period}_high",
            "idx": hi_idx,
            "side_hint": "resistance",
        })
    return levels


def _detect_round_numbers(df, current):
    """Round number levels di sekitar harga."""
    levels = []
    for step in ROUND_STEPS:
        if current < step:
            continue
        base = math.floor(current / step) * step
        # 2 round di bawah, 2 round di atas
        for k in [-2, -1, 1, 2]:
            r = base + k * step
            if r <= 0:
                continue
            levels.append({
                "price": float(r),
                "method": f"round_{step}",
                "idx": len(df) - 1,
                "side_hint": "support" if r < current else "resistance",
            })
    return levels


def _detect_prev_week_month(df):
    """Previous week high/low & previous month high/low."""
    levels = []
    if len(df) < 12:
        return levels

    last_date = df["Date"].iloc[-1]
    days_since_monday = last_date.weekday()
    cur_week_start = last_date - pd.Timedelta(days=days_since_monday)
    prev_week_start = cur_week_start - pd.Timedelta(days=7)
    prev_week_end = cur_week_start - pd.Timedelta(days=1)

    # Prev week high/low
    mask = (df["Date"] >= prev_week_start) & (df["Date"] <= prev_week_end)
    prev_week = df[mask]
    if len(prev_week) >= 2:
        lo = float(prev_week["Low"].min())
        hi = float(prev_week["High"].max())
        lo_idx = int(prev_week["Low"].idxmin())
        hi_idx = int(prev_week["High"].idxmax())
        if lo > 0:
            levels.append({"price": lo, "method": "prev_week_low", "idx": lo_idx, "side_hint": "support"})
        if hi > 0:
            levels.append({"price": hi, "method": "prev_week_high", "idx": hi_idx, "side_hint": "resistance"})

    # Prev month high/low
    cur_month_start = last_date.replace(day=1)
    prev_month_end = cur_month_start - pd.Timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    mask2 = (df["Date"] >= prev_month_start) & (df["Date"] <= prev_month_end)
    prev_month = df[mask2]
    if len(prev_month) >= 5:
        lo = float(prev_month["Low"].min())
        hi = float(prev_month["High"].max())
        lo_idx = int(prev_month["Low"].idxmin())
        hi_idx = int(prev_month["High"].idxmax())
        if lo > 0:
            levels.append({"price": lo, "method": "prev_month_low", "idx": lo_idx, "side_hint": "support"})
        if hi > 0:
            levels.append({"price": hi, "method": "prev_month_high", "idx": hi_idx, "side_hint": "resistance"})

    return levels


# ============================================================
# CLUSTERING — kelompokkan level yang berdekatan
# ============================================================
def _cluster_levels(levels, tolerance):
    """Cluster levels yang berdekatan. Return list of clusters."""
    if not levels:
        return []

    sorted_levels = sorted(levels, key=lambda x: x["price"])
    clusters = []
    current = [sorted_levels[0]]

    for lv in sorted_levels[1:]:
        if abs(lv["price"] - current[-1]["price"]) <= tolerance:
            current.append(lv)
        else:
            clusters.append(current)
            current = [lv]
    clusters.append(current)
    return clusters


def _score_cluster(cluster, current, atr, df):
    """
    Beri skor cluster berdasarkan:
    - Berapa banyak metode yang konfirmasi level (~sama)
    - Berapa banyak touch di level ini (historical)
    - Recency (semakin recent, makin tinggi)
    - Round number bonus
    """
    prices = [c["price"] for c in cluster]
    methods = set(c["method"].split("_")[0] for c in cluster)
    n_methods = len(methods)
    n_levels = len(cluster)

    level = float(np.median(prices))
    if level <= 0:
        return None

    # === Source dari semua metode ===
    sources = sorted(set(c["method"] for c in cluster))

    # === Hitung berapa kali level ini di-touch di data historis ===
    # Touch = harga high/low dalam toleransi 0.5 * atr dari level
    touch_tol = 0.5 * atr
    highs = df["High"].values
    lows = df["Low"].values
    touch_count = 0
    last_touch_idx = 0
    for i in range(len(df)):
        if lows[i] <= level + touch_tol and highs[i] >= level - touch_tol:
            touch_count += 1
            last_touch_idx = i

    if touch_count == 0:
        touch_count = n_levels
        last_touch_idx = max(c["idx"] for c in cluster)

    days_since = (df["Date"].iloc[-1] - df["Date"].iloc[last_touch_idx]).days

    # === Skor ===
    score = 0.0
    # Konfirmasi multi-metode (weight besar)
    score += n_methods * 1.2
    # Touches (semakin sering, makin kuat)
    if touch_count >= 5: score += 4
    elif touch_count >= 3: score += 3
    elif touch_count >= 2: score += 2
    else: score += 1
    # Recency (baru disentuh = lebih relevan)
    if days_since < 10: score += 2.0
    elif days_since < 30: score += 1.5
    elif days_since < 90: score += 1.0
    elif days_since < 180: score += 0.5
    # Round number
    if level > 0:
        for step in [1000, 500, 100]:
            nearest = round(level / step) * step
            if abs(level - nearest) / level < 0.005:
                score += 0.5
                break
    # Sanity cap
    score = min(score, 10.0)

    if score >= 7.0:
        strength = "STRONG"
    elif score >= 4.5:
        strength = "MODERATE"
    else:
        strength = "WEAK"

    side = "support" if level < current else ("resistance" if level > current else "neutral")

    # Band zona
    band = level * BAND_PCT
    return {
        "level": round(level, 2),
        "lower": round(level - band, 2),
        "upper": round(level + band, 2),
        "type": side,
        "original_type": side,
        "role": side,  # compat dengan technical.py (support/resistance)
        "flip": False,
        "is_elite": False,
        "width_pct": round((2 * band) / level * 100, 2),
        "n_touches": touch_count,
        "score": round(score, 2),
        "strength": strength,
        "source": " + ".join(methods),
        "sources": sources,
        "n_sources": n_methods,
        "backtest_wr": 0,
        "last_touch": df["Date"].iloc[last_touch_idx],
        "days_since_last": days_since,
        "distance_pct": round((level / current - 1) * 100, 2),
        "note": f"{n_methods} metode · {touch_count} touch",
    }


# ============================================================
# FALLBACK — N-day high/low
# ============================================================
def _fallback_levels(df, current, atr):
    """Kalau tidak ada level setelah clustering, pakai N-day high/low."""
    out = []
    for period in FALLBACK_PERIODS:
        if len(df) < period:
            continue
        lo = float(df["Low"].tail(period).min())
        hi = float(df["High"].tail(period).max())
        lo_idx = int(df["Low"].tail(period).idxmin())
        hi_idx = int(df["High"].tail(period).idxmax())

        if 0 < lo < current:
            band = lo * BAND_PCT
            out.append({
                "level": round(lo, 2),
                "lower": round(lo - band, 2),
                "upper": round(lo + band, 2),
                "type": "support",
                "original_type": "support",
                "role": "support",
                "flip": False,
                "is_elite": False,
                "width_pct": round((2 * band) / lo * 100, 2),
                "n_touches": 1,
                "score": round(5.0 - period / 200, 2),
                "strength": "MODERATE",
                "source": f"fallback_{period}d",
                "sources": [f"fallback_{period}d"],
                "n_sources": 1,
                "backtest_wr": 0,
                "last_touch": df["Date"].iloc[lo_idx],
                "days_since_last": (df["Date"].iloc[-1] - df["Date"].iloc[lo_idx]).days,
                "distance_pct": round((lo / current - 1) * 100, 2),
                "note": f"{period}-day low (fallback)",
            })

        if hi > current:
            band = hi * BAND_PCT
            out.append({
                "level": round(hi, 2),
                "lower": round(hi - band, 2),
                "upper": round(hi + band, 2),
                "type": "resistance",
                "original_type": "resistance",
                "role": "resistance",
                "flip": False,
                "is_elite": False,
                "width_pct": round((2 * band) / hi * 100, 2),
                "n_touches": 1,
                "score": round(5.0 - period / 200, 2),
                "strength": "MODERATE",
                "source": f"fallback_{period}d",
                "sources": [f"fallback_{period}d"],
                "n_sources": 1,
                "backtest_wr": 0,
                "last_touch": df["Date"].iloc[hi_idx],
                "days_since_last": (df["Date"].iloc[-1] - df["Date"].iloc[hi_idx]).days,
                "distance_pct": round((hi / current - 1) * 100, 2),
                "note": f"{period}-day high (fallback)",
            })
    return out


# ============================================================
# MAIN API
# ============================================================
def get_support_resistance(kode, timeframe="daily", **kwargs):
    """
    Analisa S/R komprehensif untuk halaman Technical.
    
    Returns dict dengan:
    - kode, timeframe, current_price, atr, tolerance, n_bars
    - supports[]: list zona support (max 5)
    - resistances[]: list zona resistance (max 5)
    - metadata: methods_used, n_raw_levels, n_clusters
    """
    try:
        return _impl(kode, timeframe)
    except Exception as e:
        print(f"[supres_technical] gagal {kode}: {e}")
        return None


def _impl(kode, timeframe):
    df = _load_ohlcv(kode)
    if df is None or len(df) < 30:
        return None

    current = float(df["Close"].iloc[-1])
    if current <= 0 or pd.isna(current):
        return None

    atr = _atr(df, 14)
    tolerance = max(atr * CLUSTER_TOLERANCE_ATR, current * 0.005)

    # === STEP 1: Collect semua level dari berbagai metode ===
    raw_levels = []

    # Multi-window swing
    for w in SWING_WINDOWS:
        raw_levels.extend(_detect_swing_levels(df, w))

    # Multi-period donchian
    for p in DONCHIAN_PERIODS:
        raw_levels.extend(_detect_donchian(df, p))

    # Round numbers
    raw_levels.extend(_detect_round_numbers(df, current))

    # Prev week/month H/L
    raw_levels.extend(_detect_prev_week_month(df))

    n_raw = len(raw_levels)

    # === STEP 2: Filter jarak dulu (jangan terlalu jauh dari harga) ===
    max_dist = current * 0.40  # max 40% dari harga sekarang
    raw_levels = [
        lv for lv in raw_levels
        if lv["price"] > 0 and abs(lv["price"] - current) <= max_dist
    ]

    # === STEP 3: Cluster levels yang berdekatan ===
    clusters = _cluster_levels(raw_levels, tolerance)
    n_clusters = len(clusters)

    # === STEP 4: Score tiap cluster ===
    scored = []
    for cluster in clusters:
        z = _score_cluster(cluster, current, atr, df)
        if z and z["score"] >= MIN_SCORE:
            scored.append(z)

    # === STEP 5: Split support vs resistance ===
    supports = [z for z in scored if z["level"] < current]
    resistances = [z for z in scored if z["level"] > current]

    # Sort by score desc, ambil top N
    supports.sort(key=lambda z: (-z["score"], -z["level"]))
    resistances.sort(key=lambda z: (-z["score"], z["level"]))
    supports = supports[:MAX_PER_SIDE]
    resistances = resistances[:MAX_PER_SIDE]

    # Sort final by distance ke harga (dekat dulu di display)
    supports.sort(key=lambda z: -z["level"])
    resistances.sort(key=lambda z: z["level"])

    # === STEP 6: Fallback kalau kosong ===
    if not supports or not resistances:
        fallbacks = _fallback_levels(df, current, atr)
        fb_sup = [z for z in fallbacks if z["type"] == "support"]
        fb_res = [z for z in fallbacks if z["type"] == "resistance"]

        if not supports:
            # Sort: yang terdekat ke harga dulu, maksimal MAX_PER_SIDE
            fb_sup.sort(key=lambda z: -z["level"])
            supports = fb_sup[:MAX_PER_SIDE]
        if not resistances:
            fb_res.sort(key=lambda z: z["level"])
            resistances = fb_res[:MAX_PER_SIDE]

    return {
        "kode": kode,
        "timeframe": timeframe,
        "current_price": current,
        "atr": atr,
        "tolerance": round(tolerance, 2),
        "n_bars": len(df),
        "scales": {"swing_windows": SWING_WINDOWS, "donchian": DONCHIAN_PERIODS},
        "supports": supports,
        "resistances": resistances,
        "metadata": {
            "n_raw_levels": n_raw,
            "n_clusters": n_clusters,
            "n_support": len(supports),
            "n_resistance": len(resistances),
            "methods": SWING_WINDOWS + DONCHIAN_PERIODS,
        },
    }