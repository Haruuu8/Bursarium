"""
backtest_accumulation.py

Verifikasi statistik: apakah "akumulasi signal" (CLV>60% + CMF>0 + Vol>2× + hijau)
benar-benar precede kenaikan harga, dan distribusi tersamar (CLV<30% + Vol>2×)
benar-benar precede penurunan?

Jalankan:
    python backtest_accumulation.py
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant.parquet_loader import load_parquet_safe


# ============================================================
# KONFIGURASI
# ============================================================
HORIZONS = [1, 3, 5, 10, 20]
COOLDOWN_DAYS = 5     # skip signal kalau saham sama sudah signal dalam N hari
GAP_MIN = 0.02        # gap T+1 minimal (sama dengan production)
GAP_MAX = 0.20        # gap T+1 maksimal
OUTPUT_CSV = "backtest_accumulation.csv"


# ============================================================
# LOAD & PREPARE
# ============================================================
def prepare_data():
    print("📥 Loading parquet...")
    df = load_parquet_safe()
    if df is None or df.empty:
        print("❌ Data tidak tersedia.")
        sys.exit(1)

    df = df.copy()
    df["Kode"] = df["Kode"].astype(str).str.strip().str.upper()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    for c in ["Open", "High", "Low", "Close", "Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[df["Close"] > 0]
    df = df.sort_values(["Kode", "Date"]).reset_index(drop=True)

    print(f"   {df['Kode'].nunique()} saham · {len(df):,} bar · "
          f"{df['Date'].min().date()} → {df['Date'].max().date()}")

    print("🔧 Computing indicators (Vol_Ratio, CLV, CMF)...")
    g = df.groupby("Kode", group_keys=False)

    df["Vol_MA20"] = g["Volume"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    df["Vol_Ratio"] = df["Volume"] / df["Vol_MA20"]

    rng = (df["High"] - df["Low"]).replace(0, np.nan)
    df["Close_Pct"] = (df["Close"] - df["Low"]) / rng
    df["MFM"] = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / rng
    df["MFV"] = df["MFM"] * df["Volume"]
    df["CMF_20"] = (
        g["MFV"].transform(lambda x: x.rolling(20, min_periods=10).sum())
        / g["Volume"].transform(lambda x: x.rolling(20, min_periods=10).sum())
    )

    print("📊 Computing forward returns & forward max/min...")

    # Entry = T+1 open
    df["entry_T1"] = g["Open"].shift(-1)
    # Gap T+1 = (open_T1 / close_T) - 1
    df["gap_T1"] = (df["entry_T1"] / df["Close"]) - 1

    def fwd_roll_max(s, h):
        return s.iloc[::-1].rolling(h, min_periods=1).max().iloc[::-1].shift(-1)

    def fwd_roll_min(s, h):
        return s.iloc[::-1].rolling(h, min_periods=1).min().iloc[::-1].shift(-1)

    for h in HORIZONS:
        # Exit = T+h close
        df[f"close_T{h}"] = g["Close"].shift(-h)
        df[f"ret_T{h}"] = (df[f"close_T{h}"] / df["entry_T1"]) - 1

        # Forward max high & min low dari T+1 s/d T+h
        df[f"maxhigh_T{h}"] = g["High"].transform(lambda s, hh=h: fwd_roll_max(s, hh))
        df[f"minlow_T{h}"] = g["Low"].transform(lambda s, hh=h: fwd_roll_min(s, hh))

        df[f"maxgain_T{h}"] = (df[f"maxhigh_T{h}"] / df["entry_T1"]) - 1
        df[f"maxdd_T{h}"] = (df[f"minlow_T{h}"] / df["entry_T1"]) - 1

    return df


# ============================================================
# SIGNAL MASKS
# ============================================================
def build_masks(df):
    """Definisikan mask untuk tiap kelompok signal."""
    base_valid = (
        df["entry_T1"].notna()
        & (df["entry_T1"] > 0)
        & df["Vol_Ratio"].notna()
        & df["Close_Pct"].notna()
        & df["CMF_20"].notna()
    )

    vol_spike = (
        base_valid
        & (df["Vol_Ratio"] > 2)
        & (df["Vol_Ratio"] < 50)
        & (df["Volume"] > 0)
    )

    accum = (
        vol_spike
        & (df["Close"] > df["Open"])
        & (df["Close_Pct"] > 0.6)
        & (df["CMF_20"] > 0)
    )

    dist = (
        vol_spike
        & (df["Close_Pct"] < 0.3)
    )

    old_filter = (
        vol_spike
        & (df["Close"] > df["Open"])
    )

    return {
        "Akumulasi (baru)": accum,
        "Distribusi tersamar": dist,
        "Filter lama (close>open saja)": old_filter,
        "Baseline (semua bar)": base_valid,
    }


def apply_cooldown(df, mask, cooldown=COOLDOWN_DAYS):
    """Skip signal kalau saham sama sudah signal dalam N hari terakhir."""
    idx = df.index[mask]
    sub = df.loc[idx, ["Kode", "Date"]].sort_values(["Kode", "Date"])
    keep = []
    last = {}
    for i, row in sub.iterrows():
        k = row["Kode"]
        d = row["Date"]
        if k in last and (d - last[k]).days < cooldown:
            continue
        keep.append(i)
        last[k] = d
    return pd.Series(df.index.isin(keep), index=df.index) & mask


# ============================================================
# STATS PER SIGNAL
# ============================================================
def compute_stats(df, mask, label, horizons):
    sub = df[mask].copy()
    rows = []
    for h in horizons:
        ret = sub[f"ret_T{h}"].dropna()
        dd = sub[f"maxdd_T{h}"].dropna()
        mg = sub[f"maxgain_T{h}"].dropna()
        n = len(ret)
        if n == 0:
            rows.append({
                "signal": label, "horizon": f"T+{h}", "n": 0,
                "wr": np.nan, "wr_3": np.nan, "wr_neg3": np.nan,
                "avg": np.nan, "median": np.nan,
                "best": np.nan, "worst": np.nan,
                "avg_maxdd": np.nan, "avg_maxgain": np.nan,
            })
            continue
        rows.append({
            "signal": label,
            "horizon": f"T+{h}",
            "n": n,
            "wr": (ret > 0).mean() * 100,
            "wr_3": (ret > 0.03).mean() * 100,
            "wr_neg3": (ret < -0.03).mean() * 100,
            "avg": ret.mean() * 100,
            "median": ret.median() * 100,
            "best": ret.max() * 100,
            "worst": ret.min() * 100,
            "avg_maxdd": dd.mean() * 100 if len(dd) else np.nan,
            "avg_maxgain": mg.mean() * 100 if len(mg) else np.nan,
        })
    return pd.DataFrame(rows)


def print_table(df_stats, title):
    print()
    print("=" * 110)
    print(f"  {title}")
    print("=" * 110)
    if df_stats.empty:
        print("  (no data)")
        return
    fmt = df_stats.copy()
    for c in ["wr", "wr_3", "wr_neg3", "avg", "median", "best", "worst",
              "avg_maxdd", "avg_maxgain"]:
        if c in fmt.columns:
            fmt[c] = fmt[c].apply(lambda v: f"{v:+.2f}" if pd.notna(v) else "—")
    fmt = fmt.rename(columns={
        "signal": "Signal", "horizon": "Horizon", "n": "N",
        "wr": "WR%", "wr_3": "WR>3%", "wr_neg3": "WR<-3%",
        "avg": "Avg%", "median": "Med%", "best": "Best%", "worst": "Worst%",
        "avg_maxdd": "AvgMaxDD%", "avg_maxgain": "AvgMaxGain%",
    })
    print(fmt.to_string(index=False))


# ============================================================
# EDGE VS BASELINE
# ============================================================
def print_edge(df_all, horizons):
    print()
    print("=" * 110)
    print("  EDGE vs BASELINE (selisih avg return T+h)")
    print("=" * 110)

    base = df_all[df_all["signal"] == "Baseline (semua bar)"].set_index("horizon")
    for sig in ["Akumulasi (baru)", "Distribusi tersamar", "Filter lama (close>open saja)"]:
        sub = df_all[df_all["signal"] == sig].set_index("horizon")
        if sub.empty:
            continue
        print(f"\n  {sig}:")
        for h in horizons:
            tag = f"T+{h}"
            if tag not in sub.index or tag not in base.index:
                continue
            a = sub.loc[tag, "avg"]
            b = base.loc[tag, "avg"]
            a_wr = sub.loc[tag, "wr"]
            b_wr = base.loc[tag, "wr"]
            if pd.isna(a) or pd.isna(b):
                continue
            edge = a - b
            edge_wr = a_wr - b_wr
            mark = "✅" if edge > 0 else "❌"
            print(f"    {tag:>4}  AvgRet: {a:+.2f}%  vs base {b:+.2f}%  "
                  f"→ edge {edge:+.2f}% {mark}   "
                  f"|  WR: {a_wr:.1f}% vs {b_wr:.1f}%  edge {edge_wr:+.1f}%")


# ============================================================
# VERDICT
# ============================================================
def print_verdict(df_all, horizons):
    print()
    print("=" * 110)
    print("  VERDICT")
    print("=" * 110)

    base = df_all[df_all["signal"] == "Baseline (semua bar)"].set_index("horizon")
    accum = df_all[df_all["signal"] == "Akumulasi (baru)"].set_index("horizon")
    dist = df_all[df_all["signal"] == "Distribusi tersamar"].set_index("horizon")
    old = df_all[df_all["signal"] == "Filter lama (close>open saja)"].set_index("horizon")

    checks = []

    # Check 1: akumulasi WR > baseline WR (di T+5)
    if "T+5" in accum.index and "T+5" in base.index:
        a_wr = accum.loc["T+5", "wr"]
        b_wr = base.loc["T+5", "wr"]
        checks.append((
            f"Akumulasi WR(T+5) > Baseline  ({a_wr:.1f}% vs {b_wr:.1f}%)",
            a_wr > b_wr,
        ))

    # Check 2: akumulasi avg return > baseline avg return (T+5)
    if "T+5" in accum.index and "T+5" in base.index:
        a_ret = accum.loc["T+5", "avg"]
        b_ret = base.loc["T+5", "avg"]
        checks.append((
            f"Akumulasi AvgRet(T+5) > Baseline  ({a_ret:+.2f}% vs {b_ret:+.2f}%)",
            a_ret > b_ret,
        ))

    # Check 3: distribusi avg return < baseline
    if "T+5" in dist.index and "T+5" in base.index:
        d_ret = dist.loc["T+5", "avg"]
        b_ret = base.loc["T+5", "avg"]
        checks.append((
            f"Distribusi AvgRet(T+5) < Baseline  ({d_ret:+.2f}% vs {b_ret:+.2f}%)",
            d_ret < b_ret,
        ))

    # Check 4: akumulasi > filter lama
    if "T+5" in accum.index and "T+5" in old.index:
        a_ret = accum.loc["T+5", "avg"]
        o_ret = old.loc["T+5", "avg"]
        checks.append((
            f"Akumulasi AvgRet(T+5) > Filter Lama  ({a_ret:+.2f}% vs {o_ret:+.2f}%)",
            a_ret > o_ret,
        ))

    if not checks:
        print("  ⚠️ Tidak cukup data untuk verdict.")
        return

    for desc, ok in checks:
        print(f"  {'✅' if ok else '❌'}  {desc}")

    n_pass = sum(1 for _, ok in checks if ok)
    print()
    if n_pass == len(checks):
        print("  🏆 SEMUA CHECK LULUS — filter akumulasi valid dan lebih baik dari filter lama.")
    elif n_pass >= len(checks) * 0.75:
        print(f"  ✅ {n_pass}/{len(checks)} check lulus — filter akumulasi cukup valid.")
    else:
        print(f"  ⚠️  {n_pass}/{len(checks)} check lulus — perlu review threshold.")


# ============================================================
# SPOT-CHECK: SAMPLE SIGNALS
# ============================================================
def print_samples(df, mask, label, n=5):
    sub = df[mask].copy()
    sub = sub.dropna(subset=["ret_T5"])
    if sub.empty:
        return

    sub = sub.sort_values("ret_T5", ascending=False)

    print()
    print("=" * 110)
    print(f"  SAMPLE — {label}")
    print("=" * 110)

    print(f"\n  Top {n} (gain terbesar di T+5):")
    cols = ["Date", "Kode", "Close", "Close_Pct", "CMF_20", "Vol_Ratio",
            "gap_T1", "ret_T5", "maxgain_T5", "maxdd_T5"]
    cols = [c for c in cols if c in sub.columns]
    top = sub[cols].head(n).copy()
    for c in ["Close_Pct"]:
        if c in top.columns:
            top[c] = top[c] * 100
    for c in ["gap_T1", "ret_T5", "maxgain_T5", "maxdd_T5"]:
        if c in top.columns:
            top[c] = top[c] * 100
    top["Date"] = top["Date"].dt.strftime("%Y-%m-%d")
    print(top.round(2).to_string(index=False))

    print(f"\n  Bottom {n} (loss terbesar di T+5) — cek apakah false positive:")
    bot = sub[cols].tail(n).copy()
    for c in ["Close_Pct"]:
        if c in bot.columns:
            bot[c] = bot[c] * 100
    for c in ["gap_T1", "ret_T5", "maxgain_T5", "maxdd_T5"]:
        if c in bot.columns:
            bot[c] = bot[c] * 100
    bot["Date"] = bot["Date"].dt.strftime("%Y-%m-%d")
    print(bot.round(2).to_string(index=False))


# ============================================================
# WITH GAP FILTER (PRODUCTION REALISTIC)
# ============================================================
def compute_with_gap(df, mask, label, horizons):
    """Backtest yang lebih realistis: filter gap T+1 2-20% (sesuai production)."""
    gap_mask = mask & (df["gap_T1"] >= GAP_MIN) & (df["gap_T1"] <= GAP_MAX)
    return compute_stats(df, gap_mask, label, horizons)


# ============================================================
# MAIN
# ============================================================
def main():
    print()
    print("=" * 110)
    print("  BACKTEST: APAKAH AKUMULASI SIGNAL BENAR-BENAR PRECEDE KENAIKAN?")
    print("=" * 110)

    df = prepare_data()

    print("\n🎯 Building signal masks...")
    masks = build_masks(df)

    # Counts
    print()
    print("=" * 110)
    print("  DISTRIBUSI SIGNAL")
    print("=" * 110)
    for label, m in masks.items():
        print(f"  {label:<35} : {m.sum():>7,} bar  ({m.sum()/len(df)*100:5.2f}%)")

    # Apply cooldown untuk signal (bukan baseline)
    print(f"\n🔁 Apply cooldown {COOLDOWN_DAYS} hari (hindari overlap sinyal beruntun)...")
    masks_clean = {}
    for label, m in masks.items():
        if label == "Baseline (semua bar)":
            masks_clean[label] = m
        else:
            masks_clean[label] = apply_cooldown(df, m, COOLDOWN_DAYS)
            print(f"  {label:<35} : {m.sum():>7,} → {masks_clean[label].sum():>7,} "
                  f"setelah dedup")

    # Stats per signal
    print("\n📊 Computing stats per signal...")
    all_stats = []
    for label, m in masks_clean.items():
        s = compute_stats(df, m, label, HORIZONS)
        all_stats.append(s)
    df_all = pd.concat(all_stats, ignore_index=True)

    # Print
    for label, m in masks_clean.items():
        sub_stats = df_all[df_all["signal"] == label].reset_index(drop=True)
        print_table(sub_stats, f"SIGNAL: {label}  (N={m.sum():,} bar)")

    # Edge
    print_edge(df_all, HORIZONS)

    # Verdict
    print_verdict(df_all, HORIZONS)

    # Spot check
    print_samples(df, masks_clean["Akumulasi (baru)"],
                  "Akumulasi — top vs bottom performer T+5", n=5)
    print_samples(df, masks_clean["Distribusi tersamar"],
                  "Distribusi — top vs bottom performer T+5", n=5)

    # Realistic (with gap filter)
    print()
    print("=" * 110)
    print(f"  PRODUCTION-REALISTIC: + GAP FILTER T+1 {GAP_MIN*100:.0f}%–{GAP_MAX*100:.0f}%")
    print("=" * 110)
    gap_stats = []
    for label in ["Akumulasi (baru)", "Filter lama (close>open saja)"]:
        s = compute_with_gap(df, masks_clean[label], label + " [gap filtered]", HORIZONS)
        gap_stats.append(s)
    df_gap = pd.concat(gap_stats, ignore_index=True)
    for label in ["Akumulasi (baru) [gap filtered]",
                  "Filter lama (close>open saja) [gap filtered]"]:
        sub_stats = df_gap[df_gap["signal"] == label].reset_index(drop=True)
        print_table(sub_stats, label)

    # Save CSV
    df_all.to_csv(OUTPUT_CSV, index=False)
    print()
    print(f"💾 Hasil lengkap tersimpan di: {OUTPUT_CSV}")

    print()
    print("=" * 110)
    print("  SELESAI")
    print("=" * 110)


if __name__ == "__main__":
    main()