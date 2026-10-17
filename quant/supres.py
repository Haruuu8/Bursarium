"""
Support/Resistance v2 - Multi-Timeframe + Multi-Scale Pivot.
(Dimodifikasi untuk membaca dari file parquet)
"""

import os
import numpy as np
import pandas as pd
import streamlit as st

PARQUET_FILE = "ohlcv_idx_2026_all.parquet"

@st.cache_data(ttl=3600)
def _get_parquet():
    if not os.path.exists(PARQUET_FILE):
        return None
    df = pd.read_parquet(PARQUET_FILE)
    df.columns = [str(c).strip().title() for c in df.columns]
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    return df

def _load_ohlcv(kode, timeframe="daily"):
    df_all = _get_parquet()
    if df_all is None or "Kode" not in df_all.columns:
        return None
    
    df = df_all[df_all["Kode"] == kode].copy()
    if df.empty:
        return None
        
    if "Volume" not in df.columns:
        df["Volume"] = 0

    if timeframe == "weekly":
        df = df.set_index("Date").resample("W").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna().reset_index()
    elif timeframe == "2week":
        df = df.set_index("Date").resample("2W").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna().reset_index()
    elif timeframe == "monthly":
        df = df.set_index("Date").resample("ME").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna().reset_index()

    return df


def _atr(df, n=14):
    prev = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev).abs(),
        (df["Low"] - prev).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def find_pivots(df, n=5):
    highs = df["High"].values
    lows = df["Low"].values
    dates = df["Date"].values

    pivots = []
    for i in range(n, len(df) - n):
        left_h = highs[i - n:i]
        right_h = highs[i + 1:i + 1 + n]
        if highs[i] > left_h.max() and highs[i] > right_h.max():
            pivots.append({
                "date": dates[i], "price": float(highs[i]),
                "type": "high", "idx": i,
            })

        left_l = lows[i - n:i]
        right_l = lows[i + 1:i + 1 + n]
        if lows[i] < left_l.min() and lows[i] < right_l.min():
            pivots.append({
                "date": dates[i], "price": float(lows[i]),
                "type": "low", "idx": i,
            })

    return pivots


def cluster_pivots(pivots, tolerance):
    if not pivots:
        return []
    sorted_p = sorted(pivots, key=lambda x: x["price"])
    clusters = []
    current = [sorted_p[0]]

    for p in sorted_p[1:]:
        if abs(p["price"] - current[-1]["price"]) <= tolerance:
            current.append(p)
        else:
            clusters.append(current)
            current = [p]
    clusters.append(current)

    out = []
    for c in clusters:
        prices = [p["price"] for p in c]
        dates = [p["date"] for p in c]
        out.append({
            "pivots": c,
            "level": float(np.median(prices)),
            "lower": float(min(prices)),
            "upper": float(max(prices)),
            "n_touches": len(c),
            "first_touch": min(dates),
            "last_touch": max(dates),
            "pivot_types": [p["type"] for p in c],
        })
    return out


def check_break(zone, df, atr_val, original_type):
    last_price = float(df["Close"].iloc[-1])
    recent = df.tail(5)

    if original_type == "support":
        if last_price < zone["lower"] - 0.3 * atr_val:
            if (recent["Close"] < zone["lower"]).sum() >= 2:
                return {"broken": True, "direction": "down", "flip": "resistance"}
    else:
        if last_price > zone["upper"] + 0.3 * atr_val:
            if (recent["Close"] > zone["upper"]).sum() >= 2:
                return {"broken": True, "direction": "up", "flip": "support"}

    return {"broken": False, "direction": None, "flip": None}


def score_zone(zone, df, atr_val, current_price, scale_weight=1.0):
    score = 0
    n_touches = zone["n_touches"]
    types = zone["pivot_types"]
    n_low = types.count("low")
    n_high = types.count("high")

    if n_low > n_high:
        original_type = "support"
    elif n_high > n_low:
        original_type = "resistance"
    else:
        original_type = "support" if zone["level"] < current_price else "resistance"

    if n_touches >= 5: score += 4
    elif n_touches >= 3: score += 3
    elif n_touches >= 2: score += 2
    else: score += 1

    bounces = 0
    for p in zone["pivots"]:
        idx = p["idx"]
        if idx + 5 >= len(df): continue
        future = df.iloc[idx + 1:idx + 6]
        if p["type"] == "low":
            move = (future["High"].max() - p["price"]) / p["price"]
            if move >= atr_val / p["price"]: bounces += 1
        else:
            move = (p["price"] - future["Low"].min()) / p["price"]
            if move >= atr_val / p["price"]: bounces += 1
    if bounces >= 2: score += 2
    elif bounces >= 1: score += 1

    if "Volume" in df.columns and df["Volume"].sum() > 0:
        vma = df["Volume"].rolling(20).mean()
        high_vol = 0
        for p in zone["pivots"]:
            idx = p["idx"]
            if idx < 20: continue
            if df["Volume"].iloc[idx] > vma.iloc[idx] * 1.2:
                high_vol += 1
        if high_vol >= 2: score += 1.5
        elif high_vol >= 1: score += 0.75

    days_ago = (df["Date"].iloc[-1] - zone["last_touch"]).days
    recency = np.exp(-days_ago / 365)
    score += recency * 1.5

    level = zone["level"]
    for step in [1000, 500, 100]:
        nearest = round(level / step) * step
        if abs(level - nearest) / level < 0.003:
            score += 1
            break

    score *= scale_weight

    brk = check_break(zone, df, atr_val, original_type)

    if level < current_price:
        final_type = "support"
    elif level > current_price:
        final_type = "resistance"
    else:
        final_type = original_type

    is_flip = (final_type != original_type) and brk["broken"]

    if brk["broken"]:
        final_type = brk["flip"]

    if score >= 7: strength = "STRONG"
    elif score >= 4.5: strength = "MODERATE"
    else: strength = "WEAK"

    return {
        "level": level,
        "lower": zone["lower"],
        "upper": zone["upper"],
        "type": final_type,
        "original_type": original_type,
        "flip": is_flip,
        "n_touches": n_touches,
        "last_touch": zone["last_touch"],
        "days_since_last": days_ago,
        "score": round(score, 2),
        "strength": strength,
        "bounces": bounces,
    }


def detect_zones_at_scale(df, n_pivot, atr_val, current_price,
                           tolerance, min_touches=2, scale_weight=1.0):
    pivots = find_pivots(df, n=n_pivot)
    if not pivots:
        return []

    clusters = cluster_pivots(pivots, tolerance)

    zones = []
    for c in clusters:
        if c["n_touches"] < min_touches:
            continue
        z = score_zone(c, df, atr_val, current_price, scale_weight)

        dist = abs(z["level"] - current_price) / current_price
        if dist > 0.25:
            continue

        z["distance_pct"] = round((z["level"] - current_price) / current_price * 100, 2)
        z["scale_n"] = n_pivot
        zones.append(z)

    return zones


def dedup_zones(zones, tolerance):
    if not zones:
        return []

    sorted_z = sorted(zones, key=lambda x: x["level"])
    merged = []
    current = [sorted_z[0]]

    for z in sorted_z[1:]:
        if abs(z["level"] - current[-1]["level"]) <= tolerance:
            current.append(z)
        else:
            merged.append(_merge_group(current))
            current = [z]
    merged.append(_merge_group(current))
    return merged


def _merge_group(group):
    if len(group) == 1:
        z = group[0].copy()
        z["scales"] = [z.get("scale_n", 0)]
        z["n_scales"] = 1
        return z

    levels = [z["level"] for z in group]
    lowest = min(z["lower"] for z in group)
    highest = max(z["upper"] for z in group)
    best = max(group, key=lambda x: x["score"])

    total_touches = sum(z["n_touches"] for z in group)
    scales = sorted(set(z.get("scale_n", 0) for z in group))

    bonus = 0
    if len(scales) >= 3: bonus = 2.0
    elif len(scales) >= 2: bonus = 1.0

    new_score = best["score"] + bonus
    if new_score >= 7: strength = "STRONG"
    elif new_score >= 4.5: strength = "MODERATE"
    else: strength = "WEAK"

    return {
        "level": float(np.median(levels)),
        "lower": float(lowest),
        "upper": float(highest),
        "type": best["type"],
        "original_type": best["original_type"],
        "flip": best["flip"],
        "n_touches": total_touches,
        "last_touch": max(z["last_touch"] for z in group),
        "days_since_last": min(z["days_since_last"] for z in group),
        "score": round(new_score, 2),
        "strength": strength,
        "scales": scales,
        "n_scales": len(scales),
        "distance_pct": best["distance_pct"],
    }


def get_support_resistance(kode, timeframe="daily",
                            scales=None, max_per_side=5,
                            min_touches=2, atr_mult_tolerance=0.5):
    if scales is None:
        scales = {"short": 3, "medium": 7, "long": 15}

    df = _load_ohlcv(kode, timeframe=timeframe)
    if df is None or len(df) < 30:
        return None

    atr_series = _atr(df, 14)
    atr_val = float(atr_series.iloc[-1]) if atr_series.notna().any() else 0
    current = float(df["Close"].iloc[-1])

    tol_atr = atr_mult_tolerance * atr_val if atr_val > 0 else 0
    tol_pct = 0.008 * current
    tolerance = max(tol_atr, tol_pct)

    weights = {"short": 0.9, "medium": 1.0, "long": 1.1}

    result_scales = {}
    all_zones = []

    for name, n_pivot in scales.items():
        if len(df) < n_pivot * 4:
            continue
        zones = detect_zones_at_scale(
            df, n_pivot, atr_val, current, tolerance,
            min_touches=min_touches,
            scale_weight=weights.get(name, 1.0),
        )
        result_scales[name] = zones
        all_zones.extend(zones)

    if not all_zones:
        return None

    combined = dedup_zones(all_zones, tolerance)

    supports = [z for z in combined if z["level"] < current]
    resistances = [z for z in combined if z["level"] > current]

    supports = sorted(supports, key=lambda x: (-x["score"], -x["level"]))[:max_per_side]
    resistances = sorted(resistances, key=lambda x: (-x["score"], x["level"]))[:max_per_side]

    supports = sorted(supports, key=lambda x: -x["level"])
    resistances = sorted(resistances, key=lambda x: x["level"])

    if not supports and len(df) >= 20:
        low_20 = float(df["Low"].tail(20).min())
        low_60 = float(df["Low"].tail(60).min()) if len(df) >= 60 else low_20
        low_120 = float(df["Low"].tail(120).min()) if len(df) >= 120 else low_60

        fallbacks = []
        if low_60 < current:
            fallbacks.append({
                "level": low_60, "lower": low_60 * 0.995, "upper": low_60 * 1.005,
                "type": "support", "original_type": "support", "flip": False,
                "n_touches": 0, "last_touch": df["Date"].iloc[-len(df)], "days_since_last": 999,
                "score": 5.5, "strength": "MODERATE", "scales": [], "n_scales": 0,
                "note": "60d low", "distance_pct": round((low_60 / current - 1) * 100, 2),
            })
        if low_120 < low_60 and low_120 < current:
            fallbacks.append({
                "level": low_120, "lower": low_120 * 0.995, "upper": low_120 * 1.005,
                "type": "support", "original_type": "support", "flip": False,
                "n_touches": 0, "last_touch": df["Date"].iloc[-len(df)], "days_since_last": 999,
                "score": 6.0, "strength": "MODERATE", "scales": [], "n_scales": 0,
                "note": "120d low", "distance_pct": round((low_120 / current - 1) * 100, 2),
            })
        supports = sorted(fallbacks, key=lambda x: -x["level"])[:max_per_side]

    if not resistances and len(df) >= 20:
        high_20 = float(df["High"].tail(20).max())
        high_60 = float(df["High"].tail(60).max()) if len(df) >= 60 else high_20
        high_120 = float(df["High"].tail(120).max()) if len(df) >= 120 else high_60

        fallbacks = []
        if high_20 > current:
            fallbacks.append({
                "level": high_20, "lower": high_20 * 0.995, "upper": high_20 * 1.005,
                "type": "resistance", "original_type": "resistance", "flip": False,
                "n_touches": 0, "last_touch": df["Date"].iloc[-1], "days_since_last": 0,
                "score": 5.5, "strength": "MODERATE", "scales": [], "n_scales": 0,
                "note": "20d high", "distance_pct": round((high_20 / current - 1) * 100, 2),
            })
        if high_120 > high_20:
            fallbacks.append({
                "level": high_120, "lower": high_120 * 0.995, "upper": high_120 * 1.005,
                "type": "resistance", "original_type": "resistance", "flip": False,
                "n_touches": 0, "last_touch": df["Date"].iloc[-1], "days_since_last": 0,
                "score": 6.0, "strength": "MODERATE", "scales": [], "n_scales": 0,
                "note": "120d high", "distance_pct": round((high_120 / current - 1) * 100, 2),
            })
        resistances = sorted(fallbacks, key=lambda x: x["level"])[:max_per_side]

    return {
        "kode": kode, "timeframe": timeframe, "current_price": current,
        "atr": atr_val, "tolerance": round(tolerance, 2), "n_bars": len(df),
        "scales": {k: len(v) for k, v in result_scales.items()},
        "supports": supports, "resistances": resistances,
    }