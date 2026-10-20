#!/usr/bin/env python3
"""
Pencarian kombinasi fitur untuk Buy on Support & Buy on Breakout
dengan validasi anti-overfitting (train/val/test + permutation test).

Data : folder berisi CSV per ticker, kolom: Date,Open,High,Low,Close,Volume
Pakai: python combo_search.py --data ./data --mode both --depth 4
"""
import argparse, glob, heapq, os, time
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# 1. INDIKATOR & FITUR BINER (semua hanya memakai data s/d candle sinyal)
# ----------------------------------------------------------------------------
def load_csv(path):
    df = pd.read_csv(path)
    df.columns = [c.strip().capitalize() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").dropna(subset=["Open", "High", "Low", "Close"])
    return df.reset_index(drop=True)

def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def atr(df, n=14):
    pc = df.Close.shift()
    tr = pd.concat([df.High - df.Low, (df.High - pc).abs(), (df.Low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()

def adx(df, n=14):
    up, dn = df.High.diff(), -df.Low.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * pd.Series(pdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    ndi = 100 * pd.Series(ndm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean()

def add_indicators(df):
    c, v = df.Close, df.Volume.replace(0, np.nan)
    df["ATR"] = atr(df)
    df["RSI"] = rsi(c)
    df["SMA20"], df["SMA50"], df["SMA200"] = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    df["EMA20"] = c.ewm(span=20, adjust=False).mean()
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df["MACDH"] = macd - macd.ewm(span=9, adjust=False).mean()
    bbw = (4 * c.rolling(20).std()) / df.SMA20
    df["BBW"] = bbw
    df["BBW_Q20"] = bbw.rolling(120).quantile(0.2)
    atrp = df.ATR / c
    df["ATRP"] = atrp
    df["ATRP_Q30"], df["ATRP_Q70"] = atrp.rolling(120).quantile(0.3), atrp.rolling(120).quantile(0.7)
    df["VOLR"] = v / v.rolling(20).mean()
    df["ADX"] = adx(df)
    rng = (df.High - df.Low).replace(0, np.nan)
    df["CLOC"] = (c - df.Low) / rng                     # posisi close dalam candle
    df["LWICK"] = (np.minimum(df.Open, c) - df.Low) / rng
    df["BODY"] = (c - df.Open).abs() / rng
    df["RANGE_ATR"] = rng / df.ATR
    df["ROC5"] = c.pct_change(5)
    df["ROC20"] = c.pct_change(20)
    hi252, lo252 = df.High.rolling(252, min_periods=60).max(), df.Low.rolling(252, min_periods=60).min()
    df["POS52"] = (c - lo252) / (hi252 - lo252)
    return df

def binary_features(df, i):
    """Dict fitur biner pada candle sinyal i (vektor untuk banyak i sekaligus)."""
    g = lambda col: df[col].values[i]
    c = g("Close")
    f = {}
    for t in (30, 40, 45, 50):  f[f"RSI<{t}"] = g("RSI") < t
    for t in (50, 55, 60, 70):  f[f"RSI>{t}"] = g("RSI") > t
    for t in (1.2, 1.5, 2.0):   f[f"Vol>{t}x"] = g("VOLR") > t
    f["Vol<0.8x"] = g("VOLR") < 0.8
    for t in (20, 25, 30):      f[f"ADX>{t}"] = g("ADX") > t
    f["ADX<20"] = g("ADX") < 20
    f["C>SMA20"], f["C<SMA20"] = c > g("SMA20"), c < g("SMA20")
    f["C>SMA50"], f["C<SMA50"] = c > g("SMA50"), c < g("SMA50")
    f["C>SMA200"], f["C<SMA200"] = c > g("SMA200"), c < g("SMA200")
    f["C>EMA20"] = c > g("EMA20")
    f["SMA50>SMA200"] = g("SMA50") > g("SMA200")
    f["MACDH>0"] = g("MACDH") > 0
    prev = df["MACDH"].shift(1).values[i]
    f["MACDH_naik"] = g("MACDH") > prev
    f["BB_Squeeze"] = g("BBW") < g("BBW_Q20")
    f["ATR_Low"], f["ATR_High"] = g("ATRP") < g("ATRP_Q30"), g("ATRP") > g("ATRP_Q70")
    f["Bullish"] = c > g("Open")
    f["CloseTop30%"] = g("CLOC") > 0.7
    f["LowerWick>40%"] = g("LWICK") > 0.4
    f["Body>60%"] = g("BODY") > 0.6
    f["Range>1.2ATR"] = g("RANGE_ATR") > 1.2
    f["Range<0.8ATR"] = g("RANGE_ATR") < 0.8
    for t in (-0.05, -0.03): f[f"ROC5<{t:.0%}"] = g("ROC5") < t
    for t in (0.03, 0.06):   f[f"ROC5>{t:.0%}"] = g("ROC5") > t
    f["ROC20>0"], f["ROC20<0"] = g("ROC20") > 0, g("ROC20") < 0
    f["Pos52>0.8"], f["Pos52<0.3"] = g("POS52") > 0.8, g("POS52") < 0.3
    f["Dekat_SMA50(<3%)"] = np.abs(c / g("SMA50") - 1) < 0.03
    return {k: np.asarray(v, dtype=bool) for k, v in f.items()}

# ----------------------------------------------------------------------------
# 2. DETEKSI EVENT (tanpa look-ahead) + SIMULASI TRADE
# ----------------------------------------------------------------------------
def simulate(df, sig_idx, sl_price, sl_atr, rr, max_hold, cost):
    """Entry open candle berikutnya. SL & TP dicek per candle, SL dulu bila bersamaan.
    Return R-multiple bersih (sudah dikurangi fee) atau nan bila tidak valid."""
    O, H, L, C, A = (df[k].values for k in ("Open", "High", "Low", "Close", "ATR"))
    out = np.full(len(sig_idx), np.nan)
    for n, (i, lvl) in enumerate(zip(sig_idx, sl_price)):
        if i + 2 >= len(df) or np.isnan(A[i]):
            continue
        entry = O[i + 1]
        sl = min(lvl, entry) - sl_atr * A[i]
        risk = entry - sl
        if risk <= 0 or risk / entry < 0.003:
            continue
        tp = entry + rr * risk
        res = None
        for k in range(i + 1, min(i + 1 + max_hold, len(df))):
            if O[k] <= sl: res = (O[k] - entry) / risk; break        # gap down
            if L[k] <= sl: res = -1.0; break
            if H[k] >= tp: res = rr; break
        if res is None:
            res = (C[min(i + max_hold, len(df) - 1)] - entry) / risk  # timeout
        out[n] = res - cost * entry / risk
    return out

def support_events(df, pivot_w=5, tol_atr=0.3, min_age=10, max_age=120):
    """Support = swing low yang baru 'diketahui' setelah pivot_w candle (tanpa look-ahead).
    Event = candle pertama yang menyentuh zona lalu close di atas level."""
    L, C, A = df.Low.values, df.Close.values, df.ATR.values
    n = len(df)
    pivots = []
    for p in range(pivot_w, n - pivot_w):
        if L[p] == L[p - pivot_w: p + pivot_w + 1].min():
            pivots.append((p + pivot_w, L[p]))                      # (baru diketahui di, level)
    idx, lvl = [], []
    for known, level in pivots:
        for t in range(known + min_age, min(known + max_age, n - 2)):
            if np.isnan(A[t]): continue
            if L[t] < level - 1.0 * A[t]: break                     # support sudah jebol
            if L[t] <= level + tol_atr * A[t] and C[t] > level:
                idx.append(t); lvl.append(min(level, L[t])); break
    return np.array(idx, dtype=int), np.array(lvl)

def breakout_events(df, lookback):
    """Breakout = close pertama di atas high tertinggi N candle sebelumnya."""
    hh = df.High.shift(1).rolling(lookback).max().values
    C = df.Close.values
    prev_c = np.r_[np.nan, C[:-1]]
    prev_hh = np.r_[np.nan, hh[:-1]]
    ok = (C > hh) & ~(prev_c > prev_hh)
    idx = np.where(ok & ~np.isnan(hh))[0]
    return idx, hh[idx]

def build_events(data_dir, mode, scenarios, max_hold, cost):
    frames = {"support": [], "breakout": []}
    files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    for fp in files:
        tk = os.path.splitext(os.path.basename(fp))[0]
        try:
            df = add_indicators(load_csv(fp))
        except Exception as e:
            print(f"skip {tk}: {e}"); continue
        if len(df) < 300: continue
        jobs = []
        if mode in ("support", "both"):
            jobs.append(("support", "", *support_events(df)))
        if mode in ("breakout", "both"):
            for lb in (20, 50):
                jobs.append(("breakout", f"LB{lb}", *breakout_events(df, lb)))
        for kind, tag, idx, lvl in jobs:
            if len(idx) == 0: continue
            feats = binary_features(df, idx)
            for (sl_atr, rr) in scenarios:
                R = simulate(df, idx, lvl, sl_atr, rr, max_hold, cost)
                ok = ~np.isnan(R)
                part = pd.DataFrame({"ticker": tk, "date": df.Date.values[idx][ok],
                                     "scenario": f"{tag}|SL{sl_atr}ATR|RR{rr}", "R": R[ok]})
                for k, v in feats.items(): part[k] = v[ok]
                frames[kind].append(part)
    out = {}
    for k, v in frames.items():
        if v: out[k] = pd.concat(v, ignore_index=True)
    return out

# ----------------------------------------------------------------------------
# 3. PENCARIAN KOMBINASI (DFS + pruning) & STATISTIK
# ----------------------------------------------------------------------------
def tstat(r):
    n = len(r)
    sd = r.std(ddof=1)
    return 0.0 if sd == 0 else r.mean() / (sd / np.sqrt(n))

def search(Ft, R, names, depth, min_n, top_k):
    """Ft: matriks fitur (F, N) bool. Mengembalikan top_k kombinasi menurut t-stat (mean>0)."""
    heap, counter = [], [0]
    def rec(idx, start, combo):
        for j in range(start, Ft.shape[0]):
            sub = idx[Ft[j][idx]]
            if len(sub) < min_n or len(sub) == len(idx):
                continue
            counter[0] += 1
            r = R[sub]
            if r.mean() > 0:
                t = tstat(r)
                item = (t, len(sub), r.mean(), tuple(combo + [j]))
                if len(heap) < top_k: heapq.heappush(heap, item)
                elif t > heap[0][0]: heapq.heapreplace(heap, item)
            if len(combo) + 1 < depth:
                rec(sub, j + 1, combo + [j])
    rec(np.arange(Ft.shape[1]), 0, [])
    return sorted(heap, reverse=True), counter[0]

def stats(R, mask):
    r = R[mask]
    if len(r) < 2: return dict(N=len(r), WR=np.nan, ExpR=np.nan, PF=np.nan, t=np.nan)
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    return dict(N=len(r), WR=100 * (r > 0).mean(), ExpR=r.mean(), PF=(w / l if l > 0 else np.inf), t=tstat(r))

def mask_of(F, combo):
    m = np.ones(F.shape[1], dtype=bool)
    for j in combo: m &= F[j]
    return m

# ----------------------------------------------------------------------------
# 4. PIPELINE
# ----------------------------------------------------------------------------
def run_kind(kind, ev, args):
    print("\n" + "=" * 90 + f"\n  {kind.upper()}  | total event: {len(ev)}\n" + "=" * 90)
    names = [c for c in ev.columns if c not in ("ticker", "date", "scenario", "R")]
    results = []
    for scen, g in ev.groupby("scenario"):
        g = g.sort_values("date").reset_index(drop=True)
        n = len(g)
        c1, c2 = int(n * args.train), int(n * (args.train + args.val))
        tr, va, te = g.iloc[:c1], g.iloc[c1:c2], g.iloc[c2:]
        if len(tr) < 3 * args.min_n:
            print(f"[{scen}] data terlalu sedikit, dilewati"); continue
        F = lambda d: d[names].values.T.astype(bool)
        Ftr, Fva, Fte = F(tr), F(va), F(te)
        Rtr, Rva, Rte = tr.R.values, va.R.values, te.R.values

        t0 = time.time()
        top, n_tested = search(Ftr, Rtr, names, args.depth, args.min_n, args.top_k)
        # permutation test: acak R (putus hubungan fitur-hasil), cari max t-stat lagi
        null_max = []
        rng = np.random.default_rng(42)
        for _ in range(args.perms):
            h, _ = search(Ftr, rng.permutation(Rtr), names, args.depth, args.min_n, 1)
            null_max.append(h[0][0] if h else 0.0)
        null_p95 = np.percentile(null_max, 95) if null_max else 0.0
        real_max = top[0][0] if top else 0.0
        print(f"\n[{scen}] train={len(tr)} val={len(va)} test={len(te)} | kombinasi diuji={n_tested:,} "
              f"({time.time()-t0:.0f}s)")
        print(f"  t-stat tertinggi di TRAIN (nyata) : {real_max:.2f}")
        print(f"  t-stat tertinggi pada DATA ACAK   : p95={null_p95:.2f}  <- jika nyata <= ini, itu NOISE")

        for t, nn, mean, combo in top:
            if t <= null_p95: continue                                   # lolos permutation test
            mv = stats(Rva, mask_of(Fva, combo))
            if mv["N"] < args.min_n_val or not (mv["ExpR"] > 0) or mv["t"] < 1.65: continue
            mt = stats(Rte, mask_of(Fte, combo))                         # test: dilihat sekali
            results.append(dict(scenario=scen, combo=" & ".join(names[j] for j in combo),
                                tr_N=nn, tr_ExpR=mean, tr_t=t,
                                va_N=mv["N"], va_WR=mv["WR"], va_ExpR=mv["ExpR"],
                                te_N=mt["N"], te_WR=mt["WR"], te_ExpR=mt["ExpR"], te_PF=mt["PF"]))
    if not results:
        print("\n>> TIDAK ADA kombinasi yang lolos semua uji. Itu hasil yang jujur: "
              "kemungkinan tidak ada edge yang kuat pada data/aturan ini.")
        return None
    res = pd.DataFrame(results).sort_values("va_ExpR", ascending=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 70)
    print(f"\n>> {len(res)} kombinasi lolos TRAIN + permutation + VALIDATION. Kolom te_* = TEST (data belum pernah dilihat):")
    print(res.head(25).round(2).to_string(index=False))
    good = res[(res.te_N >= args.min_n_val) & (res.te_ExpR > 0)]
    print(f"\n>> Yang tetap profit di TEST: {len(good)} dari {len(res)}")
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="folder CSV per ticker")
    ap.add_argument("--mode", default="both", choices=["support", "breakout", "both"])
    ap.add_argument("--depth", type=int, default=4, help="maks fitur per kombinasi")
    ap.add_argument("--min_n", type=int, default=100, help="min sample di train")
    ap.add_argument("--min_n_val", type=int, default=30, help="min sample di val/test")
    ap.add_argument("--top_k", type=int, default=300)
    ap.add_argument("--perms", type=int, default=20, help="jumlah shuffle permutation test")
    ap.add_argument("--train", type=float, default=0.5)
    ap.add_argument("--val", type=float, default=0.25)
    ap.add_argument("--max_hold", type=int, default=20)
    ap.add_argument("--cost", type=float, default=0.003, help="fee+slippage round trip (0.003 = 0.3 persen)")
    ap.add_argument("--out", default="hasil_kombinasi")
    args = ap.parse_args()

    scenarios = [(0.5, 2.0), (1.0, 2.0), (1.0, 3.0)]   # (SL buffer x ATR di bawah level, RR)
    events = build_events(args.data, args.mode, scenarios, args.max_hold, args.cost)
    for kind, ev in events.items():
        res = run_kind(kind, ev, args)
        if res is not None:
            res.to_csv(f"{args.out}_{kind}.csv", index=False)
            print(f"tersimpan: {args.out}_{kind}.csv")

if __name__ == "__main__":
    main()