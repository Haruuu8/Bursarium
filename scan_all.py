"""Scan SEMUA setup → simpan ke JSON. Jalankan sekali sehari setelah update."""
import json
import time
from pathlib import Path

OUT_DIR = Path("data_scans")
OUT_DIR.mkdir(exist_ok=True)


def scan_precross():
    print("  [1/4] Pre-Cross 85+...")
    from quant.pre_cross import scan_pre_cross
    r = scan_pre_cross()
    with open(OUT_DIR / "precross.json", "w") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"),
                    "items": r or []}, f, ensure_ascii=False, default=str)
    print(f"      → {len(r or [])} saham")


def scan_emerging():
    print("  [2/4] Emerging 65-84...")
    from quant.pre_cross import scan_emerging_pre_cross
    r = scan_emerging_pre_cross(min_skor=65, max_skor=84, max_gap=5.0)
    with open(OUT_DIR / "emerging.json", "w") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"),
                    "items": r or []}, f, ensure_ascii=False, default=str)
    print(f"      → {len(r or [])} saham")


def scan_bottom():
    print("  [3/4] Bottom Fishing...")
    import sys
    sys.path.insert(0, ".")
    import pandas as pd
    import numpy as np
    import os
    from quant.rsi import _cek_df_hidup

    OHLCV_DIR = "data_ohlcv_idx"
    FUND_DIR = "data_fundamental"

    def hitung_rsi(series, periode=14):
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        ag = gain.ewm(alpha=1/periode, adjust=False, min_periods=periode).mean()
        al = loss.ewm(alpha=1/periode, adjust=False, min_periods=periode).mean()
        rs = ag / al.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def cek_kualitas_fund(fund, strict=True):
        """Cek fundamental dengan SEMUA rule:
        - Q1 + Q2 ada, se-tahun, Q2 standalone >= 0
        - Laba tidak turun drastis (> 50%)
        - Revenue YoY tidak turun > 30%
        - DER < 2.0
        - ROE > 10%
        - Pengecualian: premium ekspansi (ROE>15 + Rev>10 + DER<1)
        """
        if not fund:
            return False, "No fundamental", {}
        rk = fund.get("rasio_kunci", {}) or {}
        q = fund.get("quarterly", {}) or {}
        m = {"roe": None, "der": None, "ni_growth": None,
             "rev_growth": None, "special_flag": None}

        ni_q = q.get("net_income", {}) or {}
        if not ni_q:
            return False, "No quarterly", m
        keys = sorted(ni_q.keys(), reverse=True)
        if len(keys) < 2:
            return False, f"Hanya {len(keys)} kuartal", m
        if keys[0].split("-")[0] != keys[1].split("-")[0]:
            return False, "Tidak se-tahun", m

        try:
            cl = float(ni_q[keys[0]])
            cp = float(ni_q[keys[1]])
        except Exception:
            return False, "Invalid", m

        standalone = cl - cp

        roe = rk.get("roe")
        roe_val = None
        if roe:
            try:
                roe_val = float(roe)
                if abs(roe_val) < 1:
                    roe_val *= 100
                m["roe"] = roe_val
            except Exception:
                pass

        rev_yoy = None
        rev_q = q.get("revenue", {}) or {}
        if rev_q:
            try:
                year_now, q_now = keys[0].split("-")
                yoy_l = f"{int(year_now)-1}-{q_now}"
                if yoy_l in rev_q and keys[0] in rev_q:
                    rn = float(rev_q[keys[0]])
                    rp = float(rev_q[yoy_l])
                    if rp > 0:
                        rev_yoy = (rn - rp) / rp * 100
                        m["rev_growth"] = rev_yoy
            except Exception:
                pass

        de = rk.get("de")
        de_val = None
        if de:
            try:
                de_val = float(de)
                if de_val > 5:
                    de_val /= 100
                m["der"] = de_val
            except Exception:
                pass

        is_premium = (
            roe_val is not None and roe_val > 15 and
            rev_yoy is not None and rev_yoy > 10 and
            de_val is not None and de_val < 1.0
        )

        if standalone < 0 and not is_premium:
            return False, f"Q2 standalone negatif ({standalone/1e9:.1f}B)", m

        if cl > 0 and cp > 0 and (cl - cp) / cp * 100 < -50 and not is_premium:
            return False, "Laba turun drastis", m

        if strict and rev_yoy is not None and rev_yoy < -30:
            return False, f"Revenue turun YoY {rev_yoy:.0f}%", m

        if strict and de_val is not None and de_val > 2.0:
            return False, f"DER {de_val:.2f}", m

        if strict and roe_val is not None and roe_val < 10:
            return False, f"ROE {roe_val:.1f}%", m

        return True, "OK", m

    files = sorted([f for f in os.listdir(OHLCV_DIR) if f.endswith(".csv")])
    rows = []
    for f in files:
        kode = f.replace(".csv", "")
        p = os.path.join(OHLCV_DIR, f)
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if not _cek_df_hidup(df):
            continue
        df.columns = [str(c).strip().title() for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated(keep="first")]
        if "Close" not in df.columns or len(df) < 20:
            continue
        try:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date").reset_index(drop=True)
        except Exception:
            continue
        for c in ["Open", "High", "Low", "Close"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        rsi = hitung_rsi(df["Close"], 14)
        rsi_now = rsi.iloc[-1]
        if pd.isna(rsi_now) or rsi_now > 40:
            continue

        fp = os.path.join(FUND_DIR, f"{kode}.json")
        fund = None
        if os.path.exists(fp):
            try:
                fund = json.load(open(fp, encoding="utf-8"))
            except Exception:
                pass

        passed, reason, m = cek_kualitas_fund(fund, strict=True)
        if not passed:
            continue

        rsi_prev = rsi.iloc[-2] if len(rsi) > 1 else rsi_now
        try:
            h = float(df["Close"].iloc[-1])
        except Exception:
            h = 0
        rows.append({
            "kode": kode, "harga": round(h, 0),
            "rsi": round(float(rsi_now), 2),
            "rsi_change": round(float(rsi_now - rsi_prev), 2),
            "ni_growth": m.get("ni_growth"),
            "rev_growth": m.get("rev_growth"),
            "der": m.get("der"), "roe": m.get("roe"),
            "special_flag": m.get("special_flag"),
        })

    rows.sort(key=lambda x: x["rsi"])
    with open(OUT_DIR / "bottom.json", "w") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"),
                    "items": rows}, f, ensure_ascii=False, default=str)
    print(f"      → {len(rows)} saham")


# ============================================================
# SCAN SETUPS — SWING_W5 (91% WR)
# ============================================================
def scan_setups():
    """
    Generate data_setups.json dari supres.py (swing_w5, 91% WR support).

    BUY SUPPORT:
    - role='buy_limit'
    - Harga 0-5% di atas zona atau di dalam zona
    - RR >= 1.5
    - Entry = zona_hi, SL = zona_lo × 0.99, TP1 = next resistance atau 2R

    BREAKOUT:
    - role='breakout_trigger'
    - Harga 0-3% di bawah resistance
    - RR >= 1.5
    - Entry = zona_hi × 1.001, SL = zona_lo × 0.995, TP1 = next resistance atau 2R

    Sort: imminence × score, limit top 30 support & top 20 breakout.
    """
    print("  [4/4] Setups (Buy Support + Breakout) — swing_w5 91% WR...")

    from quant.supres import get_support_resistance
    from quant.parquet_loader import load_parquet_safe

    df_all = load_parquet_safe()
    if df_all is None or df_all.empty:
        print("      ⚠️  Gagal load parquet")
        sup, brk = [], []
    else:
        df_all["Kode"] = df_all["Kode"].astype(str).str.strip().str.upper()
        kodes = sorted(df_all["Kode"].unique())

        sup = []
        brk = []

        for i, kode in enumerate(kodes, 1):
            try:
                sr = get_support_resistance(kode, timeframe="daily")
                if not sr:
                    continue

                current = sr["current_price"]
                if current <= 0:
                    continue

                # ============================================================
                # BUY SUPPORT
                # ============================================================
                for z in sr["supports"]:
                    if z.get("role") != "buy_limit":
                        continue

                    zona_lo = z["lower"]
                    zona_hi = z["upper"]

                    # Filter kedekatan: harga 0-5% di atas zona atau di dalam zona
                    if current < zona_lo * 0.99:
                        continue
                    if current > zona_hi * 1.05:
                        continue

                    entry = zona_hi
                    sl = zona_lo * 0.99

                    risk = entry - sl
                    if risk <= 0:
                        continue
                    risk_pct = risk / entry * 100

                    # TP1: next resistance, fallback 2R
                    tp1 = None
                    for r in sr["resistances"]:
                        if r["level"] > entry * 1.02 and r.get("role") == "breakout_trigger":
                            tp1 = r["level"]
                            break
                    if tp1 is None:
                        tp1 = entry + 2 * risk

                    rr_tp1 = (tp1 - entry) / risk
                    jarak = (entry - current) / current * 100

                    if rr_tp1 < 1.5:
                        continue

                    if jarak < 0:
                        imminence = max(0, 1 - abs(jarak) / 5)
                    else:
                        imminence = 1.0

                    sup.append({
                        "kode": kode,
                        "harga": current,
                        "entry": round(entry, 2),
                        "sl": round(sl, 2),
                        "tp1": round(tp1, 2),
                        "tp2": None,
                        "rr_tp1": round(rr_tp1, 2),
                        "rr_tp2": None,
                        "risk_pct": round(risk_pct, 2),
                        "jarak_entry_pct": round(jarak, 2),
                        "zona_lo": zona_lo,
                        "zona_hi": zona_hi,
                        "lot": 0,
                        "_source": "swing_w5",
                        "_score": z.get("score", 8.0),
                        "_strength": z.get("strength", "MODERATE"),
                        "_imminence": round(imminence, 3),
                    })

                # ============================================================
                # BREAKOUT
                # ============================================================
                for z in sr["resistances"]:
                    if z.get("role") != "breakout_trigger":
                        continue

                    zona_lo = z["lower"]
                    zona_hi = z["upper"]

                    # Filter kedekatan: harga 0-3% di bawah resistance
                    if current > zona_hi * 1.005:
                        continue
                    if current < zona_lo * 0.97:
                        continue

                    entry = zona_hi * 1.001
                    sl = zona_lo * 0.995

                    risk = entry - sl
                    if risk <= 0:
                        continue
                    risk_pct = risk / entry * 100

                    tp1 = None
                    for r in sr["resistances"]:
                        if r["level"] > entry * 1.02 and r.get("role") in ("breakout_trigger", "reversal_warning"):
                            if r["level"] != z["level"]:
                                tp1 = r["level"]
                                break
                    if tp1 is None:
                        tp1 = entry + 2 * risk

                    rr_tp1 = (tp1 - entry) / risk
                    jarak = (entry - current) / current * 100

                    if rr_tp1 < 1.5:
                        continue
                    if jarak < 0 or jarak > 3:
                        continue

                    imminence = max(0, 1 - jarak / 3)

                    brk.append({
                        "kode": kode,
                        "harga": current,
                        "entry": round(entry, 2),
                        "sl": round(sl, 2),
                        "tp1": round(tp1, 2),
                        "tp2": None,
                        "rr_tp1": round(rr_tp1, 2),
                        "rr_tp2": None,
                        "risk_pct": round(risk_pct, 2),
                        "jarak_entry_pct": round(jarak, 2),
                        "zona_lo": zona_lo,
                        "zona_hi": zona_hi,
                        "lot": 0,
                        "_source": "swing_w5",
                        "_score": z.get("score", 8.0),
                        "_strength": z.get("strength", "MODERATE"),
                        "_imminence": round(imminence, 3),
                    })
            except Exception:
                continue

            if i % 100 == 0 or i == len(kodes):
                print(f"      [{i}/{len(kodes)}] S={len(sup)} B={len(brk)}", flush=True)

        # Sort: imminence × score × RR
        sup.sort(key=lambda x: (-x["_imminence"], -x["_score"], -x["rr_tp1"]))
        brk.sort(key=lambda x: (-x["_imminence"], -x["_score"], -x["rr_tp1"]))

        # Limit top N (buang yang kurang imminent)
        sup = sup[:30]
        brk = brk[:20]

    # Save
    with open(Path("data_setups.json"), "w") as f:
        json.dump({
            "generated": time.strftime("%Y-%m-%d %H:%M"),
            "method": "swing_w5",
            "buy_support": sup,
            "breakout_buy": brk,
        }, f, ensure_ascii=False, default=str)

    print(f"      → {len(sup)} Buy Support · {len(brk)} Breakout Buy")


def main():
    print("=" * 55)
    print(f"SCAN ALL — {time.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)
    t0 = time.time()

    try:
        scan_precross()
    except Exception as e:
        print(f"      ERROR: {e}")

    try:
        scan_emerging()
    except Exception as e:
        print(f"      ERROR: {e}")

    try:
        scan_bottom()
    except Exception as e:
        print(f"      ERROR: {e}")

    try:
        scan_setups()
    except Exception as e:
        print(f"      ERROR: {e}")

    print("=" * 55)
    print(f"Selesai: {time.time()-t0:.0f} detik")
    print(f"Output: data_scans/ + data_setups.json")
    print("=" * 55)


if __name__ == "__main__":
    main()