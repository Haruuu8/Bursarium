"""
WR90 HUNTER — Target WR ≥ 90% dengan N ≥ 1500.
Strategi:
1. Loosen rule_a (dapat lebih banyak sinyal)
2. Gap filter (2-20%, 2-10%, 5-15%)
3. Quality filter (HL, 52w, ATR) untuk boost WR
4. Tighter trailing (0.5% vs 1%)
5. Test 100+ kombinasi

Find Pareto: N ≥ 1500, WR ≥ 90%.
"""
import os
import numpy as np
import pandas as pd
import concurrent.futures
import itertools

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXED_PARQUET = os.path.join(BASE_DIR, "ohlcv_idx_fixed.parquet")

MIN_PRICE = 50
MIN_VOLUME = 100000
MAX_DAYS = 30


def _process(args):
    kode, sub = args
    sub = sub.sort_values("Date").reset_index(drop=True).copy()
    n = len(sub)
    if n < 100: return None

    o = sub["Open"].values.astype(np.float64)
    h = sub["High"].values.astype(np.float64)
    l = sub["Low"].values.astype(np.float64)
    c = sub["Close"].values.astype(np.float64)
    v = sub["Volume"].values.astype(np.float64)
    dates = sub["Date"].values

    s_c = pd.Series(c); s_h = pd.Series(h); s_l = pd.Series(l); s_v = pd.Series(v)
    prev_c = s_c.shift(1)

    for n_ in [20, 50, 200]:
        sub[f"sma{n_}"] = s_c.rolling(n_).mean()
    sub["ret_1d"] = s_c.pct_change(1)
    sub["ret_3d"] = s_c.pct_change(3)
    sub["ret_5d"] = s_c.pct_change(5)
    sub["ret_10d"] = s_c.pct_change(10)
    sub["px_vs_sma20"] = s_c / sub["sma20"] - 1
    sub["px_vs_sma50"] = s_c / sub["sma50"] - 1
    sub["range"] = (s_h - s_l) / s_c
    vol_ma = s_v.rolling(20).mean()
    vol_std = s_v.rolling(20).std()
    sub["vol_z_20"] = (s_v - vol_ma) / vol_std.replace(0, np.nan)
    tr = np.maximum(s_h - s_l, np.maximum((s_h - prev_c).abs(), (s_l - prev_c).abs()))
    sub["atr_pct"] = tr.rolling(14).mean() / s_c

    up_day = (s_c > prev_c).astype(int)
    sub["consec_up"] = up_day.groupby((up_day != up_day.shift()).cumsum()).cumsum()
    sub["hl"] = (s_l > prev_c).astype(int)
    sub["hl5"] = sub["hl"].rolling(5).sum()

    sub["high_252"] = s_h.rolling(252, min_periods=200).max()
    sub["low_252"] = s_l.rolling(252, min_periods=200).min()
    den = sub["high_252"] - sub["low_252"]
    sub["pos_52w"] = np.where(den > 0, (s_c - sub["low_252"]) / den, np.nan)

    # For each candidate, simulate with 4 trailing configs
    # Trail 0.5% (tight), 0.75%, 1.0%, 1.25%
    TRAIL_CONFIGS = [0.005, 0.0075, 0.01, 0.0125]
    SL_PCT = 0.03

    ret1 = sub["ret_1d"].values
    ret3 = sub["ret_3d"].values
    ret5 = sub["ret_5d"].values
    ret10 = sub["ret_10d"].values
    px20 = sub["px_vs_sma20"].values
    px50 = sub["px_vs_sma50"].values
    rng = sub["range"].values
    vz = sub["vol_z_20"].values
    atr = sub["atr_pct"].values
    cu = sub["consec_up"].values
    hl5 = sub["hl5"].values
    p52 = sub["pos_52w"].values

    base_superset = ((ret1 > 0.05) | (ret3 > 0.08) | (ret5 > 0.08) | (ret10 > 0.10))
    cand_idx = np.where(base_superset)[0]
    cand_idx = cand_idx[cand_idx < n - 5]

    rows = []
    for i in cand_idx:
        if i + 1 >= n: continue
        signal_close = c[i]
        entry = o[i + 1]
        if np.isnan(entry) or entry <= 0 or signal_close <= 0:
            continue

        gap_pct = (entry / signal_close - 1) * 100
        if gap_pct < 2 or gap_pct > 20:
            continue

        sl_price = entry * (1 - SL_PCT)

        # For each trail config, simulate
        for trail in TRAIL_CONFIGS:
            key = f"trail{int(trail*1000)}"
            peak = entry
            exit_ret = np.nan
            exit_reason = "PENDING"

            for j in range(i + 1, min(i + 1 + MAX_DAYS, n)):
                hj = h[j]; lj = l[j]
                if np.isnan(hj) or np.isnan(lj): continue
                if hj > peak:
                    peak = hj
                trail_stop = peak * (1 - trail)

                if trail_stop > entry and lj <= trail_stop:
                    exit_ret = (trail_stop / entry) - 1
                    exit_reason = "TRAIL"
                    break
                if lj <= sl_price:
                    exit_ret = -SL_PCT
                    exit_reason = "SL"
                    break

            if exit_reason == "PENDING":
                last_idx = min(i + 1 + MAX_DAYS, n) - 1
                if not np.isnan(c[last_idx]):
                    exit_ret = (c[last_idx] / entry) - 1
                    exit_reason = "HOLD"

            rows.append({
                "Date": dates[i],
                "Kode": kode,
                "gap_pct": gap_pct,
                "ret1": ret1[i], "ret3": ret3[i], "ret5": ret5[i],
                "ret10": ret10[i], "px20": px20[i], "px50": px50[i],
                "range": rng[i], "vol_z": vz[i], "atr": atr[i],
                "consec_up": cu[i], "hl5": hl5[i], "pos_52w": p52[i],
                "trail_cfg": key,
                "exit_ret": exit_ret * 100 if not np.isnan(exit_ret) else np.nan,
                "exit_reason": exit_reason,
            })

    return pd.DataFrame(rows) if rows else None


def main():
    print("="*95)
    print("WR90 HUNTER — Target WR ≥ 90%, N ≥ 1500")
    print("="*95)

    df = pd.read_parquet(FIXED_PARQUET)
    df = df.sort_values(["Kode", "Date"]).reset_index(drop=True)
    df = df[(df["Close"] >= MIN_PRICE) & (df["Volume"] >= MIN_VOLUME)].reset_index(drop=True)
    print(f"Data: {len(df):,}")

    print("Proses (20 workers)...")
    with concurrent.futures.ProcessPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(_process, (k, g)) for k, g in df.groupby("Kode")]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    sig_df = pd.concat([r for r in results if r is not None], ignore_index=True)
    sig_df = sig_df.dropna(subset=["exit_ret"]).reset_index(drop=True)
    print(f"Kandidat gap 2-20% × 4 trail configs: {len(sig_df):,}\n")

    # ============================================================
    # DEFINE BASE RULES (longgar)
    # ============================================================
    base_rules = {
        "A_Orig": (sig_df["ret1"] > 0.15) & (sig_df["ret5"] > 0.15) & (sig_df["px20"] > 0.20),
        "A_Loose": (sig_df["ret1"] > 0.10) & (sig_df["ret5"] > 0.10) & (sig_df["px20"] > 0.10),
        "A_Mid": (sig_df["ret1"] > 0.12) & (sig_df["ret5"] > 0.12) & (sig_df["px20"] > 0.15),
        "B_Loose": (sig_df["ret1"] > 0.10) & (sig_df["ret5"] > 0.15) & (sig_df["range"] > 0.08) & (sig_df["vol_z"] > 1.5),
        "New_C": (sig_df["ret3"] > 0.12) & (sig_df["px20"] > 0.15),
        "New_C2": (sig_df["ret3"] > 0.10) & (sig_df["px20"] > 0.10),
        "Union_AC": (
            ((sig_df["ret1"] > 0.10) & (sig_df["ret5"] > 0.10) & (sig_df["px20"] > 0.10)) |
            ((sig_df["ret3"] > 0.12) & (sig_df["px20"] > 0.15))
        ),
        "Union_ABC": (
            ((sig_df["ret1"] > 0.10) & (sig_df["ret5"] > 0.10) & (sig_df["px20"] > 0.10)) |
            ((sig_df["ret1"] > 0.10) & (sig_df["ret5"] > 0.15) & (sig_df["range"] > 0.08) & (sig_df["vol_z"] > 1.5)) |
            ((sig_df["ret3"] > 0.12) & (sig_df["px20"] > 0.15))
        ),
    }

    # ============================================================
    # GAP FILTERS
    # ============================================================
    gap_filters = {
        "Gap 2-20%": (sig_df["gap_pct"] >= 2) & (sig_df["gap_pct"] <= 20),
        "Gap 2-10%": (sig_df["gap_pct"] >= 2) & (sig_df["gap_pct"] <= 10),
        "Gap 2-15%": (sig_df["gap_pct"] >= 2) & (sig_df["gap_pct"] <= 15),
        "Gap 5-15%": (sig_df["gap_pct"] >= 5) & (sig_df["gap_pct"] <= 15),
        "Gap 3-20%": (sig_df["gap_pct"] >= 3) & (sig_df["gap_pct"] <= 20),
    }

    # ============================================================
    # QUALITY FILTERS
    # ============================================================
    quality_filters = {
        "none": pd.Series(True, index=sig_df.index),
        "ATR>3%": sig_df["atr"] > 0.03,
        "ATR>4%": sig_df["atr"] > 0.04,
        "52w>0.7": sig_df["pos_52w"] > 0.7,
        "52w>0.8": sig_df["pos_52w"] > 0.8,
        "HL3": sig_df["hl5"] >= 3,
        "HL4": sig_df["hl5"] >= 4,
        "CU3": sig_df["consec_up"] >= 3,
    }

    # ============================================================
    # TRAIL CONFIGS
    # ============================================================
    trail_configs = ["trail5", "trail7", "trail10", "trail12"]

    # ============================================================
    # GRID SEARCH
    # ============================================================
    print(f"{'='*95}")
    print(f"GRID SEARCH: {len(base_rules)} base × {len(gap_filters)} gap × {len(quality_filters)} quality × {len(trail_configs)} trail")
    print(f"Total: {len(base_rules) * len(gap_filters) * len(quality_filters) * len(trail_configs)}")
    print(f"{'='*95}\n")

    all_results = []
    for bname, bmask in base_rules.items():
        for gname, gmask in gap_filters.items():
            for qname, qmask in quality_filters.items():
                for tcfg in trail_configs:
                    mask = bmask.fillna(False) & gmask.fillna(False) & qmask.fillna(False)
                    sub = sig_df[mask & (sig_df["trail_cfg"] == tcfg)]
                    n = len(sub)
                    if n < 100: continue
                    wr = (sub["exit_ret"] > 0).mean() * 100
                    avg = sub["exit_ret"].mean()
                    sl_rate = (sub["exit_reason"] == "SL").mean() * 100
                    all_results.append({
                        "Base": bname, "Gap": gname, "Quality": qname, "Trail": tcfg,
                        "N": n, "WR": wr, "Avg": avg, "SL_rate": sl_rate,
                    })

    res_df = pd.DataFrame(all_results)
    print(f"Valid combos: {len(res_df):,}\n")

    # ============================================================
    # FILTER: WR ≥ 90% AND N ≥ 1500
    # ============================================================
    print(f"{'='*95}")
    print("🎯 TARGET: WR ≥ 90% AND N ≥ 1500")
    print(f"{'='*95}\n")

    hit_target = res_df[(res_df["WR"] >= 90) & (res_df["N"] >= 1500)].sort_values("WR", ascending=False)

    if len(hit_target) > 0:
        print(f"✅ FOUND {len(hit_target)} COMBOS!\n")
        print(f"{'#':<3} {'Base':<12} {'Gap':<10} {'Quality':<8} {'Trail':<8} {'N':<7} {'WR%':<7} {'Avg%':<8} {'SL%'}")
        print(f"{'-'*95}")
        for i, (_, r) in enumerate(hit_target.head(15).iterrows(), 1):
            m = " 🥇" if i == 1 else (" 🥈" if i == 2 else (" 🥉" if i == 3 else ""))
            print(f"{i:<3} {r['Base']:<12} {r['Gap']:<10} {r['Quality']:<8} {r['Trail']:<8} "
                  f"{r['N']:<7,} {r['WR']:>5.1f}  {r['Avg']:>+6.2f}  {r['SL_rate']:>4.1f}{m}")
    else:
        print("⚠️ Tidak ada yang WR ≥ 90% dengan N ≥ 1500.")
        print("Coba turunkan ke N ≥ 1200:\n")
        hit_target = res_df[(res_df["WR"] >= 90) & (res_df["N"] >= 1200)].sort_values("WR", ascending=False)
        if len(hit_target) > 0:
            print(f"{'#':<3} {'Base':<12} {'Gap':<10} {'Quality':<8} {'Trail':<8} {'N':<7} {'WR%':<7} {'Avg%':<8} {'SL%'}")
            print(f"{'-'*95}")
            for i, (_, r) in enumerate(hit_target.head(15).iterrows(), 1):
                print(f"{i:<3} {r['Base']:<12} {r['Gap']:<10} {r['Quality']:<8} {r['Trail']:<8} "
                      f"{r['N']:<7,} {r['WR']:>5.1f}  {r['Avg']:>+6.2f}  {r['SL_rate']:>4.1f}")

    # ============================================================
    # TOP WR OVERALL (any N ≥ 1000)
    # ============================================================
    print(f"\n{'='*95}")
    print("🏆 TOP 15 WR (N ≥ 1000)")
    print(f"{'='*95}\n")

    top_wr = res_df[res_df["N"] >= 1000].sort_values("WR", ascending=False).head(15)
    print(f"{'#':<3} {'Base':<12} {'Gap':<10} {'Quality':<8} {'Trail':<8} {'N':<7} {'WR%':<7} {'Avg%':<8} {'SL%'}")
    print(f"{'-'*95}")
    for i, (_, r) in enumerate(top_wr.iterrows(), 1):
        m = " 🥇" if i == 1 else (" 🥈" if i == 2 else (" 🥉" if i == 3 else ""))
        print(f"{i:<3} {r['Base']:<12} {r['Gap']:<10} {r['Quality']:<8} {r['Trail']:<8} "
              f"{r['N']:<7,} {r['WR']:>5.1f}  {r['Avg']:>+6.2f}  {r['SL_rate']:>4.1f}{m}")

    # ============================================================
    # PARETO (N vs WR) with N ≥ 1000
    # ============================================================
    print(f"\n{'='*95}")
    print("⚖️ PARETO OPTIMAL (N ≥ 1000)")
    print(f"{'='*95}\n")

    viable = res_df[res_df["N"] >= 1000].copy()
    viable_sorted = viable.sort_values("N", ascending=False)

    pareto = []
    for _, r in viable_sorted.iterrows():
        dominated = False
        for _, other in viable.iterrows():
            if other.name == r.name: continue
            if other["N"] >= r["N"] and other["WR"] >= r["WR"] and (other["N"] > r["N"] or other["WR"] > r["WR"]):
                dominated = True
                break
        if not dominated:
            pareto.append(r)

    print(f"{'Base':<12} {'Gap':<10} {'Quality':<8} {'Trail':<8} {'N':<7} {'WR%':<7} {'Avg%'}")
    print(f"{'-'*80}")
    for r in sorted(pareto, key=lambda x: x["N"], reverse=True):
        marker = ""
        if r["WR"] >= 90 and r["N"] >= 1500:
            marker = " ⭐ (TARGET HIT)"
        elif r["WR"] >= 90:
            marker = " 🟡 (WR ok, N < 1500)"
        print(f"{r['Base']:<12} {r['Gap']:<10} {r['Quality']:<8} {r['Trail']:<8} "
              f"{r['N']:<7,} {r['WR']:>5.1f}  {r['Avg']:>+6.2f}{marker}")

    # ============================================================
    # EFEKTIVITAS FILTER
    # ============================================================
    print(f"\n{'='*95}")
    print("📊 EFEKTIVITAS FILTER (dari TOP 30 WR tertinggi, N ≥ 1000)")
    print(f"{'='*95}\n")

    top30 = res_df[res_df["N"] >= 1000].sort_values("WR", ascending=False).head(30)

    print("Quality filter yang sering muncul:")
    for q, cnt in top30["Quality"].value_counts().items():
        print(f"  {q:<10} {cnt}x")

    print("\nGap filter yang sering muncul:")
    for g, cnt in top30["Gap"].value_counts().items():
        print(f"  {g:<10} {cnt}x")

    print("\nTrail config yang sering muncul:")
    for t, cnt in top30["Trail"].value_counts().items():
        print(f"  {t:<10} {cnt}x")

    print("\nBase rule yang sering muncul:")
    for b, cnt in top30["Base"].value_counts().items():
        print(f"  {b:<12} {cnt}x")


if __name__ == "__main__":
    main()