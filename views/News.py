"""Halaman NEWS - Berita & Keterbukaan Informasi IDX."""

import os
import sys
import json

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# GUARD LOGIN
# ============================================================
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

from quant.theme import load_theme, page_header, section_title, empty_state
from quant.idx_news import scan_news, get_stats, KATEGORI

load_theme()


# ============================================================
# CACHE WRAPPER UNTUK STREAMLIT
# ============================================================
@st.cache_data(ttl=1800, show_spinner=False)
def load_news_data(days, force=False):
    """Wrapper agar scan_news tidak dijalankan berulang kali saat tab diklik."""
    return scan_news(days=days, force_refresh=force)


def fmt_date(s):
    try:
        dt = pd.Timestamp(s)
        return dt.strftime("%d %b - %H:%M")
    except Exception:
        return str(s)[:16]


def render_card(r, highlight=False):
    tipe = r["tipe"]
    kategori_list = r["kategori"]
    bobot = r.get("bobot", 0)

    # High-Contrast Monokrom: Good = Putih, Warning = Abu Gelap, Neutral = Abu Terang
    if tipe == "good":
        accent = "#ffffff"
    elif tipe == "warning":
        accent = "#737373"
    else:
        accent = "#a3a3a3"

    bobot_badge = ""
    if bobot >= 9:
        bobot_badge = (
            '<span style="background:#ffffff; color:#0a0a0a; '
            'padding:4px 10px; border-radius:4px; font-size:11px; '
            'font-weight:700; letter-spacing:0.5px; margin-left:10px;">HOT</span>'
        )
    elif bobot >= 7:
        bobot_badge = (
            '<span style="background:#262626; color:#ffffff; border: 1px solid #404040; '
            'padding:4px 10px; border-radius:4px; font-size:11px; '
            'font-weight:600; letter-spacing:0.5px; margin-left:10px;">PENTING</span>'
        )

    kat_html = ""
    for k in kategori_list:
        kat_html += (
            f'<span style="font-size:11px; padding:4px 10px; '
            f'background:#262626; color:#a3a3a3; border: 1px solid #404040; '
            f'border-radius:4px; font-weight:500; margin-right:8px;">'
            f'{k}</span>'
        )

    lamp_html = ""
    if r.get("lampiran"):
        lamp_html = (
            f'<a href="{r["lampiran"]}" target="_blank" '
            f'style="font-size:12px; color:#ffffff; text-decoration:none; '
            f'margin-left:10px; font-weight:600; padding: 4px 0; border-bottom: 1px solid #737373;">'
            f'Lihat Dokumen</a>'
        )

    if highlight:
        border_style = f"border:1px solid #404040; border-left:4px solid {accent};"
    else:
        border_style = f"border:1px solid #27272a; border-left:4px solid {accent};"

    st.markdown(
        '<div style="'
        'background: #171717; '
        f'{border_style} '
        'border-radius: 8px; '
        'padding: 20px 24px; margin-bottom: 16px; '
        'position: relative; overflow: hidden; '
        'box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'
        '<div style="padding-left:4px;">'
        '<div style="display:flex; justify-content:space-between; '
        'align-items:center; margin-bottom:12px; gap:12px; flex-wrap:wrap;">'
        '<div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">'
        f'<span style="font-size:18px; font-weight:700; color:#ffffff; '
        f'letter-spacing:-0.02em;">{r["kode"] or "-"}</span>'
        f'{bobot_badge}'
        '</div>'
        f'<div style="font-size:13px; color:#737373; font-weight:500;">'
        f'{fmt_date(r["tanggal"])}</div>'
        '</div>'
        f'<div style="font-size:15px; color:#e5e5e5; font-weight:500; '
        f'line-height:1.6; margin-bottom:16px;">{r["judul"]}</div>'
        '<div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">'
        f'{kat_html}{lamp_html}'
        '</div>'
        '</div></div>',
        unsafe_allow_html=True
    )


def render_list(df_section, max_items=None):
    if df_section.empty:
        st.markdown(
            '<div style="text-align:center; color:#737373; font-size:14px; '
            'padding:40px 20px;">Belum ada berita di kategori ini</div>',
            unsafe_allow_html=True
        )
        return

    display = df_section.head(max_items) if max_items else df_section
    for _, r in display.iterrows():
        render_card(r)

    if max_items and len(df_section) > max_items:
        st.markdown(
            f'<div style="font-size:13px; color:#737373; '
            f'text-align:center; padding:16px;">'
            f'... dan {len(df_section) - max_items} berita lainnya</div>',
            unsafe_allow_html=True
        )


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "IDX News Flash",
                        "Keterbukaan informasi resmi emiten IDX"),
            unsafe_allow_html=True)

# Filter row
c1, c2 = st.columns([3, 1])
with c1:
    days = st.selectbox(
        "Periode",
        [7, 14, 30, 60, 90],
        index=2,
        format_func=lambda x: f"{x} hari terakhir",
        label_visibility="collapsed",
    )
with c2:
    refresh = st.button("Refresh", use_container_width=True)


# ============================================================
# LOAD DATA
# ============================================================
with st.spinner(f"Memuat pengumuman ({days} hari)..."):
    try:
        df = load_news_data(days=days, force=refresh)
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        df = pd.DataFrame()

if df.empty:
    st.warning(
        "Data pengumuman IDX belum tersedia atau gagal diambil. "
        "Pastikan file `data_news_static.json` sudah ada di folder utama."
    )
    df = pd.DataFrame(columns=[
        "kode", "judul", "tanggal", "tipe", "kategori", "bobot", "lampiran"
    ])

# Info bar
st.markdown(
    f'<div style="font-size:13px; color:#a3a3a3; '
    f'padding:10px 16px; margin-bottom:20px; '
    f'background:#171717; border: 1px solid #27272a; border-radius:8px; '
    f'display:inline-flex; align-items:center; gap:16px;">'
    f'<span><b style="color:#ffffff;">{len(df)}</b> pengumuman</span>'
    f'<span>{days} hari terakhir</span>'
    f'</div>',
    unsafe_allow_html=True
)

try:
    stats = get_stats(df)
except Exception:
    stats = {}


# ============================================================
# TABS
# ============================================================
if not df.empty:
    terbaru = df.head(10)
    katalis_all = df[df["bobot"] >= 7].copy()

    good_kat = ["DIVIDEN", "BUYBACK", "LABA_NAIK", "KONTRAK"]
    good = df[df["kategori"].apply(
        lambda x: any(k in x for k in good_kat))].copy()

    pengendali = df[df["kategori"].apply(lambda x: "PENGENDALI" in x)].copy()
    pmt = df[df["kategori"].apply(lambda x: "PMTHMETD" in x)].copy()
    investor = df[df["kategori"].apply(
        lambda x: "INVESTOR_BARU" in x or "TENDER" in x)].copy()
    warn = df[df["tipe"] == "warning"].copy()
else:
    terbaru, katalis_all, good, pengendali, pmt, investor, warn = [pd.DataFrame()] * 7

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Terbaru",
    f"Katalis ({len(katalis_all)})",
    f"Good ({len(good)})",
    f"Pengendali ({len(pengendali)})",
    f"PMTHMETD ({len(pmt)})",
    f"Investor ({len(investor)})",
    f"Warning ({len(warn)})",
])

with tab1:
    st.markdown(
        '<div style="font-size:14px; color:#a3a3a3; '
        'margin:8px 0 16px 0; font-weight:500;">'
        '10 pengumuman terbaru dari IDX</div>',
        unsafe_allow_html=True
    )
    render_list(terbaru)

with tab2:
    st.markdown(
        '<div style="font-size:14px; color:#a3a3a3; '
        'margin:8px 0 16px 0; font-weight:500;">'
        'Bobot >= 7 - katalis penting</div>',
        unsafe_allow_html=True
    )
    render_list(katalis_all, max_items=30)

with tab3:
    st.markdown(
        '<div style="font-size:14px; color:#a3a3a3; '
        'margin:8px 0 16px 0; font-weight:500;">'
        'Dividen - buyback - laba naik - kontrak baru</div>',
        unsafe_allow_html=True
    )
    render_list(good, max_items=30)

with tab4:
    st.markdown(
        '<div style="font-size:14px; color:#a3a3a3; '
        'margin:8px 0 16px 0; font-weight:500;">'
        'Akuisisi - takeover - pengendali baru</div>',
        unsafe_allow_html=True
    )
    render_list(pengendali, max_items=30)

with tab5:
    st.markdown(
        '<div style="font-size:14px; color:#a3a3a3; '
        'margin:8px 0 16px 0; font-weight:500;">'
        'Penambahan modal tanpa HMETD</div>',
        unsafe_allow_html=True
    )
    render_list(pmt, max_items=30)

with tab6:
    st.markdown(
        '<div style="font-size:14px; color:#a3a3a3; '
        'margin:8px 0 16px 0; font-weight:500;">'
        'Investor baru - tender offer</div>',
        unsafe_allow_html=True
    )
    render_list(investor, max_items=30)

with tab7:
    st.markdown(
        '<div style="font-size:14px; color:#a3a3a3; '
        'margin:8px 0 16px 0; font-weight:500;">'
        'Rugi - sanksi - pengunduran diri</div>',
        unsafe_allow_html=True
    )
    render_list(warn, max_items=30)


with st.expander("Statistik per Kategori", expanded=False):
    by_kat = stats.get("by_kategori", {})
    if by_kat:
        df_kat = pd.DataFrame([
            {
                "Kategori": k,
                "Tipe": KATEGORI.get(k, {}).get("tipe", "neutral").upper(),
                "Bobot": KATEGORI.get(k, {}).get("bobot", 0),
                "Jumlah": v,
            }
            for k, v in by_kat.items()
        ]).sort_values("Jumlah", ascending=False).reset_index(drop=True)
        df_kat.insert(0, "No", range(1, len(df_kat) + 1))
        st.dataframe(df_kat, use_container_width=True, hide_index=True,
                     height=min(500, 40 + len(df_kat) * 35))
    else:
        st.info("Belum ada data kategori.")

st.markdown(
    '<div style="text-align:center; color:#737373; font-size:12px; '
    'margin-top:32px; padding-top:20px; border-top:1px solid #27272a;">'
    'Sumber: IDX Keterbukaan Informasi - Auto-update via GitHub'
    '</div>',
    unsafe_allow_html=True
)