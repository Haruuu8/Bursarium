import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.info("Buka tab baru → http://localhost:8501")
    st.stop()

# Halaman TECHNICAL — multi-scale S/R + indikator + sinyal + R:R long-only.

import os, sys
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.technical import (
    hitung_indikator_teknikal,
    hitung_sinyal_trading,
)
from quant.supres import get_support_resistance
from quant.riskreward import hitung_rr_skenario
from quant.theme import (
    load_theme, page_header, section_title, empty_state,
)
from quant.parquet_loader import load_parquet_safe

st.set_page_config(page_title="Technical", page_icon="📉", layout="wide")
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
    st.markdown(empty_state("📭", "Belum ada data", "Data teknikal belum tersedia. Silakan hubungi admin."), unsafe_allow_html=True)
    st.stop()

if "tech_kode" not in st.session_state:
    st.session_state.tech_kode = "BBCA" if "BBCA" in saham_list else saham_list[0]

kode_input = st.text_input(
    "Kode Saham",
    value=st.session_state.tech_kode,
    placeholder="Ketik kode saham, mis. BBCA",
    max_chars=6,
).upper().strip()

if not kode_input:
    st.info("Ketik kode saham di atas untuk mulai.")
    st.stop()

if kode_input not in saham_list:
    st.warning(f"⚠️ Saham **{kode_input}** tidak ditemukan.")
    st.caption(f"Tersedia {len(saham_list)} saham. Contoh: BBCA, BBRI, TLKM, ASII, ANTM")
    st.stop()

st.session_state.tech_kode = kode_input
kode_pilih = kode_input

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
chg_color = "#10b981" if chg >= 0 else "#f43f5e"
chg_sign = "+" if chg >= 0 else ""

ind = hitung_indikator_teknikal(kode_pilih)

st.markdown(
    '<div style="'
    'background: #0f172a; border: 1px solid #1e293b; '
    'border-radius: 14px; padding: 22px 26px; margin-bottom: 24px; '
    'display: flex; align-items: center; gap: 20px;">'
    '<div style="flex-grow: 1;">'
    f'<div style="font-size:12px; color:#7d8ba3; margin-bottom:5px; '
    f'font-weight: 600;">Technical Analysis · Daily · {len(df)} hari</div>'
    f'<div style="font-size:19px; font-weight:700; color:#ffffff; '
    f'margin-bottom:8px;">{kode_pilih}</div>'
    '<div style="display:flex; align-items:baseline; gap:12px;">'
    f'<span style="font-size:30px; font-weight:800; color:#ffffff; '
    f'letter-spacing:-0.03em; line-height:1;">{harga:,.0f}</span>'
    f'<span style="font-size:14px; font-weight:700; padding:4px 12px; '
    f'border-radius:8px; background:rgba({_rgb(chg_color)}, 0.12); '
    f'color:{chg_color}; border:1px solid {chg_color}40;">'
    f'{chg_sign}{chg:.2f}%</span>'
    '</div></div></div>',
    unsafe_allow_html=True
)

# Banner timeframe
st.markdown(
    '<div style="background:rgba(245,158,11,0.08); '
    'border:1px solid rgba(245,158,11,0.25); '
    'border-left:4px solid #f59e0b; '
    'border-radius:10px; padding:10px 16px; margin-bottom:20px; '
    'font-size:12px; color:#cbd5e1;">'
    '📅 <b style="color:#f59e0b;">Timeframe: Daily</b>'
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
                f'<div style="font-size:11px; color:#64748b; margin-top:6px;">'
                f'{sub}</div>'
            ) if sub else ''
            st.markdown(
                '<div style="background:#0f172a; border:1px solid #1e293b; '
                'border-radius:12px; padding:16px 20px; margin-bottom:12px;">'
                f'<div style="font-size:11px; color:#64748b; font-weight:600; '
                f'letter-spacing:0.06em; text-transform:uppercase; '
                f'margin-bottom:8px;">{label}</div>'
                f'<div style="font-size:22px; font-weight:800; color:#ffffff; '
                f'letter-spacing:-0.02em;">{val}</div>'
                f'{sub_html}'
                '</div>',
                unsafe_allow_html=True
            )

    # ------------------------------------------------------------
    # SUPERTREND — kartu khusus
    # ------------------------------------------------------------
    st_val = ind.get("supertrend")
    st_lbl = ind.get("supertrend_label", "NEUTRAL")
    st_dist = ind.get("supertrend_dist_pct", 0)
    st_color = "#10b981" if st_lbl == "BULLISH" else ("#f43f5e" if st_lbl == "BEARISH" else "#f59e0b")
    st_icon = "↗" if st_lbl == "BULLISH" else ("↘" if st_lbl == "BEARISH" else "—")

    st_val_html = f"{st_val:,.0f}" if st_val is not None else "—"

    st.markdown(
        '<div style="background:#0f172a; border:1px solid #1e293b; '
        f'border-left:4px solid {st_color}; border-radius:12px; '
        'padding:18px 22px; margin-bottom:12px;">'
        '<div style="display:flex; justify-content:space-between; '
        'align-items:center;">'
        '<div>'
        '<div style="font-size:11px; color:#64748b; font-weight:600; '
        'letter-spacing:0.06em; text-transform:uppercase; '
        'margin-bottom:6px;">SUPERTREND (10, 3.0)</div>'
        f'<div style="font-size:24px; font-weight:800; color:#ffffff; '
        f'letter-spacing:-0.02em;">{st_val_html}</div>'
        '</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:18px; font-weight:800; color:{st_color};">'
        f'{st_icon} {st_lbl}</div>'
        f'<div style="font-size:11px; color:#94a3b8; margin-top:4px;">'
        f'Jarak: {st_dist:+.2f}%</div>'
        '</div></div></div>',
        unsafe_allow_html=True
    )


# ============================================================
# SUPPORT & RESISTANCE (DENGAN BADGE AREA PENTING)
# ============================================================
st.markdown(section_title("Support & Resistance (Daily)", "Multi-scale pivot · SHORT=3 · MEDIUM=7 · LONG=15"), unsafe_allow_html=True)

sr = get_support_resistance(kode_pilih, timeframe="daily")

if sr:
    st.markdown(
        f'<div style="background:rgba(99,102,241,0.08); '
        f'border:1px solid rgba(99,102,241,0.2); '
        f'border-radius:10px; padding:12px 18px; margin-bottom:16px; '
        f'font-size:12px; color:#94a3b8;">'
        f'ATR: <b style="color:#a5b4fc;">{sr["atr"]:,.0f}</b> · '
        f'Tolerance: <b style="color:#a5b4fc;">{sr["tolerance"]:,.0f}</b> · '
        f'Bars: <b style="color:#a5b4fc;">{sr["n_bars"]}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ACTIONABLE ALERT
    for z in sr["resistances"]:
        if z["lower"] <= harga <= z["upper"] and z["score"] >= 70:
            st.warning(f"⚠️ **PERINGATAN:** Harga saat ini ({harga:,.0f}) sedang berada di Zona Resistance Kuat ({z['lower']:,.0f} - {z['upper']:,.0f}). Risiko tertahan dan berbalik turun sangat tinggi. Hati-hati beli di sini!")
            
    for z in sr["supports"]:
        if z["lower"] <= harga <= z["upper"] and z["score"] >= 70:
            st.success(f"✅ **PELUANG:** Harga saat ini ({harga:,.0f}) sedang berada di Zona Support Kuat ({z['lower']:,.0f} - {z['upper']:,.0f}). Ini adalah area yang bagus untuk mencoba Entry Buy / Limit Order (selama tidak break).")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            '<div style="font-size:11px; color:#64748b; font-weight:700; '
            'letter-spacing:0.08em; text-transform:uppercase; '
            'margin-bottom:12px;">🔴 RESISTANCE</div>',
            unsafe_allow_html=True
        )
        if sr["resistances"]:
            for z in sorted(sr["resistances"], key=lambda x: abs(x["distance_pct"])):
                score = z["score"]
                strength = z["strength"]
                n_touch = z["n_touches"]
                dist = z["distance_pct"]
                
                # --- LOGIKA BADGE AREA PENTING ---
                is_elite = z.get("is_elite", False)
                
                if is_elite:
                    color = "#f43f5e"
                    bg_meter = "rgba(244,63,94,0.4)"
                    badge_text = "🚨 AREA PENTING"
                else:
                    color = "#f43f5e" if score >= 80 else ("#f59e0b" if score >= 50 else "#94a3b8")
                    bg_meter = "rgba(244,63,94,0.2)" if score >= 80 else "rgba(245,158,11,0.2)" if score >= 50 else "rgba(148,163,184,0.2)"
                    badge_text = strength
                # ---------------------------
                
                st.markdown(
                    f'<div style="background:#0f172a; border:1px solid #1e293b; border-radius:10px; padding:14px 18px; margin-bottom:10px; {"border:1px solid #f43f5e;" if is_elite else ""}">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
                    f'<span style="color:#e6ebf5; font-weight:700; font-size:15px;">{z["lower"]:,.0f} – {z["upper"]:,.0f}</span>'
                    f'<span style="font-size:11px; font-weight:800; color:{color};">{badge_text}</span>'
                    f'</div>'
                    f'<div style="width:100%; height:6px; background:{bg_meter}; border-radius:3px; margin-bottom:8px; overflow:hidden;">'
                    f'<div style="width:{score}%; height:100%; background:{color}; border-radius:3px;"></div>'
                    f'</div>'
                    f'<div style="display:flex; justify-content:space-between; font-size:11px; color:#7d8ba3;">'
                    f'<span>Skor: <b style="color:#cbd5e1;">{score}</b> / 100</span>'
                    f'<span>{n_touch}x Touch</span>'
                    f'<span>Jarak: <b style="color:{color};">{dist:+.2f}%</b></span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div style="color:#475569; font-size:13px; padding:8px;">Tidak ada resistance terdeteksi</div>', unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<div style="font-size:11px; color:#64748b; font-weight:700; '
            'letter-spacing:0.08em; text-transform:uppercase; '
            'margin-bottom:12px;">🟢 SUPPORT</div>',
            unsafe_allow_html=True
        )
        if sr["supports"]:
            for z in sorted(sr["supports"], key=lambda x: abs(x["distance_pct"])):
                score = z["score"]
                strength = z["strength"]
                n_touch = z["n_touches"]
                dist = z["distance_pct"]
                
                color = "#10b981" if score >= 80 else ("#f59e0b" if score >= 50 else "#94a3b8")
                bg_meter = "rgba(16,185,129,0.2)" if score >= 80 else "rgba(245,158,11,0.2)" if score >= 50 else "rgba(148,163,184,0.2)"
                badge_icon = "🛡️" if score >= 80 else ("⚡" if score >= 50 else "")
                
                st.markdown(
                    f'<div style="background:#0f172a; border:1px solid #1e293b; border-radius:10px; padding:14px 18px; margin-bottom:10px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
                    f'<span style="color:#e6ebf5; font-weight:700; font-size:15px;">{z["lower"]:,.0f} – {z["upper"]:,.0f}</span>'
                    f'<span style="font-size:11px; font-weight:800; color:{color};">{badge_icon} {strength}</span>'
                    f'</div>'
                    f'<div style="width:100%; height:6px; background:{bg_meter}; border-radius:3px; margin-bottom:8px; overflow:hidden;">'
                    f'<div style="width:{score}%; height:100%; background:{color}; border-radius:3px;"></div>'
                    f'</div>'
                    f'<div style="display:flex; justify-content:space-between; font-size:11px; color:#7d8ba3;">'
                    f'<span>Skor: <b style="color:#cbd5e1;">{score}</b> / 100</span>'
                    f'<span>{n_touch}x Touch</span>'
                    f'<span>Jarak: <b style="color:{color};">{dist:+.2f}%</b></span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div style="color:#475569; font-size:13px; padding:8px;">Tidak ada support terdeteksi</div>', unsafe_allow_html=True)
else:
    st.info("Data OHLCV tidak cukup untuk analisa S/R.")


# ============================================================
# FIBONACCI SNIPER SIGNAL (WR 95%)
# ============================================================
st.markdown(section_title("Fibo Sniper Signal (Daily)", "Hanya 0.618, 0.786, 0.850 (Win Rate 90%+)"), unsafe_allow_html=True)

recent_df = df.tail(150)
swing_high = float(recent_df["High"].max())
swing_low = float(recent_df["Low"].min())
diff = swing_high - swing_low
low_idx = recent_df["Low"].idxmin()
high_idx = recent_df["High"].idxmax()
is_uptrend = low_idx < high_idx

rsi_val = ind['rsi14'] if ind else 50
vol_ma = df['Volume'].rolling(20).mean().iloc[-1]
vol_ratio = df['Volume'].iloc[-1] / vol_ma if vol_ma > 0 else 1

if is_uptrend:
    fib_850 = swing_high - diff * 0.850
    fib_786 = swing_high - diff * 0.786
    dist_850 = abs(harga - fib_850) / fib_850 * 100
    dist_786 = abs(harga - fib_786) / fib_786 * 100
    
    # Cek Sinyal BUY (Uptrend + Fib 0.786/0.850 + RSI < 45)
    if (dist_850 < 2 or dist_786 < 2) and rsi_val < 45:
        st.markdown(
            f'<div style="background:rgba(16,185,129,0.15); border:2px solid #10b981; border-radius:16px; padding:24px; margin-bottom:16px;">'
            f'<div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">'
            f'<div style="font-size:32px;">✅</div>'
            f'<div style="font-size:20px; font-weight:900; color:#10b981;">SINYAL BUY (WR 90%+)</div>'
            f'</div>'
            f'<div style="font-size:14px; color:#cbd5e1; font-weight:700; margin-bottom:6px;">Harga menyentuh Fib 0.850/0.786. RSI Oversold ({rsi_val:.1f}). Volume {vol_ratio:.1f}x.</div>'
            f'<div style="font-size:12px; color:#94a3b8;">Setup Uptrend Pullback. Ini adalah area beli terbaik.</div>'
            f'</div>', unsafe_allow_html=True
        )
    elif dist_850 < 3 or dist_786 < 3:
        st.markdown(
            f'<div style="background:rgba(245,158,11,0.15); border:2px solid #f59e0b; border-radius:16px; padding:24px; margin-bottom:16px;">'
            f'<div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">'
            f'<div style="font-size:32px;">⏳</div>'
            f'<div style="font-size:20px; font-weight:900; color:#f59e0b;">PANTAU (WATCH)</div>'
            f'</div>'
            f'<div style="font-size:14px; color:#cbd5e1; font-weight:700; margin-bottom:6px;">Harga mendekati Fib 0.850/0.786. Tunggu RSI turun di bawah 45.</div>'
            f'</div>', unsafe_allow_html=True
        )
else:
    fib_850 = swing_low + diff * 0.850
    fib_786 = swing_low + diff * 0.786
    dist_850 = abs(harga - fib_850) / fib_850 * 100
    dist_786 = abs(harga - fib_786) / fib_786 * 100
    
    # Cek Sinyal SELL (Downtrend + Fib 0.786/0.850 + RSI < 45)
    if (dist_850 < 2 or dist_786 < 2) and rsi_val < 45:
        st.markdown(
            f'<div style="background:rgba(244,63,94,0.15); border:2px solid #f43f5e; border-radius:16px; padding:24px; margin-bottom:16px;">'
            f'<div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">'
            f'<div style="font-size:32px;">🚨</div>'
            f'<div style="font-size:20px; font-weight:900; color:#f43f5e;">SINYAL SELL (WR 95%)</div>'
            f'</div>'
            f'<div style="font-size:14px; color:#cbd5e1; font-weight:700; margin-bottom:6px;">Harga menyentuh Fib 0.850/0.786 (Resistance). RSI < 45. Volume {vol_ratio:.1f}x.</div>'
            f'<div style="font-size:12px; color:#94a3b8;">Jangan beli / Segera jual. Harga hampir pasti ditolak turun.</div>'
            f'</div>', unsafe_allow_html=True
        )
    elif dist_850 < 3 or dist_786 < 3:
        st.markdown(
            f'<div style="background:rgba(245,158,11,0.15); border:2px solid #f59e0b; border-radius:16px; padding:24px; margin-bottom:16px;">'
            f'<div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">'
            f'<div style="font-size:32px;">⏳</div>'
            f'<div style="font-size:20px; font-weight:900; color:#f59e0b;">PANTAU (WATCH)</div>'
            f'</div>'
            f'<div style="font-size:14px; color:#cbd5e1; font-weight:700; margin-bottom:6px;">Harga mendekati Fib 0.850/0.786 (Resistance).</div>'
            f'</div>', unsafe_allow_html=True
        )

# Tampilkan Tabel Level Fibo
st.markdown(
    f'<div style="background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.2); '
    f'border-radius:10px; padding:12px 18px; margin-bottom:16px; font-size:12px; color:#94a3b8;">'
    f'Swing High: <b style="color:#a5b4fc;">{swing_high:,.0f}</b> · '
    f'Swing Low: <b style="color:#a5b4fc;">{swing_low:,.0f}</b> · '
    f'Tren: <b style="color:{"#10b981" if is_uptrend else "#f43f5e"};">{"UPTREND (Support)" if is_uptrend else "DOWNTREND (Resistance)"}</b>'
    f'</div>',
    unsafe_allow_html=True
)

fibo_levels = [
    ("0.618", swing_high - diff * 0.618) if is_uptrend else ("0.618", swing_low + diff * 0.618),
    ("0.786", swing_high - diff * 0.786) if is_uptrend else ("0.786", swing_low + diff * 0.786),
    ("0.850", swing_high - diff * 0.850) if is_uptrend else ("0.850", swing_low + diff * 0.850),
]

for label, level in fibo_levels:
    dist_pct = (level / harga - 1) * 100
    if is_uptrend:
        color = "#10b981" if dist_pct < 2 else "#94a3b8"
        bg = "rgba(16,185,129,0.1)" if dist_pct < 2 else "rgba(148,163,184,0.1)"
        status = "SUPPORT KUAT" if dist_pct < 2 else "SUPPORT"
    else:
        color = "#f43f5e" if dist_pct > -2 else "#94a3b8"
        bg = "rgba(244,63,94,0.1)" if dist_pct > -2 else "rgba(148,163,184,0.1)"
        status = "RESISTANCE KUAT" if dist_pct > -2 else "RESISTANCE"

    st.markdown(
        f'<div style="background:{bg}; border:1px solid {color}40; border-left:4px solid {color}; '
        f'border-radius:8px; padding:12px 16px; margin-bottom:10px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
        f'<span style="font-size:12px; color:#94a3b8; font-weight:700;">Fib {label}</span>'
        f'<span style="font-size:10px; color:{color}; font-weight:800;">{status}</span>'
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:6px;">'
        f'<span style="font-size:18px; font-weight:800; color:#ffffff;">{level:,.0f}</span>'
        f'<span style="font-size:12px; font-weight:700; color:{color};">({dist_pct:+.2f}%)</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )


# ============================================================
# RISK / REWARD — LONG ONLY
# ============================================================
rr_multi = hitung_rr_skenario(kode_pilih)

STRATEGI_INFO = {
    "BUY at Support": {
        "warna": "#10b981",
        "kapan": "Harga turun masuk zona support & ada candle penolakan "
                 "(lower wick panjang / bullish engulfing / close kembali "
                 "di atas batas atas zona).",
        "cara_entry": "Limit buy di zona. 50% di tengah zona, "
                      "50% setelah candle konfirmasi muncul.",
        "cara_konfirmasi": "Tidak perlu — limit order sudah menunggu di zona.",
        "invalidasi": "Setup batal kalau candle close tembus ke bawah zona.",
    },
    "BREAKOUT BUY": {
        "warna": "#06b6d4",
        "kapan": "Harga menembus ke atas zona resistance dengan tenaga "
                 "(close di atas batas atas + volume naik).",
        "cara_entry": "Buy stop di atas resistance. Order baru aktif "
                      "begitu harga menembus trigger.",
        "cara_konfirmasi": "Tunggu candle daily CLOSE di atas batas atas "
                           "zona resistance. Jangan entry kalau baru wick "
                           "yang tembus.",
        "invalidasi": "Setup batal kalau setelah breakout harga balik "
                      "masuk zona (false break).",
    },
}

if rr_multi and rr_multi.get("scenarios"):
    st.markdown(
        section_title(
            "Risk/Reward — Skenario LONG (Daily)",
            "Buy Support · Breakout Buy · RR net setelah fee · "
            "IDX tidak bisa short"
        ),
        unsafe_allow_html=True,
    )

    n_lolos = rr_multi.get("n_lolos", 0)
    n_gugur = rr_multi.get("n_gugur", 0)
    info_color = "#10b981" if n_lolos > 0 else "#f59e0b"

    st.markdown(
        f'<div style="background:rgba(99,102,241,0.08); '
        f'border:1px solid rgba(99,102,241,0.2); '
        f'border-radius:10px; padding:12px 18px; margin-bottom:20px; '
        f'font-size:12px; color:#94a3b8;">'
        f'Harga: <b style="color:#a5b4fc;">{rr_multi["current_price"]:,.0f}</b> · '
        f'ATR: <b style="color:#a5b4fc;">{rr_multi["atr"]:,.0f}</b> · '
        f'Lolos filter: <b style="color:{info_color};">{n_lolos}</b> · '
        f'Gugur: <b style="color:#94a3b8;">{n_gugur}</b>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for s in rr_multi["scenarios"]:
        tp1_disp = s.get("tp1") or 0
        tp2_disp = s.get("tp2") or 0
        entry_disp = s.get("entry") or 0
        sl_disp = s.get("sl") or 0
        rr_tp1 = s.get("rr_tp1") or 0
        rr_tp2 = s.get("rr_tp2") or 0

        info = STRATEGI_INFO.get(s["tipe"], {})
        lolos = s.get("lolos", False)
        accent = info.get("warna", "#6366f1") if lolos else "#475569"
        op = "1.0" if lolos else "0.55"

        rr_col = "#10b981" if rr_tp1 >= 2 else (
                 "#f59e0b" if rr_tp1 >= 1.5 else "#f43f5e")

        if lolos:
            status_badge = (
                '<span style="font-size:10px; color:#10b981; font-weight:700; '
                'background:rgba(16,185,129,0.15); padding:3px 10px; '
                'border-radius:6px; margin-left:8px;">✓ LOLOS</span>'
            )
        else:
            status_badge = (
                '<span style="font-size:10px; color:#94a3b8; font-weight:700; '
                'background:rgba(148,163,184,0.15); padding:3px 10px; '
                'border-radius:6px; margin-left:8px;">✕ GUGUR</span>'
            )

        order_badge = (
            '<span style="font-size:10px; color:#f59e0b; font-weight:700; '
            'background:rgba(245,158,11,0.12); padding:3px 8px; '
            'border-radius:6px; margin-left:8px;">STOP ORDER</span>'
            if s.get("confirm_needed") else
            '<span style="font-size:10px; color:#10b981; font-weight:700; '
            'background:rgba(16,185,129,0.12); padding:3px 8px; '
            'border-radius:6px; margin-left:8px;">LIMIT ORDER</span>'
        )

        tp2_html = ""
        if s.get("tp2"):
            tp2_html = (
                f'<span><span style="color:#64748b;">TP2</span> '
                f'<b style="color:#cbd5e1;">{tp2_disp:,.0f}</b> '
                f'<span style="color:{rr_col};">(RR {rr_tp2:.2f})</span></span>'
            )

        alasan_html = ""
        if not lolos and s.get("alasan_gugur"):
            alasan_html = (
                f'<div style="background:rgba(244,63,94,0.08); '
                f'border-left:3px solid #f43f5e; '
                f'border-radius:8px; padding:10px 14px; margin-bottom:12px; '
                f'font-size:12px; color:#fda4af;">'
                f'<b>✕ Alasan gugur:</b> {s["alasan_gugur"]}'
                f'</div>'
            )

        st.markdown(
            f'<div style="background:#0f172a; border:1px solid #1e293b; '
            f'border-left:4px solid {accent}; border-radius:12px; '
            f'padding:20px 24px; margin-bottom:14px; opacity:{op};">'

            f'<div style="display:flex; justify-content:space-between; '
            f'align-items:center; margin-bottom:14px;">'
            f'<div>'
            f'<span style="font-size:15px; font-weight:800; color:#ffffff;">'
            f'{s["tipe"]}</span>'
            f'<span style="font-size:10px; color:{accent}; font-weight:700; '
            f'background:rgba({_rgb(accent) if lolos else "148,163,184"},0.12); '
            f'padding:3px 8px; border-radius:6px; margin-left:8px;">LONG</span>'
            f'{order_badge}'
            f'{status_badge}'
            f'</div>'
            f'<div style="font-size:20px; font-weight:800; color:{rr_col}; '
            f'letter-spacing:-0.02em;">1 : {rr_tp1:.2f}</div>'
            f'</div>'

            f'{alasan_html}'

            f'<div style="background:rgba(99,102,241,0.06); '
            f'border-radius:8px; padding:12px 16px; margin-bottom:12px; '
            f'font-size:12px; color:#cbd5e1; line-height:1.6;">'
            f'<div style="color:#a5b4fc; font-weight:700; '
            f'font-size:10px; letter-spacing:0.08em; '
            f'text-transform:uppercase; margin-bottom:6px;">📋 Strategi</div>'
            f'<div style="margin-bottom:4px;">'
            f'<b style="color:#e6ebf5;">Kapan:</b> {info.get("kapan","")}'
            f'</div>'
            f'<div><b style="color:#e6ebf5;">Cara entry:</b> '
            f'{info.get("cara_entry","")}</div>'
            f'</div>'

            f'<div style="background:rgba(245,158,11,0.06); '
            f'border-left:3px solid #f59e0b; '
            f'border-radius:8px; padding:12px 16px; margin-bottom:12px; '
            f'font-size:12px; color:#cbd5e1; line-height:1.6;">'
            f'<div style="color:#f59e0b; font-weight:700; '
            f'font-size:10px; letter-spacing:0.08em; '
            f'text-transform:uppercase; margin-bottom:6px;">'
            f'✅ Cara Konfirmasi</div>'
            f'{info.get("cara_konfirmasi","")}'
            f'</div>'

            f'<div style="display:grid; grid-template-columns:'
            f'repeat(3, 1fr); gap:12px; font-size:12px; '
            f'margin-bottom:12px;">'
            f'<div><span style="color:#64748b;">Entry</span><br>'
            f'<b style="color:#ffffff; font-size:15px;">'
            f'{entry_disp:,.0f}</b></div>'
            f'<div><span style="color:#64748b;">Stop Loss</span><br>'
            f'<b style="color:#f43f5e; font-size:15px;">'
            f'{sl_disp:,.0f}</b></div>'
            f'<div><span style="color:#64748b;">TP1</span><br>'
            f'<b style="color:#10b981; font-size:15px;">'
            f'{tp1_disp:,.0f}</b></div>'
            f'</div>'

            f'<div style="padding-top:12px; border-top:1px solid #1e293b; '
            f'font-size:11px; color:#7d8ba3; '
            f'display:flex; gap:18px; flex-wrap:wrap;">'
            f'<span><span style="color:#64748b;">Zona entry</span> '
            f'<b style="color:#cbd5e1;">'
            f'{s["zona_entry"][0]:,.0f}–{s["zona_entry"][1]:,.0f}</b></span>'
            f'<span><span style="color:#64748b;">Risk</span> '
            f'<b style="color:#cbd5e1;">{s.get("risk_pct", 0):.2f}%</b></span>'
            f'{tp2_html}'
            f'<span><span style="color:#64748b;">Jarak entry</span> '
            f'<b style="color:#cbd5e1;">{s.get("jarak_entry_pct", 0):+.2f}%</b></span>'
            f'</div>'

            f'<div style="margin-top:10px; font-size:11px; color:#7d8ba3;">'
            f'<span style="color:#f43f5e; font-weight:700;">✕ Batal kalau:</span> '
            f'{info.get("invalidasi","")}'
            f'</div>'

            f'</div>',
            unsafe_allow_html=True,
        )

else:
    st.markdown(section_title("Risk/Reward — Skenario LONG (Daily)"),
                unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#475569; font-size:13px; padding:8px;">'
        'Data S/R tidak tersedia untuk saham ini.</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# SINYAL TRADING
# ============================================================
sig = hitung_sinyal_trading(kode_pilih)

if sig:
    st.markdown(section_title("Sinyal Trading (Daily)"), unsafe_allow_html=True)
    sig_color = "#10b981" if sig['sinyal'] == 'BUY' else (
                "#f43f5e" if sig['sinyal'] == 'SELL' else "#f59e0b")
    sig_icon = "↗" if sig['sinyal'] == 'BUY' else (
               "↘" if sig['sinyal'] == 'SELL' else "—")

    st.markdown(
        '<div style="background:#0f172a; border:1px solid #1e293b; '
        f'border-left:4px solid {sig_color}; border-radius:12px; '
        'padding:22px 26px;">'
        '<div style="display:flex; align-items:center; gap:16px; '
        'margin-bottom:14px;">'
        f'<div style="font-size:32px; color:{sig_color}; font-weight:700;">'
        f'{sig_icon}</div>'
        '<div>'
        f'<div style="font-size:22px; font-weight:800; color:{sig_color};">'
        f'{sig["sinyal"]}</div>'
        f'<div style="font-size:12px; color:#94a3b8; margin-top:2px;">'
        f'Confidence {sig["confidence"]}%</div>'
        '</div></div>'
        f'<div style="font-size:13px; color:#94a3b8; line-height:1.5;">'
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
        color = "#10b981" if trend == "BULLISH" else (
                "#f43f5e" if trend == "BEARISH" else "#f59e0b")
        with col:
            st.markdown(
                '<div style="background:#0f172a; border:1px solid #1e293b; '
                'border-radius:12px; padding:16px; text-align:center; '
                'margin-top:12px;">'
                f'<div style="font-size:10px; color:#64748b; '
                f'letter-spacing:0.08em; font-weight:600; '
                f'text-transform:uppercase;">{label}</div>'
                f'<div style="font-size:15px; font-weight:800; color:{color}; '
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
        color = "#10b981"
    elif tipe == "DISTRIBUTION":
        color = "#f43f5e"
    else:
        color = "#f59e0b"
    cmf = akum.get("cmf", 0)
    vol_trend = akum.get("vol_trend", 1)
    price_chg = akum.get("price_chg_20d", 0)

    st.markdown(
        '<div style="background:#0f172a; border:1px solid #1e293b; '
        f'border-left:4px solid {color}; border-radius:12px; '
        'padding:20px 22px;">'
        '<div style="display:flex; justify-content:space-between; '
        'align-items:center; margin-bottom:14px;">'
        '<div>'
        f'<div style="font-size:14px; font-weight:700; color:{color}; '
        f'margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:12px; color:#94a3b8;">'
        f'CMF: <b style="color:#e6ebf5;">{cmf:+.3f}</b> · '
        f'Vol trend: <b style="color:#e6ebf5;">{vol_trend:.2f}x</b>'
        f'</div></div>'
        f'<div style="font-size:30px; font-weight:800; color:{color}; '
        f'letter-spacing:-0.03em; line-height:1;">'
        f'{score:.1f}'
        '<span style="font-size:13px; color:#64748b; font-weight:600;">/10</span>'
        '</div></div>'
        '<div style="display:flex; gap:8px;">'
        '<div style="flex:1; background:#0a0f1e; border-radius:8px; '
        'padding:10px 14px; border:1px solid #1a2338;">'
        '<div style="font-size:10px; color:#7d8ba3; font-weight:600; '
        'text-transform:uppercase; letter-spacing:0.06em; '
        'margin-bottom:3px;">Chaikin MF</div>'
        f'<div style="font-size:15px; font-weight:700; color:#e6ebf5;">'
        f'{cmf:+.3f}</div></div>'
        '<div style="flex:1; background:#0a0f1e; border-radius:8px; '
        'padding:10px 14px; border:1px solid #1a2338;">'
        '<div style="font-size:10px; color:#7d8ba3; font-weight:600; '
        'text-transform:uppercase; letter-spacing:0.06em; '
        'margin-bottom:3px;">Perubahan 20H</div>'
        f'<div style="font-size:15px; font-weight:700; color:#e6ebf5;">'
        f'{price_chg:+.1f}%</div></div>'
        '</div></div>',
        unsafe_allow_html=True
    )