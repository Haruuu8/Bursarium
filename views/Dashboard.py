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

SEKTOR_ICON = {
    "IXN": "💻", "IXG": "🏦", "IXJ": "💊", "RXI": "🛍️",
    "KXI": "🛒", "IXC": "⚡", "EXI": "🏭", "MXI": "📦",
    "RWO": "🏢", "JXI": "🔌", "IXP": "📱"
}

# Warna Premium (High Contrast)
STATUS_STYLE = {
    "Leading":   {"bg": "rgba(16,185,129,0.1)", "border": "#10B981", "text": "#10B981", "label": "LEADING"},
    "Weakening": {"bg": "rgba(245,158,11,0.1)", "border": "#F59E0B", "text": "#F59E0B", "label": "WEAKENING"},
    "Lagging":   {"bg": "rgba(239,68,68,0.1)",  "border": "#EF4444", "text": "#EF4444", "label": "LAGGING"},
    "Improving": {"bg": "rgba(99,102,241,0.1)", "border": "#6366F1", "text": "#818CF8", "label": "IMPROVING"},
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
st.markdown(page_header("🌍", "Global Sector Rotation", phase_desc), unsafe_allow_html=True)

st.markdown(
    '<div style="margin-bottom: 32px;">'
    '<span style="display: inline-block; padding: 8px 18px; '
    'background: linear-gradient(135deg, #1E293B, #0F172A); color: #06b6d4; '
    'border: 1px solid #334155; border-radius: 8px; font-size: 14px; '
    'font-weight: 800; letter-spacing: 1px; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">'
    f'PHASE: {phase}'
    '</span>'
    '</div>',
    unsafe_allow_html=True
)

# ============================================================
# SECTOR CARDS (Grid Layout for more space)
# ============================================================
STATUS_ORDER = {"Leading": 0, "Improving": 1, "Weakening": 2, "Lagging": 3}
df_status["order"] = df_status["status"].map(STATUS_ORDER)
df_sorted = df_status.sort_values(["order", "ret_1d"], ascending=[True, False]).reset_index(drop=True)

st.markdown(
    '<div style="font-size: 14px; color: #94A3B8; '
    'margin-bottom: 20px; padding: 14px 20px; '
    'background: #1E293B; border-radius: 8px; border-left: 4px solid #6366F1;">'
    '<b style="color:#F8FAFC;">Keterangan:</b> '
    'Angka pertama = return <b>1 hari</b> · '
    'Angka kedua = selisih return <b>20 hari</b> vs MSCI World · '
    'Label = kuadran RRG'
    '</div>',
    unsafe_allow_html=True
)

# Tampilkan 2 kolom agar lebih lega
cols = st.columns(2)
for i, (_, r) in enumerate(df_sorted.iterrows()):
    sektor = r["sektor"]; status = r["status"]; ret = r["ret_1d"]
    spread = r.get("spread_20d")
    nama_id = SEKTOR_ID.get(sektor, sektor)
    icon = SEKTOR_ICON.get(sektor, "📁")
    style = STATUS_STYLE[status]
    
    # Warna kontras tinggi
    color_ret = "#10B981" if ret >= 0 else "#EF4444"
    sign = "+" if ret >= 0 else ""

    if spread is not None and not pd.isna(spread):
        sp_color = "#10B981" if spread >= 0 else "#EF4444"
        sp_sign = "+" if spread >= 0 else ""
        spread_html = (
            f'<span style="font-size: 12px; color: {sp_color}; '
            f'font-weight: 700; background: rgba({int(sp_color[1:3], 16)}, {int(sp_color[3:5], 16)}, {int(sp_color[5:7], 16)}, 0.1); '
            f'padding: 6px 12px; border-radius: 6px; border: 1px solid rgba({int(sp_color[1:3], 16)}, {int(sp_color[3:5], 16)}, {int(sp_color[5:7], 16)}, 0.3);">'
            f'20d: {sp_sign}{spread:.2f}%</span>'
        )
    else:
        spread_html = ""

    with cols[i % 2]:
        st.markdown(
            '<div style="'
            f'background: {style["bg"]}; '
            f'border: 1px solid {style["border"]}; '
            'border-radius: 10px; padding: 20px; margin-bottom: 16px; '
            'display: flex; flex-direction: column; justify-content: space-between; height: 100%;'
            'box-shadow: 0 4px 15px rgba(0,0,0,0.1);">'
            
            '<div style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px;">'
            f'<div style="font-size: 24px; background: #0F172A; padding: 10px; border-radius: 8px; border: 1px solid #334155;">{icon}</div>'
            f'<div>'
            f'<div style="font-size: 16px; font-weight: 700; color: #F8FAFC; margin-bottom: 4px;">{nama_id}</div>'
            f'<span style="font-size: 11px; font-weight: 800; '
            f'padding: 4px 10px; border-radius: 4px; '
            f'background: rgba(0,0,0,0.2); color: {style["text"]}; '
            f'border: 1px solid {style["border"]};">'
            f'{style["label"]}</span>'
            '</div></div>'
            
            '<div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">'
            f'<span style="font-size: 18px; font-weight: 800; color: {color_ret};">'
            f'{sign}{ret:.2f}%</span>'
            f'{spread_html}'
            '</div></div>',
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

# Warna sentimen premium
if "BULLISH" in sentimen_status:
    sent_color = "#10B981"
    sent_bg = "rgba(16,185,129,0.1)"
elif "BEARISH" in sentimen_status:
    sent_color = "#EF4444"
    sent_bg = "rgba(239,68,68,0.1)"
else:
    sent_color = "#F59E0B"
    sent_bg = "rgba(245,158,11,0.1)"

st.markdown(
    '<div style="'
    f'background: {sent_bg}; '
    f'border: 1px solid {sent_color}; '
    f'border-left: 4px solid {sent_color}; '
    'border-radius: 12px; padding: 24px 28px; margin-bottom: 24px; '
    'box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'
    '<div style="font-size: 12px; color: #94A3B8; letter-spacing: 1px; '
    'margin-bottom: 8px; font-weight: 700; text-transform: uppercase;">'
    'Sentimen Global</div>'
    f'<div style="font-size: 24px; font-weight: 800; color: {sent_color}; '
    f'margin-bottom: 6px;">{sentimen_status}</div>'
    f'<div style="font-size: 14px; color: #E2E8F0;">{sentimen_detail}</div>'
    '</div>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)

def render_market_list(items, title):
    st.markdown(
        f'<div style="font-size: 12px; color: #6366F1; letter-spacing: 0.08em; '
        f'font-weight: 800; text-transform: uppercase; margin-bottom: 16px;">'
        f'{title}</div>',
        unsafe_allow_html=True
    )
    for nama, d in items.items():
        chg = d["change_pct"]
        warna = "#10B981" if chg >= 0 else "#EF4444" # Hijau / Merah
        sign = "+" if chg >= 0 else ""
        harga_str = (f"{d['harga']:,.2f}" if d['harga'] < 10000 else f"{d['harga']:,.0f}")
        
        st.markdown(
            '<div style="display: flex; justify-content: space-between; '
            'padding: 10px 0; font-size: 14px; '
            'border-bottom: 1px solid #1E293B;">'
            f'<span style="color: #94A3B8; font-weight: 500;">{nama.strip()}</span>'
            f'<span style="color: {warna}; font-weight: 700;">'
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
    # Teks & Warna
    if status == "POSITIF":
        badge_text = "POSITIF"
        warna = "#10B981"
        bg = "rgba(16,185,129,0.1)"
    elif status == "NEGATIF":
        badge_text = "NEGATIF"
        warna = "#EF4444"
        bg = "rgba(239,68,68,0.1)"
    else:
        badge_text = "NETRAL"
        warna = "#F59E0B"
        bg = "rgba(245,158,11,0.1)"

    st.markdown(
        '<div style="'
        f'background: {bg}; '
        'border: 1px solid #334155; '
        f'border-left: 4px solid {warna}; '
        'padding: 16px 20px; border-radius: 10px; margin-bottom: 12px;">'
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; margin-bottom: 6px;">'
        f'<span style="color: #F8FAFC; font-weight: 700; font-size: 14px;">'
        f'{nama} <span style="font-size: 11px; color: {warna}; margin-left: 8px;">[{badge_text}]</span></span>'
        f'<span style="color: {warna}; font-weight: 800; font-size: 16px;">'
        f'{nilai}</span></div>'
        f'<div style="color: #94A3B8; font-size: 13px;">{ket}</div>'
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# FOOTER
# ============================================================
st.markdown(
    '<div style="text-align: center; color: #64748B; font-size: 12px; '
    'margin-top: 40px; padding-top: 24px; border-top: 1px solid #1E293B;">'
    f'Update: {datetime.now().strftime("%d %B %Y, %H:%M")} · '
    f'Data dari Yahoo Finance'
    '</div>',
    unsafe_allow_html=True
)