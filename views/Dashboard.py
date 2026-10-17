# Dashboard Rotasi Sektor IDX - Halaman Utama.

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.global_data import (
    get_all_global_data,
    hitung_sentimen,
    get_dampak_ihsg,
)
from quant.theme import load_theme, page_header, section_title
from quant.parquet_loader import load_parquet_safe

import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime


st.set_page_config(
    page_title="Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not st.session_state.get("authentication_status"):
    st.error("⚠ Silakan login dulu di halaman utama.")
    st.stop()

load_theme()

BENCHMARK = "IHSG"
RS_WINDOW = 20
MOMENTUM_WINDOW = 10
REL_WINDOW = 20  # ← untuk hitung 20d spread vs IHSG


# ============================================================
# MAPPING
# ============================================================
SEKTOR_ID = {
    "Energy": "Energi", "Basic Materials": "Barang Baku",
    "Industrials": "Perindustrian",
    "Consumer Non-Cyclicals": "Barang Konsumen Primer",
    "Consumer Cyclicals": "Barang Konsumen Non-Primer",
    "Healthcare": "Kesehatan", "Financials": "Keuangan",
    "Properties & Real Estate": "Properti & Real Estat",
    "Technology": "Teknologi", "Infrastructures": "Infrastruktur",
    "Transportation & Logistic": "Transportasi & Logistik",
}

STATUS_STYLE = {
    "Leading":   {"bg": "rgba(16,185,129,0.08)",
                   "border": "rgba(16,185,129,0.3)",
                   "text": "#10b981", "arrow": "↗"},
    "Weakening": {"bg": "rgba(245,158,11,0.08)",
                   "border": "rgba(245,158,11,0.3)",
                   "text": "#f59e0b", "arrow": "↘"},
    "Lagging":   {"bg": "rgba(244,63,94,0.08)",
                   "border": "rgba(244,63,94,0.3)",
                   "text": "#f43f5e", "arrow": "↙"},
    "Improving": {"bg": "rgba(99,102,241,0.08)",
                   "border": "rgba(99,102,241,0.3)",
                   "text": "#818cf8", "arrow": "↗"},
}


# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data(ttl=1800)
def load_data():
    df = load_parquet_safe()
    if df is None:
        raise FileNotFoundError("ohlcv_idx_2026_all.parquet tidak ditemukan.")
    df = df.dropna(subset=["Date"])
    sektor = pd.read_csv("data_sektor.csv")
    sektor["kode"] = sektor["kode"].str.upper()
    df = df.merge(sektor, left_on="Kode", right_on="kode", how="left")
    df = df.drop(columns=["kode"], errors="ignore")
    return df[df["sektor"].notna()].copy()


def build_sector_index(df):
    df = df.sort_values(["Kode", "Date"]).copy()
    df["ret_1d"] = df.groupby("Kode")["Close"].pct_change()
    df = df[df["ret_1d"].notna()]
    sector_ret = df.groupby(["Date", "sektor"])["ret_1d"].mean().reset_index()
    sector_ret = sector_ret.pivot(index="Date", columns="sektor",
                                   values="ret_1d").fillna(0)
    return (1 + sector_ret).cumprod() * 100


def build_benchmark(df):
    df = df.sort_values(["Kode", "Date"]).copy()
    df["ret_1d"] = df.groupby("Kode")["Close"].pct_change()
    df = df[df["ret_1d"].notna()]
    bench = df.groupby("Date")["ret_1d"].mean()
    return (1 + bench).cumprod() * 100


def calc_rrg(sector_index, benchmark):
    common = sector_index.index.intersection(benchmark.index)
    si = sector_index.loc[common]
    bm = benchmark.loc[common]
    rs = si.div(bm, axis=0)
    rs_mean = rs.rolling(RS_WINDOW, min_periods=5).mean()
    rs_std = rs.rolling(RS_WINDOW, min_periods=5).std()
    rs_ratio = 100 + (rs - rs_mean) / rs_std.replace(0, np.nan) * 5
    rs_mom = 100 + rs_ratio.pct_change(MOMENTUM_WINDOW) * 100 * 2
    valid = rs_ratio.notna().all(axis=1) & rs_mom.notna().all(axis=1)
    return rs_ratio[valid], rs_mom[valid]


def classify_quadrant(x, y):
    if x >= 100 and y >= 100: return "Leading"
    if x >= 100 and y < 100: return "Weakening"
    if x < 100 and y < 100: return "Lagging"
    return "Improving"


def detect_market_phase(sc):
    n_lead = sc.get("Leading", 0)
    n_imp = sc.get("Improving", 0)
    n_weak = sc.get("Weakening", 0)
    n_lag = sc.get("Lagging", 0)
    total = n_lead + n_imp + n_weak + n_lag
    if n_lead >= total * 0.5:
        return "MARKUP", "Pasar bull kuat, mayoritas sektor memimpin"
    elif n_lead + n_imp >= total * 0.7:
        return "EARLY EXPANSION", "Awal ekspansi, rotasi ke sektor baru"
    elif n_lag >= total * 0.5:
        return "MARKDOWN", "Pasar bear, mayoritas sektor tertinggal"
    elif n_weak + n_lag >= total * 0.7:
        return "LATE CYCLE", "Siklus akhir, ambil untung"
    return "MIXED", "Pasar campuran, rotasi sedang berlangsung"


# ============================================================
# LOAD & HITUNG
# ============================================================
with st.spinner("Memuat data..."):
    try:
        df = load_data()
    except FileNotFoundError as e:
        st.error(f"File tidak ditemukan: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Error memuat data: {e}")
        st.stop()

sector_index = build_sector_index(df)
benchmark = build_benchmark(df)
rs_ratio, rs_mom = calc_rrg(sector_index, benchmark)

# 20d spread IHSG (untuk semua sektor)
bm_20d = None
if len(benchmark) >= REL_WINDOW + 1:
    bm_20d = (benchmark.iloc[-1] / benchmark.iloc[-(REL_WINDOW + 1)] - 1) * 100

sector_data = []
for sektor in rs_ratio.columns:
    x = rs_ratio[sektor].iloc[-1]
    y = rs_mom[sektor].iloc[-1]
    status = classify_quadrant(x, y)

    ret_1d = 0
    if len(sector_index) >= 2:
        ret_1d = (sector_index[sektor].iloc[-1] /
                  sector_index[sektor].iloc[-2] - 1) * 100

    # 20d relative vs IHSG
    spread_20d = None
    if bm_20d is not None and len(sector_index) >= REL_WINDOW + 1:
        sec_20d = (sector_index[sektor].iloc[-1] /
                   sector_index[sektor].iloc[-(REL_WINDOW + 1)] - 1) * 100
        spread_20d = sec_20d - bm_20d

    sector_data.append({
        "sektor": sektor, "status": status, "ret_1d": ret_1d,
        "spread_20d": spread_20d,
        "rs_ratio": x, "rs_mom": y,
    })

df_status = pd.DataFrame(sector_data)
status_counts = df_status["status"].value_counts().to_dict()
phase, phase_desc = detect_market_phase(status_counts)


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Rotasi Sektor", phase_desc),
            unsafe_allow_html=True)

st.markdown(
    '<div style="margin-bottom: 24px;">'
    '<span style="display: inline-block; padding: 8px 16px; '
    'background: linear-gradient(135deg, #131a2a, #0f1420); '
    'color: #06b6d4; border: 1px solid #1f2a3d; '
    'border-radius: 8px; font-size: 12px; font-weight: 700; '
    'letter-spacing: 1px;">'
    f'PHASE: {phase}'
    '</span>'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SECTOR CARDS
# ============================================================
STATUS_ORDER = {"Leading": 0, "Improving": 1, "Weakening": 2, "Lagging": 3}
df_status["order"] = df_status["status"].map(STATUS_ORDER)
df_sorted = df_status.sort_values(
    ["order", "ret_1d"], ascending=[True, False]
).reset_index(drop=True)

# Keterangan kolom
st.markdown(
    '<div style="font-size: 11px; color: #64748b; '
    'margin-bottom: 12px; padding: 8px 12px; '
    'background: rgba(30,41,59,0.3); border-radius: 8px; '
    'border-left: 2px solid #475569;">'
    '<b style="color:#94a3b8;">Keterangan:</b> '
    'Angka pertama = return <b>1 hari</b> · '
    'Angka kedua = selisih return <b>20 hari</b> vs IHSG · '
    'Label = kuadran RRG (kumulatif)'
    '</div>',
    unsafe_allow_html=True
)

for _, r in df_sorted.iterrows():
    sektor = r["sektor"]; status = r["status"]; ret = r["ret_1d"]
    spread = r.get("spread_20d")
    nama_id = SEKTOR_ID.get(sektor, sektor)
    style = STATUS_STYLE[status]
    color_ret = "#10b981" if ret >= 0 else "#f43f5e"
    sign = "+" if ret >= 0 else ""

    # Badge 20d spread
    if spread is not None and not pd.isna(spread):
        sp_color = "#10b981" if spread >= 0 else "#f43f5e"
        sp_sign = "+" if spread >= 0 else ""
        spread_html = (
            f'<span style="font-size: 11px; color: {sp_color}; '
            f'font-weight: 600; background: rgba(15,23,42,0.6); '
            f'padding: 3px 8px; border-radius: 5px;">'
            f'20d: {sp_sign}{spread:.2f}% vs IHSG</span>'
        )
    else:
        spread_html = ""

    st.markdown(
        '<div style="'
        f'background: linear-gradient(135deg, {style["bg"]}, #0f1420); '
        f'border: 1px solid {style["border"]}; '
        'border-radius: 12px; padding: 16px 20px; margin-bottom: 10px; '
        'display: flex; align-items: center; gap: 16px; '
        'box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);">'
        '<div style="flex-grow: 1;">'
        f'<div style="font-size: 15px; font-weight: 700; color: #ffffff; '
        f'margin-bottom: 8px;">{nama_id}</div>'
        '<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">'
        f'<span style="font-size: 10px; font-weight: 700; '
        f'letter-spacing: 0.8px; padding: 4px 10px; border-radius: 6px; '
        f'background: {style["bg"]}; color: {style["text"]}; '
        f'border: 1px solid {style["border"]};">'
        f'{style["arrow"]} {status.upper()}</span>'
        f'<span style="font-size: 13px; font-weight: 700; color: {color_ret};">'
        f'{sign}{ret:.2f}%</span>'
        f'{spread_html}'
        '</div></div></div>',
        unsafe_allow_html=True
    )


# ============================================================
# RINGKASAN PAGI
# ============================================================
st.markdown(section_title("Ringkasan Pagi", "Global market update"),
            unsafe_allow_html=True)

with st.spinner("Mengambil data global..."):
    global_data = get_all_global_data()
    sentimen_status, sentimen_detail, _ = hitung_sentimen(global_data)
    dampak_ihsg = get_dampak_ihsg(global_data)

warna_sentimen = (
    "#10b981" if "BULLISH" in sentimen_status else
    "#f43f5e" if "BEARISH" in sentimen_status else
    "#f59e0b"
)

st.markdown(
    '<div style="'
    'background: linear-gradient(135deg, #131a2a 0%, #0f1420 100%); '
    'border: 1px solid #1f2a3d; '
    f'border-left: 4px solid {warna_sentimen}; '
    'border-radius: 12px; padding: 20px 24px; margin-bottom: 20px; '
    'box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);">'
    '<div style="font-size: 11px; color: #64748b; letter-spacing: 1px; '
    'margin-bottom: 8px; font-weight: 700; text-transform: uppercase;">'
    'Sentimen Global</div>'
    f'<div style="font-size: 22px; font-weight: 800; color: {warna_sentimen}; '
    f'margin-bottom: 6px;">{sentimen_status}</div>'
    f'<div style="font-size: 13px; color: #94a3b8;">{sentimen_detail}</div>'
    '</div>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)


def render_market_list(items, title):
    st.markdown(
        f'<div style="font-size: 11px; color: #64748b; letter-spacing: 0.08em; '
        f'font-weight: 700; text-transform: uppercase; margin-bottom: 12px;">'
        f'{title}</div>',
        unsafe_allow_html=True
    )
    for nama, d in items.items():
        chg = d["change_pct"]
        warna = "#10b981" if chg >= 0 else "#f43f5e"
        sign = "+" if chg >= 0 else ""
        harga_str = (f"{d['harga']:,.2f}" if d['harga'] < 10000
                     else f"{d['harga']:,.0f}")
        st.markdown(
            '<div style="display: flex; justify-content: space-between; '
            'padding: 8px 0; font-size: 12px; '
            'border-bottom: 1px solid #1a2332;">'
            f'<span style="color: #94a3b8;">{nama.strip()}</span>'
            f'<span style="color: {warna}; font-weight: 600;">'
            f'{harga_str} ({sign}{chg:.2f}%)</span></div>',
            unsafe_allow_html=True
        )


with col1:
    render_market_list(global_data["indeks"], "Indeks Global")
with col2:
    render_market_list(global_data["mata_uang"], "Mata Uang")
with col3:
    render_market_list(global_data["komoditas"], "Komoditas")


# ============================================================
# DAMPAK KE IHSG
# ============================================================
st.markdown(section_title("Dampak ke IHSG"), unsafe_allow_html=True)

for nama, nilai, status, ket in dampak_ihsg:
    warna = (
        "#10b981" if status == "POSITIF" else
        "#f43f5e" if status == "NEGATIF" else
        "#f59e0b"
    )
    # Emoji status DIKEMBALIKAN
    badge_icon = (
        "🟢" if status == "POSITIF" else
        "🔴" if status == "NEGATIF" else "🟡"
    )
    st.markdown(
        '<div style="'
        'background: linear-gradient(135deg, #131a2a 0%, #0f1420 100%); '
        'border: 1px solid #1f2a3d; '
        f'border-left: 3px solid {warna}; '
        'padding: 12px 16px; border-radius: 10px; margin-bottom: 8px;">'
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; margin-bottom: 4px;">'
        f'<span style="color: #e2e8f0; font-weight: 600; font-size: 13px;">'
        f'{badge_icon} {nama}</span>'
        f'<span style="color: {warna}; font-weight: 700; font-size: 14px;">'
        f'{nilai}</span></div>'
        f'<div style="color: #64748b; font-size: 11px;">{ket}</div>'
        '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# FOOTER
# ============================================================
st.markdown(
    '<div style="text-align: center; color: #475569; font-size: 11px; '
    'margin-top: 30px; padding-top: 20px; border-top: 1px solid #1a2332;">'
    f'Update: {datetime.now().strftime("%d %B %Y, %H:%M")} · '
    f'Data dari {len(df):,} baris · {df["sektor"].nunique()} sektor'
    '</div>',
    unsafe_allow_html=True
)