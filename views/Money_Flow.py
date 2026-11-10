import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title, render_table
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


@st.cache_data(ttl=1800, show_spinner=False)
def compute_volume_spikes():
    d = load_parquet_safe()
    if d is None or d.empty:
        return None

    d = d.copy()
    d["Kode"] = d["Kode"].astype(str).str.strip().str.upper()
    
    # Normalisasi tanggal (hilangkan jam)
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce").dt.normalize()
    d = d.dropna(subset=["Date"])

    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")

    d = d.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    d = d[d["Close"] > 0]
    d = d.sort_values(["Kode", "Date"]).reset_index(drop=True)

    # Hitung MA20 dan Vol Ratio
    d["Vol_MA20"] = d.groupby("Kode")["Volume"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    d["Vol_Ratio"] = (d["Volume"] / d["Vol_MA20"]).fillna(0)
    
    # Hitung Pct Change
    d["Prev_Close"] = d.groupby("Kode")["Close"].shift(1)
    d["Pct_Change"] = (d["Close"] / d["Prev_Close"] - 1) * 100
    
    # Hitung CMF 5
    rng = (d["High"] - d["Low"]).replace(0, 0.0001)
    d["MFM"] = ((d["Close"] - d["Low"]) - (d["High"] - d["Close"])) / rng
    d["MFV"] = d["MFM"] * d["Volume"]
    d["CMF_5"] = d.groupby("Kode")["MFV"].transform(
        lambda x: x.rolling(5, min_periods=5).sum()
    ) / d.groupby("Kode")["Volume"].transform(
        lambda x: x.rolling(5, min_periods=5).sum()
    )
    d["CMF_5"] = d["CMF_5"].fillna(0)

    return d


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Volume Spike Screener", "Mencari saham dengan volume meledak"), unsafe_allow_html=True)

# ============================================================
# SCAN LOGIC
# ============================================================
df_ind = compute_volume_spikes()

if df_ind is None or df_ind.empty:
    st.stop()

# Ambil baris terakhir dari MASING-MASING saham
df_latest = df_ind.sort_values("Date").groupby("Kode").tail(1).copy()

# Filter Volume Spike (> 1.5x MA20)
df_spike = df_latest[(df_latest["Vol_Ratio"] > 1.5) & (df_latest["Volume"] > 0)].copy()
df_spike = df_spike.sort_values("Vol_Ratio", ascending=False)

# Panel Info
st.markdown(
    f'<div style="background:#171717; border:1px solid #27272a; border-radius:8px; '
    f'padding:20px 24px; margin-bottom:24px; font-size:14px; color:#e5e5e5;">'
    f'Total Saham di Database: <b>{len(df_latest)}</b><br>'
    f'Total Saham Volume > 1.5x MA20: <b style="color:#ffffff; font-size:18px;">{len(df_spike)}</b>'
    f'</div>',
    unsafe_allow_html=True
)

if df_spike.empty:
    st.warning("Tidak ada saham yang volume-nya meledak > 1.5x MA20 saat ini.")
else:
    df_show = df_spike.copy()

    def get_verdict(row):
        pct = row["Pct_Change"]
        cmf = row["CMF_5"]
        if pct > 0 and cmf > 0:
            return "AKUMULASI"
        elif pct > 0 and cmf < 0:
            return "DISTRIBUSI TERSAMAR"
        elif pct < 0 and cmf < 0:
            return "DISTRIBUSI"
        elif pct < 0 and cmf > 0:
            return "AKUMULASI DIAM-DIAM"
        return "NETRAL"

    df_show["Verdict"] = df_show.apply(get_verdict, axis=1)

    df_show["Close"] = df_show["Close"].round(0)
    df_show["Pct_Change"] = df_show["Pct_Change"].round(2)
    df_show["Vol_Ratio"] = df_show["Vol_Ratio"].round(2)
    df_show["CMF_5"] = df_show["CMF_5"].round(3)
    df_show["Volume_Str"] = df_show["Volume"].apply(lambda x: f"{x:,.0f}")
    df_show["Vol_MA20_Str"] = df_show["Vol_MA20"].apply(lambda x: f"{x:,.0f}")

    df_show = df_show[[
        "Kode", "Date", "Close", "Pct_Change", "Volume_Str", "Vol_MA20_Str", "Vol_Ratio", "CMF_5", "Verdict"
    ]].rename(columns={
        "Date": "Tanggal",
        "Close": "Harga",
        "Pct_Change": "Chg %",
        "Volume_Str": "Volume",
        "Vol_MA20_Str": "Avg Vol 20D",
        "Vol_Ratio": "Vol Ratio",
        "CMF_5": "CMF (5)",
    })

    render_table(df_show)

# ============================================================
# DETAIL SAHAM (GRAFIK)
# ============================================================
st.markdown("<br><hr style='border-color:#27272a; margin: 30px 0;'><br>", unsafe_allow_html=True)
st.markdown(section_title("Analisis Per Saham", "Pilih saham di bawah untuk melihat grafik volume"), unsafe_allow_html=True)

saham_list = df_spike["Kode"].tolist() if not df_spike.empty else list_available()
kode = st.selectbox("Pilih Saham", saham_list)

df = load_ohlcv(kode)
if df is not None and not df.empty:
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

# ============================================================
# PANEL DEBUGGING BARU (VALIDASI CSV vs PARQUET)
# ============================================================
with st.expander("🕵️ Cek Validasi Data (CSV vs Parquet)"):
    st.markdown("Panel ini akan mengecek apakah data Parquet yang dibaca Streamlit sudah sesuai dengan folder CSV asli di laptop Anda.")
    
    csv_dir = "data_ohlcv_idx"
    csv_count = 0
    if os.path.exists(csv_dir):
        csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
        csv_count = len(csv_files)
        
    df_raw = load_parquet_safe()
    
    col1, col2 = st.columns(2)
    col1.metric("Total File CSV di Folder", f"{csv_count:,} file")
    col2.metric("Total Saham di Parquet (Dibaca Aplikasi)", f"{df_raw['Kode'].nunique():,} saham")