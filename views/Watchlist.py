import streamlit as st
if not st.session_state.get("authentication_status"):
    st.write("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys, json
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme

st.set_page_config(page_title="Watchlist", layout="wide")
load_theme()

if not st.session_state.get("authentication_status"):
    st.write("Silakan login dulu di halaman utama.")
    st.stop()

WATCHLIST_FILE = "data_watchlist.json"
OUTPUT_DIR = "quant/output"
OHLCV_DIR = "data_ohlcv_idx"
FUND_DIR = "data_fundamental"
SEKTOR_CSV = "data_sektor.csv"
SETUPS_FILE = "data_setups.json"
SCANS_DIR = "data_scans"

def load_json_safe(path):
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
    fs.sort(key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)), reverse=True)
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

def fmt_num(v, dec=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        if abs(v) >= 1e12: return f"{v/1e12:.{dec}f}T"
        if abs(v) >= 1e9: return f"{v/1e9:.{dec}f}B"
        if abs(v) >= 1e6: return f"{v/1e6:.{dec}f}M"
        return f"{v:,.{dec}f}"
    except Exception:
        return "—"

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
        df = yf.download("^JKSE", start=start_date_str, end=end_date_str, progress=False)
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

def wl_row(kode, nama, harga, chg_pct, rating=0, match="-", strength=0):
    return f"**{kode}** - {nama} | Harga: {harga:,.0f} | Chg: {chg_pct:+.2f}% | Rating: {rating} | Match: {match} | Strength: {strength}"

def bf_row(kode, nama, harga, rsi, rsi_chg, ni_g, rev_g, der, roe, special_flag=None):
    der_str = f"{der:.2f}x" if der is not None and not pd.isna(der) else "—"
    roe_str = f"{roe:.1f}%" if roe is not None and not pd.isna(roe) else "—"
    return f"**{kode}** - {nama} | Harga: {harga:,.0f} | RSI: {rsi:.1f} | DER: {der_str} | ROE: {roe_str}"

def setup_row(r, tipe="support"):
    kode = r["kode"]
    nama = r.get("_nama", kode)[:50]
    harga = r.get("harga", 0)
    entry = r.get("entry", 0)
    sl = r.get("sl", 0)
    tp1 = r.get("tp1", 0)
    return f"**{kode}** - {nama} | Harga: {harga:,.0f} | Entry: {entry:,.0f} | SL: {sl:,.0f} | TP1: {tp1:,.0f} | RR: {r.get('rr_tp1',0):.2f}"

def setup_table(items, nama_map):
    rows = []
    for r in items:
        rows.append({
            "Kode": r["kode"], "Nama": nama_map.get(r["kode"], r["kode"])[:30],
            "Harga": r["harga"], "Entry": r["entry"], "SL": r["sl"],
            "TP1": r["tp1"], "TP2": r.get("tp2"), "RR": r["rr_tp1"],
            "Risk %": r["risk_pct"], "Jarak %": r["jarak_entry_pct"],
            "Zona Lo": r["zona_lo"], "Zona Hi": r["zona_hi"], "Lot": r["lot"],
        })
    df_show = pd.DataFrame(rows)
    st.dataframe(df_show, use_container_width=True, hide_index=True, height=min(700, 40 + len(df_show) * 35))

st.title("Watchlist")
st.write("Haka Pagi · Bottom Fishing · Pre-Cross · Setups · Performa")

nama_map = load_nama()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Haka Pagi", "Bottom Fishing", "Pre-Cross", "Buy on Support", "Breakout Buy", "Performa"
])

with tab1:
    st.write("**ATURAN SCREENER**")
    st.write("Entry: Open T+1 (hari bursa berikutnya setelah sinyal)")
    st.write("Exit: TP High-1% (kalau High naik >= 1%) | SL -3% (sudah termasuk fee)")
    st.write("Rule A: Ret1d > 15% · Ret5d > 15% · Price > SMA20 + 20%")
    st.write("Rule B: Ret1d > 15% · Ret5d > 20% · Range > 10% · VolZ-20 > 2")

    files = list_kandidat_files()
    if not files:
        st.write("Belum ada kandidat. Jalankan screener dulu.")
    else:
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            selected = st.selectbox("File", files, label_visibility="collapsed")
        with c2:
            min_str = st.selectbox("Min Strength", [1, 2, 3, 4], index=1, label_visibility="collapsed")
        with c3:
            min_rating = st.slider("Min Rating", 0, 100, 0, 5, label_visibility="collapsed")

        df = load_csv(os.path.join(OUTPUT_DIR, selected))
        if df.empty:
            st.write("File kosong.")
        else:
            if "strength" in df.columns and "rating" in df.columns:
                df = df[(df["strength"] >= min_str) & (df["rating"] >= min_rating)]

            st.write(f"{len(df)} kandidat ditampilkan · {selected}")
            for idx, r in df.iterrows():
                kode = str(r["kode"]).upper()
                nama = nama_map.get(kode, kode)
                close = float(r["close"])
                rating = float(r.get("rating", 0))
                match = str(r.get("match", "-"))
                strength = int(r.get("strength", 0))
                ret1d = float(r.get("ret_1d", 0)) * 100
                st.write(wl_row(kode, nama, close, ret1d, rating, match, strength))

with tab2:
    st.write("**BOTTOM FISHING — SAHAM SEHAT**")
    st.write("Q1 dan Q2 ada, se-tahun, Q2 standalone >= 0")
    st.write("Laba tidak turun drastis (> 50%) — kecuali premium ekspansi")
    st.write("Revenue YoY tidak turun > 30% | DER < 2.0x · ROE > 10%")

    items_bf, gen_bf = load_scan("bottom")
    if not items_bf:
        st.write("Data Bottom Fishing belum tersedia.")
    else:
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            st.write(f"{len(items_bf)} saham · generated {gen_bf}")
        with c2:
            max_rsi = st.slider("Max RSI", 10, 60, 40, 5, key="bf_rsi", label_visibility="collapsed")
        with c3:
            if st.button("Reload", key="reload_bf", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        filtered = [x for x in items_bf if x["rsi"] <= max_rsi]
        st.write(f"{len(filtered)} saham RSI <= {max_rsi}")

        if not filtered:
            st.write("Tidak ada saham lolos filter RSI.")
        else:
            for r in filtered:
                st.write(bf_row(r["kode"], nama_map.get(r["kode"], r["kode"]), r["harga"], r["rsi"], r["rsi_change"], r.get("ni_growth"), r.get("rev_growth"), r.get("der"), r.get("roe"), special_flag=r.get("special_flag")))

with tab3:
    st.write("**PRE-GOLDEN-CROSS**")
    st.write("Setup skor >= 85 · Winrate backtest 91.2% · Gap EMA20-EMA50 <= 4%")

    items_pc, gen_pc = load_scan("precross")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.write(f"{len(items_pc)} setup skor >=85 · generated {gen_pc}")
    with c2:
        if st.button("Reload", key="reload_pc", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if gen_pc == "?":
        st.write("Data scan belum tersedia.")
    elif not items_pc:
        st.write("Tidak ada setup skor >= 85 hari ini.")
    else:
        for i, r in enumerate(items_pc):
            kode = r["kode"]
            nama = nama_map.get(kode, kode)[:55]
            skor = r["skor"]
            gap = r["gap_pct"]
            harga = r["harga"]
            st.write(f"**{kode}** - {nama} | Skor: {skor:.0f} | Harga: {harga:,.0f} | Gap: {gap:.2f}%")

    st.write("---")
    st.write("**EMERGING — MENUJU SKOR 85+**")
    st.write("Saham skor 65–84 yang sedang konvergen dan EMA20 naik.")

    items_emg, gen_emg = load_scan("emerging")
    if gen_emg == "?":
        st.write("Data scan emerging belum tersedia.")
    elif not items_emg:
        st.write("Belum ada kandidat emerging hari ini.")
    else:
        st.write(f"{len(items_emg)} kandidat · generated {gen_emg}")
        for i, r in enumerate(items_emg):
            kode = r["kode"]
            nama = nama_map.get(kode, kode)[:55]
            skor = r["skor"]
            gap = r["gap_pct"]
            harga = r["harga"]
            st.write(f"**{kode}** - {nama} | Skor: {skor:.0f} | Harga: {harga:,.0f} | Gap: {gap:.2f}%")

with tab4:
    st.write("**BUY ON SUPPORT — SETUP LIMIT ORDER**")
    st.write("Entry limit di zona support · RR min 1.5 · jarak harga->entry <= 5%")

    setups = load_setups()
    if not setups:
        st.write("Data setup belum tersedia.")
    else:
        items = setups.get("buy_support", [])
        generated = setups.get("generated", "?")

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            st.write(f"{len(items)} saham · generated {generated}")
        with c2:
            min_rr = st.slider("Min RR", 1.5, 5.0, 2.0, 0.1, key="rr_min_support", label_visibility="collapsed")
        with c3:
            view_mode = st.selectbox("View", ["Card", "Table"], key="view_support", label_visibility="collapsed")
        with c4:
            if st.button("Reload", key="reload_support", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        filtered = [x for x in items if x["rr_tp1"] >= min_rr]
        st.write(f"{len(filtered)} saham setelah filter RR >= {min_rr}")

        if not filtered:
            st.write(f"Tidak ada saham dengan RR >= {min_rr}")
        elif view_mode == "Table":
            setup_table(filtered, nama_map)
        else:
            for r in filtered:
                r["_nama"] = nama_map.get(r["kode"], r["kode"])
                st.write(setup_row(r, tipe="support"))

with tab5:
    st.write("**BREAKOUT BUY — SETUP STOP ORDER**")
    st.write("Buy stop di atas resistance · RR min 1.5 · jarak harga->trigger <= 5%")

    setups = load_setups()
    if not setups:
        st.write("Data setup belum tersedia.")
    else:
        items = setups.get("breakout_buy", [])
        generated = setups.get("generated", "?")

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            st.write(f"{len(items)} saham · generated {generated}")
        with c2:
            min_rr = st.slider("Min RR", 1.5, 5.0, 2.0, 0.1, key="rr_min_breakout", label_visibility="collapsed")
        with c3:
            view_mode = st.selectbox("View", ["Card", "Table"], key="view_breakout", label_visibility="collapsed")
        with c4:
            if st.button("Reload", key="reload_breakout", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        filtered = [x for x in items if x["rr_tp1"] >= min_rr]
        st.write(f"{len(filtered)} saham setelah filter RR >= {min_rr}")

        if not filtered:
            st.write(f"Tidak ada saham dengan RR >= {min_rr}")
        elif view_mode == "Table":
            setup_table(filtered, nama_map)
        else:
            for r in filtered:
                r["_nama"] = nama_map.get(r["kode"], r["kode"])
                st.write(setup_row(r, tipe="breakout"))

with tab6:
    rekap_files = list_rekap_files()
    if not rekap_files:
        st.write("Belum ada data performa.")
    else:
        fname = st.selectbox("Pilih file", rekap_files, label_visibility="collapsed")
        bulan_label = fname.replace("Rekap_Trading_", "").replace(".xlsx", "")
        df_rev = load_rekap_sheet(fname, "Review Harian")

        if df_rev is None or df_rev.empty:
            st.write(f"Belum ada data performa di {fname}.")
        else:
            if "P/L %" in df_rev.columns:
                df_rev["P/L %"] = pd.to_numeric(df_rev["P/L %"], errors="coerce")

            st.subheader(f"Ringkasan Bulanan — {bulan_label}")
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

            st.write(f"Total: {n_total} | Tereksekusi: {n_exec} | TP: {n_tp} | SL: {n_sl} | Skip: {n_skip} | Suspended: {n_susp}")
            if n_exec > 0:
                c1, c2, c3 = st.columns(3)
                c1.metric("WIN RATE", f"{wr:.1f}%")
                c2.metric("AVG RETURN", f"{avg:+.2f}%")
                c3.metric("TOTAL RETURN", f"{tot:+.2f}%")

            st.subheader("Ringkasan Harian vs IHSG")
            df_rev["_tgl"] = pd.to_datetime(df_rev["Tanggal"], errors="coerce")
            valid_tgl = df_rev.dropna(subset=["_tgl"])

            if valid_tgl.empty:
                st.write("Kolom Tanggal tidak tersedia.")
            else:
                min_tgl = valid_tgl["_tgl"].min()
                max_tgl = valid_tgl["_tgl"].max()
                start_str = (min_tgl - timedelta(days=7)).strftime("%Y-%m-%d")
                end_str = (max_tgl + timedelta(days=7)).strftime("%Y-%m-%d")
                df_ihsg = get_ihsg_daily(start_str, end_str)

                if df_ihsg is None or df_ihsg.empty:
                    st.write("Data IHSG tidak tersedia.")
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

                        alpha = (port_ret - ihsg_ret if not pd.isna(port_ret) and not pd.isna(ihsg_ret) else np.nan)
                        daily_rows.append({
                            "Tanggal": tgl, "N_exec": n_exec_d,
                            "Portofolio": port_ret, "IHSG": ihsg_ret, "Alpha": alpha,
                        })

                    df_daily = pd.DataFrame(daily_rows)
                    if not df_daily.empty:
                        df_daily = df_daily.sort_values("Tanggal").reset_index(drop=True)
                        for _, r in df_daily.iterrows():
                            tgl_str = pd.Timestamp(r["Tanggal"]).strftime("%d %b (%a)")
                            port = r["Portofolio"]; ihsg_r = r["IHSG"]; alpha = r["Alpha"]
                            port_str = f"{port:+.2f}%" if not pd.isna(port) else "—"
                            ihsg_str = f"{ihsg_r:+.2f}%" if not pd.isna(ihsg_r) else "—"
                            alpha_str = f"{alpha:+.2f}%" if not pd.isna(alpha) else "—"
                            st.write(f"{tgl_str} | {r['N_exec']} trade | Porto: {port_str} | IHSG: {ihsg_str} | Alpha: {alpha_str}")

            st.subheader("Ringkasan Mingguan")
            df_ming = load_rekap_sheet(fname, "Review Mingguan")
            if df_ming is None or df_ming.empty:
                st.write("Belum ada data mingguan di Excel.")
            elif "Info" in df_ming.columns:
                st.write("Belum ada sinyal mingguan di bulan ini.")
            else:
                for _, r in df_ming.iterrows():
                    minggu = str(r.get("Minggu Ke", "")).strip()
                    periode = str(r.get("Rentang Aktual", "") or r.get("Periode", "")).strip()
                    total_pl = r.get("Total P/L %", 0)
                    win_rate = r.get("Win Rate %", 0)
                    st.write(f"{minggu} ({periode}) | Total P/L: {total_pl}% | Win Rate: {win_rate}%")

            with st.expander("Lihat tabel lengkap"):
                df_display = df_rev.copy().drop(columns=["_tgl"], errors="ignore")
                st.dataframe(df_display, use_container_width=True, hide_index=True)