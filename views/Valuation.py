"""Halaman VALUATION - Fair Value (Conservative), Search, Top 10 Undervalued."""

import os
import sys
import json

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# GUARD LOGIN
# ============================================================
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

from quant.theme import (
    load_theme, page_header, section_title, empty_state, render_table,
)

load_theme()

FUND_DIR = "data_fundamental"
SEKTOR_CSV = "data_sektor.csv"

# ===== Konstanta valuasi (konservatif) =====
PE_HARD_CAP = 15.0
PB_HARD_CAP = 2.0
TARGET_DISCOUNT = 0.90
MARGIN_OF_SAFETY = 0.85
FV_CAP_RATIO = 2.0
PE_SUSPECT_LOW = 0.5
PE_SUSPECT_HIGH = 3.0


# ============================================================
# HELPERS
# ============================================================
@st.cache_data(ttl=3600)
def load_nama():
    nama = {}
    if os.path.exists(SEKTOR_CSV):
        try:
            df = pd.read_csv(SEKTOR_CSV)
            if "kode" in df.columns and "nama" in df.columns:
                for _, r in df.iterrows():
                    k = str(r["kode"]).strip().upper()
                    n = str(r["nama"]).strip()
                    if k and n and n.lower() != "nan":
                        nama[k] = n
        except Exception:
            pass
    return nama


def _num(v):
    if v is None:
        return np.nan
    try:
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            return np.nan
        return f
    except (ValueError, TypeError):
        return np.nan


def _parse_q(q_dict):
    if not q_dict:
        return []
    try:
        items = [(k, _num(v)) for k, v in q_dict.items()]
        items = [(k, v) for k, v in items if not pd.isna(v)]
        items.sort(key=lambda x: str(x[0]), reverse=True)
        return items
    except Exception:
        return []


@st.cache_data(ttl=1800)
def load_all_fundamental():
    if not os.path.exists(FUND_DIR):
        return pd.DataFrame()

    rows = []
    files = sorted([f for f in os.listdir(FUND_DIR) if f.endswith(".json")])

    for f in files:
        kode = f.replace(".json", "").upper()
        path = os.path.join(FUND_DIR, f)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue

        rk = d.get("rasio_kunci", {}) or {}
        quarterly = d.get("quarterly", {}) or {}

        q_eps = _parse_q((quarterly or {}).get("eps", {}))
        q_ni = _parse_q((quarterly or {}).get("net_income", {}))
        ref_q = q_eps if q_eps else q_ni
        n_q_neg = sum(1 for _, v in ref_q[:4] if not pd.isna(v) and v < 0)

        rows.append({
            "kode": kode,
            "nama": d.get("nama", ""),
            "sektor": d.get("sektor", "") or d.get("industri", "") or "default",
            "harga": _num(d.get("harga")),
            "eps": _num(rk.get("eps")),
            "eps_src": rk.get("eps_src", "?"),
            "eps_reliable": rk.get("eps_reliable", True),
            "bv": _num(rk.get("bv")),
            "bv_src": rk.get("bv_src", "?"),
            "pe": _num(rk.get("pe")),
            "pb": _num(rk.get("pb")),
            "roe": _num(rk.get("roe")),
            "de": _num(rk.get("de")),
            "margin_net": _num(rk.get("margin_net")),
            "n_q_neg": n_q_neg,
        })

    return pd.DataFrame(rows)


def fmt(v, dec=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    try:
        return f"{v:,.{dec}f}"
    except Exception:
        return "-"


def fmt_pct(v, dec=1, sign=False):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    try:
        return f"{v:+.{dec}f}%" if sign else f"{v:.{dec}f}%"
    except Exception:
        return "-"


# ============================================================
# SECTOR MEDIANS (dynamic)
# ============================================================
def compute_sector_medians(df):
    pe_valid = df[(df["pe"] > 3) & (df["pe"] < 50)]
    pb_valid = df[(df["pb"] > 0.2) & (df["pb"] < 8)]

    pe_med = pe_valid.groupby("sektor")["pe"].median().to_dict()
    pb_med = pb_valid.groupby("sektor")["pb"].median().to_dict()

    pe_def = float(pe_valid["pe"].median()) if len(pe_valid) else 12.0
    pb_def = float(pb_valid["pb"].median()) if len(pb_valid) else 1.2

    pe_med = {k: min(v, PE_HARD_CAP) for k, v in pe_med.items()}
    pb_med = {k: min(v, PB_HARD_CAP) for k, v in pb_med.items()}
    pe_def = min(pe_def, PE_HARD_CAP)
    pb_def = min(pb_def, PB_HARD_CAP)

    return pe_med, pb_med, pe_def, pb_def


# ============================================================
# VALUASI
# ============================================================
def hitung_valuasi(df,
                   min_roe=5.0, max_der=2.0,
                   min_pe=2.0, max_pe=30.0,
                   min_pb=0.2, max_pb=5.0,
                   require_positive_margin=True,
                   skip_inconsistent=True,
                   filter_suspect=True):
    d = df.copy()

    d["roe_pct"] = d["roe"].apply(
        lambda x: x * 100 if not pd.isna(x) and abs(x) < 1 else x
    )
    d["de_val"] = d["de"].apply(
        lambda x: x / 100 if not pd.isna(x) and x > 5 else x
    )

    pe_med, pb_med, pe_def, pb_def = compute_sector_medians(d)

    d["target_pe"] = d["sektor"].apply(lambda s: pe_med.get(s, pe_def)) * TARGET_DISCOUNT
    d["target_pb"] = d["sektor"].apply(lambda s: pb_med.get(s, pb_def)) * TARGET_DISCOUNT

    d["fv_graham"] = np.sqrt(22.5 * d["eps"].clip(lower=0) * d["bv"].clip(lower=0))
    d.loc[(d["eps"] <= 0) | (d["bv"] <= 0), "fv_graham"] = np.nan

    d["fv_pe"] = d["eps"] * d["target_pe"]
    d.loc[d["eps"] <= 0, "fv_pe"] = np.nan

    d["fv_pb"] = d["bv"] * d["target_pb"]
    d.loc[d["bv"] <= 0, "fv_pb"] = np.nan

    W = {"fv_graham": 0.40, "fv_pe": 0.30, "fv_pb": 0.30}

    def wfv(row):
        vals, ws = [], []
        for col, w in W.items():
            v = row[col]
            if not pd.isna(v) and v > 0:
                vals.append(v)
                ws.append(w)
        if not vals:
            return np.nan
        tw = sum(ws)
        return sum(v * w for v, w in zip(vals, ws)) / tw

    d["fv_raw"] = d.apply(wfv, axis=1)

    d["fv_cap_val"] = FV_CAP_RATIO * d["harga"]
    d["fv_capped"] = d["fv_raw"] > d["fv_cap_val"]
    d["fv"] = np.minimum(d["fv_raw"], d["fv_cap_val"])
    d["fv"] = d["fv"] * MARGIN_OF_SAFETY
    d["fv_capped"] = d["fv_capped"] | (d["fv_raw"] * MARGIN_OF_SAFETY > FV_CAP_RATIO * d["harga"])

    d["potential"] = (d["fv"] - d["harga"]) / d["harga"] * 100
    d["potential_raw"] = ((d["fv_raw"] * MARGIN_OF_SAFETY) - d["harga"]) / d["harga"] * 100

    d["pe_gap_ratio"] = d["pe"] / d["target_pe"]
    d["pe_suspect"] = (
        (d["pe"] > 0) &
        ((d["pe_gap_ratio"] < PE_SUSPECT_LOW) | (d["pe_gap_ratio"] > PE_SUSPECT_HIGH))
    )

    red = pd.Series("", index=d.index)
    red = red.mask(d["eps"].isna() | (d["eps"] <= 0), "EPS tidak valid")
    red = red.mask(d["bv"].isna() | (d["bv"] <= 0), "BV tidak valid")
    red = red.mask(d["roe_pct"].fillna(0) < min_roe, f"ROE < {min_roe}%")
    red = red.mask(d["de_val"].fillna(0) > max_der, f"DER > {max_der}")

    pe_ok = d["pe"].notna()
    red = red.mask(pe_ok & ((d["pe"] < min_pe) | (d["pe"] > max_pe)),
                    f"PE di luar {min_pe}-{max_pe}")
    pb_ok = d["pb"].notna()
    red = red.mask(pb_ok & ((d["pb"] < min_pb) | (d["pb"] > max_pb)),
                    f"PB di luar {min_pb}-{max_pb}")

    if require_positive_margin:
        red = red.mask(d["margin_net"].fillna(1) < 0, "Margin negatif")
    red = red.mask(d["n_q_neg"] >= 2, "2+ kuartal rugi")
    if skip_inconsistent:
        red = red.mask(d["eps_reliable"] == False, "EPS tidak konsisten")
    if filter_suspect:
        red = red.mask(d["fv_capped"], "FV di-cap (sanity)")
        red = red.mask(d["pe_suspect"], "PE terlalu jauh dari median")

    d["red_flag"] = red

    def skor(row):
        s = 0
        pot = row["potential"]
        if pd.isna(pot):
            s += 0
        elif pot > 40:
            s += 40
        elif pot > 30:
            s += 32
        elif pot > 20:
            s += 24
        elif pot > 10:
            s += 16
        elif pot > 0:
            s += 8

        roe = row["roe_pct"]
        if pd.isna(roe):
            s += 0
        elif roe > 25:
            s += 20
        elif roe > 20:
            s += 16
        elif roe > 15:
            s += 12
        elif roe > 10:
            s += 8
        elif roe > 5:
            s += 4

        de = row["de_val"]
        if pd.isna(de):
            s += 0
        elif de < 0.3:
            s += 20
        elif de < 0.6:
            s += 16
        elif de < 1.0:
            s += 12
        elif de < 1.5:
            s += 8
        elif de < 2.0:
            s += 4

        marg = row["margin_net"]
        if pd.isna(marg):
            s += 0
        elif marg > 0.20:
            s += 10
        elif marg > 0.15:
            s += 8
        elif marg > 0.10:
            s += 6
        elif marg > 0.05:
            s += 4
        elif marg > 0:
            s += 2

        pe = row["pe"]
        if pd.isna(pe) or pe <= 0:
            s += 0
        elif pe < 8:
            s += 10
        elif pe < 12:
            s += 8
        elif pe < 15:
            s += 6
        elif pe < 20:
            s += 4
        elif pe < 25:
            s += 2

        return round(s, 1)

    d["skor"] = d.apply(skor, axis=1)
    return d


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Valuation",
                        "Conservative Fair Value - Margin of Safety 15%"),
            unsafe_allow_html=True)

df_fund = load_all_fundamental()

if df_fund.empty:
    st.markdown(empty_state("", "Belum ada data fundamental",
                            "Jalankan `python -m quant.fundamental` dulu"),
                unsafe_allow_html=True)
    st.stop()

nama_map = load_nama()


# ============================================================
# PENGATURAN (collapsed)
# ============================================================
with st.expander("Pengaturan Filter", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        min_roe_f = st.slider("Min ROE (%)", 0, 30, 5, 1)
    with c2:
        max_der_f = st.slider("Max DER", 0.5, 5.0, 2.0, 0.1)
    with c3:
        require_margin = st.checkbox("Wajib margin positif", value=True)

    c4, c5 = st.columns(2)
    with c4:
        min_pe_f, max_pe_f = st.slider("Range PE", 1.0, 50.0,
                                        (2.0, 30.0), 0.5)
    with c5:
        min_pb_f, max_pb_f = st.slider("Range PB", 0.1, 10.0,
                                        (0.2, 5.0), 0.1)

    c6, c7 = st.columns(2)
    with c6:
        skip_incons = st.checkbox("Skip EPS tidak konsisten", value=True)
    with c7:
        filter_susp = st.checkbox(
            "Skip suspect (FV capped / PE ekstrem)",
            value=True,
            help="FV di-cap 2x harga atau PE sangat jauh dari median sektor",
        )

    st.caption(
        f"**FV = (0.40xGraham + 0.30xPE-based + 0.30xPB-based) "
        f"x {MARGIN_OF_SAFETY}** - "
        f"PE target = min(median, {PE_HARD_CAP}) x {TARGET_DISCOUNT} - "
        f"PB target = min(median, {PB_HARD_CAP}) x {TARGET_DISCOUNT} - "
        f"FV cap = {FV_CAP_RATIO}x harga"
    )


val_all = hitung_valuasi(
    df_fund,
    min_roe=float(min_roe_f),
    max_der=float(max_der_f),
    min_pe=min_pe_f,
    max_pe=max_pe_f,
    min_pb=min_pb_f,
    max_pb=max_pb_f,
    require_positive_margin=require_margin,
    skip_inconsistent=skip_incons,
    filter_suspect=filter_susp,
)

val_bersih = val_all[val_all["red_flag"] == ""].copy()
val_redflag = val_all[val_all["red_flag"] != ""].copy()
val_underval = val_bersih[val_bersih["potential"] > 0].copy()


# ============================================================
# RINGKASAN PASAR
# ============================================================
st.markdown(section_title("Ringkasan Pasar"), unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
for col, label, val_show, color in [
    (c1, "TOTAL SAHAM", f"{len(val_all)}", "#ffffff"),
    (c2, "UNDERVALUED", f"{len(val_underval)}", "#ffffff"),
    (c3, "RED FLAG SKIP", f"{len(val_redflag)}", "#737373"),
    (c4, "AVG POTENTIAL",
     fmt_pct(val_underval["potential"].mean()
             if len(val_underval) > 0 else 0, 1, True),
     "#ffffff"),
]:
    with col:
        st.markdown(
            '<div style="background: #171717; '
            'border-radius: 8px; padding: 22px 24px; '
            'border: 1px solid #27272a;">'
            f'<div style="font-size: 11px; color: #a3a3a3; '
            f'letter-spacing: 0.8px; font-weight: 500;">{label}</div>'
            f'<div style="font-size: 28px; font-weight: 600; '
            f'color: {color}; margin-top: 8px; '
            f'letter-spacing: -0.03em;">{val_show}</div>'
            '</div>',
            unsafe_allow_html=True
        )


# ============================================================
# SEARCH BAR
# ============================================================
st.markdown(section_title("Cari Saham",
                          "Ketik kode untuk lihat detail valuasi"),
            unsafe_allow_html=True)

search_kode = st.text_input(
    "Cari saham",
    placeholder="Ketik kode saham, mis. BBCA / TLKM / ASII",
    max_chars=6,
    key="val_search",
    label_visibility="collapsed",
).upper().strip()

if search_kode:
    found = val_all[val_all["kode"] == search_kode]
    if found.empty:
        st.warning(f"Saham **{search_kode}** tidak ditemukan di data fundamental.")
    else:
        r = found.iloc[0]
        kode = r["kode"]
        nama = nama_map.get(kode, r.get("nama", kode))
        harga = r.get("harga", np.nan)
        fv = r.get("fv", np.nan)
        pot = r.get("potential", np.nan)
        skor = r.get("skor", 0)
        roe = r.get("roe_pct", np.nan)
        de_val = r.get("de_val", np.nan)
        pe = r.get("pe", np.nan)
        pb = r.get("pb", np.nan)
        sektor = r.get("sektor", "")
        target_pe = r.get("target_pe", np.nan)
        target_pb = r.get("target_pb", np.nan)
        eps_val = r.get("eps", np.nan)
        eps_src = r.get("eps_src", "?")
        bv_val = r.get("bv", np.nan)
        fv_graham = r.get("fv_graham", np.nan)
        fv_pe = r.get("fv_pe", np.nan)
        fv_pb = r.get("fv_pb", np.nan)
        red_flag = r.get("red_flag", "")
        suspect = bool(r.get("fv_capped", False)) or bool(r.get("pe_suspect", False))

        is_red = bool(red_flag)
        is_suspect = suspect and not is_red

        if is_red:
            pot_color = "#737373"
            pot_label = "TIDAK VALID"
            accent = "#737373"
            status_badge = (
                f'<span style="background:#262626; color:#a3a3a3; border: 1px solid #404040; '
                f'padding:4px 10px; border-radius:4px; font-size:11px; '
                f'font-weight:500;">RED FLAG - {red_flag}</span>'
            )
        elif is_suspect:
            pot_color = "#a3a3a3"
            pot_label = "SUSPECT"
            accent = "#a3a3a3"
            status_badge = (
                '<span style="background:#262626; color:#a3a3a3; border: 1px solid #404040; '
                'padding:4px 10px; border-radius:4px; font-size:11px; '
                'font-weight:500;">Suspect - data perlu dicek</span>'
            )
        elif pd.isna(pot):
            pot_color = "#737373"
            pot_label = "N/A"
            accent = "#737373"
            status_badge = ""
        elif pot >= 40:
            pot_color = "#ffffff"
            pot_label = "SANGAT MURAH"
            accent = "#ffffff"
            status_badge = (
                '<span style="background:#ffffff; color:#0a0a0a; '
                'padding:4px 10px; border-radius:4px; font-size:11px; '
                'font-weight:700;">VALID</span>'
            )
        elif pot >= 20:
            pot_color = "#ffffff"
            pot_label = "MURAH"
            accent = "#ffffff"
            status_badge = (
                '<span style="background:#262626; color:#ffffff; border: 1px solid #ffffff; '
                'padding:4px 10px; border-radius:4px; font-size:11px; '
                'font-weight:500;">VALID</span>'
            )
        elif pot >= 0:
            pot_color = "#e5e5e5"
            pot_label = "WAJAR"
            accent = "#e5e5e5"
            status_badge = (
                '<span style="background:#262626; color:#a3a3a3; border: 1px solid #404040; '
                'padding:4px 10px; border-radius:4px; font-size:11px; '
                'font-weight:500;">WAJAR</span>'
            )
        else:
            pot_color = "#737373"
            pot_label = "MAHAL"
            accent = "#737373"
            status_badge = (
                '<span style="background:#262626; color:#737373; border: 1px solid #404040; '
                'padding:4px 10px; border-radius:4px; font-size:11px; '
                'font-weight:500;">MAHAL</span>'
            )

        warning_banner = ""
        if is_red:
            warning_banner = (
                '<div style="background:#262626; '
                'border:1px solid #404040; '
                'border-left:4px solid #737373; border-radius:6px; '
                'padding:16px 20px; margin-bottom:24px;">'
                '<div style="font-size:14px; font-weight:600; color:#a3a3a3; '
                'margin-bottom:8px;">SAHAM INI TIDAK MASUK REKOMENDASI</div>'
                f'<div style="font-size:13px; color:#a3a3a3; line-height:1.6;">'
                f'Alasan: <b style="color:#ffffff;">{red_flag}</b><br>'
                'Nilai potential di bawah tetap dihitung secara matematis, '
                'tetapi <b>tidak bisa dijadikan dasar pembelian</b> karena '
                'fundamental tidak memenuhi kriteria kelayakan.</div>'
                '</div>'
            )

        st.markdown(
            f'<div style="background:#171717; '
            f'border:1px solid #27272a; border-left:4px solid {accent}; '
            f'border-radius:8px; padding:24px 28px; margin:16px 0 24px;">'

            f'<div style="margin-bottom:20px;">'
            f'<div style="font-size:26px; font-weight:700; color:#ffffff; letter-spacing:-0.03em;">{kode}</div>'
            f'<div style="font-size:14px; color:#a3a3a3; margin-top:6px;">{nama} - <span style="color:#737373;">{sektor}</span></div>'
            f'<div style="margin-top:12px;">{status_badge}</div>'
            f'</div>'

            f'<div style="margin-bottom:24px;">'
            f'<div style="font-size:11px; color:#737373; letter-spacing:0.5px; font-weight:500;">HARGA SAAT INI</div>'
            f'<div style="font-size:32px; font-weight:700; color:#ffffff; letter-spacing:-0.03em; margin-top:4px;">{fmt(harga, 0)}</div>'
            f'</div>'

            f'{warning_banner}'

            f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; margin-bottom:20px;">'
            f'<div style="background:#262626; border:1px solid #404040; border-radius:6px; padding:16px 20px;">'
            f'<div style="font-size:11px; color:#a3a3a3; letter-spacing:0.5px;">FAIR VALUE</div>'
            f'<div style="font-size:22px; font-weight:600; color:#ffffff; margin-top:6px;">{fmt(fv, 0)}</div></div>'

            f'<div style="background:#262626; border:1px solid #404040; border-radius:6px; padding:16px 20px;">'
            f'<div style="font-size:11px; color:#a3a3a3; letter-spacing:0.5px;">POTENTIAL</div>'
            f'<div style="font-size:22px; font-weight:600; color:{pot_color}; margin-top:6px;">{fmt_pct(pot, 1, True)}</div>'
            f'<div style="font-size:11px; color:{pot_color}; font-weight:600; margin-top:4px;">{pot_label}</div></div>'

            f'<div style="background:#262626; border:1px solid #404040; border-radius:6px; padding:16px 20px;">'
            f'<div style="font-size:11px; color:#a3a3a3; letter-spacing:0.5px;">SKOR</div>'
            f'<div style="font-size:22px; font-weight:600; color:#ffffff; margin-top:6px;">{skor:.0f}<span style="font-size:12px; color:#737373;">/100</span></div></div>'
            f'</div>'

            f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; margin-bottom:20px;">'
            f'<div style="background:#0a0a0a; border:1px solid #27272a; border-radius:6px; padding:14px 16px;">'
            f'<div style="font-size:11px; color:#737373;">EPS</div>'
            f'<div style="font-size:15px; font-weight:600; color:#ffffff; margin-top:4px;">{fmt(eps_val, 1)} <span style="font-size:11px; color:#737373;">({eps_src})</span></div></div>'

            f'<div style="background:#0a0a0a; border:1px solid #27272a; border-radius:6px; padding:14px 16px;">'
            f'<div style="font-size:11px; color:#737373;">BV</div>'
            f'<div style="font-size:15px; font-weight:600; color:#ffffff; margin-top:4px;">{fmt(bv_val, 0)}</div></div>'

            f'<div style="background:#0a0a0a; border:1px solid #27272a; border-radius:6px; padding:14px 16px;">'
            f'<div style="font-size:11px; color:#737373;">ROE</div>'
            f'<div style="font-size:15px; font-weight:600; color:#ffffff; margin-top:4px;">{fmt_pct(roe, 1)}</div></div>'

            f'<div style="background:#0a0a0a; border:1px solid #27272a; border-radius:6px; padding:14px 16px;">'
            f'<div style="font-size:11px; color:#737373;">PE</div>'
            f'<div style="font-size:15px; font-weight:600; color:#ffffff; margin-top:4px;">{fmt(pe, 1)} <span style="font-size:11px; color:#737373;">(tgt {fmt(target_pe, 1)})</span></div></div>'

            f'<div style="background:#0a0a0a; border:1px solid #27272a; border-radius:6px; padding:14px 16px;">'
            f'<div style="font-size:11px; color:#737373;">PB</div>'
            f'<div style="font-size:15px; font-weight:600; color:#ffffff; margin-top:4px;">{fmt(pb, 2)} <span style="font-size:11px; color:#737373;">(tgt {fmt(target_pb, 2)})</span></div></div>'

            f'<div style="background:#0a0a0a; border:1px solid #27272a; border-radius:6px; padding:14px 16px;">'
            f'<div style="font-size:11px; color:#737373;">DER</div>'
            f'<div style="font-size:15px; font-weight:600; color:#ffffff; margin-top:4px;">{fmt(de_val, 2)}</div></div>'
            f'</div>'

            f'<div style="border-top:1px solid #27272a; padding-top:16px; display:flex; gap:24px; flex-wrap:wrap; font-size:12px; color:#a3a3a3;">'
            f'<span>FV Graham: <b style="color:#ffffff; font-weight:500;">{fmt(fv_graham, 0)}</b></span>'
            f'<span>FV-PE: <b style="color:#ffffff; font-weight:500;">{fmt(fv_pe, 0)}</b></span>'
            f'<span>FV-PB: <b style="color:#ffffff; font-weight:500;">{fmt(fv_pb, 0)}</b></span>'
            f'</div>'

            f'</div>',
            unsafe_allow_html=True
        )

st.markdown(
    '<div style="height:1px; background:#27272a; margin:32px 0 24px;"></div>',
    unsafe_allow_html=True
)


# ============================================================
# TOP 10 UNDERVALUED (auto) - SORTED BY SKOR
# ============================================================
st.markdown(section_title("Top 10 Undervalued",
                          "Auto-sorted by Skor - Conservative FV"),
            unsafe_allow_html=True)

top = val_underval.sort_values(by=["skor", "potential"], ascending=[False, False]).head(10).reset_index(drop=True)

if top.empty:
    st.markdown(empty_state("", "Tidak ada saham undervalued saat ini",
                            "Semua saham dianggap wajar atau mahal"),
                unsafe_allow_html=True)
else:
    for i, r in top.iterrows():
        kode = r["kode"]
        nama = nama_map.get(kode, r.get("nama", kode))[:50]
        harga = r["harga"]
        fv = r["fv"]
        pot = r["potential"]
        skor = r["skor"]
        roe = r["roe_pct"]
        de_val = r["de_val"]
        pe = r["pe"]
        pb = r["pb"]
        sektor = r.get("sektor", "")
        eps_val = r.get("eps", np.nan)

        pot_color = "#ffffff" if pot >= 0 else "#737373"

        st.markdown(
            f'<div style="background: #171717; border-radius: 8px; border: 1px solid #27272a; padding: 24px; margin-bottom: 16px; border-left: 4px solid #ffffff;">'
            
            f'<div style="display: flex; justify-content: space-between; align-items: stretch; border-bottom: 1px solid #27272a; padding-bottom: 16px; margin-bottom: 16px;">'
            f'<div style="flex: 1;">'
            f'<div style="font-size: 24px; font-weight: 700; color: #ffffff; line-height: 1.2;">{kode}</div>'
            f'<div style="font-size: 13px; color: #a3a3a3; margin-top: 4px;">Last: {harga:,.2f}</div>'
            f'</div>'
            f'<div style="width: 1px; background: #27272a; margin: 0 16px;"></div>'
            f'<div style="flex: 1; text-align: right; display: flex; flex-direction: column; justify-content: center;">'
            f'<div style="font-size: 11px; color: #737373; text-transform:uppercase;">Target Range:</div>'
            f'<div style="font-size: 20px; font-weight: 600; color: #ffffff;">{fv:,.0f}</div>'
            f'</div>'
            f'</div>'

            f'<div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; text-align: center; border-bottom: 1px solid #27272a; padding-bottom: 16px; margin-bottom: 16px;">'
            f'<div>'
            f'<div style="font-size: 11px; color: #737373; margin-bottom: 4px;">Rank</div>'
            f'<div style="font-size: 15px; font-weight: 600; color: #ffffff;">#{i+1}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #737373; margin-bottom: 4px;">ROE</div>'
            f'<div style="font-size: 15px; font-weight: 600; color: #ffffff;">{fmt_pct(roe, 1)}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #737373; margin-bottom: 4px;">DER</div>'
            f'<div style="font-size: 15px; font-weight: 600; color: #ffffff;">{fmt(de_val, 2)}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #737373; margin-bottom: 4px;">EPS</div>'
            f'<div style="font-size: 15px; font-weight: 600; color: #ffffff;">{fmt(eps_val, 1)}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #737373; margin-bottom: 4px;">PE</div>'
            f'<div style="font-size: 15px; font-weight: 600; color: #ffffff;">{fmt(pe, 1)}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size: 11px; color: #737373; margin-bottom: 4px;">PB</div>'
            f'<div style="font-size: 15px; font-weight: 600; color: #ffffff;">{fmt(pb, 2)}</div>'
            f'</div>'
            f'</div>'

            f'<div style="display: flex; justify-content: space-between; align-items: center;">'
            
            f'<div style="background: #262626; border: 1px solid #404040; border-radius: 6px; padding: 10px 16px; display: flex; align-items: center; gap: 12px;">'
            f'<span style="font-size: 12px; color: #a3a3a3;">Score:</span>'
            f'<span style="font-size: 18px; font-weight: 600; color: #ffffff;">{skor:.0f}</span>'
            f'</div>'

            f'<div style="text-align: right;">'
            f'<div style="font-size: 11px; color: #737373; text-transform:uppercase;">Potential:</div>'
            f'<div style="font-size: 24px; font-weight: 700; color: {pot_color};">{pot:+.1f}%</div>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )


# ============================================================
# TABEL SEMUA UNDERVALUED (SORTED BY SKOR)
# ============================================================
st.markdown(section_title("Semua Saham Undervalued", "Auto-sorted by Skor"), unsafe_allow_html=True)

tampil = val_underval.sort_values(by=["skor", "potential"], ascending=[False, False]).reset_index(drop=True)

if tampil.empty:
    st.info("Tidak ada saham undervalued saat ini.")
else:
    df_show = tampil[[
        "kode", "nama", "sektor", "harga",
        "fv", "fv_graham", "fv_pe", "fv_pb", "potential", "skor",
        "eps", "eps_src", "bv", "pe", "pb", "roe_pct", "de_val",
        "target_pe", "target_pb",
    ]].copy()

    for c in ["fv", "fv_graham", "fv_pe", "fv_pb", "harga", "bv"]:
        df_show[c] = df_show[c].round(0)
    df_show["potential"] = df_show["potential"].round(1)
    df_show["roe_pct"] = df_show["roe_pct"].round(1)
    df_show["de_val"] = df_show["de_val"].round(2)
    df_show["pe"] = df_show["pe"].round(1)
    df_show["pb"] = df_show["pb"].round(2)
    df_show["eps"] = df_show["eps"].round(2)
    df_show["target_pe"] = df_show["target_pe"].round(1)
    df_show["target_pb"] = df_show["target_pb"].round(2)

    df_show = df_show.rename(columns={
        "kode": "Kode", "nama": "Nama", "sektor": "Sektor",
        "harga": "Harga", "fv": "FV", "fv_graham": "FV-Graham",
        "fv_pe": "FV-PE", "fv_pb": "FV-PB",
        "potential": "Potential %", "skor": "Skor",
        "eps": "EPS", "eps_src": "EPS Src", "bv": "BV",
        "pe": "PE", "pb": "PB", "roe_pct": "ROE %", "de_val": "DER",
        "target_pe": "Tgt PE", "target_pb": "Tgt PB",
    })
    df_show.insert(0, "No", range(1, len(df_show) + 1))

    render_table(df_show)

    st.caption(f"{len(df_show)} saham undervalued - "
               f"Diurutkan berdasarkan Skor (Kualitas Fundamental & Valuasi)")


# ============================================================
# PANEL RED FLAG
# ============================================================
if not val_redflag.empty:
    with st.expander(f"{len(val_redflag)} saham di-skip (red flag)"):
        st.caption("Saham ini tidak masuk ranking karena masalah fundamental, "
                   "data tidak konsisten, atau valuasi suspect.")

        df_rf = val_redflag[["kode", "nama", "sektor", "harga",
                              "eps", "eps_src", "eps_reliable",
                              "pe", "pb", "roe_pct", "de_val",
                              "margin_net", "fv_capped", "pe_suspect",
                              "red_flag"]].copy()
        df_rf = df_rf.sort_values("kode")
        df_rf["roe_pct"] = df_rf["roe_pct"].round(1)
        df_rf["pe"] = df_rf["pe"].round(1)
        df_rf["pb"] = df_rf["pb"].round(2)
        df_rf["de_val"] = df_rf["de_val"].round(2)
        df_rf["margin_net"] = (df_rf["margin_net"] * 100).round(1)
        df_rf["eps"] = df_rf["eps"].round(2)

        df_rf = df_rf.rename(columns={
            "kode": "Kode", "nama": "Nama", "sektor": "Sektor",
            "harga": "Harga", "eps": "EPS", "eps_src": "Src",
            "eps_reliable": "Reliable?",
            "pe": "PE", "pb": "PB", "roe_pct": "ROE %",
            "de_val": "DER", "margin_net": "Margin %",
            "fv_capped": "FV Capped?", "pe_suspect": "PE Suspect?",
            "red_flag": "Alasan",
        })

        render_table(df_rf)


# ============================================================
# SECTOR MEDIAN (referensi)
# ============================================================
with st.expander("Median PE & PB per Sektor (referensi)"):
    pe_med, pb_med, pe_def, pb_def = compute_sector_medians(df_fund)
    sectors = sorted(set(list(pe_med.keys()) + list(pb_med.keys())))
    rows = []
    for s in sectors:
        rows.append({
            "Sektor": s,
            "Median PE (capped 15)": round(pe_med.get(s, pe_def), 2),
            "Median PB (capped 2.0)": round(pb_med.get(s, pb_def), 3),
        })
    if rows:
        df_med = pd.DataFrame(rows).sort_values("Median PE (capped 15)").reset_index(drop=True)
        df_med.insert(0, "No", range(1, len(df_med) + 1))
        render_table(df_med)
        st.caption(f"Target PE dipakai = median x {TARGET_DISCOUNT} (diskon 10%) - "
                   f"Target PB dipakai = median x {TARGET_DISCOUNT} - "
                   f"FV final x {MARGIN_OF_SAFETY} (margin of safety 15%)")