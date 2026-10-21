"""Halaman NEWS - Berita & Keterbukaan Informasi IDX."""

import os
import sys

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="News", layout="wide")

# ============================================================
# GUARD LOGIN
# ============================================================
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

from quant.theme import load_theme, page_header, section_title, empty_state
from quant.idx_news import scan_news, get_stats, KATEGORI

load_theme()


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)}"


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

    if tipe == "good":
        accent = "#10b981"
    elif tipe == "warning":
        accent = "#f43f5e"
    else:
        accent = "#a5b4fc"

    bobot_badge = ""
    if bobot >= 9:
        bobot_badge = (
            '<span style="background:rgba(245,158,11,0.20); color:#f59e0b; '
            'padding:3px 8px; border-radius:6px; font-size:10px; '
            'font-weight:800; letter-spacing:0.5px;">HOT</span>'
        )
    elif bobot >= 7:
        bobot_badge = (
            '<span style="background:rgba(165,180,252,0.15); color:#a5b4fc; '
            'padding:3px 8px; border-radius:6px; font-size:10px; '
            'font-weight:700; letter-spacing:0.5px;">PENTING</span>'
        )

    kat_html = ""
    for k in kategori_list:
        info = KATEGORI.get(k, {})
        warna = info.get("warna", "#94a3b8")
        kat_html += (
            f'<span style="font-size:10px; padding:2px 8px; '
            f'background:rgba({_rgb(warna)},0.12); '
            f'color:{warna}; border-radius:4px; '
            f'font-weight:700; margin-right:4px;">'
            f'{k}</span>'
        )

    lamp_html = ""
    if r.get("lampiran"):
        lamp_html = (
            f'<a href="{r["lampiran"]}" target="_blank" '
            f'style="font-size:11px; color:#06b6d4; text-decoration:none; '
            f'margin-left:8px; font-weight:600;">Dokumen</a>'
        )

    if highlight:
        border_style = f"border:1px solid {accent}40; border-left:3px solid {accent};"
    else:
        border_style = f"border:1px solid #1a2338; border-left:3px solid {accent};"

    st.markdown(
        '<div style="'
        'background: linear-gradient(135deg, #131a2a 0%, #0f1628 100%); '
        f'{border_style} '
        'border-radius: 12px; '
        'padding: 14px 18px; margin-bottom: 8px; '
        'position: relative; overflow: hidden;">'
        '<div style="padding-left:4px;">'
        '<div style="display:flex; justify-content:space-between; '
        'align-items:center; margin-bottom:6px; gap:10px; flex-wrap:wrap;">'
        '<div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">'
        f'<span style="font-size:15px; font-weight:800; color:#ffffff; '
        f'letter-spacing:-0.02em;">{r["kode"] or "-"}</span>'
        f'{bobot_badge}'
        '</div>'
        f'<div style="font-size:11px; color:#7d8ba3; font-weight:600;">'
        f'{fmt_date(r["tanggal"])}</div>'
        '</div>'
        f'<div style="font-size:13px; color:#e6ebf5; font-weight:600; '
        f'line-height:1.5; margin-bottom:6px;">{r["judul"]}</div>'
        '<div style="display:flex; gap:4px; flex-wrap:wrap; align-items:center;">'
        f'{kat_html}{lamp_html}'
        '</div>'
        '</div></div>',
        unsafe_allow_html=True
    )


def render_list(df_section, max_items=None):
    if df_section.empty:
        st.markdown(
            '<div style="text-align:center; color:#475569; font-size:13px; '
            'padding:40px 20px;">Belum ada berita di kategori ini</div>',
            unsafe_allow_html=True
        )
        return

    display = df_section.head(max_items) if max_items else df_section
    for _, r in display.iterrows():
        render_card(r)

    if max_items and len(df_section) > max_items:
        st.markdown(
            f'<div style="font-size:11px; color:#7d8ba3; '
            f'text-align:center; padding:8px; font-style:italic;">'
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
    refresh = st.button("🔄 Refresh", use_container_width=True)


# ============================================================
# LOAD DATA - session state per days (retry-friendly)
# ============================================================
RETRY_COOLDOWN_SEC = 60      # auto-retry kalau kosong, tiap 60 detik
SESSION_DATA_TTL_SEC = 3600  # ✅ FIX: force refetch tiap 1 jam (bukan 4 hari)

if "news_df" not in st.session_state:
    st.session_state.news_df = None
if "news_days_loaded" not in st.session_state:
    st.session_state.news_days_loaded = None
if "news_last_refresh" not in st.session_state:
    st.session_state.news_last_refresh = None
if "news_last_attempt" not in st.session_state:
    st.session_state.news_last_attempt = None

now = pd.Timestamp.now()
last_attempt = st.session_state.news_last_attempt

cooldown_ok = (
    last_attempt is None
    or (now - last_attempt).total_seconds() > RETRY_COOLDOWN_SEC
)

has_data = (
    st.session_state.news_df is not None
    and not st.session_state.news_df.empty
)

# ✅ FIX: cek umur data di session_state
data_age_sec = (
    (now - st.session_state.news_last_refresh).total_seconds()
    if st.session_state.news_last_refresh
    else float("inf")
)
data_stale = data_age_sec > SESSION_DATA_TTL_SEC

need_fetch = (
    refresh
    or st.session_state.news_days_loaded != days
    or data_stale                        # ← FIX UTAMA: refetch setiap 1 jam
    or (not has_data and cooldown_ok)   # auto-retry kalau kosong
)

if need_fetch:
    with st.spinner(f"Ambil pengumuman dari IDX ({days} hari)..."):
        try:
            df_fetch = scan_news(days=days, force_refresh=refresh)
        except Exception as e:
            st.error(f"Gagal mengambil data: {e}")
            df_fetch = pd.DataFrame()

    if not df_fetch.empty and "tanggal" in df_fetch.columns:
        df_fetch["tanggal_dt"] = pd.to_datetime(
            df_fetch["tanggal"], errors="coerce")
        df_fetch = df_fetch.sort_values(
            "tanggal_dt", ascending=False, na_position="last"
        ).reset_index(drop=True)
        # Sukses → simpan
        st.session_state.news_df = df_fetch
        st.session_state.news_days_loaded = days
    else:
        # GAGAL → JANGAN timpa data lama yang bagus
        if not has_data:
            st.session_state.news_df = None
            st.session_state.news_days_loaded = None

    st.session_state.news_last_refresh = pd.Timestamp.now()
    st.session_state.news_last_attempt = pd.Timestamp.now()

df = st.session_state.news_df
last_refresh = st.session_state.news_last_refresh

if df is None:
    df = pd.DataFrame()

if df.empty:
    st.warning(
        "Data pengumuman IDX belum tersedia atau gagal diambil dari server IDX."
    )
    retry_cols = st.columns([1, 1, 3])
    with retry_cols[0]:
        if st.button("🔄 Coba lagi", type="primary", use_container_width=True):
            st.session_state.news_last_attempt = None  # bypass cooldown
            st.session_state.news_df = None
            st.rerun()
    with retry_cols[1]:
        if st.button("Bersihkan cache", use_container_width=True):
            import shutil
            shutil.rmtree("data_idx_news", ignore_errors=True)
            st.session_state.news_df = None
            st.session_state.news_last_attempt = None
            st.rerun()
    df = pd.DataFrame(columns=[
        "kode", "judul", "tanggal", "tipe", "kategori", "bobot", "lampiran"
    ])

# Info bar
_data_age_min = (
    (pd.Timestamp.now() - last_refresh).total_seconds() / 60
    if last_refresh else 0
)

if _data_age_min < 60:
    _age_str = f"{int(_data_age_min)} menit lalu"
else:
    _age_str = f"{int(_data_age_min / 60)} jam lalu"

st.markdown(
    f'<div style="font-size:11px; color:#7d8ba3; '
    f'padding:6px 12px; margin-bottom:12px; '
    f'background:rgba(99,102,241,0.08); border-radius:8px; '
    f'display:inline-block;">'
    f'<b style="color:#a5b4fc;">{len(df)}</b> pengumuman · '
    f'{days} hari terakhir · '
    f'Diperbarui: <b style="color:#f59e0b;">{_age_str}</b>'
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
        '<div style="font-size:12px; color:#7d8ba3; '
        'margin:8px 0 12px 4px; font-weight:500;">'
        '10 pengumuman terbaru dari IDX</div>',
        unsafe_allow_html=True
    )
    render_list(terbaru)

with tab2:
    st.markdown(
        '<div style="font-size:12px; color:#7d8ba3; '
        'margin:8px 0 12px 4px; font-weight:500;">'
        'Bobot >= 7 - katalis penting</div>',
        unsafe_allow_html=True
    )
    render_list(katalis_all, max_items=30)

with tab3:
    st.markdown(
        '<div style="font-size:12px; color:#7d8ba3; '
        'margin:8px 0 12px 4px; font-weight:500;">'
        'Dividen - buyback - laba naik - kontrak baru</div>',
        unsafe_allow_html=True
    )
    render_list(good, max_items=30)

with tab4:
    st.markdown(
        '<div style="font-size:12px; color:#7d8ba3; '
        'margin:8px 0 12px 4px; font-weight:500;">'
        'Akuisisi - takeover - pengendali baru</div>',
        unsafe_allow_html=True
    )
    render_list(pengendali, max_items=30)

with tab5:
    st.markdown(
        '<div style="font-size:12px; color:#7d8ba3; '
        'margin:8px 0 12px 4px; font-weight:500;">'
        'Penambahan modal tanpa HMETD</div>',
        unsafe_allow_html=True
    )
    render_list(pmt, max_items=30)

with tab6:
    st.markdown(
        '<div style="font-size:12px; color:#7d8ba3; '
        'margin:8px 0 12px 4px; font-weight:500;">'
        'Investor baru - tender offer</div>',
        unsafe_allow_html=True
    )
    render_list(investor, max_items=30)

with tab7:
    st.markdown(
        '<div style="font-size:12px; color:#7d8ba3; '
        'margin:8px 0 12px 4px; font-weight:500;">'
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
    '<div style="text-align:center; color:#475569; font-size:11px; '
    'margin-top:20px; padding-top:16px; border-top:1px solid #1a2338;">'
    'Sumber: IDX Keterbukaan Informasi - Data di-cache 3 jam - '
    'IDX publish delay 1-2 hari kerja'
    '</div>',
    unsafe_allow_html=True
)