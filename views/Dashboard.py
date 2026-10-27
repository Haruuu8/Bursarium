# Dashboard Rotasi Sektor GLOBAL (MSCI WORLD) - Halaman Utama.

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.global_data import (
    get_all_global_data,
    hitung_sentimen,
    get_dampak_ihsg,
    fetch_yahoo_chart_direct,
)
from quant.theme import load_theme, page_header, section_title

import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
import time 

if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

load_theme()

BENCHMARK = "URTH" 
RS_WINDOW = 20
MOMENTUM_WINDOW = 10
REL_WINDOW = 20

SEKTOR_ID = {
    "IXN": "Teknologi", "IXG": "Keuangan", "IXJ": "Kesehatan",
    "RXI": "Konsumen Non-Primer", "KXI": "Konsumen Primer", "IXC": "Energi",
    "EXI": "Perindustrian", "MXI": "Barang Baku", "RWO": "Properti & Real Estat",
    "JXI": "Utilitas", "IXP": "Komunikasi"
}

# Warna Notion (Soft Dark)
STATUS_STYLE = {
    "Leading":   {"bg": "#202020", "border": "#2c2c2c", "text": "#e0e0e0", "label": "LEADING"},
    "Weakening": {"bg": "#191919", "border": "#2c2c2c", "text": "#9a9a9a", "label": "WEAKENING"},
    "Lagging":   {"bg": "#191919", "border": "#2c2c2c", "text": "#6b6b6b", "label": "LAGGING"},
    "Improving": {"bg": "#191919", "border": "#2c2c2c", "text": "#9a9a9a", "label": "IMPROVING"},
}

# ============================================================
# LOAD DATA GLOBAL
# ============================================================
@st.cache_data(ttl=3600)
def load_global_data():
    tickers = list(SEKTOR_ID.keys()) + [BENCHMARK]
    data = {}
    
    for t in tickers:
        df = fetch_yahoo_chart_direct(t, range_period="1y", interval="1d")
        if df is not None and not df.empty:
            data[t] = df["Close"]
        time.sleep(0.8) 
            
    if not data:
        raise ValueError("Semua data sektor gagal diunduh. Silakan coba refresh.")
        
    df = pd.DataFrame(data)
    df = df.ffill().bfill().dropna()
    if len(df) < 35:
        raise ValueError(f"Data terlalu sedikit ({len(df)} hari).")
    return df

def build_sector_index(df):
    ret_df = df.pct_change().dropna()
    return (1 + ret_df).cumprod() * 100

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
    if total == 0: return "UNKNOWN", "Data tidak cukup"
    if n_lead >= total * 0.5: return "MARKUP", "Pasar bull kuat, mayoritas sektor memimpin"
    elif n_lead + n_imp >= total * 0.7: return "EARLY EXPANSION", "Awal ekspansi, rotasi ke sektor baru"
    elif n_lag >= total * 0.5: return "MARKDOWN", "Pasar bear, mayoritas sektor tertinggal"
    elif n_weak + n_lag >= total * 0.7: return "LATE CYCLE", "Siklus akhir, ambil untung"
    return "MIXED", "Pasar campuran, rotasi sedang berlangsung"

# ============================================================
# LOAD & HITUNG
# ============================================================
with st.spinner("Memuat data Global Sector..."):
    try:
        df_all = load_global_data()
    except Exception as e:
        st.error(f"{e}")
        st.info("Yahoo Finance terkadang membatasi pengambilan data. Tunggu 5-10 menit lalu refresh.")
        st.stop()

benchmark_series = df_all[BENCHMARK]
sector_df = df_all.drop(columns=[BENCHMARK])
sector_index = build_sector_index(sector_df)
benchmark_index = build_sector_index(benchmark_series.to_frame())[BENCHMARK]
rs_ratio, rs_mom = calc_rrg(sector_index, benchmark_index)

if rs_ratio.empty:
    st.error("Data rotasi sektor tidak dapat dihitung saat ini.")
    st.stop()

bm_20d = None
if len(benchmark_index) >= REL_WINDOW + 1:
    bm_20d = (benchmark_index.iloc[-1] / benchmark_index.iloc[-(REL_WINDOW + 1)] - 1) * 100

sector_data = []
for sektor in rs_ratio.columns:
    x = rs_ratio[sektor].iloc[-1]
    y = rs_mom[sektor].iloc[-1]
    status = classify_quadrant(x, y)

    ret_1d = 0
    if len(sector_index) >= 2:
        ret_1d = (sector_index[sektor].iloc[-1] / sector_index[sektor].iloc[-2] - 1) * 100

    spread_20d = None
    if bm_20d is not None and len(sector_index) >= REL_WINDOW + 1:
        sec_20d = (sector_index[sektor].iloc[-1] / sector_index[sektor].iloc[-(REL_WINDOW + 1)] - 1) * 100
        spread_20d = sec_20d - bm_20d

    sector_data.append({
        "sektor": sektor, "status": status, "ret_1d": ret_1d,
        "spread_20d": spread_20d, "rs_ratio": x, "rs_mom": y,
    })

df_status = pd.DataFrame(sector_data)
status_counts = df_status["status"].value_counts().to_dict()
phase, phase_desc = detect_market_phase(status_counts)

# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Global Sector Rotation", phase_desc), unsafe_allow_html=True)

st.markdown(
    '<div style="margin-bottom: 24px;">'
    '<span style="display: inline-block; padding: 6px 14px; '
    'background: #202020; color: #e0e0e0; border: 1px solid #2c2c2c; '
    'border-radius: 6px; font-size: 12px; font-weight: 600; '
    'letter-spacing: 0.5px;">'
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
df_sorted = df_status.sort_values(["order", "ret_1d"], ascending=[True, False]).reset_index(drop=True)

st.markdown(
    '<div style="font-size: 13px; color: #9a9a9a; '
    'margin-bottom: 16px; padding: 12px 16px; '
    'background: #202020; border-radius: 6px; border: 1px solid #2c2c2c;">'
    '<b style="color:#e0e0e0;">Keterangan:</b> '
    'Angka pertama = return <b>1 hari</b> · '
    'Angka kedua = selisih return <b>20 hari</b> vs MSCI World · '
    'Label = kuadran RRG'
    '</div>',
    unsafe_allow_html=True
)

for _, r in df_sorted.iterrows():
    sektor = r["sektor"]; status = r["status"]; ret = r["ret_1d"]
    spread = r.get("spread_20d")
    nama_id = SEKTOR_ID.get(sektor, sektor)
    style = STATUS_STYLE[status]
    
    # Positif = Putih Tulang, Negatif = Abu
    color_ret = "#e0e0e0" if ret >= 0 else "#9a9a9a"
    sign = "+" if ret >= 0 else ""

    if spread is not None and not pd.isna(spread):
        sp_color = "#e0e0e0" if spread >= 0 else "#9a9a9a"
        sp_sign = "+" if spread >= 0 else ""
        spread_html = (
            f'<span style="font-size: 12px; color: {sp_color}; '
            f'font-weight: 500; background: #2c2c2c; '
            f'padding: 4px 10px; border-radius: 4px; border: 1px solid #3a3a3a;">'
            f'20d: {sp_sign}{spread:.2f}% vs MSCI World</span>'
        )
    else:
        spread_html = ""

    st.markdown(
        '<div style="'
        f'background: {style["bg"]}; '
        f'border: 1px solid {style["border"]}; '
        'border-radius: 8px; padding: 16px 20px; margin-bottom: 10px; '
        'display: flex; align-items: center; justify-content: space-between;">'
        '<div>'
        f'<div style="font-size: 16px; font-weight: 600; color: #e0e0e0; '
        f'margin-bottom: 10px;">{nama_id}</div>'
        '<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">'
        f'<span style="font-size: 11px; font-weight: 600; '
        f'padding: 4px 10px; border-radius: 4px; '
        f'background: transparent; color: {style["text"]}; '
        f'border: 1px solid {style["border"]};">'
        f'{style["label"]}</span>'
        f'<span style="font-size: 14px; font-weight: 600; color: {color_ret};">'
        f'{sign}{ret:.2f}%</span>'
        f'{spread_html}'
        '</div></div></div>',
        unsafe_allow_html=True
    )

# ============================================================
# RINGKASAN PAGI
# ============================================================
st.markdown(section_title("Ringkasan Pagi", "Global market update"), unsafe_allow_html=True)

with st.spinner("Mengambil data global..."):
    global_data = get_all_global_data()
    sentimen_status, sentimen_detail, _ = hitung_sentimen(global_data)
    dampak_ihsg = get_dampak_ihsg(global_data)

# Status sentimen dibuat seragam (putih tulang)
st.markdown(
    '<div style="'
    'background: #202020; '
    'border: 1px solid #2c2c2c; '
    'border-left: 3px solid #e0e0e0; '
    'border-radius: 8px; padding: 20px 24px; margin-bottom: 24px;">'
    '<div style="font-size: 11px; color: #9a9a9a; letter-spacing: 1px; '
    'margin-bottom: 8px; font-weight: 600; text-transform: uppercase;">'
    'Sentimen Global</div>'
    f'<div style="font-size: 20px; font-weight: 600; color: #e0e0e0; '
    f'margin-bottom: 6px;">{sentimen_status}</div>'
    f'<div style="font-size: 13px; color: #9a9a9a;">{sentimen_detail}</div>'
    '</div>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)

def render_market_list(items, title):
    st.markdown(
        f'<div style="font-size: 11px; color: #9a9a9a; letter-spacing: 0.08em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 12px;">'
        f'{title}</div>',
        unsafe_allow_html=True
    )
    for nama, d in items.items():
        chg = d["change_pct"]
        warna = "#e0e0e0" if chg >= 0 else "#9a9a9a" # Putih naik, Abu turun
        sign = "+" if chg >= 0 else ""
        harga_str = (f"{d['harga']:,.2f}" if d['harga'] < 10000 else f"{d['harga']:,.0f}")
        
        st.markdown(
            '<div style="display: flex; justify-content: space-between; '
            'padding: 8px 0; font-size: 13px; '
            'border-bottom: 1px solid #2c2c2c;">'
            f'<span style="color: #9a9a9a;">{nama.strip()}</span>'
            f'<span style="color: {warna}; font-weight: 500;">'
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
    # Teks pengganti emoji
    if status == "POSITIF":
        badge_text = "[POSITIF]"
        warna = "#e0e0e0"
    elif status == "NEGATIF":
        badge_text = "[NEGATIF]"
        warna = "#9a9a9a"
    else:
        badge_text = "[NETRAL]"
        warna = "#9a9a9a"

    st.markdown(
        '<div style="'
        'background: #202020; '
        'border: 1px solid #2c2c2c; '
        'padding: 14px 16px; border-radius: 6px; margin-bottom: 10px;">'
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; margin-bottom: 6px;">'
        f'<span style="color: #e0e0e0; font-weight: 500; font-size: 13px;">'
        f'{badge_text} {nama}</span>'
        f'<span style="color: {warna}; font-weight: 600; font-size: 14px;">'
        f'{nilai}</span></div>'
        f'<div style="color: #9a9a9a; font-size: 12px;">{ket}</div>'
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# FOOTER
# ============================================================
st.markdown(
    '<div style="text-align: center; color: #6b6b6b; font-size: 11px; '
    'margin-top: 32px; padding-top: 20px; border-top: 1px solid #2c2c2c;">'
    f'Update: {datetime.now().strftime("%d %B %Y, %H:%M")} · '
    f'Data dari Yahoo Finance'
    '</div>',
    unsafe_allow_html=True
)