import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.info("Buka tab baru → http://localhost:8501")
    st.stop()

# Halaman FUNDAMENTAL — baca data_fundamental/, tanpa grafik, dengan Quarterly.

import os, sys, json
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title, empty_state
from quant.parquet_loader import load_parquet_safe

load_theme()

DETAIL_DIR = "data_fundamental"


# ============================================================
# HELPER
# ============================================================
def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)}"


@st.cache_data(ttl=1800)
def list_available():
    if not os.path.exists(DETAIL_DIR):
        return []
    return sorted(f.replace(".json", "") for f in os.listdir(DETAIL_DIR)
                  if f.endswith(".json"))


@st.cache_data(ttl=1800)
def load_detail(kode):
    path = os.path.join(DETAIL_DIR, f"{kode}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=1800)
def load_ohlcv(kode):
    df_all = load_parquet_safe()
    if df_all is None or "Kode" not in df_all.columns:
        return None
    df = df_all[df_all["Kode"] == kode].copy()
    if df.empty:
        return None
    return df.sort_values("Date").reset_index(drop=True)


def fmt_num(v, dec=2, suffix=""):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        if abs(v) >= 1e12: return f"{v/1e12:.{dec}f}T{suffix}"
        if abs(v) >= 1e9: return f"{v/1e9:.{dec}f}B{suffix}"
        if abs(v) >= 1e6: return f"{v/1e6:.{dec}f}M{suffix}"
        return f"{v:,.{dec}f}{suffix}"
    except Exception:
        return "—"


def fmt_pct(v, dec=2, plus=False):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        if abs(v) < 1:
            v *= 100
        return f"{v:+.{dec}f}%" if plus else f"{v:.{dec}f}%"
    except Exception:
        return "—"


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Fundamental", "Analisis Rasio Keuangan"),
            unsafe_allow_html=True)

saham_list = list_available()
if not saham_list:
    st.markdown(empty_state("", "Belum ada data",
                            "Data fundamental belum tersedia. Silakan hubungi admin."),
                unsafe_allow_html=True)
    st.stop()

# INISIALISASI STATE KHUSUS UNTUK INPUT
if "fund_kode" not in st.session_state:
    st.session_state.fund_kode = "BBCA" if "BBCA" in saham_list else saham_list[0]

# GUNAKAN KEY, JANGAN GUNAKAN VALUE
kode_input = st.text_input(
    "Kode Saham",
    key="fund_kode",
    placeholder="Ketik kode saham, mis. BBCA",
    max_chars=6,
)

kode_pilih = kode_input.upper().strip()

if not kode_pilih:
    st.info("Ketik kode saham di atas untuk mulai.")
    st.stop()

if kode_pilih not in saham_list:
    st.warning(f"Saham **{kode_pilih}** tidak ditemukan.")
    st.caption(f"Tersedia {len(saham_list)} saham. Contoh: BBCA, BBRI, TLKM, ASII, ANTM")
    st.stop()

data = load_detail(kode_pilih)
if not data:
    st.error(f"Data {kode_pilih} tidak ditemukan.")
    st.stop()


# ============================================================
# HEADER SAHAM
# ============================================================
harga = data.get("harga") or 0
chg = 0
df_ohlcv = load_ohlcv(kode_pilih)

if df_ohlcv is not None and len(df_ohlcv) >= 2:
    last = float(df_ohlcv["Close"].iloc[-1])
    prev = float(df_ohlcv["Close"].iloc[-2])
    chg = (last / prev - 1) * 100
    harga = last

chg_color = "#ffffff" if chg >= 0 else "#737373"
chg_sign = "+" if chg >= 0 else ""

st.markdown(
    '<div style="'
    'background: #171717; '
    'border: 1px solid #27272a; border-radius: 8px; '
    'padding: 22px 26px; margin-bottom: 24px; '
    'display: flex; align-items: center; gap: 20px;">'
    '<div style="flex-grow: 1;">'
    f'<div style="font-size: 12px; color: #a3a3a3; margin-bottom: 5px; '
    f'font-weight: 500; letter-spacing: 0.5px;">'
    f'{data.get("sektor", "")} · {data.get("industri", "")}</div>'
    f'<div style="font-size: 19px; font-weight: 600; color: #ffffff; '
    f'margin-bottom: 8px;">{data.get("nama", kode_pilih)}</div>'
    '<div style="display: flex; align-items: baseline; gap: 12px;">'
    f'<span style="font-size: 30px; font-weight: 600; color: #ffffff; '
    f'letter-spacing: -0.03em; line-height: 1;">{harga:,.0f}</span>'
    f'<span style="font-size: 14px; font-weight: 500; padding: 4px 12px; '
    f'border-radius: 4px; background: #262626; '
    f'color: {chg_color}; border: 1px solid #404040;">'
    f'{chg_sign}{chg:.2f}%</span>'
    '</div></div></div>',
    unsafe_allow_html=True
)


# ============================================================
# RASIO KUNCI
# ============================================================
rk = data.get("rasio_kunci", {})
tahun = data.get("update", "")[:4] or "2026"

st.markdown(section_title("Rasio Kunci", f"Tahun fiskal {tahun}"),
            unsafe_allow_html=True)

metrics = [
    ("P/E", fmt_num(rk.get("pe"), 2)),
    ("P/B", fmt_num(rk.get("pb"), 2)),
    ("P/S", fmt_num(rk.get("ps"), 2)),
    ("ROE", fmt_pct(rk.get("roe"))),
    ("EPS", fmt_num(rk.get("eps"), 2)),
    ("D/E", fmt_num(rk.get("de"), 2)),
    ("Margin Bersih", fmt_pct(rk.get("margin_net"))),
    ("Current Ratio", fmt_num(rk.get("current_ratio"), 2)),
]

cols = st.columns(2)
for i, (label, val) in enumerate(metrics):
    with cols[i % 2]:
        st.markdown(
            '<div style="background: #171717; border: 1px solid #27272a; '
            'border-radius: 6px; padding: 14px 18px; margin-bottom: 10px; '
            'display: flex; justify-content: space-between; align-items: center;">'
            f'<div style="font-size: 13px; color: #a3a3a3;">{label}</div>'
            f'<div style="font-size: 18px; font-weight: 600; color: #ffffff; '
            f'letter-spacing: -0.02em;">{val}</div>'
            '</div>',
            unsafe_allow_html=True
        )


# ============================================================
# QUARTERLY PERFORMANCE
# ============================================================
quarterly = data.get("quarterly", {}) or {}
q_rev = quarterly.get("revenue", {}) or {}
q_eps = quarterly.get("eps", {}) or {}
q_ni = quarterly.get("net_income", {}) or {}


def get_last_4(d):
    if not d:
        return []
    keys = sorted(d.keys(), reverse=True)[:4]
    return [(k, d[k]) for k in keys]


rev_4q = get_last_4(q_rev)
eps_4q = get_last_4(q_eps)
ni_4q = get_last_4(q_ni)

if rev_4q or eps_4q:
    st.markdown(section_title("Quarterly Performance",
                              "4 kuartal terakhir"),
                unsafe_allow_html=True)

    if rev_4q:
        st.markdown(
            '<div style="font-size: 11px; color: #a3a3a3; letter-spacing: 0.08em; '
            'font-weight: 600; text-transform: uppercase; '
            'margin: 0 0 12px 4px;">REVENUE</div>',
            unsafe_allow_html=True
        )

        max_rev = max((v for _, v in rev_4q if v is not None), default=1)

        for q, v in rev_4q:
            if v is None:
                continue
            bar_pct = min(abs(v) / max_rev * 100, 100) if max_rev > 0 else 0
            st.markdown(
                '<div style="margin-bottom: 12px;">'
                '<div style="display: flex; justify-content: space-between; '
                'margin-bottom: 6px;">'
                f'<span style="font-size: 13px; color: #a3a3a3; '
                f'font-weight: 500;">{q}</span>'
                f'<span style="font-size: 13px; color: #ffffff; '
                f'font-weight: 600;">{fmt_num(v, 1)}</span>'
                '</div>'
                '<div style="width: 100%; height: 4px; background: #27272a; '
                'border-radius: 2px; overflow: hidden;">'
                f'<div style="width: {bar_pct}%; height: 100%; '
                f'background: #ffffff;"></div></div></div>',
                unsafe_allow_html=True
            )

    if eps_4q:
        st.markdown(
            '<div style="font-size: 11px; color: #a3a3a3; letter-spacing: 0.08em; '
            'font-weight: 600; text-transform: uppercase; '
            'margin: 24px 0 12px 4px;">EPS</div>',
            unsafe_allow_html=True
        )

        cols = st.columns(4)
        for i, (q, v) in enumerate(eps_4q[:4]):
            with cols[i]:
                val_str = f"{v:.2f}" if v is not None else "—"
                st.markdown(
                    '<div style="background: #171717; border: 1px solid #27272a; '
                    'border-radius: 6px; padding: 14px; text-align: center;">'
                    f'<div style="font-size: 11px; color: #a3a3a3; '
                    f'font-weight: 500; margin-bottom: 6px;">{q}</div>'
                    f'<div style="font-size: 16px; font-weight: 600; '
                    f'color: #ffffff;">{val_str}</div>'
                    '</div>',
                    unsafe_allow_html=True
                )

    if ni_4q:
        st.markdown(
            '<div style="font-size: 11px; color: #a3a3a3; letter-spacing: 0.08em; '
            'font-weight: 600; text-transform: uppercase; '
            'margin: 24px 0 12px 4px;">NET INCOME</div>',
            unsafe_allow_html=True
        )

        cols = st.columns(4)
        for i, (q, v) in enumerate(ni_4q[:4]):
            with cols[i]:
                val_str = fmt_num(v, 0) if v is not None else "—"
                color = "#ffffff" if (v is not None and v >= 0) else "#737373"
                st.markdown(
                    '<div style="background: #171717; border: 1px solid #27272a; '
                    'border-radius: 6px; padding: 14px; text-align: center;">'
                    f'<div style="font-size: 11px; color: #a3a3a3; '
                    f'font-weight: 500; margin-bottom: 6px;">{q}</div>'
                    f'<div style="font-size: 15px; font-weight: 600; '
                    f'color: {color};">{val_str}</div>'
                    '</div>',
                    unsafe_allow_html=True
                )


# ============================================================
# RIWAYAT TAHUNAN
# ============================================================
riwayat = data.get("riwayat", {})
eps_hist = riwayat.get("eps", {}) or {}
rev_hist = riwayat.get("revenue_per_share", {}) or riwayat.get("revenue", {}) or {}
tahun_list = sorted(set(list(eps_hist.keys()) + list(rev_hist.keys())),
                    reverse=True)[:5]

if tahun_list:
    st.markdown(section_title("Riwayat Tahunan", "EPS & pendapatan per tahun"),
                unsafe_allow_html=True)

    rows = ""
    for y in tahun_list:
        e = eps_hist.get(y)
        r = rev_hist.get(y)
        rows += (
            '<tr>'
            f'<td style="padding: 12px 14px; color: #ffffff; font-weight: 500; '
            f'border-bottom: 1px solid #27272a; font-size: 13px;">{y}</td>'
            f'<td style="padding: 12px 14px; color: #a3a3a3; '
            f'border-bottom: 1px solid #27272a; font-size: 13px;">'
            f'{fmt_num(e, 0) if e else "—"}</td>'
            f'<td style="padding: 12px 14px; color: #a3a3a3; '
            f'border-bottom: 1px solid #27272a; font-size: 13px;">'
            f'{fmt_num(r, 0) if r else "—"}</td>'
            '</tr>'
        )

    st.markdown(
        '<div style="background: #171717; border: 1px solid #27272a; '
        'border-radius: 8px; padding: 4px; margin-bottom: 12px; overflow: hidden;">'
        '<table style="width: 100%; border-collapse: collapse;">'
        '<thead><tr>'
        '<th style="text-align: left; padding: 12px 14px; font-size: 11px; '
        'color: #a3a3a3; font-weight: 500; letter-spacing: 0.06em; '
        'text-transform: uppercase; border-bottom: 1px solid #27272a;">Tahun</th>'
        '<th style="text-align: left; padding: 12px 14px; font-size: 11px; '
        'color: #a3a3a3; font-weight: 500; letter-spacing: 0.06em; '
        'text-transform: uppercase; border-bottom: 1px solid #27272a;">EPS</th>'
        '<th style="text-align: left; padding: 12px 14px; font-size: 11px; '
        'color: #a3a3a3; font-weight: 500; letter-spacing: 0.06em; '
        'text-transform: uppercase; border-bottom: 1px solid #27272a;">'
        'Pendapatan/Saham</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody>'
        '</table></div>',
        unsafe_allow_html=True
    )


# ============================================================
# STATISTIK
# ============================================================
stat = data.get("statistik", {})
st.markdown(section_title("Statistik & Laporan Keuangan", "Mata uang: IDR"),
            unsafe_allow_html=True)

stat_items = [
    ("Market Cap", fmt_num(stat.get("market_cap"), 0)),
    ("Enterprise Value", fmt_num(stat.get("enterprise_value"), 0)),
    ("Saham Beredar", fmt_num(stat.get("shares_outstanding"), 0)),
    ("Free Float", fmt_pct(stat.get("free_float_pct"))),
]

cols = st.columns(2)
for i, (label, val) in enumerate(stat_items):
    with cols[i % 2]:
        st.markdown(
            '<div style="background: #171717; border: 1px solid #27272a; '
            'border-radius: 6px; padding: 14px 18px; margin-bottom: 10px; '
            'display: flex; justify-content: space-between; align-items: center;">'
            f'<div style="font-size: 13px; color: #a3a3a3;">{label}</div>'
            f'<div style="font-size: 17px; font-weight: 600; color: #ffffff; '
            f'letter-spacing: -0.02em;">{val}</div>'
            '</div>',
            unsafe_allow_html=True
        )

st.markdown(
    f'<div style="font-size: 11px; color: #a3a3a3; letter-spacing: 0.08em; '
    f'font-weight: 500; text-transform: uppercase; margin: 24px 0 12px 2px;">'
    f'RASIO EKUITAS {tahun}</div>',
    unsafe_allow_html=True
)

roe_str = fmt_pct(rk.get("roe"))
roa_str = fmt_pct(rk.get("roa"))

c1, c2 = st.columns(2)
for col, label, val in [
    (c1, "ROE", roe_str),
    (c2, "ROA", roa_str),
]:
    with col:
        st.markdown(
            '<div style="background: #171717; border: 1px solid #27272a; '
            'border-radius: 6px; padding: 16px 18px;">'
            f'<div style="font-size: 11px; color: #a3a3a3; font-weight: 500; '
            f'letter-spacing: 0.06em; text-transform: uppercase; '
            f'margin-bottom: 6px;">{label}</div>'
            f'<div style="font-size: 24px; font-weight: 600; color: #ffffff; '
            f'letter-spacing: -0.02em;">{val}</div>'
            '</div>',
            unsafe_allow_html=True
        )

