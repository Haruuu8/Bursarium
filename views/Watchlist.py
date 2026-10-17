import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.info("Buka tab baru → http://localhost:8501")
    st.stop()

# Halaman WATCHLIST — 6 tab, baca dari JSON (fast).

import os, sys, json
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import (
    load_theme, page_header, section_title, empty_state,
)

st.set_page_config(page_title="Watchlist", layout="wide")
load_theme()

# ============================================================
# GUARD LOGIN
# ============================================================
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()


WATCHLIST_FILE = "data_watchlist.json"
OUTPUT_DIR = "quant/output"
OHLCV_DIR = "data_ohlcv_idx"
FUND_DIR = "data_fundamental"
SEKTOR_CSV = "data_sektor.csv"
SETUPS_FILE = "data_setups.json"
SCANS_DIR = "data_scans"


# ============================================================
# LOAD JSON HELPERS
# ============================================================
def load_json_safe(path):
    """Baca file JSON, return None kalau tidak ada / error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_setups():
    return load_json_safe(SETUPS_FILE)


def load_scan(name):
    """Baca data_scans/{name}.json → return list items + generated."""
    d = load_json_safe(os.path.join(SCANS_DIR, f"{name}.json"))
    if not d:
        return [], "?"
    return d.get("items", []), d.get("generated", "?")


# ============================================================
# PERSISTENCE & HELPERS
# ============================================================
@st.cache_data(ttl=3600)
def load_nama():
    nama = {}
    if os.path.exists(SEKTOR_CSV):
        try:
            df = pd.read_csv(SEKTOR_CSV)
            if "kode" in df.columns and "nama" in df.columns:
                for _, r in df.iterrows():
                    k = str(r["kode"]).strip().upper()
                    n = str(r["nama"]).strip()
                    if k and n and n.lower() != "nan":
                        nama[k] = n
        except Exception:
            pass

    if os.path.exists(FUND_DIR):
        try:
            for f in os.listdir(FUND_DIR):
                if not f.endswith(".json"):
                    continue
                kode = f.replace(".json", "").upper()
                if kode in nama and nama[kode]:
                    continue
                try:
                    with open(os.path.join(FUND_DIR, f), "r",
                              encoding="utf-8") as fh:
                        d = json.load(fh)
                    n = str(d.get("nama", "")).strip()
                    if n and n.lower() != "nan":
                        nama[kode] = n
                except Exception:
                    pass
        except Exception:
            pass
    return nama


def list_kandidat_files():
    if not os.path.exists(OUTPUT_DIR):
        return []
    fs = [f for f in os.listdir(OUTPUT_DIR)
          if f.startswith("kandidat") and f.endswith(".csv")
          and "union" not in f.lower()
          and "combined" not in f.lower()]
    fs.sort(key=lambda f: os.path.getmtime(
        os.path.join(OUTPUT_DIR, f)), reverse=True)
    return fs


def list_rekap_files():
    if not os.path.exists(OUTPUT_DIR):
        return []
    fs = [f for f in os.listdir(OUTPUT_DIR)
          if f.startswith("Rekap_Trading_") and f.endswith(".xlsx")]
    fs.sort(reverse=True)
    return fs


@st.cache_data(ttl=300)
def load_csv(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_rekap_sheet(fname, sheet_name):
    path = os.path.join(OUTPUT_DIR, fname)
    if not os.path.exists(path):
        return None
    try:
        raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    except Exception:
        return None

    header_row = None
    for i in range(min(10, len(raw))):
        row = raw.iloc[i]
        vals = [str(v).strip() for v in row.values if pd.notna(v)]
        if any(v in ("Tanggal", "No", "Kode", "Metrik",
                     "Minggu Ke", "Info") for v in vals):
            header_row = i
            break

    if header_row is None:
        header_row = 0

    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    except Exception:
        return None
    return df


def fmt_num(v, dec=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        return f"{v:,.{dec}f}"
    except Exception:
        return "—"


# ============================================================
# IHSG LOADER
# ============================================================
@st.cache_data(ttl=3600)
def get_ihsg_daily(start_date_str, end_date_str):
    candidates = [
        os.path.join(OHLCV_DIR, "^JKSE.csv"),
        os.path.join(OHLCV_DIR, "JKSE.csv"),
        os.path.join(OHLCV_DIR, "IHSG.csv"),
        "data_ihsg.csv",
        os.path.join(OUTPUT_DIR, "IHSG.csv"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path)
            df.columns = [str(c).strip().title() for c in df.columns]
            close_col = None
            for c in df.columns:
                if str(c).lower() in ("close", "closeprice", "adj close"):
                    close_col = c
                    break
            if "Date" not in df.columns or close_col is None:
                continue
            out = pd.DataFrame()
            out["Date"] = pd.to_datetime(df["Date"])
            out["Close"] = pd.to_numeric(df[close_col], errors="coerce")
            out = out.dropna().sort_values("Date").reset_index(drop=True)
            out["ret"] = out["Close"].pct_change() * 100
            return out
        except Exception:
            continue
    try:
        import yfinance as yf
        df = yf.download("^JKSE", start=start_date_str,
                         end=end_date_str, progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            df.columns = [str(c).strip() for c in df.columns]
            close_col = None
            for c in df.columns:
                if str(c).lower() == "close":
                    close_col = c
                    break
            if "Date" in df.columns and close_col:
                out = pd.DataFrame()
                out["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
                out["Close"] = pd.to_numeric(df[close_col], errors="coerce")
                out = out.dropna().sort_values("Date").reset_index(drop=True)
                out["ret"] = out["Close"].pct_change() * 100
                return out
    except Exception:
        pass
    return None


# ============================================================
# CARD: HAKA PAGI
# ============================================================
def wl_row(kode, nama, harga, chg_pct, rating=0, match="-", strength=0):
    nama_disp = nama[:50] + "…" if len(nama) > 50 else nama

    if chg_pct > 0: chg_color, chg_sign = "#10b981", "+"
    elif chg_pct < 0: chg_color, chg_sign = "#f43f5e", ""
    else: chg_color, chg_sign = "#94a3b8", ""

    badges = ""
    if rating and rating > 0:
        badges += (
            '<span style="display:inline-flex; align-items:center; '
            'font-size:11px; font-weight:800; padding:4px 10px; '
            'border-radius:6px; letter-spacing:0.3px; margin-right:6px; '
            'background:rgba(99,102,241,0.15); color:#a5b4fc; '
            'border:1px solid rgba(99,102,241,0.35);">'
            f'★ {rating:.0f}</span>'
        )
    if match and match != "-":
        badges += (
            '<span style="display:inline-block; '
            'font-size:11px; font-weight:800; padding:4px 10px; '
            'border-radius:6px; letter-spacing:0.3px; margin-right:6px; '
            'background:rgba(168,85,247,0.15); color:#c4b5fd; '
            'border:1px solid rgba(168,85,247,0.35);">'
            f'{match}</span>'
        )
    if strength and strength > 0:
        badges += (
            '<span style="display:inline-block; '
            'font-size:11px; font-weight:800; padding:4px 10px; '
            'border-radius:6px; letter-spacing:0.3px; margin-right:6px; '
            'background:rgba(245,158,11,0.15); color:#fbbf24; '
            'border:1px solid rgba(245,158,11,0.35);">'
            f'S{strength}</span>'
        )

    return (
        '<div style="'
        'background: linear-gradient(135deg, #131a2a 0%, #0f1628 100%); '
        'border: 1px solid #1a2338; border-radius: 14px; '
        'padding: 18px 22px; margin-bottom: 10px; '
        'display: flex; align-items: center; gap: 20px; '
        'position: relative; overflow: hidden;">'
        '<div style="position:absolute; left:0; top:0; bottom:0; width:3px; '
        'background: linear-gradient(180deg, #06b6d4, rgba(6,182,212,0.3));"></div>'
        '<div style="flex: 1; min-width: 0; padding-left: 8px;">'
        f'<div style="font-size:17px; font-weight:800; color:#ffffff; '
        f'letter-spacing:-0.02em; line-height:1.2;">{kode}</div>'
        f'<div style="font-size:12px; color:#7d8ba3; margin-top:3px; '
        f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">'
        f'{nama_disp}</div>'
        f'<div style="margin-top:10px; display:flex; flex-wrap:wrap;">'
        f'{badges}</div>'
        '</div>'
        '<div style="text-align:right; flex-shrink:0; min-width:110px;">'
        f'<div style="font-size:22px; font-weight:800; color:#ffffff; '
        f'letter-spacing:-0.03em; line-height:1;">{harga:,.0f}</div>'
        f'<div style="font-size:13px; font-weight:700; color:{chg_color}; '
        f'margin-top:5px;">{chg_sign}{chg_pct:.2f}%</div>'
        '</div></div>'
    )


# ============================================================
# CARD: BOTTOM FISHING
# ============================================================
def bf_row(kode, nama, harga, rsi, rsi_chg, ni_g, rev_g, der, roe,
           special_flag=None):
    nama_disp = nama[:50] + "…" if len(nama) > 50 else nama

    if rsi < 20: rsi_color, rsi_bg, rsi_label = "#ff5252", "rgba(255,82,82,0.15)", "EXTREME"
    elif rsi < 30: rsi_color, rsi_bg, rsi_label = "#f43f5e", "rgba(244,63,94,0.12)", "OVERSOLD"
    elif rsi < 40: rsi_color, rsi_bg, rsi_label = "#f59e0b", "rgba(245,158,11,0.12)", "WEAK"
    else: rsi_color, rsi_bg, rsi_label = "#94a3b8", "rgba(148,163,184,0.12)", "NORMAL"

    rsi_arrow = "▲" if rsi_chg > 0 else ("▼" if rsi_chg < 0 else "—")
    rsi_arrow_color = "#10b981" if rsi_chg > 0 else ("#f43f5e" if rsi_chg < 0 else "#94a3b8")

    def growth_badge(v, label):
        if v is None or pd.isna(v):
            return (f'<span style="font-size:10px; color:#7d8ba3; '
                    f'padding:3px 8px; background:#0f172a; '
                    f'border-radius:5px; margin-right:4px;">{label} —</span>')
        color = "#10b981" if v >= 0 else "#f43f5e"
        sign = "+" if v >= 0 else ""
        rgb = "16,185,129" if v >= 0 else "244,63,94"
        return (f'<span style="font-size:10px; color:{color}; '
                f'padding:3px 8px; background:rgba({rgb},0.1); '
                f'border-radius:5px; margin-right:4px; font-weight:700;">'
                f'{label} {sign}{v:.1f}%</span>')

    der_str = f"{der:.2f}x" if der is not None and not pd.isna(der) else "—"
    der_color = ("#10b981" if (der is not None and der < 0.5) else
                 "#f59e0b" if (der is not None and der < 1.0) else
                 "#f43f5e" if der is not None else "#7d8ba3")

    roe_str = f"{roe:.1f}%" if roe is not None and not pd.isna(roe) else "—"
    roe_color = ("#10b981" if (roe is not None and roe > 15) else
                 "#f59e0b" if (roe is not None and roe > 5) else
                 "#f43f5e" if roe is not None else "#7d8ba3")

    eksp_badge = ""
    if special_flag:
        eksp_badge = (
            f'<span style="font-size:10px; padding:3px 8px; '
            f'background:rgba(99,102,241,0.15); color:#a5b4fc; '
            f'border-radius:5px; font-weight:700; margin-left:6px;">'
            f'🚀 {special_flag}</span>'
        )

    return (
        '<div style="'
        'background: linear-gradient(135deg, #131a2a 0%, #0f1628 100%); '
        'border: 1px solid #1a2338; border-radius: 14px; '
        'padding: 18px 22px; margin-bottom: 10px; '
        'position: relative; overflow: hidden;">'
        f'<div style="position:absolute; left:0; top:0; bottom:0; width:3px; '
        f'background: {rsi_color};"></div>'
        '<div style="display:flex; justify-content:space-between; align-items:flex-start; '
        'padding-left: 8px; gap: 16px;">'
        '<div style="flex: 1; min-width: 0;">'
        f'<div style="font-size:17px; font-weight:800; color:#ffffff; '
        f'letter-spacing:-0.02em; line-height:1.2;">{kode}{eksp_badge}</div>'
        f'<div style="font-size:12px; color:#7d8ba3; margin-top:3px;">{nama_disp}</div>'
        '<div style="margin-top:12px; display:flex; flex-wrap:wrap; gap:4px; align-items:center;">'
        f'<span style="font-size:11px; font-weight:800; padding:4px 10px; '
        f'border-radius:6px; background:{rsi_bg}; color:{rsi_color}; '
        f'border:1px solid {rsi_color}40;">RSI {rsi:.1f}</span>'
        f'<span style="font-size:11px; color:{rsi_color}; font-weight:700; '
        f'margin-right:8px;">{rsi_label}</span>'
        f'<span style="font-size:11px; color:{rsi_arrow_color}; '
        f'font-weight:700; margin-right:8px;">{rsi_arrow} {abs(rsi_chg):.1f}</span>'
        f'{growth_badge(ni_g, "NI")}'
        f'{growth_badge(rev_g, "Rev")}'
        '</div>'
        '<div style="margin-top:10px; display:flex; flex-wrap:wrap; gap:14px;">'
        f'<span style="font-size:11px; color:#7d8ba3;">DER <b style="color:{der_color};">{der_str}</b></span>'
        f'<span style="font-size:11px; color:#7d8ba3;">ROE <b style="color:{roe_color};">{roe_str}</b></span>'
        '</div>'
        '</div>'
        '<div style="text-align:right; flex-shrink:0;">'
        f'<div style="font-size:10px; color:#64748b; letter-spacing:0.6px; '
        f'margin-bottom:2px;">HARGA</div>'
        f'<div style="font-size:22px; font-weight:800; color:#ffffff; '
        f'letter-spacing:-0.03em; line-height:1;">{harga:,.0f}</div>'
        '</div>'
        '</div></div>'
    )


# ============================================================
# CARD: SETUP (Buy Support / Breakout)
# ============================================================
def setup_row(r, tipe="support"):
    kode = r["kode"]
    nama = r.get("_nama", kode)[:50]
    harga = r.get("harga", 0)
    entry = r.get("entry", 0)
    sl = r.get("sl", 0)
    tp1 = r.get("tp1", 0)
    tp2 = r.get("tp2")
    rr_tp1 = r.get("rr_tp1", 0)
    rr_tp2 = r.get("rr_tp2")
    risk_pct = r.get("risk_pct", 0)
    jarak = r.get("jarak_entry_pct", 0)
    zona_lo = r.get("zona_lo", 0)
    zona_hi = r.get("zona_hi", 0)
    lot = r.get("lot", 0)

    if tipe == "support":
        accent = "#10b981"
        badge = ('<span style="background:rgba(16,185,129,0.15); color:#10b981; '
                 'padding:3px 10px; border-radius:6px; font-size:10px; '
                 'font-weight:800;">🎯 LIMIT · ZONA SUPPORT</span>')
        if harga < zona_lo:
            posisi_txt = "↓ di bawah zona"
            posisi_color = "#f43f5e"
        elif harga > zona_hi:
            posisi_txt = "↑ di atas zona"
            posisi_color = "#f59e0b"
        else:
            posisi_txt = "● di dalam zona"
            posisi_color = "#10b981"
    else:
        accent = "#06b6d4"
        badge = ('<span style="background:rgba(6,182,212,0.15); color:#06b6d4; '
                 'padding:3px 10px; border-radius:6px; font-size:10px; '
                 'font-weight:800;">🚀 STOP · BREAKOUT</span>')
        if harga < entry:
            posisi_txt = f"↓ {((entry-harga)/harga*100):.1f}% di bawah trigger"
            posisi_color = "#94a3b8"
        else:
            posisi_txt = "↑ sudah melewati trigger"
            posisi_color = "#f43f5e"

    if rr_tp1 >= 3: rr_color = "#10b981"
    elif rr_tp1 >= 2: rr_color = "#34d399"
    elif rr_tp1 >= 1.5: rr_color = "#f59e0b"
    else: rr_color = "#f43f5e"

    if jarak > 0:
        jarak_color = "#f59e0b"
        jarak_icon = "↑"
    elif jarak < 0:
        jarak_color = "#10b981"
        jarak_icon = "↓"
    else:
        jarak_color = "#94a3b8"
        jarak_icon = "="

    tp2_disp = f'{tp2:,.0f}' if tp2 else "—"
    tp2_rr = f'RR {rr_tp2:.2f}' if tp2 else "—"

    return (
        f'<div style="background:linear-gradient(135deg, #131a2a, #0f1628); '
        f'border:1px solid #1a2338; border-left:4px solid {accent}; '
        f'border-radius:14px; padding:20px 24px; margin-bottom:12px;">'

        f'<div style="display:flex; justify-content:space-between; '
        f'align-items:flex-start; gap:20px; margin-bottom:16px; '
        f'flex-wrap:wrap;">'
        f'<div style="flex:1; min-width:200px;">'
        f'<div style="display:flex; align-items:baseline; gap:10px; flex-wrap:wrap;">'
        f'<span style="font-size:20px; font-weight:900; color:#ffffff; '
        f'letter-spacing:-0.02em;">{kode}</span>'
        f'{badge}'
        f'</div>'
        f'<div style="font-size:12px; color:#94a3b8; margin-top:4px;">{nama}</div>'
        f'</div>'

        f'<div style="text-align:right; min-width:140px;">'
        f'<div style="font-size:10px; color:#64748b; letter-spacing:0.8px; '
        f'font-weight:700; text-transform:uppercase;">Harga Saat Ini</div>'
        f'<div style="font-size:26px; font-weight:900; color:#ffffff; '
        f'letter-spacing:-0.03em; margin-top:2px;">'
        f'{harga:,.0f}</div>'
        f'<div style="font-size:10px; color:{posisi_color}; font-weight:700; '
        f'margin-top:2px;">{posisi_txt}</div>'
        f'</div>'
        f'</div>'

        f'<div style="background:rgba(99,102,241,0.06); '
        f'border:1px solid rgba(99,102,241,0.15); border-radius:10px; '
        f'padding:12px 18px; margin-bottom:16px; '
        f'display:flex; justify-content:space-between; align-items:center; '
        f'flex-wrap:wrap; gap:12px;">'
        f'<div style="display:flex; align-items:center; gap:14px;">'
        f'<span style="font-size:14px; font-weight:700; color:#cbd5e1;">'
        f'{harga:,.0f}</span>'
        f'<span style="font-size:16px; color:#64748b;">→</span>'
        f'<span style="font-size:16px; font-weight:800; color:#a5b4fc;">'
        f'{entry:,.0f}</span>'
        f'<span style="font-size:11px; color:{jarak_color}; font-weight:700;">'
        f'({jarak_icon} {abs(jarak):.2f}% ke entry)</span>'
        f'</div>'
        f'<span style="font-size:10px; color:#64748b; letter-spacing:0.6px; '
        f'font-weight:600;">HARGA SAAT INI → ENTRY</span>'
        f'</div>'

        f'<div style="display:grid; grid-template-columns:repeat(4, 1fr); '
        f'gap:12px; margin-bottom:14px;">'
        f'<div style="background:#0a0f1e; border:1px solid #1a2338; '
        f'border-radius:10px; padding:12px 14px;">'
        f'<div style="font-size:10px; color:#64748b; letter-spacing:0.6px; '
        f'font-weight:600;">ENTRY</div>'
        f'<div style="font-size:17px; font-weight:800; color:#ffffff; '
        f'margin-top:4px;">{entry:,.0f}</div></div>'

        f'<div style="background:#0a0f1e; border:1px solid #1a2338; '
        f'border-radius:10px; padding:12px 14px;">'
        f'<div style="font-size:10px; color:#64748b; letter-spacing:0.6px; '
        f'font-weight:600;">STOP LOSS</div>'
        f'<div style="font-size:17px; font-weight:800; color:#f43f5e; '
        f'margin-top:4px;">{sl:,.0f}</div>'
        f'<div style="font-size:10px; color:#64748b; margin-top:2px;">'
        f'-{risk_pct:.2f}%</div></div>'

        f'<div style="background:#0a0f1e; border:1px solid #1a2338; '
        f'border-radius:10px; padding:12px 14px;">'
        f'<div style="font-size:10px; color:#64748b; letter-spacing:0.6px; '
        f'font-weight:600;">TP1</div>'
        f'<div style="font-size:17px; font-weight:800; color:#10b981; '
        f'margin-top:4px;">{tp1:,.0f}</div>'
        f'<div style="font-size:10px; color:#64748b; margin-top:2px;">'
        f'RR {rr_tp1:.2f}</div></div>'

        f'<div style="background:#0a0f1e; border:1px solid #1a2338; '
        f'border-radius:10px; padding:12px 14px;">'
        f'<div style="font-size:10px; color:#64748b; letter-spacing:0.6px; '
        f'font-weight:600;">TP2</div>'
        f'<div style="font-size:17px; font-weight:800; color:#10b981; '
        f'margin-top:4px;">{tp2_disp}</div>'
        f'<div style="font-size:10px; color:#64748b; margin-top:2px;">'
        f'{tp2_rr}</div></div>'
        f'</div>'

        f'<div style="border-top:1px solid #1a2338; padding-top:12px; '
        f'display:flex; gap:24px; flex-wrap:wrap; font-size:11px; color:#94a3b8;">'
        f'<span>RR <b style="color:{rr_color}; font-size:13px;">{rr_tp1:.2f}</b></span>'
        f'<span>Risk <b style="color:#cbd5e1;">{risk_pct:.2f}%</b></span>'
        f'<span>Zona <b style="color:#cbd5e1;">{zona_lo:,.0f} – {zona_hi:,.0f}</b></span>'
        f'<span>Lot <b style="color:#cbd5e1;">{lot}</b></span>'
        f'</div>'
        f'</div>'
    )


def setup_table(items, nama_map):
    rows = []
    for r in items:
        rows.append({
            "Kode": r["kode"],
            "Nama": nama_map.get(r["kode"], r["kode"])[:30],
            "Harga": r["harga"],
            "Entry": r["entry"],
            "SL": r["sl"],
            "TP1": r["tp1"],
            "TP2": r.get("tp2"),
            "RR": r["rr_tp1"],
            "Risk %": r["risk_pct"],
            "Jarak %": r["jarak_entry_pct"],
            "Zona Lo": r["zona_lo"],
            "Zona Hi": r["zona_hi"],
            "Lot": r["lot"],
        })
    df_show = pd.DataFrame(rows)
    
    # Semua baris ditampilkan penuh
    tinggi_tabel = (len(df_show) * 35) + 40
    
    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=tinggi_tabel,
    )


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Watchlist",
                        "Haka Pagi · Bottom Fishing · Pre-Cross · Setups · Performa"),
            unsafe_allow_html=True)

nama_map = load_nama()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌅 Haka Pagi", "🎣 Bottom Fishing", "⚡ Pre-Cross",
    "🎯 Buy on Support", "🚀 Breakout Buy", "📊 Performa"
])


# ============================================================
# TAB 1: HAKA PAGI
# ============================================================
with tab1:
    st.markdown(
        '<div style="background: linear-gradient(135deg, rgba(99,102,241,0.10), '
        'rgba(6,182,212,0.05)); '
        'border: 1px solid rgba(99,102,241,0.25); border-radius: 12px; '
        'padding: 16px 20px; margin-bottom: 20px;">'
        '<div style="font-size: 13px; color: #a5b4fc; font-weight: 700; '
        'margin-bottom: 10px;">📋 ATURAN SCREENER</div>'
        '<div style="font-size: 12px; color: #cbd5e1; line-height: 1.8;">'
        '<b style="color:#e6ebf5;">Entry:</b> Open T+1 (hari bursa berikutnya '
        'setelah sinyal)<br>'
        '<b style="color:#e6ebf5;">Exit:</b> TP High-1% (kalau High naik ≥ 1%) '
        '| SL -3% (sudah termasuk fee)'
        '</div></div>',
        unsafe_allow_html=True
    )

    files = list_kandidat_files()

    if not files:
        st.markdown(empty_state("📭", "Belum ada kandidat",
                                "Jalankan screener dulu"), unsafe_allow_html=True)
    else:
        # OTOMATISASI: Ambil file terbaru, hilangkan dropdown, dan set filter secara default
        selected = files[0]
        min_str = 2
        min_rating = 0

        df = load_csv(os.path.join(OUTPUT_DIR, selected))

        if df.empty:
            st.error("File kosong.")
        else:
            if "strength" in df.columns and "rating" in df.columns:
                df = df[(df["strength"] >= min_str) &
                        (df["rating"] >= min_rating)]

            st.markdown(
                f'<div style="font-size:12px; color:#7d8ba3; '
                f'margin:8px 0 16px; font-weight:500;">'
                f'{len(df)} kandidat ditampilkan</div>',
                unsafe_allow_html=True
            )

            for idx, r in df.iterrows():
                kode = str(r["kode"]).upper()
                nama = nama_map.get(kode, kode)
                close = float(r["close"])
                rating = float(r.get("rating", 0))
                match = str(r.get("match", "-"))
                strength = int(r.get("strength", 0))
                ret1d = float(r.get("ret_1d", 0)) * 100

                st.markdown(
                    wl_row(kode, nama, close, ret1d, rating, match, strength),
                    unsafe_allow_html=True
                )


# ============================================================
# TAB 2: BOTTOM FISHING (baca JSON)
# ============================================================
with tab2:
    st.markdown(
        '<div style="background: linear-gradient(135deg, rgba(6,182,212,0.10), rgba(16,185,129,0.05)); '
        'border: 1px solid rgba(6,182,212,0.25); border-radius: 12px; '
        'padding: 16px 20px; margin-bottom: 20px;">'
        '<div style="font-size: 13px; color: #06b6d4; font-weight: 700; '
        'margin-bottom: 8px;">🎣 BOTTOM FISHING — SAHAM SEHAT</div>'
        '<div style="font-size: 12px; color: #94a3b8; line-height: 1.6;">'
        '✓ Q1 dan Q2 ada, se-tahun, Q2 standalone ≥ 0<br>'
        '✓ Laba tidak turun drastis (&gt; 50%) — kecuali premium ekspansi<br>'
        '✓ Revenue YoY tidak turun &gt; 30%<br>'
        '✓ DER &lt; 2.0x · ROE &gt; 10%<br>'
        '✓ Saham masih aktif bergerak'
        '</div></div>',
        unsafe_allow_html=True
    )

    items_bf, gen_bf = load_scan("bottom")

    if not items_bf:
        st.warning("Data Bottom Fishing belum tersedia. Silakan hubungi admin.")
    else:
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            st.markdown(
                f'<div style="font-size:12px; color:#7d8ba3; padding:6px 0;">'
                f'<b style="color:#06b6d4;">{len(items_bf)}</b> saham · '
                f'generated {gen_bf}</div>',
                unsafe_allow_html=True
            )
        with c2:
            max_rsi = st.slider("Max RSI", 10, 60, 40, 5,
                                 key="bf_rsi",
                                 label_visibility="collapsed")
        with c3:
            if st.button("🔄 Reload", key="reload_bf",
                          use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        filtered = [x for x in items_bf if x["rsi"] <= max_rsi]
        st.caption(f"{len(filtered)} saham RSI ≤ {max_rsi}")

        if not filtered:
            st.info("Tidak ada saham lolos filter RSI.")
        else:
            for r in filtered:
                st.markdown(
                    bf_row(
                        r["kode"], nama_map.get(r["kode"], r["kode"]),
                        r["harga"], r["rsi"], r["rsi_change"],
                        r.get("ni_growth"), r.get("rev_growth"),
                        r.get("der"), r.get("roe"),
                        special_flag=r.get("special_flag"),
                    ),
                    unsafe_allow_html=True
                )


# ============================================================
# TAB 3: PRE-CROSS (baca JSON)
# ============================================================
with tab3:
    st.markdown(
        '<div style="background: linear-gradient(135deg, rgba(16,185,129,0.12), '
        'rgba(6,182,212,0.05)); border: 1px solid rgba(16,185,129,0.30); '
        'border-radius: 12px; padding: 18px 22px; margin-bottom: 20px;">'
        '<div style="font-size: 14px; color: #10b981; font-weight: 800; '
        'letter-spacing:0.5px; margin-bottom:10px;">⚡ PRE-GOLDEN-CROSS</div>'
        '<div style="font-size: 12px; color: #cbd5e1; line-height: 1.8;">'
        'Setup skor ≥ <b>85</b> · Winrate backtest 91.2% · Gap EMA20-EMA50 ≤ 4%'
        '</div></div>',
        unsafe_allow_html=True
    )

    items_pc, gen_pc = load_scan("precross")

    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(
            f'<div style="font-size:12px; color:#7d8ba3; padding:6px 0;">'
            f'<b style="color:#10b981;">{len(items_pc)}</b> setup skor ≥85 · '
            f'generated {gen_pc}</div>',
            unsafe_allow_html=True
        )
    with c2:
        if st.button("🔄 Reload", key="reload_pc",
                      use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if gen_pc == "?":
        st.warning("Data scan belum tersedia. Silakan hubungi admin untuk update data terbaru.")
    elif not items_pc:
        st.markdown(
            '<div style="background:linear-gradient(135deg, #131a2a, #0f1628); '
            'border:1px dashed #334155; border-radius:14px; '
            'padding:40px 32px; text-align:center;">'
            '<div style="font-size:15px; font-weight:700; color:#cbd5e1; '
            'margin-bottom:8px;">Tidak ada setup skor ≥ 85 hari ini</div>'
            '<div style="font-size:12px; color:#7d8ba3; max-width:480px; '
            'margin:0 auto;">Setup presisi tinggi jarang muncul. '
            'Cek kandidat emerging di bawah.</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        for i, r in enumerate(items_pc):
            kode = r["kode"]
            nama = nama_map.get(kode, kode)[:55]
            skor = r["skor"]
            gap = r["gap_pct"]
            konv = r["konv_pct"]
            harga = r["harga"]
            ema20 = r["ema20"]
            ema50 = r["ema50"]

            st.markdown(
                f'<div style="background:linear-gradient(135deg, #131a2a, #0f1628); '
                f'border:1px solid #1a2338; border-left:4px solid #10b981; '
                f'border-radius:14px; padding:18px 22px; margin-bottom:12px;">'
                f'<div style="display:flex; justify-content:space-between; '
                f'align-items:center; gap:16px;">'
                f'<div>'
                f'<div style="display:flex; align-items:baseline; gap:12px;">'
                f'<span style="font-size:18px; font-weight:800; color:#10b981;">#{i+1}</span>'
                f'<span style="font-size:18px; font-weight:800; color:#ffffff;">{kode}</span>'
                f'<span style="background:rgba(16,185,129,0.15); color:#10b981; '
                f'padding:3px 10px; border-radius:6px; font-size:10px; '
                f'font-weight:800;">🔥 SKOR {skor:.0f}</span>'
                f'</div>'
                f'<div style="font-size:12px; color:#7d8ba3; margin-top:4px;">{nama}</div>'
                f'<div style="margin-top:10px; display:flex; gap:16px; flex-wrap:wrap; '
                f'font-size:11px; color:#94a3b8;">'
                f'<span>Harga <b style="color:#fff;">{harga:,.0f}</b></span>'
                f'<span>EMA20 <b style="color:#06b6d4;">{ema20:,.0f}</b></span>'
                f'<span>EMA50 <b style="color:#f59e0b;">{ema50:,.0f}</b></span>'
                f'<span>Gap <b style="color:#fff;">{gap:.2f}%</b></span>'
                f'<span>Konv <b style="color:#10b981;">+{konv:.0f}%</b></span>'
                f'</div></div></div></div>',
                unsafe_allow_html=True
            )

    st.markdown(
        '<div style="height:1px; background:linear-gradient(90deg, '
        'transparent, #334155, transparent); margin:32px 0 20px;"></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="background: linear-gradient(135deg, rgba(245,158,11,0.10), '
        'rgba(99,102,241,0.05)); border: 1px solid rgba(245,158,11,0.30); '
        'border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">'
        '<div style="font-size: 13px; color: #f59e0b; font-weight: 800; '
        'margin-bottom: 8px;">🌱 EMERGING — MENUJU SKOR 85+</div>'
        '<div style="font-size: 12px; color: #cbd5e1; line-height: 1.7;">'
        'Saham skor 65–84 yang sedang konvergen dan EMA20 naik.'
        '</div></div>',
        unsafe_allow_html=True
    )

    items_emg, gen_emg = load_scan("emerging")

    if gen_emg == "?":
        st.warning("Data scan emerging belum tersedia. Silakan hubungi admin untuk update data terbaru.")
    elif not items_emg:
        st.info("Belum ada kandidat emerging hari ini.")
    else:
        st.markdown(
            f'<div style="font-size:12px; color:#7d8ba3; margin:4px 0 16px;">'
            f'<b style="color:#f59e0b;">{len(items_emg)}</b> kandidat · '
            f'generated {gen_emg}</div>',
            unsafe_allow_html=True
        )

        for i, r in enumerate(items_emg):
            kode = r["kode"]
            nama = nama_map.get(kode, kode)[:55]
            skor = r["skor"]
            gap = r["gap_pct"]
            konv = r["konv_pct"]
            harga = r["harga"]

            if skor >= 80: color = "#10b981"
            elif skor >= 75: color = "#a5b4fc"
            elif skor >= 70: color = "#f59e0b"
            else: color = "#94a3b8"

            gap_to = 85 - skor

            st.markdown(
                f'<div style="background:linear-gradient(135deg, #131a2a, #0f1628); '
                f'border:1px solid #1a2338; border-left:3px solid {color}; '
                f'border-radius:14px; padding:14px 20px; margin-bottom:10px;">'
                f'<div style="display:flex; justify-content:space-between; '
                f'align-items:center; gap:16px;">'
                f'<div>'
                f'<div style="display:flex; align-items:baseline; gap:10px;">'
                f'<span style="font-size:14px; font-weight:800; color:#94a3b8;">#{i+1}</span>'
                f'<span style="font-size:16px; font-weight:800; color:#ffffff;">{kode}</span>'
                f'<span style="background:rgba(148,163,184,0.15); color:{color}; '
                f'padding:3px 10px; border-radius:6px; font-size:10px; '
                f'font-weight:800;">SKOR {skor:.0f}</span>'
                f'</div>'
                f'<div style="font-size:11px; color:#7d8ba3; margin-top:3px;">{nama}</div>'
                f'<div style="margin-top:8px; display:flex; gap:14px; flex-wrap:wrap; '
                f'font-size:11px; color:#94a3b8;">'
                f'<span>Harga <b style="color:#fff;">{harga:,.0f}</b></span>'
                f'<span>Gap <b style="color:#fff;">{gap:.2f}%</b></span>'
                f'<span>Konv <b style="color:#10b981;">+{konv:.0f}%</b></span>'
                f'</div></div>'
                f'<div style="text-align:right;">'
                f'<div style="font-size:24px; font-weight:800; color:{color};">{skor:.0f}</div>'
                f'<div style="font-size:10px; color:#f59e0b;">−{gap_to:.0f} ke 85</div>'
                f'</div></div></div>',
                unsafe_allow_html=True
            )


# ============================================================
# TAB 4: BUY ON SUPPORT (baca JSON, Card default)
# ============================================================
with tab4:
    st.markdown(
        '<div style="background: linear-gradient(135deg, rgba(16,185,129,0.10), '
        'rgba(6,182,212,0.05)); border: 1px solid rgba(16,185,129,0.30); '
        'border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">'
        '<div style="font-size: 13px; color: #10b981; font-weight: 800; '
        'margin-bottom: 8px;">🎯 BUY ON SUPPORT — SETUP LIMIT ORDER</div>'
        '<div style="font-size: 12px; color: #cbd5e1; line-height: 1.7;">'
        'Entry limit di zona support · RR min 1.5 · '
        'jarak harga→entry ≤ 5%'
        '</div></div>',
        unsafe_allow_html=True
    )

    setups = load_setups()
    if not setups:
        st.warning("Data setup belum tersedia. Silakan hubungi admin.")
    else:
        items = setups.get("buy_support", [])
        generated = setups.get("generated", "?")

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            st.markdown(
                f'<div style="font-size:12px; color:#7d8ba3; padding:6px 0;">'
                f'<b style="color:#10b981;">{len(items)}</b> saham · '
                f'generated {generated}</div>',
                unsafe_allow_html=True
            )
        with c2:
            min_rr = st.slider("Min RR", 1.5, 5.0, 2.0, 0.1,
                                key="rr_min_support",
                                label_visibility="collapsed")
        with c3:
            view_mode = st.selectbox(
                "View", ["🎴 Card", "📊 Table"],
                key="view_support",
                label_visibility="collapsed",
            )
        with c4:
            if st.button("🔄 Reload", key="reload_support",
                          use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        filtered = [x for x in items if x["rr_tp1"] >= min_rr]
        st.caption(f"{len(filtered)} saham setelah filter RR ≥ {min_rr}")

        if not filtered:
            st.info(f"Tidak ada saham dengan RR ≥ {min_rr}")
        elif view_mode == "📊 Table":
            setup_table(filtered, nama_map)
        else:
            max_show = st.slider("Tampilkan N card", 10,
                                  max(10, len(filtered)),
                                  len(filtered),
                                  5,
                                  key="max_card_support")
            st.caption(f"Menampilkan {min(max_show, len(filtered))} dari "
                       f"{len(filtered)} saham")
            for r in filtered[:max_show]:
                r["_nama"] = nama_map.get(r["kode"], r["kode"])
                st.markdown(setup_row(r, tipe="support"),
                            unsafe_allow_html=True)
            if len(filtered) > max_show:
                st.caption(f"… dan {len(filtered) - max_show} saham lainnya. "
                           f"Ubah dropdown ke Table untuk lihat semua.")


# ============================================================
# TAB 5: BREAKOUT BUY
# ============================================================
with tab5:
    st.markdown(
        '<div style="background: linear-gradient(135deg, rgba(6,182,212,0.10), '
        'rgba(99,102,241,0.05)); border: 1px solid rgba(6,182,212,0.30); '
        'border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">'
        '<div style="font-size: 13px; color: #06b6d4; font-weight: 800; '
        'margin-bottom: 8px;">🚀 BREAKOUT BUY — SETUP STOP ORDER</div>'
        '<div style="font-size: 12px; color: #cbd5e1; line-height: 1.7;">'
        'Buy stop di atas resistance · RR min 1.5 · '
        'jarak harga→trigger ≤ 5%'
        '</div></div>',
        unsafe_allow_html=True
    )

    setups = load_setups()
    if not setups:
        st.warning("Data setup belum tersedia. Silakan hubungi admin.")
    else:
        items = setups.get("breakout_buy", [])
        generated = setups.get("generated", "?")

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            st.markdown(
                f'<div style="font-size:12px; color:#7d8ba3; padding:6px 0;">'
                f'<b style="color:#06b6d4;">{len(items)}</b> saham · '
                f'generated {generated}</div>',
                unsafe_allow_html=True
            )
        with c2:
            min_rr = st.slider("Min RR", 1.5, 5.0, 2.0, 0.1,
                                key="rr_min_breakout",
                                label_visibility="collapsed")
        with c3:
            view_mode = st.selectbox(
                "View", ["🎴 Card", "📊 Table"],
                key="view_breakout",
                label_visibility="collapsed",
            )
        with c4:
            if st.button("🔄 Reload", key="reload_breakout",
                          use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        filtered = [x for x in items if x["rr_tp1"] >= min_rr]
        st.caption(f"{len(filtered)} saham setelah filter RR ≥ {min_rr}")

        if not filtered:
            st.info(f"Tidak ada saham dengan RR ≥ {min_rr}")
        elif view_mode == "📊 Table":
            setup_table(filtered, nama_map)
        else:
            max_show = st.slider("Tampilkan N card", 10,
                                  max(10, len(filtered)),
                                  len(filtered),
                                  5,
                                  key="max_card_breakout")
            st.caption(f"Menampilkan {min(max_show, len(filtered))} dari "
                       f"{len(filtered)} saham")
            for r in filtered[:max_show]:
                r["_nama"] = nama_map.get(r["kode"], r["kode"])
                st.markdown(setup_row(r, tipe="breakout"),
                            unsafe_allow_html=True)
            if len(filtered) > max_show:
                st.caption(f"… dan {len(filtered) - max_show} saham lainnya.")


# ============================================================
# TAB 6: PERFORMA
# ============================================================
with tab6:
    rekap_files = list_rekap_files()

    if not rekap_files:
        st.warning("Belum ada data performa. Silakan hubungi admin.")
    else:
        # OTOMATISASI: Langsung ambil file rekap terbaru tanpa dropdown
        fname = rekap_files[0]
        bulan_label = fname.replace("Rekap_Trading_", "").replace(".xlsx", "")
        df_rev = load_rekap_sheet(fname, "Review Harian")

        if df_rev is None or df_rev.empty:
            st.warning(f"Belum ada data performa.")
        else:
            if "P/L %" in df_rev.columns:
                df_rev["P/L %"] = pd.to_numeric(df_rev["P/L %"], errors="coerce")

            st.markdown(
                section_title(f"Ringkasan Bulanan — {bulan_label}",
                              "Dari sheet Review Harian"),
                unsafe_allow_html=True,
            )

            n_total = len(df_rev)
            n_tp = int((df_rev["Status"] == "TP").sum()) if "Status" in df_rev.columns else 0
            n_sl = int((df_rev["Status"] == "SL").sum()) if "Status" in df_rev.columns else 0
            n_skip = int((df_rev["Status"] == "SKIP_GAP_DOWN").sum()) if "Status" in df_rev.columns else 0
            n_susp = int((df_rev["Status"] == "SUSPENDED").sum()) if "Status" in df_rev.columns else 0

            eksekusi = df_rev[df_rev["P/L %"].notna()]
            n_exec = len(eksekusi)
            if n_exec > 0:
                wr = (eksekusi["P/L %"] > 0).sum() / n_exec * 100
                avg = eksekusi["P/L %"].mean()
                tot = eksekusi["P/L %"].sum()
            else:
                wr = avg = tot = 0

            st.markdown(
                '<div style="background: linear-gradient(135deg, #131a2a, #0f1628); '
                'border: 1px solid #1a2338; border-radius: 12px; '
                'padding: 14px 20px; margin: 16px 0 20px; '
                'display: flex; gap: 24px; flex-wrap: wrap;">'
                f'<div><span style="font-size:11px; color:#7d8ba3;">Total</span>'
                f'<div style="font-size:18px; font-weight:800; color:#ffffff;">{n_total}</div></div>'
                f'<div><span style="font-size:11px; color:#7d8ba3;">Tereksekusi</span>'
                f'<div style="font-size:18px; font-weight:800; color:#10b981;">{n_exec}</div></div>'
                f'<div><span style="font-size:11px; color:#7d8ba3;">TP</span>'
                f'<div style="font-size:18px; font-weight:800; color:#10b981;">{n_tp}</div></div>'
                f'<div><span style="font-size:11px; color:#7d8ba3;">SL</span>'
                f'<div style="font-size:18px; font-weight:800; color:#f43f5e;">{n_sl}</div></div>'
                f'<div><span style="font-size:11px; color:#7d8ba3;">Skip</span>'
                f'<div style="font-size:18px; font-weight:800; color:#94a3b8;">{n_skip}</div></div>'
                f'<div><span style="font-size:11px; color:#7d8ba3;">Suspended</span>'
                f'<div style="font-size:18px; font-weight:800; color:#f43f5e;">{n_susp}</div></div>'
                '</div>',
                unsafe_allow_html=True
            )

            if n_exec > 0:
                c1, c2, c3 = st.columns(3)
                for col, label, val, color in [
                    (c1, "WIN RATE", f"{wr:.1f}%",
                     "#10b981" if wr >= 50 else "#f43f5e"),
                    (c2, "AVG RETURN", f"{avg:+.2f}%",
                     "#10b981" if avg >= 0 else "#f43f5e"),
                    (c3, "TOTAL RETURN", f"{tot:+.2f}%",
                     "#10b981" if tot >= 0 else "#f43f5e"),
                ]:
                    with col:
                        st.markdown(
                            '<div style="background:linear-gradient(180deg, #131a2a, #0f1628); '
                            'border-radius:14px; padding:22px 24px; '
                            'border:1px solid #1a2338;">'
                            f'<div style="font-size:11px; color:#7d8ba3; '
                            f'letter-spacing:0.8px; font-weight:600;">{label}</div>'
                            f'<div style="font-size:30px; font-weight:800; '
                            f'color:{color}; margin-top:8px;">{val}</div>'
                            '</div>',
                            unsafe_allow_html=True
                        )

            st.markdown(section_title("Ringkasan Harian vs IHSG"),
                        unsafe_allow_html=True)

            df_rev["_tgl"] = pd.to_datetime(df_rev["Tanggal"], errors="coerce")
            valid_tgl = df_rev.dropna(subset=["_tgl"])

            if valid_tgl.empty:
                st.info("Kolom Tanggal tidak tersedia.")
            else:
                min_tgl = valid_tgl["_tgl"].min()
                max_tgl = valid_tgl["_tgl"].max()
                start_str = (min_tgl - timedelta(days=7)).strftime("%Y-%m-%d")
                end_str = (max_tgl + timedelta(days=7)).strftime("%Y-%m-%d")

                with st.spinner("Ambil data IHSG..."):
                    df_ihsg = get_ihsg_daily(start_str, end_str)

                if df_ihsg is None or df_ihsg.empty:
                    st.caption("Data IHSG tidak tersedia.")
                else:
                    daily_rows = []
                    for tgl, grp in valid_tgl.groupby("_tgl"):
                        grp_pl = grp["P/L %"].dropna()
                        n_exec_d = len(grp_pl)
                        port_ret = grp_pl.mean() if n_exec_d > 0 else np.nan

                        ihsg_row = df_ihsg[df_ihsg["Date"] == tgl]
                        if ihsg_row.empty:
                            prev = df_ihsg[df_ihsg["Date"] <= tgl]
                            ihsg_ret = prev.iloc[-1]["ret"] if not prev.empty else np.nan
                        else:
                            ihsg_ret = ihsg_row.iloc[0]["ret"]

                        alpha = (port_ret - ihsg_ret
                                 if not pd.isna(port_ret) and not pd.isna(ihsg_ret)
                                 else np.nan)

                        daily_rows.append({
                            "Tanggal": tgl, "N": len(grp), "N_exec": n_exec_d,
                            "Portofolio": port_ret, "IHSG": ihsg_ret,
                            "Alpha": alpha,
                        })

                    df_daily = pd.DataFrame(daily_rows)
                    if not df_daily.empty:
                        df_daily = df_daily.sort_values("Tanggal").reset_index(drop=True)
                        for _, r in df_daily.iterrows():
                            tgl_str = pd.Timestamp(r["Tanggal"]).strftime("%d %b (%a)")
                            port = r["Portofolio"]; ihsg_r = r["IHSG"]
                            port_str = f"{port:+.2f}%" if not pd.isna(port) else "—"
                            ihsg_str = f"{ihsg_r:+.2f}%" if not pd.isna(ihsg_r) else "—"
                            port_col = ("#10b981" if (not pd.isna(port) and port >= 0)
                                        else "#f43f5e" if not pd.isna(port) else "#64748b")
                            ihsg_col = ("#10b981" if (not pd.isna(ihsg_r) and ihsg_r >= 0)
                                        else "#f43f5e" if not pd.isna(ihsg_r) else "#64748b")

                            # ALPHA DIHAPUS & TATA LETAK RAPI KE KIRI BAWAH
                            st.markdown(
                                '<div style="background:linear-gradient(135deg, #131a2a, #0f1628); '
                                'border-radius:10px; margin-bottom:8px; padding:12px 16px; '
                                'border:1px solid #1a2338; display:flex; flex-direction:column; gap:6px;">'
                                f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                                f'<span style="font-size:13px; color:#e6ebf5; font-weight:700;">{tgl_str}</span>'
                                f'<span style="font-size:11px; color:#7d8ba3;">{r["N_exec"]} trade</span>'
                                f'</div>'
                                f'<div style="display:flex; gap:30px; margin-top:4px;">'
                                f'<div style="text-align:left;">'
                                f'<div style="font-size:10px; color:#64748b; margin-bottom:2px;">Porto</div>'
                                f'<div style="font-size:13px; font-weight:800; color:{port_col};">{port_str}</div>'
                                f'</div>'
                                f'<div style="text-align:left;">'
                                f'<div style="font-size:10px; color:#64748b; margin-bottom:2px;">IHSG</div>'
                                f'<div style="font-size:13px; font-weight:800; color:{ihsg_col};">{ihsg_str}</div>'
                                f'</div>'
                                f'</div>'
                                '</div>',
                                unsafe_allow_html=True
                            )

            st.markdown(section_title("Ringkasan Mingguan"),
                        unsafe_allow_html=True)

            df_ming = load_rekap_sheet(fname, "Review Mingguan")
            if df_ming is None or df_ming.empty:
                st.info("Belum ada data mingguan di Excel.")
            elif "Info" in df_ming.columns:
                st.info("Belum ada sinyal mingguan di bulan ini.")
            else:
                for _, r in df_ming.iterrows():
                    minggu = str(r.get("Minggu Ke", "")).strip()
                    periode = str(r.get("Rentang Aktual", "")
                                   or r.get("Periode", "")).strip()
                    total_pl = r.get("Total P/L %", 0)
                    win_rate = r.get("Win Rate %", 0)
                    try: total_pl = float(total_pl)
                    except Exception: total_pl = 0
                    try: win_rate = float(win_rate)
                    except Exception: win_rate = 0
                    pl_col = "#10b981" if total_pl >= 0 else "#f43f5e"
                    wr_col = "#10b981" if win_rate >= 50 else "#f43f5e"

                    st.markdown(
                        '<div style="background:linear-gradient(135deg, #131a2a, #0f1628); '
                        'border-radius:12px; padding:16px 20px; '
                        'border:1px solid #1a2338; margin-bottom:8px;">'
                        f'<div style="display:flex; justify-content:space-between; '
                        f'align-items:center; margin-bottom:10px;">'
                        f'<div>'
                        f'<div style="font-size:14px; font-weight:800; color:#e6ebf5;">'
                        f'{minggu}</div>'
                        f'<div style="font-size:11px; color:#7d8ba3; margin-top:2px;">'
                        f'{periode}</div>'
                        f'</div>'
                        f'<div style="font-size:20px; font-weight:800; color:{pl_col};">'
                        f'{total_pl:+.2f}%</div>'
                        f'</div>'
                        f'<div style="display:flex; gap:20px; flex-wrap:wrap; '
                        f'font-size:11px; color:#94a3b8;">'
                        f'<span>Win Rate <b style="color:{wr_col};">{win_rate:.1f}%</b></span>'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )

            with st.expander("Lihat tabel lengkap"):
                df_display = df_rev.copy()
                df_display = df_display.drop(columns=["_tgl"], errors="ignore")
                st.dataframe(df_display, use_container_width=True,
                             hide_index=True)