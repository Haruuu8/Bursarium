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

    mfm = ((d['Close'] - d['Low']) - (d['High'] - d['Close'])) / (d['High'] - d['Low'])
    mfv = mfm * d['Volume']
    d['CMF'] = mfv.rolling(20).sum() / d['Volume'].rolling(20).sum()

    d['OBV'] = (np.sign(d['Close'].diff()) * d['Volume']).fillna(0).cumsum()

    d['Vol_MA20'] = d['Volume'].rolling(20).mean()
    d['Vol_Ratio'] = d['Volume'] / d['Vol_MA20']
    return d


# ============================================================
# COMPUTE INDICATORS FOR ALL STOCKS
# ============================================================
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

    # Volume ratio
    d["Vol_MA20"] = d.groupby("Kode")["Volume"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    d["Vol_Ratio"] = d["Volume"] / d["Vol_MA20"]

    # % change dari close sebelumnya
    d["Pct_Change"] = d.groupby("Kode")["Close"].pct_change() * 100

    # Close position dalam range (CLV / Close Location Value)
    rng = (d["High"] - d["Low"]).replace(0, np.nan)
    d["Close_Pct"] = (d["Close"] - d["Low"]) / rng

    # CMF (20)
    d["MFM"] = ((d["Close"] - d["Low"]) - (d["High"] - d["Close"])) / rng
    d["MFV"] = d["MFM"] * d["Volume"]
    d["CMF_20"] = d.groupby("Kode")["MFV"].transform(
        lambda x: x.rolling(20, min_periods=10).sum()
    ) / d.groupby("Kode")["Volume"].transform(
        lambda x: x.rolling(20, min_periods=10).sum()
    )

    d["Spike_Flag"] = (d["Vol_Ratio"] > 1.5).astype(int)
    d["Spike_Count_20"] = d.groupby("Kode")["Spike_Flag"].transform(
        lambda x: x.rolling(20, min_periods=5).sum()
    )

    return d


def classify_verdict(close_pct, cmf, close_gt_open):
    """Klasifikasi kualitas bar tanpa emoji."""
    if pd.isna(close_pct) or pd.isna(cmf):
        return "—"
    if not close_gt_open:
        if close_pct < 0.3 and cmf < 0:
            return "DISTRIBUSI"
        return "BEARISH"
    if close_pct >= 0.7 and cmf >= 0.1:
        return "AKUMULASI KUAT"
    elif close_pct >= 0.6 and cmf > 0:
        return "AKUMULASI"
    elif close_pct >= 0.5:
        return "CAMPURAN"
    elif close_pct >= 0.3:
        return "BUYER LEMAH"
    else:
        return "DISTRIBUSI TERSAMAR"


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Smart Money Flow", "Bandarmology & Aliran Uang Besar"), unsafe_allow_html=True)

saham_list = list_available()
if not saham_list:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#ffffff; font-size:14px;">Data tidak tersedia.</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================
# PERBAIKAN INI DIA (Indentasi col1 & selectbox)
# ============================================================
col1, col2 = st.columns([1, 3])
with col1:
    if "mf_kode" not in st.session_state:
        st.session_state.mf_kode = "BBCA" if "BBCA" in saham_list else saham_list[0]
    kode = st.selectbox("Pilih Saham", saham_list, key="mf_kode")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("Grafik Statis. Data menggunakan Daily (1 Hari).")

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

# ============================================================
# SCAN: VOLUME SPIKE HARI INI
# ============================================================
df_ind = compute_all_indicators()

if df_ind is None or df_ind.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#ffffff; font-size:14px;">Data tidak tersedia untuk analisa volume spike.</div>', unsafe_allow_html=True)
    st.stop()

last_date = df_ind["Date"].max()
df_today = df_ind[df_ind["Date"] == last_date].copy()

# --- Info box ---
st.markdown(
    '<div style="background:#171717; '
    'border:1px solid #27272a; border-left:4px solid #ffffff; '
    'border-radius:8px; padding:20px 24px; margin:32px 0 24px; '
    'font-size:14px; color:#e5e5e5; line-height:1.7;">'
    '<b style="color:#ffffff;">CIRI AKUMULASI ASLI:</b><br>'
    '- Volume spike >2x MA20 <b>DAN</b> close di atas open (candle hijau)<br>'
    '- Close di <b>60%+ range</b> hari itu (CLV) — buyer dominan sampai tutup<br>'
    '- CMF(20) <b>positif</b> — tekanan beli konsisten 20 hari<br>'
    '<b style="color:#ffffff;">DISTRIBUSI TERSAMAR:</b> candle hijau + volume besar, '
    'tapi close &lt;30% range = big player jual di puncak, retail kejebak.'
    '</div>', unsafe_allow_html=True
)

# ============================================================
# SECTION 1: AKUMULASI KUAT
# ============================================================
st.markdown(
    section_title("Akumulasi Kuat — Volume Meledak + Buyer Dominan",
                  "Vol >2x MA20 · Close > Open · Close% >60% · CMF >0"),
    unsafe_allow_html=True
)

df_accum = df_today[
    (df_today["Vol_Ratio"] > 2) &
    (df_today["Vol_Ratio"] < 50) &
    (df_today["Close"] > df_today["Open"]) &
    (df_today["Close_Pct"] > 0.6) &
    (df_today["CMF_20"] > 0) &
    (df_today["Close"] > 0) &
    (df_today["Volume"] > 0)
].copy()

if df_accum.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#ffffff; font-size:14px;">Tidak ada saham dengan akumulasi asli hari ini. (Volume spike + close di atas + buyer dominan + CMF positif)</div>', unsafe_allow_html=True)
else:
    df_accum = df_accum.sort_values("Vol_Ratio", ascending=False)

    st.markdown(
        f'<div style="background:#171717; '
        f'border:1px solid #27272a; border-radius:8px; '
        f'padding:14px 20px; margin-bottom:20px; '
        f'display:flex; gap:24px; flex-wrap:wrap; font-size:14px;">'
        f'<span style="color:#a3a3a3;">Saham akumulasi: '
        f'<b style="color:#ffffff;">{len(df_accum)}</b></span>'
        f'<span style="color:#a3a3a3;">Tanggal: '
        f'<b style="color:#ffffff;">{last_date.strftime("%d %b %Y")}</b></span>'
        f'</div>',
        unsafe_allow_html=True
    )

    df_show = df_accum.head(30).reset_index(drop=True).copy()

    df_show["Verdict"] = df_show.apply(
        lambda r: classify_verdict(r["Close_Pct"], r["CMF_20"], True),
        axis=1
    )

    df_show["Close"] = df_show["Close"].round(0)
    df_show["Pct_Change"] = df_show["Pct_Change"].round(2)
    df_show["Vol_Ratio"] = df_show["Vol_Ratio"].round(2)
    df_show["CMF_20"] = df_show["CMF_20"].round(3)
    df_show["Close_Pct"] = (df_show["Close_Pct"] * 100).round(0)
    df_show["Spike_Count_20"] = df_show["Spike_Count_20"].fillna(0).astype(int)

    df_show = df_show[[
        "Kode", "Close", "Pct_Change", "Vol_Ratio",
        "Close_Pct", "CMF_20", "Spike_Count_20", "Verdict"
    ]].rename(columns={
        "Close": "Harga",
        "Pct_Change": "Chg %",
        "Vol_Ratio": "Vol Ratio",
        "Close_Pct": "Close %",
        "CMF_20": "CMF (20)",
        "Spike_Count_20": "Spike 20d",
    })

    render_table(df_show)

    st.caption(
        "**Verdict** = klasifikasi berdasarkan **CLV** (Close%) dan **CMF**: "
        "AKUMULASI KUAT (CLV>70% + CMF>0.1), "
        "AKUMULASI (CLV>60% + CMF>0), "
        "CAMPURAN. "
        "**Spike 20d** = berapa kali volume spike >1.5x dalam 20 hari."
    )

# ============================================================
# SECTION 2: PERINGATAN DISTRIBUSI TERSAMAR
# ============================================================
st.markdown(
    section_title("Distribusi Tersamar — Volume Meledak, Close Lemah",
                  "Vol >2x MA20 tapi close <30% range -> big player jual di puncak"),
    unsafe_allow_html=True
)

df_dist = df_today[
    (df_today["Vol_Ratio"] > 2) &
    (df_today["Vol_Ratio"] < 50) &
    (df_today["Close_Pct"] < 0.3) &
    (df_today["Close"] > 0) &
    (df_today["Volume"] > 0)
].copy()

if df_dist.empty:
    st.markdown(
        '<div style="background:#171717; '
        'border:1px solid #27272a; border-left:4px solid #737373; '
        'border-radius:8px; padding:16px 20px; '
        'font-size:14px; color:#e5e5e5;">'
        '[OK] Tidak ada saham dengan pola distribusi tersamar hari ini. '
        'Market sehat.'
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
        f'<span style="color:#a3a3a3;">Tanggal: '
        f'<b style="color:#ffffff;">{last_date.strftime("%d %b %Y")}</b></span>'
        f'</div>',
        unsafe_allow_html=True
    )

    df_show_d = df_dist.head(15).reset_index(drop=True).copy()

    df_show_d["Verdict"] = df_show_d.apply(
        lambda r: classify_verdict(r["Close_Pct"], r["CMF_20"],
                                    r["Close"] > r["Open"]),
        axis=1
    )

    df_show_d["Close"] = df_show_d["Close"].round(0)
    df_show_d["Pct_Change"] = df_show_d["Pct_Change"].round(2)
    df_show_d["Vol_Ratio"] = df_show_d["Vol_Ratio"].round(2)
    df_show_d["CMF_20"] = df_show_d["CMF_20"].round(3)
    df_show_d["Close_Pct"] = (df_show_d["Close_Pct"] * 100).round(0)

    df_show_d = df_show_d[[
        "Kode", "Close", "Pct_Change", "Vol_Ratio",
        "Close_Pct", "CMF_20", "Verdict"
    ]].rename(columns={
        "Close": "Harga",
        "Pct_Change": "Chg %",
        "Vol_Ratio": "Vol Ratio",
        "Close_Pct": "Close %",
        "CMF_20": "CMF (20)",
    })

    render_table(df_show_d)

    st.caption(
        "[WARN] HINDARI saham di tabel ini. Volume besar tapi close di bawah "
        "range = big player jual ke retail. Candle mungkin hijau, tapi "
        "top-heavy — harga gagal ditahan di atas. "
        "Cek besok: kalau gap down atau follow-through lemah, konfirmasi distribusi."
    )