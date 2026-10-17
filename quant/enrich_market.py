"""Isi field market (harga, PE, PB, market cap) ke JSON existing dari yfinance."""
import json
import time
import random
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import yfinance as yf
import pandas as pd

DETAIL_DIR = Path("data_fundamental")
OHLCV_DIR = Path("data_ohlcv_idx")
OHLCV_DIR.mkdir(exist_ok=True)


def _safe(v, default=None):
    if v is None:
        return default
    try:
        if pd.isna(v) or (isinstance(v, float) and not (-1e30 < v < 1e30)):
            return default
    except Exception:
        pass
    return v


def compute_akumulasi(df):
    if df is None or len(df) < 20:
        return {}
    d = df.tail(20).copy()
    high = d["High"].astype(float)
    low = d["Low"].astype(float)
    close = d["Close"].astype(float)
    vol = d["Volume"].astype(float)
    hl = (high - low).replace(0, pd.NA)
    mfm = ((close - low) - (high - close)) / hl
    mfm = mfm.fillna(0)
    mfv = mfm * vol
    cmf = float(mfv.sum() / vol.sum()) if vol.sum() else 0.0
    full = df.tail(40)
    if len(full) >= 40:
        vt = float(full["Volume"].tail(20).mean() / full["Volume"].head(20).mean()) if full["Volume"].head(20).mean() else 1.0
    else:
        vt = 1.0
    if len(df) >= 21:
        p_now = float(df["Close"].iloc[-1])
        p_then = float(df["Close"].iloc[-21])
        chg = (p_now - p_then) / p_then * 100 if p_then else 0.0
    else:
        chg = 0.0
    score = 5.0
    score += min(cmf * 15, 2) if cmf > 0 else max(cmf * 15, -2)
    if vt > 1.2 and chg > 0: score += 1
    elif vt > 1.2 and chg < 0: score -= 1
    if chg > 5: score += 0.5
    elif chg < -5: score -= 0.5
    score = max(0, min(10, score))
    if score >= 6.5: tipe, label = "ACCUMULATION", "AKUMULASI"
    elif score <= 3.5: tipe, label = "DISTRIBUTION", "DISTRIBUSI"
    else: tipe, label = "NEUTRAL", "NETRAL"
    return {"score": round(score, 1), "label": label, "tipe": tipe,
            "cmf": round(cmf, 4), "vol_trend": round(vt, 3),
            "price_chg_20d": round(chg, 2)}


def _is_enriched(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return (d.get("harga") is not None
                and (d.get("statistik") or {}).get("market_cap") is not None)
    except Exception:
        return False


def enrich_one(kode, max_retries=3):
    kode = kode.strip().upper()
    path = DETAIL_DIR / f"{kode}.json"
    if not path.exists():
        return kode, False, "no_json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return kode, False, f"read:{e}"

    info = {}
    t = None
    for attempt in range(max_retries):
        try:
            t = yf.Ticker(f"{kode}.JK")
            info = t.info or {}
            if info and info.get("regularMarketPrice") is not None:
                break
        except Exception as e:
            if "429" in str(e).lower() or "too many" in str(e).lower():
                time.sleep((2 ** attempt) + random.uniform(0, 2))
                continue
            break

    harga = (info.get("currentPrice") or info.get("regularMarketPrice")
             or info.get("previousClose"))
    if harga:
        data["harga"] = float(harga)

    rk = data.get("rasio_kunci") or {}
    eps = _safe(info.get("trailingEps"))
    if eps is not None:
        rk["eps"] = eps
    pe = _safe(info.get("trailingPE"))
    if pe is None and eps and harga:
        pe = harga / eps
    if pe is not None:
        rk["pe"] = _safe(pe)
    bvps = _safe(info.get("bookValue"))
    pb = _safe(info.get("priceToBook"))
    if pb is None and bvps and harga and bvps != 0:
        pb = harga / bvps
    if pb is not None:
        rk["pb"] = _safe(pb)
    rk["ps"] = _safe(info.get("priceToSalesTrailing12Months")) or rk.get("ps")
    rk["roe"] = _safe(info.get("returnOnEquity")) or rk.get("roe")
    rk["roa"] = _safe(info.get("returnOnAssets")) or rk.get("roa")
    rk["margin_net"] = _safe(info.get("profitMargins")) or rk.get("margin_net")
    rk["current_ratio"] = _safe(info.get("currentRatio")) or rk.get("current_ratio")
    de_raw = _safe(info.get("debtToEquity"))
    if de_raw is not None:
        rk["de"] = de_raw / 100
    data["rasio_kunci"] = rk

    market_cap = _safe(info.get("marketCap"))
    ev = _safe(info.get("enterpriseValue"))
    shares = _safe(info.get("sharesOutstanding"))
    ff = _safe(info.get("floatShares"))
    ff_pct = (ff / shares * 100) if ff and shares else None
    data["statistik"] = {
        "market_cap": market_cap,
        "enterprise_value": ev,
        "shares_outstanding": shares,
        "free_float_pct": ff_pct,
    }
    data["sektor"] = info.get("sector") or data.get("sektor")
    data["industri"] = info.get("industry") or data.get("industri")

    df_ohlcv = None
    if t is not None:
        try:
            hist = t.history(period="6mo", interval="1d", auto_adjust=False)
            if hist is not None and not hist.empty:
                df_ohlcv = hist.reset_index()
                df_ohlcv.columns = [str(c).strip().title() for c in df_ohlcv.columns]
                keep = [c for c in ["Date","Open","High","Low","Close","Volume"] if c in df_ohlcv.columns]
                df_ohlcv = df_ohlcv[keep]
                df_ohlcv.to_csv(OHLCV_DIR / f"{kode}.csv", index=False)
        except Exception:
            pass
    if df_ohlcv is not None:
        data["akumulasi"] = compute_akumulasi(df_ohlcv)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return kode, True, None


def run(workers=3, delay=1.0):
    files = sorted(DETAIL_DIR.glob("*.json"))
    kodes = [f.stem for f in files if not _is_enriched(f)]
    print(f"Enrich {len(kodes)} saham (workers={workers}, delay={delay}s)\n")

    ok, err = 0, 0
    lock = Lock()
    counter = {"n": 0}
    t0 = time.time()

    def worker(k):
        time.sleep(random.uniform(0, delay))
        return enrich_one(k)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(worker, k): k for k in kodes}
        for fut in as_completed(futures):
            k, s, e = fut.result()
            with lock:
                counter["n"] += 1
                n = counter["n"]
            if s:
                ok += 1
                print(f"[{n}/{len(kodes)}] {k}: OK", flush=True)
            else:
                err += 1
                print(f"[{n}/{len(kodes)}] {k}: ERR {e}", flush=True)

    total = time.time() - t0
    print(f"\nSelesai {total:.0f}s | OK {ok} | ERR {err}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    run(workers=args.workers, delay=args.delay)
