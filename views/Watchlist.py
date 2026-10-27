import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys, json
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import (
    load_theme, page_header, section_title, empty_state,
)
from quant.parquet_loader import load_parquet_safe
from quant.supres import get_support_resistance

load_theme()

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
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_setups_json():
    data = load_json_safe(SETUPS_FILE)
    if not data:
        return {"buy_support": [], "breakout_buy": [], "generated": "?"}
    return {
        "buy_support": data.get("buy_support", []),
        "breakout_buy": data.get("breakout_buy", []),
        "generated": data.get("generated", "?"),
    }


def load_scan(name):
    d = load_json_safe(os.path.join(SCANS_DIR, f"{name}.json"))
    if not d:
        return [], "?"
    return d.get("items", []), d.get("generated", "?")


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
                    with open(os.path.join(FUND_DIR, f), "r", encoding="utf-8") as fh:
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
    fs.sort(reverse=True)
    return fs


def list_rekap_files():
    if not os.path.exists(OUTPUT_DIR):
        return []
    fs = [f for f in os.listdir(OUTPUT_DIR)
          if f.startswith("Rekap_Trading_") and f.endswith(".xlsx")]
    fs.sort(reverse=True)
    return fs


def extract_date_label(filename, prefix, suffix):
    return filename.replace(prefix, "").replace(suffix, "")


@st.cache_data(ttl=300)
def _load_csv_cached(path, mtime):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def load_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    return _load_csv_cached(path, os.path.getmtime(path))


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
        if any(v in ("Tanggal", "No", "Kode", "Metrik", "Minggu Ke", "Info") for v in vals):
            header_row = i
            break
    if header_row is None:
        header_row = 0
    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    except Exception:
        return None
    return df


# ============================================================
# IHSG DATA LOADER
# ============================================================
@st.cache_data(ttl=3600)
def load_ihsg_history():
    for fname in ["^JKSE.csv", "JKSE.csv", "IHSG.csv"]:
        path = os.path.join(OHLCV_DIR, fname)
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                close_col = next((c for c in df.columns if str(c).lower() == 'close'), None)
                date_col = next((c for c in df.columns if str(c).lower() in ['date', 'tanggal']), None)
                if close_col and date_col:
                    df[date_col] = pd.to_datetime(df[date_col])
                    df = df.sort_values(date_col)
                    df['IHSG_Return'] = df[close_col].pct_change() * 100
                    return df[[date_col, 'IHSG_Return']].rename(columns={date_col: 'Date'})
            except Exception:
                pass
            
    try:
        df = load_parquet_safe()
        if df is not None and "Kode" in df.columns:
            for code in ["^JKSE", "JKSE", "IHSG"]:
                sub = df[df["Kode"] == code]
                if not sub.empty:
                    sub = sub.copy()
                    sub["Date"] = pd.to_datetime(sub["Date"])
                    sub = sub.sort_values("Date")
                    sub['IHSG_Return'] = sub['Close'].pct_change() * 100
                    return sub[['Date', 'IHSG_Return']]
    except Exception:
        pass
    return None


def dedup_by_kode(items, key="kode", score_key="rr_tp1"):
    best = {}
    for x in items:
        k = x.get(key)
        if k is None:
            continue
        if k not in best:
            best[k] = x
            continue
        cur_rr = best[k].get(score_key, 0) or 0
        new_rr = x.get(score_key, 0) or 0
        if new_rr > cur_rr:
            best[k] = x
        elif new_rr == cur_rr:
            cur_dist = abs(best[k].get("jarak_entry_pct", 999) or 999)
            new_dist = abs(x.get("jarak_entry_pct", 999) or 999)
            if new_dist < cur_dist:
                best[k] = x
    return list(best.values())


# ============================================================
# ANALYZE SETUP SIGNALS (TANPA FIBO)
# ============================================================
@st.cache_data(ttl=1800)
def analyze_setup_signals(kode, harga):
    result = {
        "strong_zone": False,
        "strong_zone_info": "",
        "breakout_zone": False,
        "breakout_info": "",
    }

    try:
        sr = get_support_resistance(kode, timeframe="daily")
        if not sr:
            return result

        for z in sr.get("resistances", []):
            if z.get("role") == "reversal_warning":
                if harga >= z["lower"] * 0.98 and harga <= z["upper"] * 1.02:
                    result["strong_zone"] = True
                    result["strong_zone_info"] = (
                        f"Harga di resistance psikologis {z['level']:,.0f}. "
                        f"Waspada tertahan dan berbalik turun."
                    )
                    break

        for z in sr.get("resistances", []):
            if z.get("role") == "breakout_trigger":
                if harga >= z["lower"] * 0.98 and harga <= z["upper"] * 1.02:
                    result["breakout_zone"] = True
                    result["breakout_info"] = (
                        f"Harga di breakout trigger {z['level']:,.0f}. "
                        f"Beli stop di atas {z['upper']:,.0f} untuk konfirmasi tembus."
                    )
                    break
    except Exception:
        pass
    return result


# ============================================================
# CARD: HAKA PAGI
# ============================================================
def wl_row(kode, nama, harga, chg_pct):
    nama_disp = nama[:50] + "…" if len(nama) > 50 else nama

    # Monokrom: Putih untuk positif, Abu untuk negatif
    chg_color = "#ffffff" if chg_pct >= 0 else "#737373"
    chg_sign = "+" if chg_pct >= 0 else ""

    sl_price = harga * 0.97
    
    return (
        '<div style="'
        'background: #0a0a0a; '
        'border: 1px solid #262626; border-radius: 8px; '
        'padding: 18px 22px; margin-bottom: 10px; '
        'position: relative; overflow: hidden;">'
        
        '<div style="position:absolute; left:0; top:0; bottom:0; width:2px; '
        'background: #404040;"></div>'
        
        '<div style="display: flex; justify-content: space-between; align-items: center; padding-left: 8px; margin-bottom: 14px;">'
        '<div style="flex: 1; min-width: 0;">'
        f'<div style="font-size:17px; font-weight:600; color:#ffffff; letter-spacing:-0.02em; line-height:1.2;">{kode}</div>'
        f'<div style="font-size:12px; color:#a3a3a3; margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{nama_disp}</div>'
        '</div>'
        '<div style="text-align:right; flex-shrink:0; min-width:110px;">'
        f'<div style="font-size:22px; font-weight:600; color:#ffffff; letter-spacing:-0.03em; line-height:1;">{harga:,.0f}</div>'
        f'<div style="font-size:13px; font-weight:500; color:{chg_color}; margin-top:6px;">{chg_sign}{chg_pct:.2f}%</div>'
        '</div>'
        '</div>'

        '<div style="background: #171717; border: 1px solid #262626; border-radius: 4px; padding: 10px 14px; display: flex; gap: 16px; flex-wrap: wrap; margin-left: 8px; font-size: 12px;">'
        f'<span style="color:#737373;">Entry: <b style="color:#ffffff; font-weight:500;">T+1 Open (Gap 2-20%)</b></span>'
        f'<span style="color:#737373;">SL: <b style="color:#ffffff; font-weight:500;">{sl_price:,.0f} (-3%)</b></span>'
        f'<span style="color:#737373;">TP: <b style="color:#ffffff; font-weight:500;">Trailing 0.5%</b></span>'
        '</div>'

        '</div>'
    )


# ============================================================
# CARD: BOTTOM FISHING
# ============================================================
def bf_row(kode, nama, harga, rsi, rsi_chg, ni_g, rev_g, der, roe, special_flag=None):
    nama_disp = nama[:50] + "…" if len(nama) > 50 else nama

    # Monokrom untuk RSI
    if rsi < 30:
        rsi_color, rsi_bg, rsi_label = "#ffffff", "#171717", "OVERSOLD"
    elif rsi < 40:
        rsi_color, rsi_bg, rsi_label = "#a3a3a3", "#171717", "WEAK"
    else:
        rsi_color, rsi_bg, rsi_label = "#737373", "#171717", "NORMAL"

    rsi_arrow = "+" if rsi_chg > 0 else ("-" if rsi_chg < 0 else "=")
    rsi_arrow_color = "#ffffff" if rsi_chg > 0 else ("#737373" if rsi_chg < 0 else "#a3a3a3")

    def growth_badge(v, label):
        if v is None or pd.isna(v):
            return (f'<span style="font-size:11px; color:#737373; '
                    f'padding:4px 8px; background:#171717; '
                    f'border: 1px solid #262626; border-radius:4px; margin-right:6px;">{label} —</span>')
        color = "#ffffff" if v >= 0 else "#737373"
        sign = "+" if v >= 0 else ""
        return (f'<span style="font-size:11px; color:{color}; '
                f'padding:4px 8px; background:#171717; '
                f'border: 1px solid #262626; border-radius:4px; margin-right:6px; font-weight:500;">'
                f'{label} {sign}{v:.1f}%</span>')

    der_str = f"{der:.2f}x" if der is not None and not pd.isna(der) else "—"
    roe_str = f"{roe:.1f}%" if roe is not None and not pd.isna(roe) else "—"

    eksp_badge = ""
    if special_flag:
        eksp_badge = (
            f'<span style="font-size:11px; padding:4px 8px; '
            f'background:#171717; color:#a3a3a3; border: 1px solid #262626; '
            f'border-radius:4px; font-weight:500; margin-left:8px;">'
            f'{special_flag}</span>'
        )

    return (
        '<div style="background: #0a0a0a; border: 1px solid #262626; border-radius: 8px; '
        'padding: 18px 22px; margin-bottom: 10px; position: relative;">'
        f'<div style="position:absolute; left:0; top:0; bottom:0; width:2px; background: {rsi_color}; border-radius: 8px 0 0 8px;"></div>'
        '<div style="display:flex; justify-content:space-between; align-items:flex-start; padding-left: 8px; gap: 16px;">'
        '<div style="flex: 1; min-width: 0;">'
        f'<div style="font-size:17px; font-weight:600; color:#ffffff; letter-spacing:-0.02em; line-height:1.2;">{kode}{eksp_badge}</div>'
        f'<div style="font-size:12px; color:#a3a3a3; margin-top:4px;">{nama_disp}</div>'
        '<div style="margin-top:14px; display:flex; flex-wrap:wrap; gap:8px; align-items:center;">'
        f'<span style="font-size:11px; font-weight:600; padding:4px 10px; '
        f'border-radius:4px; background:{rsi_bg}; color:{rsi_color}; '
        f'border:1px solid #262626;">RSI {rsi:.1f}</span>'
        f'<span style="font-size:11px; color:{rsi_color}; font-weight:500; '
        f'margin-right:8px;">{rsi_label}</span>'
        f'<span style="font-size:11px; color:{rsi_arrow_color}; '
        f'font-weight:500; margin-right:8px;">{rsi_arrow} {abs(rsi_chg):.1f}</span>'
        f'{growth_badge(ni_g, "NI")}'
        f'{growth_badge(rev_g, "Rev")}'
        '</div>'
        '<div style="margin-top:12px; display:flex; flex-wrap:wrap; gap:14px;">'
        f'<span style="font-size:12px; color:#737373;">DER <b style="color:#a3a3a3; font-weight:500;">{der_str}</b></span>'
        f'<span style="font-size:12px; color:#737373;">ROE <b style="color:#a3a3a3; font-weight:500;">{roe_str}</b></span>'
        '</div>'
        '</div>'
        '<div style="text-align:right; flex-shrink:0;">'
        f'<div style="font-size:11px; color:#737373; letter-spacing:0.5px; '
        f'margin-bottom:4px;">HARGA</div>'
        f'<div style="font-size:22px; font-weight:600; color:#ffffff; '
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

    signals = analyze_setup_signals(kode, harga)
    strong_zone = signals.get("strong_zone", False)
    strong_info = signals.get("strong_zone_info", "")
    breakout_zone = signals.get("breakout_zone", False)
    breakout_info = signals.get("breakout_info", "")

    if tipe == "support":
        badge = ('<span style="background:#171717; color:#a3a3a3; '
                 'padding:4px 10px; border: 1px solid #262626; border-radius:4px; font-size:11px; '
                 'font-weight:500; text-transform:uppercase;">LIMIT · ZONA SUPPORT</span>')
        if harga < zona_lo:
            posisi_txt, posisi_color = "Di bawah zona", "#737373"
        elif harga > zona_hi:
            posisi_txt, posisi_color = "Di atas zona", "#a3a3a3"
        else:
            posisi_txt, posisi_color = "Di dalam zona", "#ffffff"
    else:
        badge = ('<span style="background:#171717; color:#a3a3a3; '
                 'padding:4px 10px; border: 1px solid #262626; border-radius:4px; font-size:11px; '
                 'font-weight:500; text-transform:uppercase;">STOP · BREAKOUT</span>')
        if harga < entry:
            posisi_txt, posisi_color = f"{((entry-harga)/harga*100):.1f}% di bawah trigger", "#a3a3a3"
        else:
            posisi_txt, posisi_color = "Sudah melewati trigger", "#ffffff"

    if rr_tp1 >= 1.5: rr_color = "#ffffff"
    else: rr_color = "#737373"

    if jarak > 0:
        jarak_color, jarak_icon = "#a3a3a3", "+"
    elif jarak < 0:
        jarak_color, jarak_icon = "#ffffff", "-"
    else:
        jarak_color, jarak_icon = "#737373", "="

    tp2_disp = f'{tp2:,.0f}' if tp2 else "—"
    tp2_rr = f'RR {rr_tp2:.2f}' if tp2 else "—"

    signal_banners = ""
    if tipe == "breakout" and breakout_zone:
        signal_banners += (
            f'<div style="background:#171717; border:1px solid #262626; '
            f'border-left:3px solid #ffffff; border-radius:4px; padding:12px 14px; margin-bottom:16px;">'
            f'<div style="font-size:11px; color:#ffffff; font-weight:600; letter-spacing:0.5px; text-transform:uppercase;">BREAKOUT TRIGGER</div>'
            f'<div style="font-size:12px; color:#a3a3a3; margin-top:6px; line-height:1.5;">{breakout_info}</div>'
            f'</div>'
        )

    if tipe == "support" and strong_zone:
        signal_banners += (
            f'<div style="background:#171717; border:1px solid #262626; '
            f'border-left:3px solid #737373; border-radius:4px; padding:12px 14px; margin-bottom:16px;">'
            f'<div style="font-size:11px; color:#a3a3a3; font-weight:600; letter-spacing:0.5px; text-transform:uppercase;">RESISTANCE PSIKOLOGIS</div>'
            f'<div style="font-size:12px; color:#a3a3a3; margin-top:6px; line-height:1.5;">{strong_info}</div>'
            f'</div>'
        )

    return (
        f'<div style="background:#0a0a0a; '
        f'border: 1px solid #262626; '
        f'border-radius:8px; padding:20px 24px; margin-bottom:16px;">'

        f'<div style="display:flex; justify-content:space-between; '
        f'align-items:flex-start; gap:20px; margin-bottom:20px; '
        f'flex-wrap:wrap;">'
        f'<div style="flex:1; min-width:200px;">'
        f'<div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">'
        f'<span style="font-size:20px; font-weight:600; color:#ffffff; '
        f'letter-spacing:-0.02em;">{kode}</span>'
        f'{badge}'
        f'</div>'
        f'<div style="font-size:13px; color:#a3a3a3; margin-top:6px;">{nama}</div>'
        f'</div>'

        f'<div style="text-align:right; min-width:140px;">'
        f'<div style="font-size:11px; color:#737373; letter-spacing:0.5px; '
        f'font-weight:500; text-transform:uppercase;">Harga Saat Ini</div>'
        f'<div style="font-size:26px; font-weight:600; color:#ffffff; '
        f'letter-spacing:-0.03em; margin-top:4px;">'
        f'{harga:,.0f}</div>'
        f'<div style="font-size:11px; color:{posisi_color}; font-weight:500; '
        f'margin-top:4px;">{posisi_txt}</div>'
        f'</div>'
        f'</div>'

        f'{signal_banners}'

        f'<div style="background:#171717; '
        f'border:1px solid #262626; border-radius:6px; '
        f'padding:14px 18px; margin-bottom:20px; '
        f'display:flex; justify-content:space-between; align-items:center; '
        f'flex-wrap:wrap; gap:12px;">'
        f'<div style="display:flex; align-items:center; gap:14px;">'
        f'<span style="font-size:14px; font-weight:500; color:#a3a3a3;">'
        f'{harga:,.0f}</span>'
        f'<span style="font-size:14px; color:#737373;">→</span>'
        f'<span style="font-size:16px; font-weight:600; color:#ffffff;">'
        f'{entry:,.0f}</span>'
        f'<span style="font-size:11px; color:{jarak_color}; font-weight:500;">'
        f'({jarak_icon} {abs(jarak):.2f}% ke entry)</span>'
        f'</div>'
        f'<span style="font-size:11px; color:#737373; letter-spacing:0.5px; '
        f'font-weight:500;">HARGA → ENTRY</span>'
        f'</div>'

        f'<div style="display:grid; grid-template-columns:repeat(4, 1fr); '
        f'gap:12px; margin-bottom:16px;">'
        
        f'<div style="background:#171717; border:1px solid #262626; '
        f'border-radius:6px; padding:14px;">'
        f'<div style="font-size:11px; color:#737373; letter-spacing:0.5px; '
        f'font-weight:500;">ENTRY</div>'
        f'<div style="font-size:18px; font-weight:600; color:#ffffff; '
        f'margin-top:6px;">{entry:,.0f}</div></div>'

        f'<div style="background:#171717; border:1px solid #262626; '
        f'border-radius:6px; padding:14px;">'
        f'<div style="font-size:11px; color:#737373; letter-spacing:0.5px; '
        f'font-weight:500;">STOP LOSS</div>'
        f'<div style="font-size:18px; font-weight:600; color:#ffffff; '
        f'margin-top:6px;">{sl:,.0f}</div>'
        f'<div style="font-size:11px; color:#737373; margin-top:4px;">'
        f'-{risk_pct:.2f}%</div></div>'

        f'<div style="background:#171717; border:1px solid #262626; '
        f'border-radius:6px; padding:14px;">'
        f'<div style="font-size:11px; color:#737373; letter-spacing:0.5px; '
        f'font-weight:500;">TP1</div>'
        f'<div style="font-size:18px; font-weight:600; color:#ffffff; '
        f'margin-top:6px;">{tp1:,.0f}</div>'
        f'<div style="font-size:11px; color:#737373; margin-top:4px;">'
        f'RR {rr_tp1:.2f}</div></div>'

        f'<div style="background:#171717; border:1px solid #262626; '
        f'border-radius:6px; padding:14px;">'
        f'<div style="font-size:11px; color:#737373; letter-spacing:0.5px; '
        f'font-weight:500;">TP2</div>'
        f'<div style="font-size:18px; font-weight:600; color:#ffffff; '
        f'margin-top:6px;">{tp2_disp}</div>'
        f'<div style="font-size:11px; color:#737373; margin-top:4px;">'
        f'{tp2_rr}</div></div>'
        f'</div>'

        f'<div style="border-top:1px solid #262626; padding-top:14px; '
        f'display:flex; gap:24px; flex-wrap:wrap; font-size:12px; color:#a3a3a3;">'
        f'<span>RR <b style="color:{rr_color}; font-size:13px; font-weight:600;">{rr_tp1:.2f}</b></span>'
        f'<span>Risk <b style="color:#a3a3a3; font-weight:500;">{risk_pct:.2f}%</b></span>'
        f'<span>Zona <b style="color:#a3a3a3; font-weight:500;">{zona_lo:,.0f} – {zona_hi:,.0f}</b></span>'
        f'</div>'
        f'</div>'
    )


# ============================================================
# HEADER
# ============================================================
st.markdown(page_header("", "Watchlist",
                        "Haka Pagi · Bottom Fishing · Pre-Cross · Setups · Performa"),
            unsafe_allow_html=True)

nama_map = load_nama()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Haka Pagi", "Bottom Fishing", "Pre-Cross",
    "Buy on Support", "Breakout Buy", "Performa"
])


# ============================================================
# TAB 1: HAKA PAGI
# ============================================================
with tab1:
    files = list_kandidat_files()

    if not files:
        st.markdown(empty_state("", "Belum ada kandidat", "Jalankan screener dulu"), unsafe_allow_html=True)
    else:
        date_options, file_map = [], {}
        for f in files:
            try:
                tgl_str = extract_date_label(f, "kandidat_", ".csv")
                date_options.append(tgl_str)
                file_map[tgl_str] = f
            except Exception:
                continue

        col1, col2 = st.columns([4, 1])
        with col1:
            selected_date = st.selectbox(
                "Pilih tanggal kandidat",
                date_options, index=0,
                key="kandidat_date_picker",
            )
        with col2:
            if st.button("Refresh", key="refresh_kandidat", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        selected = file_map[selected_date]
        df = load_csv(os.path.join(OUTPUT_DIR, selected))

        if df.empty:
            st.error(f"File `{selected}` kosong atau tidak terbaca.")
        else:
            for col in ["ret_1d"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            
            if "rating" in df.columns:
                df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0)
                df = df.sort_values("rating", ascending=False, na_position="last")

            st.markdown(
                f'<div style="font-size:13px; color:#a3a3a3; '
                f'margin:12px 0 20px; font-weight:500;">'
                f'Kandidat: <code>{selected}</code> · {len(df)} saham · '
                f'{len(date_options)} hari tersedia</div>',
                unsafe_allow_html=True,
            )

            if df.empty:
                st.info("Tidak ada kandidat.")
            else:
                for _, r in df.iterrows():
                    kode = str(r["kode"]).upper()
                    nama = nama_map.get(kode, kode)
                    close = float(r["close"])

                    ret1d_raw = r.get("ret_1d", 0)
                    ret1d = (float(ret1d_raw) * 100
                             if pd.notna(ret1d_raw) else 0)

                    st.markdown(
                        wl_row(kode, nama, close, ret1d),
                        unsafe_allow_html=True,
                    )

            st.markdown(
                '<div style="background:#171717; '
                'border:1px solid #262626; '
                'border-left:3px solid #ffffff; '
                'border-radius:6px; padding:16px 20px; margin-top:24px; '
                'font-size:13px; color:#d4d4d4; line-height:1.6;">'
                '<b style="color:#ffffff;">Besok pagi saat open (T+1):</b> '
                'cek gap untuk setiap kandidat di atas. '
                '<b style="color:#ffffff;">Execute</b> jika gap 2%–20%. '
                '<b style="color:#737373;">Skip</b> jika gap &lt; 2% '
                'atau &gt; 20%.'
                '</div>',
                unsafe_allow_html=True,
            )


# ============================================================
# TAB 2: BOTTOM FISHING
# ============================================================
with tab2:
    st.markdown(
        '<div style="background: #0a0a0a; '
        'border: 1px solid #262626; border-radius: 8px; '
        'padding: 20px 24px; margin-bottom: 24px;">'
        '<div style="font-size: 14px; color: #ffffff; font-weight: 600; '
        'margin-bottom: 10px;">BOTTOM FISHING — SAHAM SEHAT</div>'
        '<div style="font-size: 13px; color: #a3a3a3; line-height: 1.6;">'
        '- Q1 dan Q2 ada, se-tahun, Q2 standalone ≥ 0<br>'
        '- Laba tidak turun drastis (&gt; 50%) — kecuali premium ekspansi<br>'
        '- Revenue YoY tidak turun &gt; 30%<br>'
        '- DER &lt; 2.0x · ROE &gt; 10%<br>'
        '- Saham masih aktif bergerak'
        '</div></div>', unsafe_allow_html=True
    )

    items_bf, gen_bf = load_scan("bottom")

    if not items_bf:
        st.warning("Data Bottom Fishing belum tersedia. Silakan hubungi admin.")
    else:
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            st.markdown(
                f'<div style="font-size:13px; color:#a3a3a3; padding:6px 0;">'
                f'<b style="color:#ffffff;">{len(items_bf)}</b> saham · '
                f'generated {gen_bf}</div>', unsafe_allow_html=True
            )
        with c2:
            max_rsi = st.slider("Max RSI", 10, 60, 40, 5, key="bf_rsi", label_visibility="collapsed")
        with c3:
            if st.button("Reload", key="reload_bf", use_container_width=True):
                st.cache_data.clear(); st.rerun()

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
                    ), unsafe_allow_html=True
                )


# ============================================================
# TAB 3: PRE-CROSS
# ============================================================
with tab3:
    st.markdown(
        '<div style="background: #0a0a0a; '
        'border: 1px solid #262626; '
        'border-radius: 8px; padding: 20px 24px; margin-bottom: 24px;">'
        '<div style="font-size: 14px; color: #ffffff; font-weight: 600; '
        'letter-spacing:0.5px; margin-bottom:10px;">PRE-GOLDEN-CROSS</div>'
        '<div style="font-size: 13px; color: #a3a3a3; line-height: 1.6;">'
        'Setup skor ≥ <b>85</b> · Winrate backtest 91.2% · Gap EMA20-EMA50 ≤ 4%'
        '</div></div>', unsafe_allow_html=True
    )

    items_pc, gen_pc = load_scan("precross")

    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(
            f'<div style="font-size:13px; color:#a3a3a3; padding:6px 0;">'
            f'<b style="color:#ffffff;">{len(items_pc)}</b> setup skor ≥85 · '
            f'generated {gen_pc}</div>', unsafe_allow_html=True
        )
    with c2:
        if st.button("Reload", key="reload_pc", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    if gen_pc == "?":
        st.warning("Data scan belum tersedia. Silakan hubungi admin untuk update data terbaru.")
    elif not items_pc:
        st.markdown(
            '<div style="background:#0a0a0a; '
            'border:1px dashed #404040; border-radius:8px; '
            'padding:40px 32px; text-align:center;">'
            '<div style="font-size:15px; font-weight:600; color:#ffffff; '
            'margin-bottom:8px;">Tidak ada setup skor ≥ 85 hari ini</div>'
            '<div style="font-size:13px; color:#a3a3a3; max-width:480px; '
            'margin:0 auto;">Setup presisi tinggi jarang muncul. '
            'Cek kandidat emerging di bawah.</div>'
            '</div>', unsafe_allow_html=True
        )
    else:
        for i, r in enumerate(items_pc):
            kode = r["kode"]; nama = nama_map.get(kode, kode)[:55]
            skor = r["skor"]; gap = r["gap_pct"]; konv = r["konv_pct"]
            harga = r["harga"]; ema20 = r["ema20"]; ema50 = r["ema50"]
            st.markdown(
                f'<div style="background:#0a0a0a; '
                f'border:1px solid #262626; border-left:3px solid #ffffff; '
                f'border-radius:8px; padding:20px 24px; margin-bottom:12px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; gap:16px;">'
                f'<div>'
                f'<div style="display:flex; align-items:baseline; gap:12px;">'
                f'<span style="font-size:16px; font-weight:600; color:#737373;">#{i+1}</span>'
                f'<span style="font-size:18px; font-weight:600; color:#ffffff;">{kode}</span>'
                f'<span style="background:#171717; color:#ffffff; border:1px solid #262626; '
                f'padding:3px 10px; border-radius:4px; font-size:11px; font-weight:600;">SKOR {skor:.0f}</span>'
                f'</div>'
                f'<div style="font-size:13px; color:#a3a3a3; margin-top:6px;">{nama}</div>'
                f'<div style="margin-top:12px; display:flex; gap:16px; flex-wrap:wrap; font-size:12px; color:#737373;">'
                f'<span>Harga <b style="color:#ffffff; font-weight:500;">{harga:,.0f}</b></span>'
                f'<span>EMA20 <b style="color:#ffffff; font-weight:500;">{ema20:,.0f}</b></span>'
                f'<span>EMA50 <b style="color:#ffffff; font-weight:500;">{ema50:,.0f}</b></span>'
                f'<span>Gap <b style="color:#ffffff; font-weight:500;">{gap:.2f}%</b></span>'
                f'<span>Konv <b style="color:#ffffff; font-weight:500;">+{konv:.0f}%</b></span>'
                f'</div></div></div></div>', unsafe_allow_html=True
            )

    st.markdown('<div style="height:1px; background:#262626; margin:32px 0;"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="background: #0a0a0a; '
        'border: 1px solid #262626; '
        'border-radius: 8px; padding: 20px 24px; margin-bottom: 24px;">'
        '<div style="font-size: 14px; color: #ffffff; font-weight: 600; '
        'margin-bottom: 10px;">EMERGING — MENUJU SKOR 85+</div>'
        '<div style="font-size: 13px; color: #a3a3a3; line-height: 1.6;">'
        'Saham skor 65–84 yang sedang konvergen dan EMA20 naik.'
        '</div></div>', unsafe_allow_html=True
    )

    items_emg, gen_emg = load_scan("emerging")

    if gen_emg == "?":
        st.warning("Data scan emerging belum tersedia. Silakan hubungi admin untuk update data terbaru.")
    elif not items_emg:
        st.info("Belum ada kandidat emerging hari ini.")
    else:
        st.markdown(
            f'<div style="font-size:13px; color:#a3a3a3; margin:4px 0 16px;">'
            f'<b style="color:#ffffff;">{len(items_emg)}</b> kandidat · generated {gen_emg}</div>',
            unsafe_allow_html=True
        )
        for i, r in enumerate(items_emg):
            kode = r["kode"]; nama = nama_map.get(kode, kode)[:55]
            skor = r["skor"]; gap = r["gap_pct"]; konv = r["konv_pct"]; harga = r["harga"]
            
            st.markdown(
                f'<div style="background:#0a0a0a; '
                f'border:1px solid #262626; border-left:3px solid #404040; '
                f'border-radius:8px; padding:16px 20px; margin-bottom:12px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; gap:16px;">'
                f'<div>'
                f'<div style="display:flex; align-items:baseline; gap:10px;">'
                f'<span style="font-size:14px; font-weight:600; color:#737373;">#{i+1}</span>'
                f'<span style="font-size:16px; font-weight:600; color:#ffffff;">{kode}</span>'
                f'<span style="background:#171717; color:#a3a3a3; border: 1px solid #262626; '
                f'padding:3px 10px; border-radius:4px; font-size:11px; font-weight:600;">SKOR {skor:.0f}</span>'
                f'</div>'
                f'<div style="font-size:12px; color:#a3a3a3; margin-top:4px;">{nama}</div>'
                f'<div style="margin-top:10px; display:flex; gap:14px; flex-wrap:wrap; font-size:12px; color:#737373;">'
                f'<span>Harga <b style="color:#ffffff; font-weight:500;">{harga:,.0f}</b></span>'
                f'<span>Gap <b style="color:#ffffff; font-weight:500;">{gap:.2f}%</b></span>'
                f'<span>Konv <b style="color:#ffffff; font-weight:500;">+{konv:.0f}%</b></span>'
                f'</div></div>'
                f'<div style="text-align:right;">'
                f'<div style="font-size:22px; font-weight:600; color:#ffffff;">{skor:.0f}</div>'
                f'<div style="font-size:11px; color:#737373;">{85 - skor:.0f} ke 85</div>'
                f'</div></div></div>', unsafe_allow_html=True
            )


# ============================================================
# TAB 4: BUY ON SUPPORT
# ============================================================
with tab4:
    st.markdown(
        '<div style="background: #0a0a0a; '
        'border: 1px solid #262626; '
        'border-radius: 8px; padding: 20px 24px; margin-bottom: 24px;">'
        '<div style="font-size: 14px; color: #ffffff; font-weight: 600; '
        'margin-bottom: 10px;">BUY ON SUPPORT — SETUP LIMIT ORDER</div>'
        '<div style="font-size: 13px; color: #a3a3a3; line-height: 1.6;">'
        'Hanya saham yang <b>harganya dekat zona support</b> '
        '(0-5% di atas zona atau sudah di dalam zona) · RR min 1.5'
        '</div></div>', unsafe_allow_html=True
    )

    setups_data = load_setups_json()

    items_support_raw = setups_data.get("buy_support", [])
    generated_support = setups_data.get("generated", "?")

    items_support = dedup_by_kode(items_support_raw)

    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(
            f'<div style="font-size:13px; color:#a3a3a3; padding:6px 0;">'
            f'<b style="color:#ffffff;">{len(items_support)}</b> saham dekat support · '
            f'scan {generated_support}</div>',
            unsafe_allow_html=True
        )
    with c2:
        if st.button("Reload", key="reload_support", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if not items_support:
        st.info("Tidak ada saham yang sedang dekat dengan support saat ini.")
    else:
        for r in items_support:
            r["_nama"] = nama_map.get(r["kode"], r["kode"])
            st.markdown(setup_row(r, tipe="support"), unsafe_allow_html=True)


# ============================================================
# TAB 5: BREAKOUT BUY
# ============================================================
with tab5:
    st.markdown(
        '<div style="background: #0a0a0a; '
        'border: 1px solid #262626; '
        'border-radius: 8px; padding: 20px 24px; margin-bottom: 24px;">'
        '<div style="font-size: 14px; color: #ffffff; font-weight: 600; '
        'margin-bottom: 10px;">BREAKOUT BUY — SETUP STOP ORDER</div>'
        '<div style="font-size: 13px; color: #a3a3a3; line-height: 1.6;">'
        'Hanya saham yang <b>harganya 0-3% di bawah resistance</b> '
        '(sedang mendekati trigger breakout) · RR min 1.5'
        '</div></div>', unsafe_allow_html=True
    )

    setups_data2 = load_setups_json()

    items_breakout_raw = setups_data2.get("breakout_buy", [])
    generated_breakout = setups_data2.get("generated", "?")

    items_breakout = dedup_by_kode(items_breakout_raw)

    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(
            f'<div style="font-size:13px; color:#a3a3a3; padding:6px 0;">'
            f'<b style="color:#ffffff;">{len(items_breakout)}</b> saham dekat resistance · '
            f'scan {generated_breakout}</div>',
            unsafe_allow_html=True
        )
    with c2:
        if st.button("Reload", key="reload_breakout", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if not items_breakout:
        st.info("Tidak ada saham yang sedang dekat dengan resistance saat ini.")
    else:
        for r in items_breakout:
            r["_nama"] = nama_map.get(r["kode"], r["kode"])
            st.markdown(setup_row(r, tipe="breakout"), unsafe_allow_html=True)


# ============================================================
# TAB 6: PERFORMA
# ============================================================
with tab6:
    rekap_files = list_rekap_files()
    if not rekap_files:
        st.warning("Belum ada data performa. Silakan hubungi admin.")
    else:
        bulan_options = []
        file_map = {}
        for f in rekap_files:
            try:
                bulan_str = extract_date_label(f, "Rekap_Trading_", ".xlsx")
                bulan_options.append(bulan_str)
                file_map[bulan_str] = f
            except Exception:
                continue

        col1, col2 = st.columns([3, 1])
        with col1:
            selected_bulan = st.selectbox(
                "Pilih bulan laporan",
                bulan_options,
                index=0,
                key="rekap_bulan_picker"
            )
        with col2:
            if st.button("Refresh", key="refresh_rekap", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        fname = file_map[selected_bulan]
        bulan_label = selected_bulan
        df_rev = load_rekap_sheet(fname, "Review Harian")

        if df_rev is None or df_rev.empty:
            st.warning(f"Data untuk bulan {bulan_label} kosong.")
        else:
            if "P/L %" in df_rev.columns:
                df_rev["P/L %"] = pd.to_numeric(df_rev["P/L %"], errors="coerce")

            st.markdown(section_title(f"Ringkasan Bulanan — {bulan_label}",
                                       f"Dari file {fname}"), unsafe_allow_html=True)

            n_total = len(df_rev)
            n_tp = int((df_rev["Status"] == "TP").sum()) if "Status" in df_rev.columns else 0
            n_sl = int((df_rev["Status"] == "SL").sum()) if "Status" in df_rev.columns else 0
            n_trail = int((df_rev["Status"] == "TRAIL").sum()) if "Status" in df_rev.columns else 0
            n_hold = int((df_rev["Status"] == "HOLD").sum()) if "Status" in df_rev.columns else 0
            n_skip = int((df_rev["Status"] == "SKIP_GAP_DOWN").sum()) if "Status" in df_rev.columns else 0
            if "Status" in df_rev.columns:
                n_skip += int((df_rev["Status"] == "SKIP_GAP_LOW").sum())
                n_skip += int((df_rev["Status"] == "SKIP_GAP_HIGH").sum())
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
                '<div style="background: #0a0a0a; '
                'border: 1px solid #262626; border-radius: 8px; '
                'padding: 16px 20px; margin: 16px 0 24px; '
                'display: flex; gap: 32px; flex-wrap: wrap;">'
                f'<div><span style="font-size:12px; color:#737373;">Total</span>'
                f'<div style="font-size:18px; font-weight:600; color:#ffffff;">{n_total}</div></div>'
                f'<div><span style="font-size:12px; color:#737373;">Tereksekusi</span>'
                f'<div style="font-size:18px; font-weight:600; color:#ffffff;">{n_exec}</div></div>'
                f'<div><span style="font-size:12px; color:#737373;">TRAIL</span>'
                f'<div style="font-size:18px; font-weight:600; color:#ffffff;">{n_trail}</div></div>'
                f'<div><span style="font-size:12px; color:#737373;">SL</span>'
                f'<div style="font-size:18px; font-weight:600; color:#737373;">{n_sl}</div></div>'
                f'<div><span style="font-size:12px; color:#737373;">HOLD</span>'
                f'<div style="font-size:18px; font-weight:600; color:#a3a3a3;">{n_hold}</div></div>'
                f'<div><span style="font-size:12px; color:#737373;">Skip</span>'
                f'<div style="font-size:18px; font-weight:600; color:#a3a3a3;">{n_skip}</div></div>'
                f'<div><span style="font-size:12px; color:#737373;">Suspended</span>'
                f'<div style="font-size:18px; font-weight:600; color:#737373;">{n_susp}</div></div>'
                '</div>', unsafe_allow_html=True
            )

            if n_exec > 0:
                c1, c2, c3 = st.columns(3)
                for col, label, val in [
                    (c1, "WIN RATE", f"{wr:.1f}%"),
                    (c2, "AVG RETURN", f"{avg:+.2f}%"),
                    (c3, "TOTAL RETURN", f"{tot:+.2f}%"),
                ]:
                    with col:
                        st.markdown(
                            '<div style="background:#0a0a0a; '
                            'border-radius:8px; padding:24px; border:1px solid #262626;">'
                            f'<div style="font-size:12px; color:#737373; letter-spacing:0.5px; font-weight:500;">{label}</div>'
                            f'<div style="font-size:28px; font-weight:600; color:#ffffff; margin-top:8px;">{val}</div>'
                            '</div>', unsafe_allow_html=True
                        )

            st.markdown(section_title("Ringkasan Harian vs IHSG"), unsafe_allow_html=True)
            df_rev["_tgl"] = pd.to_datetime(df_rev["Tanggal"], errors="coerce")
            valid_tgl = df_rev.dropna(subset=["_tgl"])

            df_ihsg = load_ihsg_history()
            ihsg_dict = {}
            if df_ihsg is not None and not df_ihsg.empty:
                df_ihsg['Date'] = pd.to_datetime(df_ihsg['Date'])
                ihsg_dict = dict(zip(df_ihsg['Date'].dt.date, df_ihsg['IHSG_Return']))

            if valid_tgl.empty:
                st.info("Kolom Tanggal tidak tersedia.")
            else:
                daily_rows = []
                for tgl, grp in valid_tgl.groupby("_tgl"):
                    grp_pl = grp["P/L %"].dropna()
                    n_exec_d = len(grp_pl)
                    port_ret = grp_pl.mean() if n_exec_d > 0 else np.nan
                    
                    tgl_date = pd.Timestamp(tgl).date()
                    ihsg_ret = ihsg_dict.get(tgl_date, np.nan)
                    
                    daily_rows.append({"Tanggal": tgl, "N_exec": n_exec_d, "Portofolio": port_ret, "IHSG": ihsg_ret})

                df_daily = pd.DataFrame(daily_rows)
                if not df_daily.empty:
                    df_daily = df_daily.sort_values("Tanggal").reset_index(drop=True)
                    for _, r in df_daily.iterrows():
                        tgl_str = pd.Timestamp(r["Tanggal"]).strftime("%d %b (%a)")
                        port = r["Portofolio"]
                        port_str = f"{port:+.2f}%" if not pd.isna(port) else "—"
                        port_col = "#ffffff" if (not pd.isna(port) and port >= 0) else "#737373"
                        
                        ihsg = r["IHSG"]
                        ihsg_str = f"{ihsg:+.2f}%" if not pd.isna(ihsg) else "—"
                        ihsg_col = "#ffffff" if (not pd.isna(ihsg) and ihsg >= 0) else "#737373"
                        
                        st.markdown(
                            '<div style="background:#0a0a0a; '
                            'border-radius:6px; margin-bottom:8px; padding:14px 18px; border:1px solid #262626;">'
                            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">'
                            f'<span style="font-size:13px; color:#ffffff; font-weight:500;">{tgl_str}</span>'
                            f'<span style="font-size:12px; color:#737373;">{r["N_exec"]} trade</span>'
                            f'</div>'
                            f'<div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">'
                            f'<div>'
                            f'<div style="font-size:11px; color:#737373; margin-bottom:4px; text-transform:uppercase;">Portofolio</div>'
                            f'<div style="font-size:14px; font-weight:600; color:{port_col};">{port_str}</div>'
                            f'</div>'
                            f'<div>'
                            f'<div style="font-size:11px; color:#737373; margin-bottom:4px; text-transform:uppercase;">IHSG</div>'
                            f'<div style="font-size:14px; font-weight:600; color:{ihsg_col};">{ihsg_str}</div>'
                            f'</div>'
                            f'</div></div>', unsafe_allow_html=True
                        )

            with st.expander("Lihat tabel lengkap"):
                df_display = df_rev.copy().drop(columns=["_tgl"], errors="ignore")
                st.dataframe(df_display, use_container_width=True, hide_index=True)