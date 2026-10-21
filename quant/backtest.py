"""
quant/backtest_sr_methods.py
Bandingkan 12 metode deteksi Support/Resistance IDX secara jujur.
Output: winrate, expectancy, stabilitas train/val/test per metode.
"""
import os, sys, math, time, warnings
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.parquet_loader import load_parquet_safe


# ============================================================
# KONFIGURASI
# ============================================================
TOUCH_ATR    = 0.3      # toleransi sentuh level (dalam ATR)
BOUNCE_ATR   = 1.5      # target profit (memantul)
BREAK_ATR    = 0.5      # stop loss (tembus)
MAX_BARS     = 10       # maksimum bar sebelum timeout
DEBOUNCE     = 5        # minimal jarak antar-touch di level yang sama
ATR_PERIOD   = 14
LOOKBACK     = 250      # level dianggap valid selama 250 bar (1 tahun)
FEE_PCT      = 0.6      # fee round-trip (%)

# Split train/val/test
SPLIT_TRAIN = 0.6
SPLIT_VAL   = 0.8

# Metode yang diuji
METHODS = [
    "swing_w3",
    "swing_w5",
    "swing_w7",
    "donchian_20",
    "donchian_55",
    "pivot_classic",
    "pivot_fib",
    "round_50",
    "round_100",
    "kijun",       # Ichimoku 26 midpoint
    "weekly_hl",   # prev week high/low
    "monthly_hl",  # prev month high/low
]


# ============================================================
# ATR
# ============================================================
def compute_atr(highs, lows, closes, period=ATR_PERIOD):
    prev_close = np.roll(closes, 1)
    prev_close[0] = closes[0]
    tr = np.maximum(highs - lows,
                    np.maximum(np.abs(highs - prev_close),
                               np.abs(lows - prev_close)))
    return pd.Series(tr).rolling(period).mean().values


# ============================================================
# DETEKSI LEVEL PER METODE
# ============================================================
def detect_swings(highs, lows, i, w):
    """Return list of (price, side, detected_at_bar)."""
    out = []
    k = i - w   # baru tahu swing setelah w bar berikutnya
    if k - w < 0: return out
    window_h = highs[k-w:k+w+1]
    window_l = lows[k-w:k+w+1]
    if len(window_h) != 2*w+1: return out
    
    if highs[k] == window_h.max():
        out.append((float(highs[k]), "resistance", k))
    if lows[k] == window_l.min():
        out.append((float(lows[k]), "support", k))
    return out


def detect_donchian(highs, lows, i, period):
    if i < period: return []
    hh = float(np.max(highs[i-period:i]))
    ll = float(np.min(lows[i-period:i]))
    return [(hh, "resistance", i-period), (ll, "support", i-period)]


def detect_pivot_classic(highs, lows, closes, i):
    if i < 2: return []
    h, l, c = highs[i-1], lows[i-1], closes[i-1]
    p = (h + l + c) / 3
    r1 = 2*p - l
    s1 = 2*p - h
    r2 = p + (h - l)
    s2 = p - (h - l)
    return [(r1, "resistance", i-1), (r2, "resistance", i-1),
            (s1, "support", i-1), (s2, "support", i-1)]


def detect_pivot_fib(highs, lows, closes, i):
    if i < 2: return []
    h, l, c = highs[i-1], lows[i-1], closes[i-1]
    p = (h + l + c) / 3
    rng = h - l
    r1 = p + 0.382 * rng
    r2 = p + 0.618 * rng
    r3 = p + 1.000 * rng
    s1 = p - 0.382 * rng
    s2 = p - 0.618 * rng
    s3 = p - 1.000 * rng
    return [(r1, "resistance", i-1), (r2, "resistance", i-1), (r3, "resistance", i-1),
            (s1, "support", i-1), (s2, "support", i-1), (s3, "support", i-1)]


def detect_round(closes, i, increment):
    c = closes[i]
    if c < increment: return []
    r_up = math.ceil(c / increment) * increment
    r_dn = math.floor(c / increment) * increment
    out = []
    if r_up > c: out.append((r_up, "resistance", i))
    if r_dn < c: out.append((r_dn, "support", i))
    return out


def detect_kijun(highs, lows, i, period=26):
    """Ichimoku Kijun-sen (26-bar midpoint) — dipakai sebagai level dinamis."""
    if i < period: return []
    mid = (float(np.max(highs[i-period:i])) + float(np.min(lows[i-period:i]))) / 2
    c = closes[i]
    if mid > c: return [(mid, "resistance", i)]
    if mid < c: return [(mid, "support", i)]
    return []


def detect_weekly_hl(dates, highs, lows, i):
    if i < 10: return []
    # find start of current week (Monday)
    dt = pd.Timestamp(dates[i])
    days_since_monday = dt.weekday()
    week_start_idx = max(0, i - days_since_monday - 7)  # start of prev week
    week_end_idx = max(0, i - days_since_monday)
    if week_end_idx <= week_start_idx or week_start_idx < 0: return []
    h = float(np.max(highs[week_start_idx:week_end_idx]))
    l = float(np.min(lows[week_start_idx:week_end_idx]))
    return [(h, "resistance", week_end_idx), (l, "support", week_end_idx)]


def detect_monthly_hl(dates, highs, lows, i):
    if i < 25: return []
    dt = pd.Timestamp(dates[i])
    # start of current month
    cur_month_start = dt.replace(day=1)
    prev_month_end = cur_month_start - pd.Timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    mask = (pd.to_datetime(dates) >= prev_month_start) & (pd.to_datetime(dates) <= prev_month_end)
    idxs = np.where(mask)[0]
    if len(idxs) == 0: return []
    h = float(np.max(highs[idxs]))
    l = float(np.min(lows[idxs]))
    return [(h, "resistance", int(idxs[0])), (l, "support", int(idxs[0]))]


def detect_all(method, highs, lows, closes, dates, i, atr):
    try:
        if method == "swing_w3": return detect_swings(highs, lows, i, 3)
        if method == "swing_w5": return detect_swings(highs, lows, i, 5)
        if method == "swing_w7": return detect_swings(highs, lows, i, 7)
        if method == "donchian_20": return detect_donchian(highs, lows, i, 20)
        if method == "donchian_55": return detect_donchian(highs, lows, i, 55)
        if method == "pivot_classic": return detect_pivot_classic(highs, lows, closes, i)
        if method == "pivot_fib": return detect_pivot_fib(highs, lows, closes, i)
        if method == "round_50": return detect_round(closes, i, 50)
        if method == "round_100": return detect_round(closes, i, 100)
        if method == "kijun": return detect_kijun(highs, lows, i)
        if method == "weekly_hl": return detect_weekly_hl(dates, highs, lows, i)
        if method == "monthly_hl": return detect_monthly_hl(dates, highs, lows, i)
    except Exception:
        return []
    return []


# ============================================================
# TRADE SIMULATION
# ============================================================
def simulate_support(level, touch_bar, highs, lows, closes, atr_touch, n):
    tp = level + BOUNCE_ATR * atr_touch
    sl = level - BREAK_ATR * atr_touch
    entry = level
    end = min(touch_bar + MAX_BARS, n - 1)
    
    # Same bar
    if lows[touch_bar] <= sl:
        return "SL", (sl - entry) / entry * 100
    if highs[touch_bar] >= tp:
        return "TP", (tp - entry) / entry * 100
    
    for j in range(touch_bar + 1, end + 1):
        hit_sl = lows[j] <= sl
        hit_tp = highs[j] >= tp
        if hit_sl and hit_tp:
            return "SL", (sl - entry) / entry * 100
        if hit_sl:
            return "SL", (sl - entry) / entry * 100
        if hit_tp:
            return "TP", (tp - entry) / entry * 100
    
    return "TIMEOUT", (closes[end] - entry) / entry * 100


def simulate_resistance(level, touch_bar, highs, lows, closes, atr_touch, n):
    tp = level - BOUNCE_ATR * atr_touch
    sl = level + BREAK_ATR * atr_touch
    entry = level
    end = min(touch_bar + MAX_BARS, n - 1)
    
    if highs[touch_bar] >= sl:
        return "SL", (entry - sl) / entry * 100
    if lows[touch_bar] <= tp:
        return "TP", (entry - tp) / entry * 100
    
    for j in range(touch_bar + 1, end + 1):
        hit_sl = highs[j] >= sl
        hit_tp = lows[j] <= tp
        if hit_sl and hit_tp:
            return "SL", (entry - sl) / entry * 100
        if hit_sl:
            return "SL", (entry - sl) / entry * 100
        if hit_tp:
            return "TP", (entry - tp) / entry * 100
    
    return "TIMEOUT", (entry - closes[end]) / entry * 100


# ============================================================
# BACKTEST PER METHOD PER STOCK
# ============================================================
def backtest_stock(kode, method, df):
    if df is None or len(df) < 150: return []
    df = df.sort_values("Date").reset_index(drop=True)
    dates  = df["Date"].values
    highs  = df["High"].astype(float).values
    lows   = df["Low"].astype(float).values
    closes = df["Close"].astype(float).values
    n = len(df)
    
    atr = compute_atr(highs, lows, closes)
    
    results = []
    active_levels = []  # list of dict {price, side, bar, last_touch}
    last_detect = -100
    
    # Detect ulang tiap 3 bar (cukup cepat)
    for i in range(60, n - MAX_BARS - 1):
        if np.isnan(atr[i]) or atr[i] <= 0:
            continue
        
        # Deteksi level baru
        if i - last_detect >= 3:
            new_lv = detect_all(method, highs, lows, closes, dates, i, atr)
            for price, side, bar in new_lv:
                active_levels.append({
                    "price": price, "side": side, "bar": bar, "last_touch": -999
                })
            last_detect = i
        
        # Expire level lama
        active_levels = [lv for lv in active_levels if i - lv["bar"] <= LOOKBACK]
        
        # Cek touch di bar i
        for lv in active_levels:
            if i - lv["last_touch"] < DEBOUNCE:
                continue
            
            price = lv["price"]
            side = lv["side"]
            tol = TOUCH_ATR * atr[i]
            
            touched = False
            if side == "support":
                if lows[i] <= price + tol and lows[i] >= price - tol:
                    touched = True
            else:
                if highs[i] >= price - tol and highs[i] <= price + tol:
                    touched = True
            
            if not touched:
                continue
            
            lv["last_touch"] = i
            
            # Simulate
            if side == "support":
                result, ret_pct = simulate_support(price, i, highs, lows, closes, atr[i], n)
            else:
                result, ret_pct = simulate_resistance(price, i, highs, lows, closes, atr[i], n)
            
            if result is None:
                continue
            
            results.append({
                "kode": kode,
                "method": method,
                "date": pd.Timestamp(dates[i]),
                "side": side,
                "result": result,
                "ret_pct": ret_pct,
                "net_ret": ret_pct - FEE_PCT,
            })
    
    return results


# ============================================================
# WRAPPER UNTUK MULTIPROCESSING
# ============================================================
def _worker(args):
    kode, method, df = args
    try:
        return backtest_stock(kode, method, df)
    except Exception:
        return []


# ============================================================
# ANALISIS PER METODE
# ============================================================
def analyze_method(df_res, method):
    if df_res.empty:
        return None
    
    df_res = df_res.copy()
    df_res["win"] = (df_res["net_ret"] > 0).astype(int)
    
    # Split by date
    dates_sorted = sorted(df_res["date"].unique())
    if len(dates_sorted) < 10:
        return None
    n_dates = len(dates_sorted)
    split_train = dates_sorted[int(n_dates * SPLIT_TRAIN)]
    split_val   = dates_sorted[int(n_dates * SPLIT_VAL)]
    
    tr = df_res[df_res["date"] < split_train]
    va = df_res[(df_res["date"] >= split_train) & (df_res["date"] < split_val)]
    te = df_res[df_res["date"] >= split_val]
    
    def _stats(sub):
        if len(sub) < 20:
            return None
        wr = sub["win"].mean() * 100
        avg = sub["net_ret"].mean()
        return {"n": len(sub), "wr": wr, "avg": avg}
    
    stats_all = _stats(df_res)
    stats_tr = _stats(tr)
    stats_va = _stats(va)
    stats_te = _stats(te)
    
    if stats_all is None:
        return None
    
    # Per-side breakdown
    sup = df_res[df_res["side"] == "support"]
    res = df_res[df_res["side"] == "resistance"]
    
    sup_wr = (sup["win"].mean() * 100) if len(sup) >= 20 else None
    res_wr = (res["win"].mean() * 100) if len(res) >= 20 else None
    
    return {
        "method": method,
        "n": stats_all["n"],
        "wr": stats_all["wr"],
        "avg_ret": stats_all["avg"],
        "sup_n": len(sup),
        "sup_wr": sup_wr,
        "res_n": len(res),
        "res_wr": res_wr,
        "n_tr": stats_tr["n"] if stats_tr else 0,
        "wr_tr": stats_tr["wr"] if stats_tr else None,
        "n_va": stats_va["n"] if stats_va else 0,
        "wr_va": stats_va["wr"] if stats_va else None,
        "n_te": stats_te["n"] if stats_te else 0,
        "wr_te": stats_te["wr"] if stats_te else None,
        "stable": (
            stats_tr and stats_va and stats_te
            and abs(stats_tr["wr"] - stats_te["wr"]) < 5
            and abs(stats_va["wr"] - stats_te["wr"]) < 5
        ),
    }


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 120)
    print("BACKTEST: 12 METODE DETEKSI S/R — JUJUR, FORWARD-LOOKING")
    print("=" * 120)
    print(f"Touch toleransi : {TOUCH_ATR} ATR")
    print(f"Bounce (TP)     : {BOUNCE_ATR} ATR")
    print(f"Break (SL)      : {BREAK_ATR} ATR")
    print(f"Max bars        : {MAX_BARS}")
    print(f"Fee round-trip  : {FEE_PCT}%")
    print(f"Split           : {SPLIT_TRAIN*100:.0f}% train, "
          f"{(SPLIT_VAL-SPLIT_TRAIN)*100:.0f}% val, "
          f"{(1-SPLIT_VAL)*100:.0f}% test")
    print()
    
    print("Loading data...")
    df_all = load_parquet_safe()
    if df_all is None or df_all.empty:
        print("❌ Gagal load data."); return
    
    df_all["Kode"] = df_all["Kode"].astype(str).str.strip().str.upper()
    df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")
    df_all = df_all.dropna(subset=["Date"])
    
    tickers = df_all["Kode"].unique()
    print(f"📊 Total {len(tickers)} saham.")
    
    # Group by ticker untuk multiprocessing
    groups = {k: v for k, v in df_all.groupby("Kode")}
    del df_all
    
    # Prepare jobs: (kode, method, df) untuk semua kombinasi
    jobs = []
    for method in METHODS:
        for kode, df in groups.items():
            jobs.append((kode, method, df))
    
    print(f"🔬 {len(jobs):,} job (saham × metode). Jalankan paralel...\n")
    
    # Run parallel
    all_results = {m: [] for m in METHODS}
    t0 = time.time()
    
    with ProcessPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_worker, job): job for job in jobs}
        done = 0
        for fut in as_completed(futures):
            done += 1
            try:
                res = fut.result()
                if res:
                    for r in res:
                        all_results[r["method"]].append(r)
            except Exception:
                pass
            if done % max(1, len(jobs) // 40) == 0:
                print(f"\r  Progress: {done}/{len(jobs)} ({done*100//len(jobs)}%) "
                      f"· {time.time()-t0:.0f}s", end="", flush=True)
    
    print(f"\n\n✅ Selesai dalam {time.time()-t0:.0f} detik")
    
    # Analyze each method
    print("\n" + "=" * 120)
    print("HASIL — RANKING METODE DETEKSI S/R")
    print("=" * 120)
    
    summary = []
    for method in METHODS:
        res_list = all_results.get(method, [])
        if not res_list:
            continue
        df_res = pd.DataFrame(res_list)
        analysis = analyze_method(df_res, method)
        if analysis:
            summary.append(analysis)
    
    if not summary:
        print("❌ Tidak ada hasil.")
        return
    
    df_sum = pd.DataFrame(summary).sort_values("wr", ascending=False).reset_index(drop=True)
    
    # Format columns
    df_sum["wr_str"] = df_sum["wr"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    df_sum["avg_str"] = df_sum["avg_ret"].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
    df_sum["sup_str"] = df_sum.apply(
        lambda r: f"{r['sup_wr']:.1f}% ({r['sup_n']:,})" if pd.notna(r['sup_wr']) else "—", axis=1
    )
    df_sum["res_str"] = df_sum.apply(
        lambda r: f"{r['res_wr']:.1f}% ({r['res_n']:,})" if pd.notna(r['res_wr']) else "—", axis=1
    )
    df_sum["split_str"] = df_sum.apply(
        lambda r: (f"{r['wr_tr']:.1f}/{r['wr_va']:.1f}/{r['wr_te']:.1f}"
                   if r['wr_tr'] is not None and r['wr_va'] is not None and r['wr_te'] is not None
                   else "—"), axis=1
    )
    df_sum["stable_str"] = df_sum["stable"].apply(lambda x: "✅" if x else "⚠️")
    
    show = df_sum[["method", "n", "wr_str", "avg_str",
                   "sup_str", "res_str", "split_str", "stable_str"]].copy()
    show.columns = ["Metode", "N Touch", "WR Total", "Avg Ret",
                    "Support (WR, N)", "Resistance (WR, N)",
                    "WR Train/Val/Test", "Stabil?"]
    show.index = range(1, len(show) + 1)
    
    print(f"\n{show.to_string()}")
    
    # Detail per side — metode TOP 3
    print("\n" + "=" * 120)
    print("DETAIL BREAKDOWN PER SIDE — METODE TERBAIK")
    print("=" * 120)
    
    for _, r in df_sum.head(3).iterrows():
        print(f"\n▶ {r['method']}  (N total: {r['n']:,}, WR: {r['wr']:.1f}%)")
        if pd.notna(r['sup_wr']):
            print(f"   Support   : {r['sup_wr']:.1f}% win dari {r['sup_n']:,} touch")
        if pd.notna(r['res_wr']):
            print(f"   Resistance: {r['res_wr']:.1f}% win dari {r['res_n']:,} touch")
    
    # Save
    os.makedirs("quant/output", exist_ok=True)
    df_sum.to_csv("quant/output/sr_methods_ranking.csv", index=False)
    print(f"\n💾 Saved: quant/output/sr_methods_ranking.csv")
    
    # Honest verdict
    print("\n" + "=" * 120)
    print("VERDICT JUJUR")
    print("=" * 120)
    
    best = df_sum.iloc[0]
    top3 = df_sum.head(3)
    
    print(f"\n🏆 METODE TERBAIK (by total WR):")
    for _, r in top3.iterrows():
        marker = "✅" if r["stable"] else "⚠️"
        print(f"   {marker} {r['method']:<15} WR {r['wr_str']:>7} | "
              f"N {r['n']:>6,} | Avg {r['avg_str']:>7} | "
              f"Stabil: {'YA' if r['stable'] else 'TIDAK'}")
    
    print(f"\n💡 INTERPRETASI:")
    print(f"   • Metode dengan WR > 55% + stabil di 3 split = layak dipakai")
    print(f"   • Metode dengan WR < 50% = lebih sering tembus dari pada memantul")
    print(f"   • Cek juga 'Avg Ret' — kalau negatif, WR tinggi pun rugi karena fee")
    print(f"   • Support WR lebih tinggi dari Resistance WR = trader-friendly")
    print(f"   • Metode dengan N kecil (<500) = hasil belum reliable")
    
    best_stable = df_sum[df_sum["stable"]].head(1)
    if not best_stable.empty:
        r = best_stable.iloc[0]
        print(f"\n   ✅ REKOMENDASI: '{r['method']}' — WR {r['wr_str']} konsisten "
              f"di train/val/test, N {r['n']:,}, avg return {r['avg_str']}")


if __name__ == "__main__":
    main()