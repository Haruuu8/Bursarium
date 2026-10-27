import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.info("Buka tab baru → http://localhost:8501")
    st.stop()

import os, sys
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.technical import (
    hitung_indikator_teknikal,
    hitung_sinyal_trading,
)
from quant.supres_technical import get_support_resistance
from quant.theme import (
    load_theme, page_header, section_title, empty_state,
)
from quant.parquet_loader import load_parquet_safe

load_theme()

OHLCV_DIR = "data_ohlcv_idx"


@st.cache_data(ttl=1800)
def list_available():
    df = load_parquet_safe()
    if df is None or "Kode" not in df.columns:
        return []
    kodes = df["Kode"].astype(str).str.strip().str.upper().unique()
    return sorted(kodes)


@st.cache_data(ttl=1800)
def load_ohlcv(kode):
    df_all = load_parquet_safe()
    if df_all is None or "Kode" not in df_all.columns:
        return None
    df_all["Kode"] = df_all["Kode"].astype(str).str.strip().str.upper()
    kode = str(kode).strip().upper()
    df = df_all[df_all["Kode"] == kode].copy()
    if df.empty:
        return None
    if "Date" not in df.columns:
        return None
    return df.sort_values("Date").reset_index(drop=True)


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)}"


def _fmt(v, default="—"):
    if v is None:
        return default
    try:
        return f"{v:,.0f}"
    except (TypeError, ValueError):
        return default


@st.cache_data(ttl=1800)
def compute_akumulasi(kode):
    df = load_ohlcv(kode)
    if df is None or len(df) < 20:
        return {}

    d = df.tail(20)
    high = d["High"].astype(float)
    low = d["Low"].astype(float)
    close = d["Close"].astype(float)
    vol = d["Volume"].astype(float)

    hl = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / hl
    mfm = mfm.fillna(0)
    mfv = mfm * vol
    cmf = float(mfv.sum() / vol.sum()) if vol.sum() else 0.0

    full = df.tail(40)
    vt = 1.0
    if len(full) >= 40:
        vr = full["Volume"].tail(20).mean()
        vp = full["Volume"].head(20).mean()
        if vp:
            vt = float(vr / vp)

    if len(df) >= 21:
        pn = float(df["Close"].iloc[-1])
        pt = float(df["Close"].iloc[-21])
        chg = (pn - pt) / pt * 100 if pt else 0.0
    else:
        chg = 0.0

    score = 5.0
    score += min(cmf * 15, 2) if cmf > 0 else max(cmf * 15, -2)
    if vt > 1.2 and chg > 0:
        score += 1
    elif vt > 1.2 and chg < 0:
        score -= 1
    if chg > 5:
        score += 0.5
    elif chg < -5:
        score -= 0.5
    score = max(0, min(10, score))

    if score >= 6.5:
        tipe, label = "ACCUMULATION", "AKUMULASI"
    elif score <= 3.5:
        tipe, label = "DISTRIBUTION", "DISTRIBUSI"
    else:
        tipe, label = "NEUTRAL", "NETRAL"

    return {
        "score": round(score, 1),
        "label": label,
        "tipe": tipe,
        "cmf": round(cmf, 4),
        "vol_trend": round(vt, 3),
        "price_chg_20d": round(chg, 2),
    }


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Technical", "Indikator & Sinyal Trading"), unsafe_allow_html=True)

saham_list = list_available()
if not saham_list:
    st.markdown(empty_state("", "Belum ada data", "Data teknikal belum tersedia. Silakan hubungi admin."), unsafe_allow_html=True)
    st.stop()

if "tech_kode" not in st.session_state:
    st.session_state.tech_kode = "BBCA" if "BBCA" in saham_list else saham_list[0]

# GUNAKAN KEY, JANGAN GUNAKAN VALUE
kode_input = st.text_input(
    "Kode Saham",
    key="tech_kode",
    placeholder="Ketik kode saham, mis. BBCA",
    max_chars=6,
)

kode_pilih = kode_input.upper().strip()

if not kode_pilih:
    st.info("Ketik kode saham di atas untuk mulai.")
    st.stop()

if kode_pilih not in saham_list:
    st.warning(f"Saham **{kode_pilih}** tidak ditemukan.")
    st.caption(f"Tersedia {len(saham_list)} saham. Contoh: BBCA, BBRI, TLKM, ASII, ANTM")
    st.stop()

df = load_ohlcv(kode_pilih)

if df is None or len(df) < 30:
    st.error(f"Data {kode_pilih} tidak cukup.")
    st.stop()

close_col = "Close" if "Close" in df.columns else "Closeprice"
if close_col not in df.columns:
    st.error("Kolom Close tidak ditemukan.")
    st.stop()

harga = float(df[close_col].iloc[-1])
prev = float(df[close_col].iloc[-2]) if len(df) >= 2 else harga
chg = (harga / prev - 1) * 100 if prev else 0

# High-Contrast Monokrom: Putih untuk positif, Abu untuk negatif
chg_color = "#ffffff" if chg >= 0 else "#737373"
chg_sign = "+" if chg >= 0 else ""

ind = hitung_indikator_teknikal(kode_pilih)

st.markdown(
    '<div style="'
    'background: #171717; border: 1px solid #27272a; '
    'border-radius: 8px; padding: 22px 26px; margin-bottom: 24px; '
    'display: flex; align-items: center; gap: 20px;">'
    '<div style="flex-grow: 1;">'
    f'<div style="font-size:12px; color:#a3a3a3; margin-bottom:5px; '
    f'font-weight: 500;">Technical Analysis · Daily · {len(df)} hari</div>'
    f'<div style="font-size:19px; font-weight:600; color:#ffffff; '
    f'margin-bottom:8px;">{kode_pilih}</div>'
    '<div style="display:flex; align-items:baseline; gap:12px;">'
    f'<span style="font-size:30px; font-weight:600; color:#ffffff; '
    f'letter-spacing:-0.03em; line-height:1;">{harga:,.0f}</span>'
    f'<span style="font-size:14px; font-weight:500; padding:4px 12px; '
    f'border-radius:4px; background:#262626; '
    f'color:{chg_color}; border:1px solid #404040;">'
    f'{chg_sign}{chg:.2f}%</span>'
    '</div></div></div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div style="background:#171717; '
    'border:1px solid #27272a; '
    'border-left:3px solid #ffffff; '
    'border-radius:4px; padding:12px 16px; margin-bottom:20px; '
    'font-size:13px; color:#e5e5e5;">'
    'Timeframe: <b style="color:#ffffff;">Daily</b>'
    '</div>',
    unsafe_allow_html=True,
)
st.caption("Semua analisis berbasis candle harian.")


# ============================================================
# INDIKATOR
# ============================================================
if ind:
    st.markdown(section_title("Indikator Teknikal (Daily)"), unsafe_allow_html=True)

    ind_items = [
        ("RSI (14)", f"{ind['rsi14']:.1f}", ind['rsi_label']),
        ("MACD", f"{ind['macd_hist']:.2f}", ind['macd_label']),
        ("Bollinger %B", f"{ind['bb_pct_b']:.1f}", ind['bb_label']),
        ("ATR", f"{ind['atr']:.0f}", f"{ind['atr_pct']:.2f}%"),
        ("SMA 20", f"{ind['sma20']:,.0f}", ""),
        ("EMA 20", f"{ind['ema20']:,.0f}", ""),
    ]

    cols = st.columns(3)
    for i, (label, val, sub) in enumerate(ind_items):
        with cols[i % 3]:
            sub_html = (
                f'<div style="font-size:12px; color:#737373; margin-top:6px;">'
                f'{sub}</div>'
            ) if sub else ''
            st.markdown(
                '<div style="background:#171717; border:1px solid #27272a; '
                'border-radius:8px; padding:16px 20px; margin-bottom:12px;">'
                f'<div style="font-size:11px; color:#a3a3a3; font-weight:500; '
                f'letter-spacing:0.06em; text-transform:uppercase; '
                f'margin-bottom:8px;">{label}</div>'
                f'<div style="font-size:22px; font-weight:600; color:#ffffff; '
                f'letter-spacing:-0.02em;">{val}</div>'
                f'{sub_html}'
                '</div>',
                unsafe_allow_html=True
            )

    # ------------------------------------------------------------
    # SUPERTREND
    # ------------------------------------------------------------
    st_val = ind.get("supertrend")
    st_lbl = ind.get("supertrend_label", "NEUTRAL")
    st_dist = ind.get("supertrend_dist_pct", 0)
    
    # High-Contrast Monokrom: Bullish = Putih, Bearish = Abu, Neutral = Abu terang
    st_color = "#ffffff" if st_lbl == "BULLISH" else ("#737373" if st_lbl == "BEARISH" else "#a3a3a3")
    st_icon = "[BULL]" if st_lbl == "BULLISH" else ("[BEAR]" if st_lbl == "BEARISH" else "[NEUT]")

    st_val_html = f"{st_val:,.0f}" if st_val is not None else "—"

    st.markdown(
        '<div style="background:#171717; border:1px solid #27272a; '
        f'border-left:3px solid {st_color}; border-radius:8px; '
        'padding:18px 22px; margin-bottom:12px;">'
        '<div style="display:flex; justify-content:space-between; '
        'align-items:center;">'
        '<div>'
        '<div style="font-size:11px; color:#a3a3a3; font-weight:500; '
        'letter-spacing:0.06em; text-transform:uppercase; '
        'margin-bottom:6px;">SUPERTREND (10, 3.0)</div>'
        f'<div style="font-size:24px; font-weight:600; color:#ffffff; '
        f'letter-spacing:-0.02em;">{st_val_html}</div>'
        '</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:14px; font-weight:600; color:{st_color};">'
        f'{st_icon} {st_lbl}</div>'
        f'<div style="font-size:12px; color:#737373; margin-top:6px;">'
        f'Jarak: {st_dist:+.2f}%</div>'
        '</div></div></div>',
        unsafe_allow_html=True
    )


# ============================================================
# SUPPORT & RESISTANCE
# ============================================================
st.markdown(
    section_title("Support & Resistance (Daily)",
                  "Metode: Swing Pivot Detection"),
    unsafe_allow_html=True
)

sr = get_support_resistance(kode_pilih, timeframe="daily")

if sr:
    st.markdown(
        f'<div style="background:#171717; '
        f'border:1px solid #27272a; '
        f'border-radius:6px; padding:12px 18px; margin-bottom:16px; '
        f'font-size:12px; color:#a3a3a3;">'
        f'ATR: <b style="color:#ffffff; font-weight:500;">{sr["atr"]:,.0f}</b> · '
        f'Tolerance: <b style="color:#ffffff; font-weight:500;">{sr["tolerance"]:,.0f}</b> · '
        f'Bars: <b style="color:#ffffff; font-weight:500;">{sr["n_bars"]}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Custom Monokrom Warning/Info Boxes
    for z in sr["resistances"]:
        if z["lower"] <= harga <= z["upper"] and z["score"] >= 7:
            st.markdown(
                f'<div style="background:#262626; border:1px solid #404040; border-left:4px solid #737373; border-radius:6px; padding:14px 18px; margin-bottom:16px; font-size:13px; color:#e5e5e5;">'
                f'<b style="color:#ffffff;">PERINGATAN:</b> Harga saat ini ({harga:,.0f}) sedang berada '
                f'di Zona Resistance ({z["lower"]:,.0f} - {z["upper"]:,.0f}). '
                f'Risiko tertahan dan berbalik turun.'
                f'</div>', unsafe_allow_html=True
            )

    for z in sr["supports"]:
        if z["lower"] <= harga <= z["upper"] and z["score"] >= 7:
            st.markdown(
                f'<div style="background:#262626; border:1px solid #404040; border-left:4px solid #ffffff; border-radius:6px; padding:14px 18px; margin-bottom:16px; font-size:13px; color:#e5e5e5;">'
                f'<b style="color:#ffffff;">PELUANG:</b> Harga saat ini ({harga:,.0f}) sedang berada '
                f'di Zona Support ({z["lower"]:,.0f} - {z["upper"]:,.0f}). '
                f'Area yang bagus untuk Entry Buy / Limit Order.'
                f'</div>', unsafe_allow_html=True
            )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            '<div style="font-size:11px; color:#a3a3a3; font-weight:500; '
            'letter-spacing:0.08em; text-transform:uppercase; '
            'margin-bottom:12px;">RESISTANCE</div>',
            unsafe_allow_html=True
        )
        if sr["resistances"]:
            for z in sorted(sr["resistances"], key=lambda x: abs(x["distance_pct"])):
                score = z["score"]
                n_touch = z["n_touches"]
                dist = z["distance_pct"]
                role = z.get("role", "reversal_warning")

                if role == "breakout_trigger":
                    color = "#ffffff"
                    bg_meter = "#404040"
                    badge_text = "BREAKOUT ZONE"
                    border_extra = "border:1px solid #ffffff;"
                elif role == "reversal_warning":
                    color = "#a3a3a3"
                    bg_meter = "#262626"
                    badge_text = "REVERSAL ZONE"
                    border_extra = ""
                else:
                    color = "#737373" if score < 8 else "#ffffff"
                    bg_meter = "#262626"
                    badge_text = z["strength"]
                    border_extra = ""

                st.markdown(
                    f'<div style="background:#171717; border:1px solid #27272a; '
                    f'border-radius:6px; padding:14px 18px; margin-bottom:10px; '
                    f'{border_extra}">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
                    f'<span style="color:#ffffff; font-weight:600; font-size:15px;">'
                    f'{z["lower"]:,.0f} – {z["upper"]:,.0f}</span>'
                    f'<span style="font-size:11px; font-weight:600; color:{color};">'
                    f'{badge_text}</span>'
                    f'</div>'
                    f'<div style="width:100%; height:4px; background:#262626; '
                    f'border-radius:2px; margin-bottom:10px; overflow:hidden;">'
                    f'<div style="width:{score * 10}%; height:100%; '
                    f'background:{color}; border-radius:2px;"></div>'
                    f'</div>'
                    f'<div style="display:flex; justify-content:space-between; '
                    f'font-size:11px; color:#737373;">'
                    f'<span>Skor: <b style="color:#a3a3a3; font-weight:500;">{score:.1f}</b> / 10</span>'
                    f'<span>{n_touch}x Touch</span>'
                    f'<span>Jarak: <b style="color:{color}; font-weight:500;">{dist:+.2f}%</b></span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="color:#737373; font-size:13px; padding:8px;">'
                'Tidak ada resistance terdeteksi</div>',
                unsafe_allow_html=True
            )

    with c2:
        st.markdown(
            '<div style="font-size:11px; color:#a3a3a3; font-weight:500; '
            'letter-spacing:0.08em; text-transform:uppercase; '
            'margin-bottom:12px;">SUPPORT</div>',
            unsafe_allow_html=True
        )
        if sr["supports"]:
            for z in sorted(sr["supports"], key=lambda x: abs(x["distance_pct"])):
                score = z["score"]
                n_touch = z["n_touches"]
                dist = z["distance_pct"]
                role = z.get("role", "buy_limit")

                if role == "buy_limit":
                    color = "#ffffff"
                    bg_meter = "#404040"
                    badge_text = "SUPPORT ZONE"
                    border_extra = "border:1px solid #ffffff;"
                else:
                    color = "#737373" if score < 8 else "#ffffff"
                    bg_meter = "#262626"
                    badge_text = z["strength"]
                    border_extra = ""

                st.markdown(
                    f'<div style="background:#171717; border:1px solid #27272a; '
                    f'border-radius:6px; padding:14px 18px; margin-bottom:10px; '
                    f'{border_extra}">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
                    f'<span style="color:#ffffff; font-weight:600; font-size:15px;">'
                    f'{z["lower"]:,.0f} – {z["upper"]:,.0f}</span>'
                    f'<span style="font-size:11px; font-weight:600; color:{color};">'
                    f'{badge_text}</span>'
                    f'</div>'
                    f'<div style="width:100%; height:4px; background:#262626; '
                    f'border-radius:2px; margin-bottom:10px; overflow:hidden;">'
                    f'<div style="width:{score * 10}%; height:100%; '
                    f'background:{color}; border-radius:2px;"></div>'
                    f'</div>'
                    f'<div style="display:flex; justify-content:space-between; '
                    f'font-size:11px; color:#737373;">'
                    f'<span>Skor: <b style="color:#a3a3a3; font-weight:500;">{score:.1f}</b> / 10</span>'
                    f'<span>{n_touch}x Touch</span>'
                    f'<span>Jarak: <b style="color:{color}; font-weight:500;">{dist:+.2f}%</b></span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="color:#737373; font-size:13px; padding:8px;">'
                'Tidak ada support terdeteksi</div>',
                unsafe_allow_html=True
            )
else:
    st.info("Data OHLCV tidak cukup untuk analisa S/R.")


# ============================================================
# SINYAL TRADING
# ============================================================
sig = hitung_sinyal_trading(kode_pilih)

if sig:
    st.markdown(section_title("Sinyal Trading (Daily)"), unsafe_allow_html=True)
    
    # High-Contrast Monokrom: BUY = Putih, SELL = Abu, NEUTRAL = Abu terang
    sig_color = "#ffffff" if sig['sinyal'] == 'BUY' else (
                "#737373" if sig['sinyal'] == 'SELL' else "#a3a3a3")
    sig_icon = "[BUY]" if sig['sinyal'] == 'BUY' else (
               "[SELL]" if sig['sinyal'] == 'SELL' else "[NEUT]")

    st.markdown(
        '<div style="background:#171717; border:1px solid #27272a; '
        f'border-left:3px solid {sig_color}; border-radius:8px; '
        'padding:22px 26px;">'
        '<div style="display:flex; align-items:center; gap:16px; '
        'margin-bottom:14px;">'
        f'<div style="font-size:14px; color:{sig_color}; font-weight:600;">'
        f'{sig_icon}</div>'
        '<div>'
        f'<div style="font-size:20px; font-weight:600; color:{sig_color};">'
        f'{sig["sinyal"]}</div>'
        f'<div style="font-size:12px; color:#a3a3a3; margin-top:4px;">'
        f'Confidence {sig["confidence"]}%</div>'
        '</div></div>'
        f'<div style="font-size:13px; color:#a3a3a3; line-height:1.5;">'
        f'{sig["deskripsi"]}</div>'
        '</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    for col, label, trend in [
        (c1, "Jangka Pendek", sig['trend_short']),
        (c2, "Jangka Menengah", sig['trend_mid']),
        (c3, "Jangka Panjang", sig['trend_long']),
    ]:
        color = "#ffffff" if trend == "BULLISH" else (
                "#737373" if trend == "BEARISH" else "#a3a3a3")
        with col:
            st.markdown(
                '<div style="background:#171717; border:1px solid #27272a; '
                'border-radius:6px; padding:16px; text-align:center; '
                'margin-top:12px;">'
                f'<div style="font-size:11px; color:#a3a3a3; '
                f'letter-spacing:0.05em; font-weight:500; '
                f'text-transform:uppercase;">{label}</div>'
                f'<div style="font-size:15px; font-weight:600; color:{color}; '
                f'margin-top:6px;">{trend}</div>'
                '</div>',
                unsafe_allow_html=True
            )


# ============================================================
# AKUMULASI VS DISTRIBUSI
# ============================================================
akum = compute_akumulasi(kode_pilih)

if akum:
    st.markdown(section_title("Akumulasi vs Distribusi (Daily)", "20 hari terakhir"),
                unsafe_allow_html=True)

    score = akum.get("score", 5)
    label = akum.get("label", "NETRAL")
    tipe = akum.get("tipe", "NEUTRAL")
    
    if tipe == "ACCUMULATION":
        color = "#ffffff"
    elif tipe == "DISTRIBUTION":
        color = "#737373"
    else:
        color = "#a3a3a3"
        
    cmf = akum.get("cmf", 0)
    vol_trend = akum.get("vol_trend", 1)
    price_chg = akum.get("price_chg_20d", 0)

    st.markdown(
        '<div style="background:#171717; border:1px solid #27272a; '
        f'border-left:3px solid {color}; border-radius:8px; '
        'padding:20px 22px;">'
        '<div style="display:flex; justify-content:space-between; '
        'align-items:center; margin-bottom:16px;">'
        '<div>'
        f'<div style="font-size:14px; font-weight:600; color:{color}; '
        f'margin-bottom:6px;">{label}</div>'
        f'<div style="font-size:12px; color:#a3a3a3;">'
        f'CMF: <b style="color:#ffffff; font-weight:500;">{cmf:+.3f}</b> · '
        f'Vol trend: <b style="color:#ffffff; font-weight:500;">{vol_trend:.2f}x</b>'
        f'</div></div>'
        f'<div style="font-size:30px; font-weight:600; color:{color}; '
        f'letter-spacing:-0.03em; line-height:1;">'
        f'{score:.1f}'
        '<span style="font-size:13px; color:#737373; font-weight:500;">/10</span>'
        '</div></div>'
        '<div style="display:flex; gap:12px;">'
        '<div style="flex:1; background:#262626; border-radius:6px; '
        'padding:12px 16px; border:1px solid #404040;">'
        '<div style="font-size:11px; color:#a3a3a3; font-weight:500; '
        'text-transform:uppercase; letter-spacing:0.05em; '
        'margin-bottom:4px;">Chaikin MF</div>'
        f'<div style="font-size:15px; font-weight:600; color:#ffffff;">'
        f'{cmf:+.3f}</div></div>'
        '<div style="flex:1; background:#262626; border-radius:6px; '
        'padding:12px 16px; border:1px solid #404040;">'
        '<div style="font-size:11px; color:#a3a3a3; font-weight:500; '
        'text-transform:uppercase; letter-spacing:0.05em; '
        'margin-bottom:4px;">Perubahan 20H</div>'
        f'<div style="font-size:15px; font-weight:600; color:#ffffff;">'
        f'{price_chg:+.1f}%</div></div>'
        '</div></div>',
        unsafe_allow_html=True
    )