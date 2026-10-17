"""
Analisis tier harga & likuiditas: apakah saham kelas tertentu lebih prediktif?
"""

import numpy as np
import pandas as pd

from .data_loader import load_panel_from_gabungan
from .data_cleaner import clean_panel
from .feature_engineering import build_features
from .event_detector import detect_events


EVENT_TARGET = "is_touch_10pct"


def add_tier_features(df):
    df = df.copy()

    # Tier harga
    df["tier_gocap"] = (df["close"] < 100).astype(int)
    df["tier_kecil"] = ((df["close"] >= 100) & (df["close"] < 500)).astype(int)
    df["tier_menengah"] = ((df["close"] >= 500) & (df["close"] < 2000)).astype(int)
    df["tier_besar"] = (df["close"] >= 2000).astype(int)

    # Tier likuiditas (value traded)
    df["tier_likuid_rendah"] = (df["value"] < 1e9).astype(int)
    df["tier_likuid_med"] = ((df["value"] >= 1e9) & (df["value"] < 5e9)).astype(int)
    df["tier_likuid_tinggi"] = (df["value"] >= 5e9).astype(int)

    df["event_next"] = (
        df.groupby("kode")[EVENT_TARGET]
             .shift(-1).fillna(0).astype(int)
    )
    return df


def main():
    print("=" * 100)
    print("ANALISIS TIER HARGA & LIKUIDITAS")
    print("=" * 100)

    panel = load_panel_from_gabungan()
    panel = clean_panel(panel)
    panel = build_features(panel)
    panel = detect_events(panel)
    panel = add_tier_features(panel)
    panel = panel[(panel["open"] > 0) & (panel["close"] > 0)].copy()

    baseline = panel["event_next"].mean()
    print(f"\nTotal: {len(panel):,}, baseline {baseline*100:.2f}%")

    print(f"\n{'='*100}")
    print("A. TIER HARGA")
    print(f"{'='*100}\n")
    print(f"{'Tier':<15} {'n':>7} {'prec%':>8} {'lift':>7}")
    print("-" * 45)

    tiers = [
        ("Gocap (<100)", panel["tier_gocap"] == 1),
        ("Kecil (100-500)", panel["tier_kecil"] == 1),
        ("Menengah (500-2k)", panel["tier_menengah"] == 1),
        ("Besar (>=2k)", panel["tier_besar"] == 1),
    ]

    for label, mask in tiers:
        sub = panel[mask]
        if len(sub) < 100:
            continue
        prec = sub["event_next"].mean()
        print(f"{label:<15} {len(sub):>7} {prec*100:>7.2f}% "
              f"{prec/baseline:>6.2f}x")

    print(f"\n{'='*100}")
    print("B. TIER LIKUIDITAS")
    print(f"{'='*100}\n")
    print(f"{'Tier':<20} {'n':>7} {'prec%':>8} {'lift':>7}")
    print("-" * 50)

    tiers_lik = [
        ("Likuid rendah (<1M)", panel["tier_likuid_rendah"] == 1),
        ("Likuid med (1-5M)", panel["tier_likuid_med"] == 1),
        ("Likuid tinggi (>=5M)", panel["tier_likuid_tinggi"] == 1),
    ]

    for label, mask in tiers_lik:
        sub = panel[mask]
        if len(sub) < 100:
            continue
        prec = sub["event_next"].mean()
        print(f"{label:<20} {len(sub):>7} {prec*100:>7.2f}% "
              f"{prec/baseline:>6.2f}x")

    print(f"\n{'='*100}")
    print("C. KOMBINASI RULE UTAMA + TIER")
    print(f"{'='*100}\n")

    # Rule multiday
    panel["ret_3d"] = panel.groupby("kode")["close"].pct_change(3)
    base_rule = lambda d: (d["gap"] > 0.05) & (d["ret_3d"] > 0.15)
    base_mask = base_rule(panel).fillna(False).values

    print(f"Rule dasar (gap>5% + ret_3d>15%):")
    sub_base = panel[base_mask]
    print(f"  n={len(sub_base)}, prec={sub_base['event_next'].mean()*100:.1f}%")

    print(f"\n{'Kondisi':<50} {'n':>6} {'prec%':>8}")
    print("-" * 70)

    for label, mask_col in [
        ("+ gocap", panel["tier_gocap"] == 1),
        ("+ kecil", panel["tier_kecil"] == 1),
        ("+ menengah", panel["tier_menengah"] == 1),
        ("+ besar", panel["tier_besar"] == 1),
        ("+ likuid rendah", panel["tier_likuid_rendah"] == 1),
        ("+ likuid med", panel["tier_likuid_med"] == 1),
        ("+ likuid tinggi", panel["tier_likuid_tinggi"] == 1),
    ]:
        m = base_mask & mask_col.values
        n = int(m.sum())
        if n < 10:
            continue
        prec = panel.loc[m, "event_next"].mean()
        print(f"gap>5% + ret_3d>15% {label:<25} {n:>6} {prec*100:>7.2f}%")


if __name__ == "__main__":
    main()