"""Halaman FUNDAMENTAL - baca data_fundamental/, tanpa grafik, dengan Quarterly."""
import os, sys, json
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
st.set_page_config(page_title="Fundamental", layout="wide")

if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

from quant.theme import load_theme, page_header, section_title, empty_state
from quant.parquet_loader import load_parquet_safe

load_theme()

DETAIL_DIR = "data_fundamental"

def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)}"

@st.cache_data(ttl=1800)
def list_available():
    if not os.path.exists(DETAIL_DIR): return []
    return sorted(f.replace(".json", "") for f in os.listdir(DETAIL_DIR) if f.endswith(".json"))

@st.cache_data(ttl=1800)
def load_detail(kode):
    path = os.path.join(DETAIL_DIR, f"{kode}.json")
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

@st.cache_data(ttl=1800)
def load_parquet_all(): return load_parquet_safe()

@st.cache_data(ttl=1800)
def load_ohlcv(kode):
    df_all = load_parquet_all()
    if df_all is None or "Kode" not in df_all.columns: return None
    df = df_all[df_all["Kode"] == kode].copy()
    if df.empty: return None
    return df.sort_values("Date").reset_index(drop=True)

def fmt_num(v, dec=2, suffix=""):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "-"
    try:
        if abs(v) >= 1e12: return f"{v/1e12:.{dec}f}T{suffix}"
        if abs(v) >= 1e9: return f"{v/1e9:.{dec}f}B{suffix}"
        if abs(v) >= 1e6: return f"{v/1e6:.{dec}f}M{suffix}"
        return f"{v:,.{dec}f}{suffix}"
    except Exception: return "-"

def fmt_pct(v, dec=2, plus=False):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "-"
    try:
        if abs(v) < 1: v *= 100
        return f"{v:+.{dec}f}%" if plus else f"{v:.{dec}f}%"
    except Exception: return "-"

st.markdown(page_header("", "Fundamental", "Analisis Rasio Keuangan"), unsafe_allow_html=True)
saham_list = list_available()
if not saham_list:
    st.markdown(empty_state("", "Belum ada data", "Data fundamental belum tersedia. Silakan hubungi admin."), unsafe_allow_html=True); st.stop()

if "fund_kode" not in st.session_state: st.session_state.fund_kode = "BBCA" if "BBCA" in saham_list else saham_list[0]
kode_input = st.text_input("Kode Saham", value=st.session_state.fund_kode, placeholder="Ketik kode saham, mis. BBCA", max_chars=6).upper().strip()
if not kode_input: st.info("Ketik kode saham di atas untuk mulai."); st.stop()
if kode_input not in saham_list: st.warning(f"Saham **{kode_input}** tidak ditemukan."); st.stop()
st.session_state.fund_kode = kode_input
kode_pilih = kode_input

data = load_detail(kode_pilih)
if not data: st.error(f"Data {kode_pilih} tidak ditemukan."); st.stop()

harga = data.get("harga") or 0
chg = 0
df_ohlcv = load_ohlcv(kode_pilih)
if df_ohlcv is not None and len(df_ohlcv) >= 2:
    last, prev = float(df_ohlcv["Close"].iloc[-1]), float(df_ohlcv["Close"].iloc[-2])
    chg = (last / prev - 1) * 100
    harga = last

chg_color = "#10b981" if chg >= 0 else "#f43f5e"
chg_sign = "+" if chg >= 0 else ""

st.markdown(f'<div style="background: linear-gradient(135deg, #131a2a 0%, #0f1628 100%); border: 1px solid #1a2338; border-radius: 14px; padding: 22px 26px; margin-bottom: 24px; display: flex; align-items: center; gap: 20px;"><div style="width: 64px; height: 64px; background: linear-gradient(135deg, #6366f1, #06b6d4); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 800; color: white;">{kode_pilih[:2]}</div><div style="flex-grow: 1;"><div style="font-size: 12px; color: #7d8ba3; margin-bottom: 5px; font-weight: 600;">{data.get("sektor", "")} - {data.get("industri", "")}</div><div style="font-size: 19px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">{data.get("nama", kode_pilih)}</div><div style="display: flex; align-items: baseline; gap: 12px;"><span style="font-size: 30px; font-weight: 800; color: #ffffff;">{harga:,.0f}</span><span style="font-size: 14px; font-weight: 700; padding: 4px 12px; border-radius: 8px; background: rgba({_rgb(chg_color)}, 0.12); color: {chg_color}; border: 1px solid {chg_color}40;">{chg_sign}{chg:.2f}%</span></div></div></div>', unsafe_allow_html=True)

rk = data.get("rasio_kunci", {})
tahun = data.get("update", "")[:4] or "2026"
st.markdown(section_title("Rasio Kunci", f"Tahun fiskal {tahun}"), unsafe_allow_html=True)
metrics = [("P/E", fmt_num(rk.get("pe"), 2)), ("P/B", fmt_num(rk.get("pb"), 2)), ("P/S", fmt_num(rk.get("ps"), 2)), ("ROE", fmt_pct(rk.get("roe"))), ("EPS", fmt_num(rk.get("eps"), 2)), ("D/E", fmt_num(rk.get("de"), 2)), ("Margin Bersih", fmt_pct(rk.get("margin_net"))), ("Current Ratio", fmt_num(rk.get("current_ratio"), 2))]
cols = st.columns(2)
for i, (label, val) in enumerate(metrics):
    with cols[i % 2]:
        st.markdown(f'<div style="background: #0f172a; border: 1px solid #1a2338; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"><div style="font-size: 13px; color: #94a3b8;">{label}</div><div style="font-size: 19px; font-weight: 700; color: #ffffff;">{val}</div></div>', unsafe_allow_html=True)

quarterly = data.get("quarterly", {}) or {}
q_rev, q_eps, q_ni = quarterly.get("revenue", {}) or {}, quarterly.get("eps", {}) or {}, quarterly.get("net_income", {}) or {}
def get_last_4(d): return [(k, d[k]) for k in sorted(d.keys(), reverse=True)[:4]] if d else []
rev_4q, eps_4q, ni_4q = get_last_4(q_rev), get_last_4(q_eps), get_last_4(q_ni)

if rev_4q or eps_4q:
    st.markdown(section_title("Quarterly Performance", "4 kuartal terakhir"), unsafe_allow_html=True)
    if rev_4q:
        st.markdown('<div style="font-size: 11px; color: #7d8ba3; font-weight: 600; text-transform: uppercase; margin: 0 0 12px 4px;">REVENUE</div>', unsafe_allow_html=True)
        max_rev = max((v for _, v in rev_4q if v is not None), default=1)
        for q, v in rev_4q:
            if v is None: continue
            bar_pct = min(abs(v) / max_rev * 100, 100) if max_rev > 0 else 0
            st.markdown(f'<div style="margin-bottom: 10px;"><div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span style="font-size: 13px; color: #7d8ba3; font-weight: 600;">{q}</span><span style="font-size: 13px; color: #06b6d4; font-weight: 700;">{fmt_num(v, 0)}</span></div><div style="width: 100%; height: 6px; background: #131a2a; border-radius: 3px; overflow: hidden;"><div style="width: {bar_pct}%; height: 100%; background: linear-gradient(90deg, #6366f1, #06b6d4);"></div></div></div>', unsafe_allow_html=True)
    if eps_4q:
        st.markdown('<div style="font-size: 11px; color: #7d8ba3; font-weight: 600; text-transform: uppercase; margin: 20px 0 12px 4px;">EPS</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, (q, v) in enumerate(eps_4q[:4]):
            with cols[i]: st.markdown(f'<div style="background: #0f172a; border: 1px solid #1a2338; border-radius: 10px; padding: 14px; text-align: center;"><div style="font-size: 10px; color: #7d8ba3; font-weight: 600; margin-bottom: 6px;">{q}</div><div style="font-size: 18px; font-weight: 800; color: #ffffff;">{f"{v:.2f}" if v is not None else "-"}</div></div>', unsafe_allow_html=True)
    if ni_4q:
        st.markdown('<div style="font-size: 11px; color: #7d8ba3; font-weight: 600; text-transform: uppercase; margin: 20px 0 12px 4px;">NET INCOME</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, (q, v) in enumerate(ni_4q[:4]):
            with cols[i]:
                val_str = fmt_num(v, 0) if v is not None else "-"
                color = "#10b981" if (v is not None and v >= 0) else "#f43f5e"
                st.markdown(f'<div style="background: #0f172a; border: 1px solid #1a2338; border-radius: 10px; padding: 14px; text-align: center;"><div style="font-size: 10px; color: #7d8ba3; font-weight: 600; margin-bottom: 6px;">{q}</div><div style="font-size: 16px; font-weight: 800; color: {color};">{val_str}</div></div>', unsafe_allow_html=True)

riwayat = data.get("riwayat", {})
eps_hist = riwayat.get("eps", {}) or {}
rev_hist = riwayat.get("revenue_per_share", {}) or riwayat.get("revenue", {}) or {}
tahun_list = sorted(set(list(eps_hist.keys()) + list(rev_hist.keys())), reverse=True)[:5]

if tahun_list:
    st.markdown(section_title("Riwayat Tahunan", "EPS & pendapatan per tahun"), unsafe_allow_html=True)
    rows = ""
    for y in tahun_list:
        e, r = eps_hist.get(y), rev_hist.get(y)
        rows += f'<tr><td style="padding: 12px 14px; color: #e6ebf5; font-weight: 600; border-bottom: 1px solid #1a2338;">{y}</td><td style="padding: 12px 14px; color: #e6ebf5; border-bottom: 1px solid #1a2338;">{fmt_num(e, 0) if e else "-"}</td><td style="padding: 12px 14px; color: #e6ebf5; border-bottom: 1px solid #1a2338;">{fmt_num(r, 0) if r else "-"}</td></tr>'
    st.markdown(f'<div style="background: #0f172a; border: 1px solid #1a2338; border-radius: 12px; padding: 4px; margin-bottom: 12px; overflow: hidden;"><table style="width: 100%; border-collapse: collapse;"><thead><tr><th style="text-align: left; padding: 12px 14px; font-size: 11px; color: #7d8ba3; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid #1a2338;">Tahun</th><th style="text-align: left; padding: 12px 14px; font-size: 11px; color: #7d8ba3; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid #1a2338;">EPS</th><th style="text-align: left; padding: 12px 14px; font-size: 11px; color: #7d8ba3; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid #1a2338;">Pendapatan/Saham</th></tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)

stat = data.get("statistik", {})
st.markdown(section_title("Statistik & Laporan Keuangan", "Mata uang: IDR"), unsafe_allow_html=True)
stat_items = [("Market Cap", fmt_num(stat.get("market_cap"), 0)), ("Enterprise Value", fmt_num(stat.get("enterprise_value"), 0)), ("Saham Beredar", fmt_num(stat.get("shares_outstanding"), 0)), ("Free Float", fmt_pct(stat.get("free_float_pct")))]
cols = st.columns(2)
for i, (label, val) in enumerate(stat_items):
    with cols[i % 2]: st.markdown(f'<div style="background: #0f172a; border: 1px solid #1a2338; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"><div style="font-size: 13px; color: #94a3b8;">{label}</div><div style="font-size: 17px; font-weight: 700; color: #ffffff;">{val}</div></div>', unsafe_allow_html=True)

st.markdown(f'<div style="font-size: 11px; color: #7d8ba3; font-weight: 600; text-transform: uppercase; margin: 18px 0 10px 2px;">RASIO EKUITAS {tahun}</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
for col, label, val, color in [(c1, "ROE", fmt_pct(rk.get("roe")), "#10b981"), (c2, "ROA", fmt_pct(rk.get("roa")), "#06b6d4")]:
    with col: st.markdown(f'<div style="background: #0f172a; border: 1px solid #1a2338; border-radius: 10px; padding: 16px 18px;"><div style="font-size: 11px; color: #7d8ba3; font-weight: 600; text-transform: uppercase; margin-bottom: 6px;">{label}</div><div style="font-size: 24px; font-weight: 800; color: {color};">{val}</div></div>', unsafe_allow_html=True)

st.markdown(f'<div style="text-align: center; color: #475569; font-size: 11px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #1a2338;">Sumber: yfinance + IDX XBRL - Update: {data.get("update", "")}</div>', unsafe_allow_html=True)