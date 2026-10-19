import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title
from quant.parquet_loader import load_parquet_safe

st.set_page_config(page_title="Money Flow", layout="wide")
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
    
    mfm = ((d['Close'] - d['Low']) - (d['High'] - d['Close'])) / (d['High'] - d['Low'])
    mfv = mfm * d['Volume']
    d['CMF'] = mfv.rolling(20).sum() / d['Volume'].rolling(20).sum()
    
    d['OBV'] = (np.sign(d['Close'].diff()) * d['Volume']).fillna(0).cumsum()
    
    d['Vol_MA20'] = d['Volume'].rolling(20).mean()
    d['Vol_Ratio'] = d['Volume'] / d['Vol_MA20']
    return d

# HEADER
st.markdown(page_header("", "Smart Money Flow", "Bandarmology & Aliran Uang Besar"), unsafe_allow_html=True)

saham_list = list_available()
if not saham_list:
    st.warning("Data tidak tersedia.")
    st.stop()

col1, col2 = st.columns([1, 3])
with col1:
    kode = st.selectbox("Pilih Saham", saham_list, index=saham_list.index("BBCA") if "BBCA" in saham_list else 0)
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("ℹ️ **Grafik Statis** (Anti Rusak). Data saat ini menggunakan Daily (1 Hari).")

df = load_ohlcv(kode)
if df is None or len(df) < 50:
    st.error("Data saham tidak cukup.")
    st.stop()

df = calculate_money_flow(df)
last = df.iloc[-1]
prev = df.iloc[-2]
harga = last['Close']
chg = (harga / prev['Close'] - 1) * 100

st.markdown(
    f'<div style="background:#131a2a; border:1px solid #1e293b; border-radius:12px; padding:20px; margin-bottom:20px;">'
    f'<div style="font-size:12px; color:#94a3b8;">{kode} - Money Flow Analysis</div>'
    f'<div style="display:flex; align-items:baseline; gap:16px; margin-top:8px;">'
    f'<div style="font-size:36px; font-weight:800; color:#fff;">{harga:,.0f}</div>'
    f'<div style="font-size:16px; font-weight:700; color:{"#10b981" if chg>=0 else "#f43f5e"};">'
    f'{"+" if chg>=0 else ""}{chg:.2f}%</div>'
    f'</div></div>',
    unsafe_allow_html=True
)

st.markdown(section_title("Indikator Aliran Uang"), unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

mfi_val = last['MFI']
mfi_desc = "Overbought" if mfi_val > 80 else "Oversold" if mfi_val < 20 else "Netral"
c1.metric("MFI (14)", f"{mfi_val:.1f}", mfi_desc)

cmf_val = last['CMF']
cmf_desc = "Akumulasi" if cmf_val > 0 else "Distribusi"
c2.metric("CMF (20)", f"{cmf_val:+.3f}", cmf_desc)

vr_val = last['Vol_Ratio']
vr_desc = "Volume Meledak!" if vr_val > 2 else "Normal"
c3.metric("Volume Ratio", f"{vr_val:.2f}x", vr_desc)

obv_now = last['OBV']
obv_prev = df['OBV'].iloc[-10]
obv_trend = "Naik" if obv_now > obv_prev else "Turun"
c4.metric("OBV Trend (10d)", obv_trend)

# ============================================================
# GRAFIK STATIS: HARGA VS VOLUME
# ============================================================
st.markdown(section_title("Harga vs Volume", "Melihat aktivitas bandar"), unsafe_allow_html=True)

fig1 = go.Figure()
fig1.add_trace(go.Bar(
    x=df['Date'], y=df['Volume'], name='Volume', 
    marker=dict(color='#38bdf8', opacity=0.7), marker_line_width=0
))
fig1.add_trace(go.Scatter(
    x=df['Date'], y=df['Close'], name='Harga', yaxis='y2', 
    line=dict(color='#06b6d4', width=2)
))
fig1.update_layout(
    template="plotly_dark", height=400,
    xaxis=dict(fixedrange=True),
    yaxis=dict(title="Volume", showgrid=False, fixedrange=True),
    yaxis2=dict(title="Harga", overlaying='y', side='right', showgrid=False, fixedrange=True),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    dragmode=False, margin=dict(l=40, r=40, t=40, b=40)
)
st.plotly_chart(fig1, use_container_width=True, config={'staticPlot': False, 'displayModeBar': False}, theme=None)

# ============================================================
# FITUR BARU 1: NET FOREIGN FLOW (ASING)
# ============================================================
st.markdown(section_title("Net Foreign Flow (Asing)", "Arah uang asing (Beli - Jual)"), unsafe_allow_html=True)

# Cek apakah data foreign_buy dan foreign_sell tersedia dan tidak kosong semua
if 'foreign_buy' in df.columns and 'foreign_sell' in df.columns:
    # Pastikan tipenya numerik
    df['foreign_buy'] = pd.to_numeric(df['foreign_buy'], errors='coerce').fillna(0)
    df['foreign_sell'] = pd.to_numeric(df['foreign_sell'], errors='coerce').fillna(0)
    
    # Jika datanya ada (tidak semua nol)
    if df['foreign_buy'].sum() > 0 or df['foreign_sell'].sum() > 0:
        df['net_foreign'] = df['foreign_buy'] - df['foreign_sell']
        
        # Warna bar: Hijau jika Net Buy, Merah jika Net Sell
        colors_foreign = ['#10b981' if val >= 0 else '#f43f5e' for val in df['net_foreign']]
        
        fig_for = go.Figure()
        fig_for.add_trace(go.Bar(
            x=df['Date'], y=df['net_foreign'], name='Net Foreign',
            marker_color=colors_foreign
        ))
        fig_for.update_layout(
            template="plotly_dark", height=300,
            xaxis=dict(fixedrange=True), yaxis=dict(title="Net (Lembar)", fixedrange=True),
            dragmode=False, margin=dict(l=40, r=40, t=20, b=40)
        )
        st.plotly_chart(fig_for, use_container_width=True, config={'staticPlot': False, 'displayModeBar': False}, theme=None)
    else:
        st.info("Data Foreign Buy/Sell bernilai 0 atau tidak tersedia di database untuk saham ini.")
else:
    st.info("Kolom data Foreign Buy/Sell tidak ditemukan di database Anda.")

# ============================================================
# FITUR BARU 2: WHALE TRACKER (SILENT ACCUMULATION)
# ============================================================
st.markdown(section_title("Whale Tracker (Akumulasi Diam-diam)", "Harga flat tapi Volume meledak"), unsafe_allow_html=True)
st.caption("Saham di bawah ini harganya bergerak sangat tipis (< 1.5%), tetapi volumenya > 2.5x lipat dari biasanya. Seringkali ini adalah tanda 'Bandar' sedang menyerap barang tanpa membuat harga naik.")

df_all = load_parquet_safe()
last_date = df_all['Date'].max()

# Hitung Vol MA 20
vol_ma = df_all.groupby('Kode')['Volume'].transform(lambda x: x.rolling(20).mean())
df_all['Vol_Ratio'] = df_all['Volume'] / vol_ma

# Hitung Perubahan Harga Harian (Close / Prev Close - 1)
df_all['Ret_1d'] = df_all.groupby('Kode')['Close'].pct_change()

# Filter data hari terakhir
df_today = df_all[df_all['Date'] == last_date].copy()

# LOGIKA WHALE TRACKER:
# 1. Volume Ratio > 2.5
# 2. Return harian antara -1.5% sampai +1.5% (Harga Flat)
df_whale = df_today[
    (df_today['Vol_Ratio'] > 2.5) & 
    (df_today['Ret_1d'].abs() < 0.015)
].sort_values('Vol_Ratio', ascending=False)

if df_whale.empty:
    st.info("Tidak ada indikasi akumulasi tersembunyi (harga flat + volume meledak) hari ini.")
else:
    cols_show = ['Kode', 'Close', 'Ret_1d', 'Volume', 'Vol_Ratio']
    df_whale = df_whale[cols_show].head(10).reset_index(drop=True)
    # Format persentase
    df_whale['Ret_1d'] = (df_whale['Ret_1d'] * 100).round(2).astype(str) + '%'
    df_whale['Vol_Ratio'] = df_whale['Vol_Ratio'].round(2)
    
    st.dataframe(df_whale, use_container_width=True, hide_index=True)