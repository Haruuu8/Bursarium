import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title
from quant.parquet_loader import load_parquet_safe

load_theme()


@st.cache_data(ttl=1800)
def load_ohlcv(kode):
    df_all = load_parquet_safe()
    if df_all is None or "Kode" not in df_all.columns:
        return None
    df = df_all[df_all["Kode"] == kode].copy()
    if df.empty:
        return None
    return df.sort_values("Date").reset_index(drop=True)


@st.cache_data(ttl=1800)
def list_available():
    df = load_parquet_safe()
    if df is None or "Kode" not in df.columns:
        return []
    return sorted(df["Kode"].unique())


def calculate_money_flow(df):
    d = df.copy()
    tp = (d['High'] + d['Low'] + d['Close']) / 3
    mf = tp * d['Volume']
    pos_mf = mf.where(tp > tp.shift(1), 0)
    neg_mf = mf.where(tp < tp.shift(1), 0)
    mfr = pos_mf.rolling(14).sum() / neg_mf.rolling(14).sum()
    d['MFI'] = 100 - (100 / (1 + mfr))

    rng = (d['High'] - d['Low']).replace(0, 0.0001)
    mfm = ((d['Close'] - d['Low']) - (d['High'] - d['Close'])) / rng
    mfv = mfm * d['Volume']
    d['CMF'] = mfv.rolling(20).sum() / d['Volume'].rolling(20).sum()

    d['OBV'] = (np.sign(d['Close'].diff()) * d['Volume']).fillna(0).cumsum()

    d['Vol_MA20'] = d['Volume'].rolling(20).mean()
    d['Vol_Ratio'] = d['Volume'] / d['Vol_MA20']
    return d


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Smart Money Flow", "Bandarmology & Aliran Uang Besar"), unsafe_allow_html=True)

saham_list = list_available()
if not saham_list:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#ffffff; font-size:14px;">Data tidak tersedia.</div>', unsafe_allow_html=True)
    st.stop()

if "mf_kode" not in st.session_state:
    st.session_state.mf_kode = "BBCA" if "BBCA" in saham_list else saham_list[0]

col_sel, _ = st.columns([1, 2])
with col_sel:
    kode = st.selectbox("Pilih Saham", saham_list, key="mf_kode")

df = load_ohlcv(kode)
if df is None or len(df) < 50:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#ffffff; font-size:14px;">Data saham tidak cukup.</div>', unsafe_allow_html=True)
    st.stop()

df = calculate_money_flow(df)
last = df.iloc[-1]
prev = df.iloc[-2]
harga = last['Close']
chg = (harga / prev['Close'] - 1) * 100

st.markdown(
    f'<div style="background:#171717; border:1px solid #27272a; border-radius:8px; padding:24px; margin-bottom:24px;">'
    f'<div style="font-size:12px; color:#a3a3a3; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">{kode} - Money Flow Analysis</div>'
    f'<div style="display:flex; align-items:baseline; gap:16px; margin-top:8px;">'
    f'<div style="font-size:36px; font-weight:800; color:#ffffff;">{harga:,.0f}</div>'
    f'<div style="font-size:16px; font-weight:600; color:{"#ffffff" if chg>=0 else "#737373"};">'
    f'{"+" if chg>=0 else ""}{chg:.2f}%</div>'
    f'</div></div>',
    unsafe_allow_html=True
)

# ============================================================
# METRIK
# ============================================================
st.markdown(section_title("Indikator Aliran Uang"), unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

def render_metric(col, title, value, desc):
    col.markdown(
        f'<div style="background: #171717; border: 1px solid #27272a; border-radius: 8px; padding: 20px;">'
        f'<div style="font-size: 11px; color: #a3a3a3; text-transform: uppercase; letter-spacing: 0.5px;">{title}</div>'
        f'<div style="font-size: 24px; font-weight: 700; color: #ffffff; margin: 10px 0;">{value}</div>'
        f'<div style="font-size: 13px; color: #737373;">{desc}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

mfi_val = last['MFI']
mfi_desc = "Overbought" if mfi_val > 80 else "Oversold" if mfi_val < 20 else "Netral"
render_metric(c1, "MFI (14)", f"{mfi_val:.1f}", mfi_desc)

cmf_val = last['CMF']
cmf_desc = "Akumulasi" if cmf_val > 0 else "Distribusi"
render_metric(c2, "CMF (20)", f"{cmf_val:+.3f}", cmf_desc)

vr_val = last['Vol_Ratio']
vr_desc = "Volume Meledak" if vr_val > 2 else "Normal"
render_metric(c3, "Volume Ratio", f"{vr_val:.2f}x", vr_desc)

obv_now = last['OBV']
obv_prev = df['OBV'].iloc[-10]
obv_trend = "Naik" if obv_now > obv_prev else "Turun"
render_metric(c4, "OBV Trend (10d)", obv_trend, "")

# ============================================================
# GRAFIK 1: HARGA VS VOLUME
# ============================================================
st.markdown(section_title("Harga vs Volume", "Melihat aktivitas bandar"), unsafe_allow_html=True)
fig1 = go.Figure()
fig1.add_trace(go.Bar(
    x=df['Date'], y=df['Volume'], name='Volume',
    marker=dict(color='#404040', opacity=0.8), marker_line_width=0
))
fig1.add_trace(go.Scatter(
    x=df['Date'], y=df['Close'], name='Harga', yaxis='y2',
    line=dict(color='#ffffff', width=2)
))
fig1.update_layout(
    template="plotly_dark", height=400,
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(fixedrange=True, gridcolor='#27272a'),
    yaxis=dict(title="Volume", showgrid=False, fixedrange=True),
    yaxis2=dict(title="Harga", overlaying='y', side='right', showgrid=False, fixedrange=True),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#ffffff")),
    dragmode=False, margin=dict(l=40, r=40, t=40, b=40)
)
st.plotly_chart(fig1, use_container_width=True, config={'staticPlot': False, 'displayModeBar': False}, theme=None)

st.markdown(
    '<div style="text-align: right; margin-top: -10px; margin-bottom: 24px; font-size: 13px; color: #737373; font-weight: 500;">'
    'Grafik Statis. Data menggunakan Daily (1 Hari).'
    '</div>', 
    unsafe_allow_html=True
)

# ============================================================
# GRAFIK 2: CMF
# ============================================================
st.markdown(section_title("Tekanan Beli vs Jual", "CMF & MFI"), unsafe_allow_html=True)
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df['Date'], y=df['CMF'], name='CMF', line=dict(color='#ffffff', width=2)))
fig2.add_hline(y=0, line_dash="dash", line_color="#404040")
fig2.update_layout(
    template="plotly_dark", height=300,
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(fixedrange=True, gridcolor='#27272a'), 
    yaxis=dict(title="CMF", fixedrange=True, gridcolor='#27272a'),
    dragmode=False, margin=dict(l=40, r=40, t=20, b=40)
)
st.plotly_chart(fig2, use_container_width=True, config={'staticPlot': False, 'displayModeBar': False}, theme=None)