"""Halaman TECHNICAL — multi-scale S/R + indikator + sinyal + R:R long-only."""
import os, sys
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.technical import hitung_indikator_teknikal, hitung_sinyal_trading
from quant.supres import get_support_resistance
from quant.riskreward import hitung_rr_skenario
from quant.theme import load_theme, page_header, section_title, empty_state
from quant.parquet_loader import load_parquet_safe

st.set_page_config(page_title="Technical", layout="wide")

if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

load_theme()

@st.cache_data(ttl=1800)
def load_parquet_all(): return load_parquet_safe()

@st.cache_data(ttl=1800)
def list_available():
    df = load_parquet_all()
    if df is None or "Kode" not in df.columns: return []
    return sorted(df["Kode"].unique())

@st.cache_data(ttl=1800)
def load_ohlcv(kode):
    df_all = load_parquet_all()
    if df_all is None or "Kode" not in df_all.columns: return None
    df = df_all[df_all["Kode"] == kode].copy()
    if df.empty: return None
    return df.sort_values("Date").reset_index(drop=True)

def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)}"

@st.cache_data(ttl=1800)
def compute_akumulasi(kode):
    df = load_ohlcv(kode)
    if df is None or len(df) < 20: return {}
    d = df.tail(20)
    high, low, close, vol = d["High"].astype(float), d["Low"].astype(float), d["Close"].astype(float), d["Volume"].astype(float)
    hl = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / hl
    cmf = float((mfm.fillna(0) * vol).sum() / vol.sum()) if vol.sum() else 0.0
    full = df.tail(40); vt = 1.0
    if len(full) >= 40:
        vr, vp = full["Volume"].tail(20).mean(), full["Volume"].head(20).mean()
        if vp: vt = float(vr / vp)
    chg = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-21]) - 1) * 100 if len(df) >= 21 else 0.0
    score = 5.0 + (min(cmf * 15, 2) if cmf > 0 else max(cmf * 15, -2))
    score += 1 if vt > 1.2 and chg > 0 else -1 if vt > 1.2 and chg < 0 else 0
    score += 0.5 if chg > 5 else -0.5 if chg < -5 else 0
    score = max(0, min(10, score))
    tipe, label = ("ACCUMULATION", "AKUMULASI") if score >= 6.5 else ("DISTRIBUTION", "DISTRIBUSI") if score <= 3.5 else ("NEUTRAL", "NETRAL")
    return {"score": round(score, 1), "label": label, "tipe": tipe, "cmf": round(cmf, 4), "vol_trend": round(vt, 3), "price_chg_20d": round(chg, 2)}

st.markdown(page_header("", "Technical", "Indikator & Sinyal Trading"), unsafe_allow_html=True)
saham_list = list_available()
if not saham_list:
    st.markdown(empty_state("", "Belum ada data", "Data teknikal belum tersedia. Silakan hubungi admin."), unsafe_allow_html=True); st.stop()

if "tech_kode" not in st.session_state: st.session_state.tech_kode = "BBCA" if "BBCA" in saham_list else saham_list[0]
kode_input = st.text_input("Kode Saham", value=st.session_state.tech_kode, placeholder="Ketik kode saham, mis. BBCA", max_chars=6).upper().strip()
if not kode_input: st.info("Ketik kode saham di atas untuk mulai."); st.stop()
if kode_input not in saham_list: st.warning(f"Saham **{kode_input}** tidak ditemukan."); st.stop()
st.session_state.tech_kode = kode_input
kode_pilih = kode_input

df = load_ohlcv(kode_pilih)
if df is None or len(df) < 30: st.error(f"Data {kode_pilih} tidak cukup."); st.stop()

harga, prev = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2]) if len(df) >= 2 else float(df["Close"].iloc[-1])
chg = (harga / prev - 1) * 100 if prev else 0
chg_color = "#10b981" if chg >= 0 else "#f43f5e"
chg_sign = "+" if chg >= 0 else ""
ind = hitung_indikator_teknikal(kode_pilih)

st.markdown(f'<div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 14px; padding: 22px 26px; margin-bottom: 24px; display: flex; align-items: center; gap: 20px;"><div style="width:64px; height:64px; background: #1e293b; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 800; color: #06b6d4;">{kode_pilih[:2]}</div><div style="flex-grow: 1;"><div style="font-size:12px; color:#7d8ba3; margin-bottom:5px; font-weight: 600;">Technical Analysis - {len(df)} hari</div><div style="font-size:19px; font-weight:700; color:#ffffff; margin-bottom:8px;">{kode_pilih}</div><div style="display:flex; align-items:baseline; gap:12px;"><span style="font-size:30px; font-weight:800; color:#ffffff;">{harga:,.0f}</span><span style="font-size:14px; font-weight:700; padding:4px 12px; border-radius:8px; background:rgba({_rgb(chg_color)}, 0.12); color:{chg_color}; border:1px solid {chg_color}40;">{chg_sign}{chg:.2f}%</span></div></div></div>', unsafe_allow_html=True)

if ind:
    st.markdown(section_title("Indikator Teknikal"), unsafe_allow_html=True)
    ind_items = [("RSI (14)", f"{ind['rsi14']:.1f}", ind['rsi_label']), ("MACD", f"{ind['macd_hist']:.2f}", ind['macd_label']), ("Bollinger %B", f"{ind['bb_pct_b']:.1f}", ind['bb_label']), ("ATR", f"{ind['atr']:.0f}", f"{ind['atr_pct']:.2f}%"), ("SMA 20", f"{ind['sma20']:,.0f}", ""), ("EMA 20", f"{ind['ema20']:,.0f}", "")]
    cols = st.columns(3)
    for i, (label, val, sub) in enumerate(ind_items):
        with cols[i % 3]:
            st.markdown(f'<div style="background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:16px 20px; margin-bottom:12px;"><div style="font-size:11px; color:#64748b; font-weight:600; text-transform:uppercase; margin-bottom:8px;">{label}</div><div style="font-size:22px; font-weight:800; color:#ffffff;">{val}</div><div style="font-size:11px; color:#64748b; margin-top:6px;">{sub}</div></div>', unsafe_allow_html=True)

st.markdown(section_title("Support & Resistance", "Multi-scale pivot"), unsafe_allow_html=True)
sr = get_support_resistance(kode_pilih, timeframe="daily")
if sr:
    st.markdown(f'<div style="background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.2); border-radius:10px; padding:12px 18px; margin-bottom:16px; font-size:12px; color:#94a3b8;">ATR: <b>{sr["atr"]:,.0f}</b> - Tolerance: <b>{sr["tolerance"]:,.0f}</b> - Bars: <b>{sr["n_bars"]}</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase; margin-bottom:12px;">RESISTANCE</div>', unsafe_allow_html=True)
        for z in sr["resistances"]:
            color = "#f43f5e" if z["strength"] == "STRONG" else "#f59e0b" if z["strength"] == "MODERATE" else "#94a3b8"
            st.markdown(f'<div style="background:#0f172a; border-left:3px solid {color}; border-radius:8px; padding:12px 16px; margin-bottom:8px;"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="color:#e6ebf5; font-weight:700;">{z["lower"]:,.0f} - {z["upper"]:,.0f}</span><span style="font-size:10px; color:{color}; font-weight:700;">{z["strength"]}</span></div><div style="font-size:10px; color:#7d8ba3;"><span>Skor <b>{z["score"]}</b></span> · <span>{z["n_touches"]}x touch</span></div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase; margin-bottom:12px;">SUPPORT</div>', unsafe_allow_html=True)
        for z in sr["supports"]:
            color = "#10b981" if z["strength"] == "STRONG" else "#f59e0b" if z["strength"] == "MODERATE" else "#94a3b8"
            st.markdown(f'<div style="background:#0f172a; border-left:3px solid {color}; border-radius:8px; padding:12px 16px; margin-bottom:8px;"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="color:#e6ebf5; font-weight:700;">{z["lower"]:,.0f} - {z["upper"]:,.0f}</span><span style="font-size:10px; color:{color}; font-weight:700;">{z["strength"]}</span></div><div style="font-size:10px; color:#7d8ba3;"><span>Skor <b>{z["score"]}</b></span> · <span>{z["n_touches"]}x touch</span></div></div>', unsafe_allow_html=True)

rr_multi = hitung_rr_skenario(kode_pilih)
STRATEGI_INFO = {
    "BUY at Support": {"warna": "#10b981", "kapan": "Harga turun masuk zona support & ada candle penolakan.", "cara_entry": "Limit buy di zona. 50% di tengah zona, 50% setelah candle konfirmasi.", "cara_konfirmasi": "Tidak perlu - limit order sudah menunggu di zona.", "invalidasi": "Setup batal kalau candle close tembus ke bawah zona."},
    "BREAKOUT BUY": {"warna": "#06b6d4", "kapan": "Harga menembus ke atas zona resistance dengan tenaga.", "cara_entry": "Buy stop di atas resistance. Order baru aktif begitu harga menembus trigger.", "cara_konfirmasi": "Tunggu candle daily CLOSE di atas batas atas zona resistance.", "invalidasi": "Setup batal kalau setelah breakout harga balik masuk zona."}
}
if rr_multi and rr_multi.get("scenarios"):
    st.markdown(section_title("Risk/Reward - Skenario LONG", "Buy Support - Breakout Buy"), unsafe_allow_html=True)
    for s in rr_multi["scenarios"]:
        info = STRATEGI_INFO.get(s["tipe"], {})
        lolos = s.get("lolos", False)
        accent = info.get("warna", "#6366f1") if lolos else "#475569"
        rr_col = "#10b981" if s.get("rr_tp1", 0) >= 2 else "#f59e0b" if s.get("rr_tp1", 0) >= 1.5 else "#f43f5e"
        st.markdown(f'<div style="background:#0f172a; border:1px solid #1e293b; border-left:4px solid {accent}; border-radius:12px; padding:20px 24px; margin-bottom:14px; opacity:{"1.0" if lolos else "0.55"};"><div style="display:flex; justify-content:space-between; margin-bottom:14px;"><div><span style="font-size:15px; font-weight:800; color:#ffffff;">{s["tipe"]}</span><span style="font-size:10px; color:{accent}; font-weight:700; padding:3px 8px; margin-left:8px;">LONG</span></div><div style="font-size:20px; font-weight:800; color:{rr_col};">1 : {s.get("rr_tp1", 0):.2f}</div></div><div style="font-size:12px; color:#cbd5e1; line-height:1.6; margin-bottom:12px;"><b style="color:#e6ebf5;">Kapan:</b> {info.get("kapan","")}<br><b style="color:#e6ebf5;">Entry:</b> {info.get("cara_entry","")}</div><div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; font-size:12px;"><div><span style="color:#64748b;">Entry</span><br><b style="color:#ffffff;">{s.get("entry", 0):,.0f}</b></div><div><span style="color:#64748b;">Stop Loss</span><br><b style="color:#f43f5e;">{s.get("sl", 0):,.0f}</b></div><div><span style="color:#64748b;">TP1</span><br><b style="color:#10b981;">{s.get("tp1", 0):,.0f}</b></div></div></div>', unsafe_allow_html=True)

sig = hitung_sinyal_trading(kode_pilih)
if sig:
    st.markdown(section_title("Sinyal Trading"), unsafe_allow_html=True)
    sig_color = "#10b981" if sig['sinyal'] == 'BUY' else "#f43f5e" if sig['sinyal'] == 'SELL' else "#f59e0b"
    st.markdown(f'<div style="background:#0f172a; border:1px solid #1e293b; border-left:4px solid {sig_color}; border-radius:12px; padding:22px 26px;"><div style="display:flex; align-items:center; gap:16px; margin-bottom:14px;"><div style="font-size:32px; color:{sig_color}; font-weight:700;">{sig["sinyal"]}</div><div style="font-size:12px; color:#94a3b8;">Confidence {sig["confidence"]}%</div></div><div style="font-size:13px; color:#94a3b8;">{sig["deskripsi"]}</div></div>', unsafe_allow_html=True)

akum = compute_akumulasi(kode_pilih)
if akum:
    st.markdown(section_title("Akumulasi vs Distribusi", "20 hari terakhir"), unsafe_allow_html=True)
    color = "#10b981" if akum["tipe"] == "ACCUMULATION" else "#f43f5e" if akum["tipe"] == "DISTRIBUTION" else "#f59e0b"
    st.markdown(f'<div style="background:#0f172a; border:1px solid #1e293b; border-left:4px solid {color}; border-radius:12px; padding:20px 22px;"><div style="display:flex; justify-content:space-between; margin-bottom:14px;"><div><div style="font-size:14px; font-weight:700; color:{color}; margin-bottom:4px;">{akum["label"]}</div><div style="font-size:12px; color:#94a3b8;">CMF: <b>{akum["cmf"]:+.3f}</b> · Vol trend: <b>{akum["vol_trend"]:.2f}x</b></div></div><div style="font-size:30px; font-weight:800; color:{color};">{akum["score"]:.1f}<span style="font-size:13px; color:#64748b;">/10</span></div></div></div>', unsafe_allow_html=True)