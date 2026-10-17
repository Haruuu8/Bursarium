"""
PRE-GOLDEN-CROSS SCANNER v3 - dengan Emerging Pre-Cross
"""
import os
import pandas as pd
import numpy as np
import streamlit as st
from quant.parquet_loader import load_parquet_safe

SKOR_MIN, GAP_MAX, REQUIRE_ABOVE_EMA20 = 85, 4.0, True
MIN_VALUE_20D, MIN_RANGE_20D = 3_000_000_000, 0.04
EMA_FAST, EMA_SLOW, EMA_TREND, CONVERGE_LB, SLOPE_LB = 20, 50, 200, 5, 5

@st.cache_data(ttl=3600)
def _get_parquet():
    return load_parquet_safe()

def ema(s, p): return s.ewm(span=p, adjust=False).mean()

def rsi(s, p=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(alpha=1/p, adjust=False, min_periods=p).mean()
    al = l.ewm(alpha=1/p, adjust=False, min_periods=p).mean()
    rs = ag / al.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd_hist(s, fast=12, slow=26, sig=9):
    ef, es = s.ewm(span=fast, adjust=False).mean(), s.ewm(span=slow, adjust=False).mean()
    line = ef - es
    return line - line.ewm(span=sig, adjust=False).mean()

def load_ohlcv(kode):
    df_all = _get_parquet()
    if df_all is None or "Kode" not in df_all.columns: return None
    df = df_all[df_all["Kode"] == kode].copy()
    if df.empty: return None
    return df.sort_values("Date").reset_index(drop=True)

def hitung_skor(df, i):
    close, ema_f, ema_s, ema_t = df["Close"].iloc[i], df["ema_f"].iloc[i], df["ema_s"].iloc[i], df["ema_t"].iloc[i]
    detail, total = {}, 0
    gap_pct = (ema_s - ema_f) / ema_s * 100 if ema_s > 0 else 999
    pts = 15 if gap_pct <= 1.0 else 10 if gap_pct <= 2.0 else 0
    total += pts; detail["gap"] = {"pts": pts, "pct": gap_pct, "max": 15}
    j = i - CONVERGE_LB; konv_pct = 0
    if j >= 0:
        es_old, ef_old = df["ema_s"].iloc[j], df["ema_f"].iloc[j]
        gap_old = (es_old - ef_old) / es_old * 100 if es_old > 0 else 0
        if gap_old > 0: konv_pct = (gap_old - gap_pct) / gap_old * 100
    pts = 15 if konv_pct >= 20 else 8 if konv_pct > 0 else 0
    total += pts; detail["konvergen"] = {"pts": pts, "pct": konv_pct, "max": 15}
    k = i - SLOPE_LB; slope_pct = 0
    if k >= 0:
        ef_old = df["ema_f"].iloc[k]
        if ef_old > 0: slope_pct = (ema_f - ef_old) / ef_old * 100
    pts = 15 if slope_pct >= 1.5 else 12 if slope_pct >= 1.0 else 8 if slope_pct > 0 else 0
    total += pts; detail["slope"] = {"pts": pts, "pct": slope_pct, "max": 15}
    rsi_v = df["rsi"].iloc[i]
    pts = 15 if not pd.isna(rsi_v) and rsi_v >= 60 else 10 if not pd.isna(rsi_v) and rsi_v >= 50 else 0
    total += pts; detail["rsi"] = {"pts": pts, "val": rsi_v, "max": 15}
    mh_v, mh_p = df["macd_h"].iloc[i], df["macd_h"].iloc[i-1] if i > 0 else np.nan
    pts = 10 if not pd.isna(mh_v) and mh_v > 0 else 6 if not pd.isna(mh_v) and not pd.isna(mh_p) and mh_v > mh_p else 0
    total += pts; detail["macd"] = {"pts": pts, "max": 10}
    pts = 10 if not pd.isna(ema_t) and close > ema_t else 0
    total += pts; detail["ema200"] = {"pts": pts, "max": 10}
    v5, vma = df["Volume"].iloc[max(0, i-4):i+1].mean(), df["vol_ma20"].iloc[i]
    vol_ratio = v5 / vma if vma > 0 else 0
    pts = 10 if vol_ratio >= 1.5 else 5 if vol_ratio >= 1.2 else 0
    total += pts; detail["volume"] = {"pts": pts, "ratio": vol_ratio, "max": 10}
    if i >= 10:
        lows = df["Low"].iloc[i-10:i+1].values; mid = len(lows) // 2
        pts = 5 if lows[mid:].min() > lows[:mid].min() else 0
    else: pts = 0
    total += pts; detail["higher_low"] = {"pts": pts, "max": 5}
    return round(total, 1), detail, {"gap_pct": round(gap_pct, 3), "konv_pct": round(konv_pct, 1), "slope_pct": round(slope_pct, 3), "rsi": round(float(rsi_v), 1) if not pd.isna(rsi_v) else None}

def _prepare_df(df):
    df["ema_f"] = ema(df["Close"], EMA_FAST); df["ema_s"] = ema(df["Close"], EMA_SLOW)
    df["ema_t"] = ema(df["Close"], EMA_TREND); df["rsi"] = rsi(df["Close"])
    df["macd_h"] = macd_hist(df["Close"]); df["vol_ma20"] = df["Volume"].rolling(20).mean()
    return df

def scan_pre_cross():
    df_all = _get_parquet()
    if df_all is None: return []
    results = []
    for kode in df_all["Kode"].unique():
        df = load_ohlcv(kode)
        if df is None or len(df) < EMA_TREND + 50: continue
        df = _prepare_df(df); i = len(df) - 1
        ema_f, ema_s = df["ema_f"].iloc[i], df["ema_s"].iloc[i]
        if not (ema_f < ema_s): continue
        gap_pct = (ema_s - ema_f) / ema_s * 100 if ema_s > 0 else 999
        if gap_pct > GAP_MAX: continue
        tail = df.tail(20); val20 = (tail["Close"] * tail["Volume"]).mean()
        if pd.isna(val20) or val20 < MIN_VALUE_20D: continue
        h20, l20 = tail["High"].max(), tail["Low"].min()
        if l20 <= 0 or (h20 - l20) / l20 < MIN_RANGE_20D: continue
        close = df["Close"].iloc[i]
        if REQUIRE_ABOVE_EMA20 and close <= ema_f: continue
        skor, detail, values = hitung_skor(df, i)
        if skor < SKOR_MIN: continue
        results.append({"kode": kode, "harga": round(float(close), 0), "ema20": round(float(ema_f), 2), "ema50": round(float(ema_s), 2), "value20": float(val20), "range20": round((h20 - l20) / l20 * 100, 2), "skor": skor, "gap_pct": values["gap_pct"], "konv_pct": values["konv_pct"], "slope_pct": values["slope_pct"], "rsi": values["rsi"], "detail": detail})
    results.sort(key=lambda x: -x["skor"]); return results

def scan_emerging_pre_cross(min_skor=65, max_skor=84, max_gap=5.0):
    df_all = _get_parquet()
    if df_all is None: return []
    results = []
    for kode in df_all["Kode"].unique():
        df = load_ohlcv(kode)
        if df is None or len(df) < EMA_TREND + 50: continue
        df = _prepare_df(df); i = len(df) - 1
        ema_f, ema_s = df["ema_f"].iloc[i], df["ema_s"].iloc[i]
        if not (ema_f < ema_s): continue
        gap_pct = (ema_s - ema_f) / ema_s * 100 if ema_s > 0 else 999
        if gap_pct > max_gap: continue
        tail = df.tail(20); val20 = (tail["Close"] * tail["Volume"]).mean()
        if pd.isna(val20) or val20 < MIN_VALUE_20D: continue
        h20, l20 = tail["High"].max(), tail["Low"].min()
        if l20 <= 0 or (h20 - l20) / l20 < MIN_RANGE_20D: continue
        close = df["Close"].iloc[i]
        if close <= ema_f: continue
        skor, detail, values = hitung_skor(df, i)
        if not (min_skor <= skor <= max_skor): continue
        if values["konv_pct"] <= 0 or values["slope_pct"] <= 0: continue
        days_to_85 = None
        if values["konv_pct"] > 0 and gap_pct > 0:
            rate_gap_per_day = (gap_pct * values["konv_pct"] / 100) / CONVERGE_LB
            if rate_gap_per_day > 0:
                days_needed = max(0, (gap_pct - 1.0) / rate_gap_per_day)
                if days_needed < 30: days_to_85 = round(days_needed, 1)
        results.append({"kode": kode, "harga": round(float(close), 0), "ema20": round(float(ema_f), 2), "ema50": round(float(ema_s), 2), "value20": float(val20), "range20": round((h20 - l20) / l20 * 100, 2), "skor": skor, "gap_pct": values["gap_pct"], "konv_pct": values["konv_pct"], "slope_pct": values["slope_pct"], "rsi": values["rsi"], "detail": detail, "days_to_85": days_to_85, "gap_to_85": round(skor - 85, 1)})
    results.sort(key=lambda x: (-x["skor"], x.get("days_to_85") or 999)); return results

def load_nama_map():
    nama = {}
    if os.path.exists("data_sektor.csv"):
        try:
            df = pd.read_csv("data_sektor.csv")
            if "kode" in df.columns and "nama" in df.columns:
                for _, r in df.iterrows():
                    k, n = str(r["kode"]).strip().upper(), str(r["nama"]).strip()
                    if k and n and n.lower() != "nan": nama[k] = n
        except Exception: pass
    return nama