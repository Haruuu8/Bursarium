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
        - Revenue YoY tidak turun > 30%    ← FIX
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

        # ROE
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

        # Revenue YoY
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

        # DER
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

        # Premium ekspansi
        is_premium = (
            roe_val is not None and roe_val > 15 and
            rev_yoy is not None and rev_yoy > 10 and
            de_val is not None and de_val < 1.0
        )

        # === RULES ===
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


def scan_setups():
    print("  [4/4] Setups (Buy Support + Breakout)...")
    from quant.riskreward import hitung_rr_skenario
    files = sorted(Path("data_ohlcv_idx").glob("*.csv"))
    sup, brk = [], []
    for f in files:
        kode = f.stem
        try:
            rr = hitung_rr_skenario(kode)
        except Exception:
            continue
        if not rr:
            continue
        for s in rr.get("scenarios", []):
            if not s.get("lolos"):
                continue
            e = {
                "kode": kode,
                "harga": rr["current_price"],
                "entry": s["entry"],
                "sl": s["sl"],
                "tp1": s["tp1"],
                "tp2": s.get("tp2"),
                "rr_tp1": s["rr_tp1"],
                "rr_tp2": s.get("rr_tp2"),
                "risk_pct": s["risk_pct"],
                "jarak_entry_pct": s["jarak_entry_pct"],
                "zona_lo": s["zona_entry"][0],
                "zona_hi": s["zona_entry"][1],
                "lot": s.get("lot", 0),
            }
            if s["tipe"] == "BUY at Support":
                sup.append(e)
                break
            elif s["tipe"] == "BREAKOUT BUY":
                brk.append(e)
                break
    sup.sort(key=lambda x: -x["rr_tp1"])
    brk.sort(key=lambda x: -x["rr_tp1"])
    with open(Path("data_setups.json"), "w") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"),
                    "buy_support": sup,
                    "breakout_buy": brk},
                   f, ensure_ascii=False, default=str)
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