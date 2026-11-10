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


@st.cache_data(ttl=1800, show_spinner=False)
def compute_all_indicators():
    d = load_parquet_safe()
    if d is None or d.empty:
        return None

    d = d.copy()
    d["Kode"] = d["Kode"].astype(str).str.strip().str.upper()
    d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    d = d.dropna(subset=["Date"])

    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")

    d = d.dropna(subset=["Open", "High", "Low", "Close"])
    d = d[d["Close"] > 0]
    d = d.sort_values(["Kode", "Date"]).reset_index(drop=True)

    d["Prev_Close"] = d.groupby("Kode")["Close"].shift(1)
    d["Pct_Change"] = (d["Close"] / d["Prev_Close"] - 1) * 100

    d["Vol_MA20"] = d.groupby("Kode")["Volume"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    d["Vol_Ratio"] = d["Volume"] / d["Vol_MA20"]

    rng = (d["High"] - d["Low"]).replace(0, 0.0001)
    d["MFM"] = ((d["Close"] - d["Low"]) - (d["High"] - d["Close"])) / rng
    d["MFV"] = d["MFM"] * d["Volume"]
    d["CMF_20"] = d.groupby("Kode")["MFV"].transform(
        lambda x: x.rolling(20, min_periods=10).sum()
    ) / d.groupby("Kode")["Volume"].transform(
        lambda x: x.rolling(20, min_periods=10).sum()
    )
    d["CMF_20"] = d["CMF_20"].fillna(0)

    d["Spike_Flag"] = (d["Vol_Ratio"] > 1.5).astype(int)
    d["Spike_Count_20"] = d.groupby("Kode")["Spike_Flag"].transform(
        lambda x: x.rolling(20, min_periods=5).sum()
    )

    return d


def classify_verdict(pct_change, cmf, close_gt_open):
    if pd.isna(pct_change) or pd.isna(cmf):
        return "—"
    
    if close_gt_open:
        if pct_change > 0 and cmf >= 0.1:
            return "AKUMULASI KUAT"
        elif pct_change > 0 and cmf > 0:
            return "AKUMULASI"
        elif pct_change > 0 and cmf < 0:
            return "DISTRIBUSI TERSAMAR"
        else:
            return "CAMPURAN"
    else:
        if pct_change < 0 and cmf < 0:
            return "DISTRIBUSI"
        elif pct_change < 0 and cmf > 0:
            return "AKUMULASI DIAM-DIAM"
        else:
            return "BEARISH"


# ============================================================
# HEADER & CHART
# ============================================================
st.markdown(page_header("", "Smart Money Flow", "Bandarmology & Aliran Uang Besar"), unsafe_allow_html=True)

saham_list = list_available()
if not saham_list:
    st.stop()

if "mf_kode" not in st.session_state:
    st.session_state.mf_kode = "BBCA" if "BBCA" in saham_list else saham_list[0]

col_sel, _ = st.columns([1, 2])
with col_sel:
    kode = st.selectbox("Pilih Saham", saham_list, key="mf_kode")

df = load_ohlcv(kode)
if df is None or len(df) < 50:
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

# ============================================================
# SCAN: VOLUME SPIKE HARI INI (PERBAIKAN FATAL)
# ============================================================
df_ind = compute_all_indicators()

if df_ind is None or df_ind.empty:
    st.stop()

# AMBIL DATA TERAKHIR DARI MASING-MASING SAHAM
# Ini menjamin kita mendapat 1 baris terbaru untuk tiap saham, tanpa terpengaruh 1 saham yang tanggalnya error
df_latest = df_ind.sort_values("Date").groupby("Kode").tail(1).copy()

with st.expander("🔍 Cek Data Mentah (Klik jika tabel kosong)"):
    st.write(f"Total saham: **{len(df_latest)}**")
    st.write(f"Saham Vol Ratio > 1.0: **{len(df_latest[df_latest['Vol_Ratio'] > 1.0])}**")
    st.write(f"Saham Harga Naik (Pct_Change > 0): **{len(df_latest[df_latest['Pct_Change'] > 0])}**")
    st.write(f"Saham Vol > 1.0 & Harga Naik: **{len(df_latest[(df_latest['Vol_Ratio'] > 1.0) & (df_latest['Pct_Change'] > 0)])}**")
    
    st.markdown("**Top 5 Volume Tertinggi Saat Ini:**")
    st.dataframe(df_latest[["Kode", "Date", "Vol_Ratio", "Pct_Change", "CMF_20", "Close"]].sort_values("Vol_Ratio", ascending=False).head(5))

# ============================================================
# SECTION 1: TOP VOLUME SPIKE
# ============================================================
st.markdown(
    section_title("Top Volume Spike — Harga Naik",
                  "Vol >1.0x MA20 · Harga Naik · Cek CMF untuk konfirmasi"),
    unsafe_allow_html=True
)

df_accum = df_latest[
    (df_latest["Vol_Ratio"] > 1.0) &
    (df_latest["Pct_Change"] > 0) &
    (df_latest["Close"] > 0)
].copy()

if df_accum.empty:
    st.markdown(
        '<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">'
        'Tidak ada saham yang harganya naik dengan volume di atas rata-rata saat ini.'
        '</div>', unsafe_allow_html=True
    )
else:
    df_accum = df_accum.sort_values("Vol_Ratio", ascending=False)

    st.markdown(
        f'<div style="background:#171717; '
        f'border:1px solid #27272a; border-radius:8px; '
        f'padding:14px 20px; margin-bottom:20px; '
        f'display:flex; gap:24px; flex-wrap:wrap; font-size:14px;">'
        f'<span style="color:#a3a3a3;">Saham naik dengan volume tinggi: '
        f'<b style="color:#ffffff;">{len(df_accum)}</b></span>'
        f'</div>',
        unsafe_allow_html=True
    )

    df_show = df_accum.head(30).reset_index(drop=True).copy()

    df_show["Verdict"] = df_show.apply(
        lambda r: classify_verdict(r["Pct_Change"], r["CMF_20"], r["Close"] >= r["Open"]),
        axis=1
    )

    df_show["Close"] = df_show["Close"].round(0)
    df_show["Pct_Change"] = df_show["Pct_Change"].round(2)
    df_show["Vol_Ratio"] = df_show["Vol_Ratio"].round(2)
    df_show["CMF_20"] = df_show["CMF_20"].round(3)
    df_show["Spike_Count_20"] = df_show["Spike_Count_20"].fillna(0).astype(int)

    df_show = df_show[[
        "Kode", "Close", "Pct_Change", "Vol_Ratio",
        "CMF_20", "Spike_Count_20", "Verdict"
    ]].rename(columns={
        "Close": "Harga",
        "Pct_Change": "Chg %",
        "Vol_Ratio": "Vol Ratio",
        "CMF_20": "CMF (20)",
        "Spike_Count_20": "Spike 20d",
    })

    render_table(df_show)

# ============================================================
# SECTION 2: PERINGATAN DISTRIBUSI TERSAMAR
# ============================================================
st.markdown(
    section_title("Distribusi Tersamar — Harga Naik tapi Uang Keluar",
                  "Vol >1.2x MA20 · Candle Hijau TAPI CMF <0 (Bandar jualan)"),
    unsafe_allow_html=True
)

df_dist = df_latest[
    (df_latest["Vol_Ratio"] > 1.2) &
    (df_latest["Pct_Change"] > 0) &
    (df_latest["Close"] >= df_latest["Open"]) &
    (df_latest["CMF_20"] < 0) &
    (df_latest["Close"] > 0) &
    (df_latest["Volume"] > 0)
].copy()

if df_dist.empty:
    st.markdown(
        '<div style="background:#171717; '
        'border:1px solid #27272a; border-left:4px solid #ffffff; '
        'border-radius:8px; padding:16px 20px; '
        'font-size:14px; color:#e5e5e5;">'
        'Tidak ada saham yang terindikasi <b>Distribusi Tersamar</b> saat ini.'
        '</div>',
        unsafe_allow_html=True
    )
else:
    df_dist = df_dist.sort_values("Vol_Ratio", ascending=False)

    st.markdown(
        f'<div style="background:#171717; '
        f'border:1px solid #27272a; border-left:4px solid #ffffff; '
        f'border-radius:8px; '
        f'padding:14px 20px; margin-bottom:20px; '
        f'display:flex; gap:24px; flex-wrap:wrap; font-size:14px;">'
        f'<span style="color:#a3a3a3;">Saham distribusi: '
        f'<b style="color:#ffffff;">{len(df_dist)}</b></span>'
        f'</div>',
        unsafe_allow_html=True
    )

    df_show_d = df_dist.head(15).reset_index(drop=True).copy()

    df_show_d["Verdict"] = df_show_d.apply(
        lambda r: classify_verdict(r["Pct_Change"], r["CMF_20"], r["Close"] >= r["Open"]),
        axis=1
    )

    df_show_d["Close"] = df_show_d["Close"].round(0)
    df_show_d["Pct_Change"] = df_show_d["Pct_Change"].round(2)
    df_show_d["Vol_Ratio"] = df_show_d["Vol_Ratio"].round(2)
    df_show_d["CMF_20"] = df_show_d["CMF_20"].round(3)

    df_show_d = df_show_d[[
        "Kode", "Close", "Pct_Change", "Vol_Ratio",
        "CMF_20", "Verdict"
    ]].rename(columns={
        "Close": "Harga",
        "Pct_Change": "Chg %",
        "Vol_Ratio": "Vol Ratio",
        "CMF_20": "CMF (20)",
    })

    render_table(df_show_d)