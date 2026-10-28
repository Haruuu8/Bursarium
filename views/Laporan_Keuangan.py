import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import pandas as pd
import numpy as np
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title

load_theme()

# ============================================================
# 1. LOAD DATA DINAMIS (YTD) DARI JSON
# ============================================================
@st.cache_data(ttl=1800)
def load_fundamental_data():
    folder_path = "data_fundamental"
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    
    if not json_files:
        st.error(f"⚠️ Tidak ada file JSON di folder `{folder_path}`. Pastikan scraper fundamental sudah dijalankan.")
        st.stop()

    data_list = []
    latest_q_global = 0 # Untuk label UI
    
    for file in json_files:
        with open(file, 'r', encoding='utf-8') as f:
            try:
                d = json.load(f)
            except Exception:
                continue
                
        kode = d.get("kode")
        sektor = d.get("sektor") or "Unknown"
        
        # Ekstrak Rasio
        rasio = d.get("rasio_kunci", {})
        roe = rasio.get("roe")
        der = rasio.get("de")
        per = rasio.get("pe")
        pbv = rasio.get("pb")
        
        # Ekstrak CFO
        arus_kas = d.get("arus_kas", {})
        cfo = arus_kas.get("arus_kas_operasi")
        
        # Ekstrak Kuartalan
        q_rev = d.get("quarterly", {}).get("revenue", {})
        q_ni = d.get("quarterly", {}).get("net_income", {})
        
        years = [int(k.split("-")[0]) for k in q_rev.keys() if "-" in k]
        if not years:
            continue
            
        latest_year = max(years)
        prev_year = latest_year - 1
        
        # Cari Kuartal Terakhir yang Tersedia (Misal: Q2)
        q_list = [int(k.split("-Q")[1]) for k in q_rev.keys() if k.startswith(f"{latest_year}-Q")]
        if not q_list:
            continue
        max_q = max(q_list)
        latest_q_global = max(latest_q_global, max_q) # Simpan untuk judul UI
        
        # Fungsi Helper
        def get_q(data, year, q): return data.get(f"{year}-Q{q}", 0)
        
        # Hitung YTD (Kumulatif) untuk Tahun Ini dan Tahun Lalu
        rev_ytd = sum([get_q(q_rev, latest_year, q) for q in range(1, max_q + 1)])
        ni_ytd = sum([get_q(q_ni, latest_year, q) for q in range(1, max_q + 1)])
        
        rev_ytd_ly = sum([get_q(q_rev, prev_year, q) for q in range(1, max_q + 1)])
        ni_ytd_ly = sum([get_q(q_ni, prev_year, q) for q in range(1, max_q + 1)])
        
        # Deteksi Bank
        industri = str(d.get("industri", "")).lower()
        sektor_str = str(sektor).lower()
        is_bank = "bank" in sektor_str or "bank" in industri
        tipe = "Bank" if is_bank else "Non-Bank"
        
        avg_val = 2_000_000_000 # Default likuiditas
        
        data_list.append({
            'Kode': kode,
            'Sektor': sektor,
            'Tipe': tipe,
            'NI_YTD': ni_ytd,
            'NI_YTD_LY': ni_ytd_ly,
            'Rev_YTD': rev_ytd,
            'Rev_YTD_LY': rev_ytd_ly,
            'CFO_YTD': cfo if cfo else 0,
            'ROE': roe if roe else 0,
            'DER': der if der else 0,
            'PER': per if per else 0,
            'PBV': pbv if pbv else 0,
            'Avg_Value_Daily': avg_val,
            'Max_Q': max_q
        })
        
    df = pd.DataFrame(data_list)
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    return df, latest_q_global

# ============================================================
# 2. LOGIKA SCREENER
# ============================================================
def run_screener(df):
    d = df.copy()
    
    # YoY Growth
    d['NI_YoY_Raw'] = (d['NI_YTD'] - d['NI_YTD_LY']) / d['NI_YTD_LY'].abs().replace(0, np.nan)
    d['Rev_YoY_Raw'] = (d['Rev_YTD'] - d['Rev_YTD_LY']) / d['Rev_YTD_LY'].abs().replace(0, np.nan)
    
    d['NI_YoY'] = np.clip(d['NI_YoY_Raw'], -1.0, 2.0).fillna(-1)
    d['Rev_YoY'] = np.clip(d['Rev_YoY_Raw'], -1.0, 2.0).fillna(-1)
    
    # Margin
    d['NPM_YTD'] = d['NI_YTD'] / d['Rev_YTD'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_YTD_LY'] / d['Rev_YTD_LY'].replace(0, np.nan)
    d['NPM_Change'] = (d['NPM_YTD'] - d['NPM_LY']).fillna(-1)
    
    # Kualitas Laba
    d['CFO_to_NI'] = d['CFO_YTD'] / d['NI_YTD'].replace(0, np.nan)
    
    # FLAGS ANOMALI
    d['Flag_Anomali'] = ""
    d.loc[d['Rev_YoY_Raw'] > 3.0, 'Flag_Anomali'] += "CEK REV, "
    d.loc[d['NPM_Change'].abs() > 0.30, 'Flag_Anomali'] += "CEK MARGIN, "
    d.loc[d['NI_YTD_LY'] <= 0, 'Flag_Anomali'] += "RUGI THN LALU, "
    
    # HARD FILTERS
    d = d[
        (d['NI_YoY_Raw'] >= 0) & 
        (d['Rev_YoY_Raw'] >= -0.20) & 
        ((d['DER'] <= 2.0) | (d['Tipe'] == 'Bank')) &
        ((d['CFO_to_NI'] >= 0.5) | (d['Tipe'] == 'Bank')) &
        (d['Avg_Value_Daily'] > 1_000_000_000)
    ].copy()
    
    if d.empty: return d
    
    def blended_rank(series, sector_series, ascending=True):
        global_rank = series.rank(method='min', pct=True, ascending=ascending) * 100
        sector_ranked = series.groupby(sector_series).rank(method='min', pct=True, ascending=ascending) * 100
        sector_counts = sector_series.map(sector_series.value_counts())
        return np.where(sector_counts >= 3, (global_rank * 0.5) + (sector_ranked * 0.5), global_rank)
    
    d['Rank_NI'] = blended_rank(d['NI_YoY'], d['Sektor'], True)
    d['Rank_Rev'] = blended_rank(d['Rev_YoY'], d['Sektor'], True)
    d['Rank_Margin'] = blended_rank(d['NPM_Change'], d['Sektor'], True)
    
    d['Rank_Quality'] = blended_rank(d['CFO_to_NI'], d['Sektor'], True)
    d.loc[d['Tipe'] == 'Bank', 'Rank_Quality'] = 50 
    
    d['Rank_ROE'] = blended_rank(d['ROE'], d['Sektor'], True)
    
    d['Rank_DER'] = blended_rank(d['DER'], d['Sektor'], False)
    d.loc[d['Tipe'] == 'Bank', 'Rank_DER'] = 50 
    
    d['PER_Fixed'] = d['PER'].apply(lambda x: x if x > 0 else np.nan)
    d['Rank_PER'] = blended_rank(d['PER_Fixed'], d['Sektor'], False)
    
    d = d.fillna({'Rank_NI': 0, 'Rank_Rev': 0, 'Rank_Margin': 0, 'Rank_Quality': 0, 'Rank_ROE': 0, 'Rank_DER': 0, 'Rank_PER': 0})
    
    d['Score_Raw'] = (
        (d['Rank_NI'] * 0.20) + (d['Rank_Rev'] * 0.15) + 
        (d['Rank_Margin'] * 0.20) + (d['Rank_Quality'] * 0.20) + 
        (d['Rank_ROE'] * 0.10) + (d['Rank_DER'] * 0.05) + 
        (d['Rank_PER'] * 0.10)
    )
    
    # Penalti Bank
    d.loc[d['Tipe'] == 'Bank', 'Score_Raw'] = d.loc[d['Tipe'] == 'Bank', 'Score_Raw'] - 10
    
    d = d.sort_values(by=['Score_Raw', 'CFO_to_NI', 'ROE', 'NI_YTD'], ascending=[False, False, False, False]).reset_index(drop=True)
    d['Score'] = d['Score_Raw'].round(2)
    return d

# ============================================================
# 3. FUNGSI FORMAT & RENDER KARTU
# ============================================================
def format_idr(val):
    abs_val = abs(val)
    if abs_val >= 1e12: return f"Rp {val/1e12:,.1f} T"
    elif abs_val >= 1e9: return f"Rp {val/1e9:,.1f} B"
    elif abs_val >= 1e6: return f"Rp {val/1e6:,.1f} M"
    else: return f"Rp {val:,.0f}"

def render_card(row, rank, label_q):
    ni_ytd_rp = format_idr(row['NI_YTD'])
    
    ni_yoy = f"{row['NI_YoY']*100:+.1f}%" if row['NI_YoY'] != -1 else "N/A"
    rev_yoy = f"{row['Rev_YoY']*100:+.1f}%" if row['Rev_YoY'] != -1 else "N/A"
    npm_chg = f"{row['NPM_Change']*100:+.2f}%" if row['NPM_Change'] != -1 else "N/A"
    
    cfo_ni = f"{row['CFO_to_NI']:.2f}x" if row['Tipe'] != 'Bank' else "N/A (Bank)"
    roe = f"{row['ROE']:.1f}%" if row['ROE'] else "N/A"
    der = f"{row['DER']:.2f}x" if row['Tipe'] != 'Bank' else "N/A (Bank)"
    per = f"{row['PER']:.1f}x" if row['PER'] > 0 else "N/A"
    pbv = f"{row['PBV']:.2f}x" if row['PBV'] > 0 else "N/A"
    
    flag_html = ""
    if row['Tipe'] == 'Bank': 
        flag_html += '<span style="background:#e5e5e5; color:#0a0a0a; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">BANK</span>'
    if row['Tipe'] != 'Bank' and row['CFO_to_NI'] < 0.8:
        flag_html += '<span style="background:#737373; color:#ffffff; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">⚠ CFO LEMAH</span>'
    if row['Flag_Anomali']:
        flag_html += f'<span style="background:#525252; color:#ffffff; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">⚠ {row["Flag_Anomali"].strip(", ")}</span>'
    
    st.markdown(
        f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; '
        f'border-radius:12px; padding:20px 24px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; '
        f'box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'
        
        f'<div style="min-width: 180px;">'
        f'<div style="font-size:12px; color:#737373; font-weight:800; letter-spacing:1px; margin-bottom:4px;">RANK #{rank}</div>'
        f'<div style="font-size:26px; font-weight:800; color:#ffffff; margin-bottom:4px;">{row["Kode"]}</div>'
        f'<div style="font-size:13px; color:#a3a3a3; margin-bottom:8px;">{row["Sektor"]}</div>'
        f'<div style="display:flex; flex-wrap:wrap; gap:4px;">{flag_html}</div>'
        f'</div>'
        
        f'<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px 24px; flex:1; max-width:700px;">'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba YTD ({label_q})</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_ytd_rp}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Rev YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{rev_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Δ Margin</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{npm_chg}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Kualitas Laba</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{cfo_ni}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">ROE</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{roe}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">DER</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{der}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">PER / PBV</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{per} / {pbv}</div></div>'
        f'</div>'
        
        f'<div style="text-align:center; background:#262626; border:1px solid #404040; border-radius:8px; padding:12px 24px; min-width:110px;">'
        f'<div style="font-size:11px; color:#a3a3a3; text-transform:uppercase; font-weight:700; letter-spacing:1px;">SCORE</div>'
        f'<div style="font-size:32px; font-weight:800; color:#ffffff; line-height:1.1;">{row["Score"]}</div>'
        f'</div>'
        
        f'</div>', 
        unsafe_allow_html=True
    )

# ============================================================
# 4. UI RENDERING UTAMA
# ============================================================
st.markdown(page_header("", "Financial Screener", "Peringkat Fundamental (YTD) Berdasarkan Sektor"), unsafe_allow_html=True)

# LOAD DATA
df_raw, latest_q_global = load_fundamental_data()
label_q = f"Q{latest_q_global}")

# Info Box untuk Q
st.markdown(
    f'<div style="background:#262626; border:1px solid #404040; border-left:4px solid #ffffff; '
    f'border-radius:8px; padding:12px 16px; margin-bottom:24px; font-size:14px; color:#e5e5e5;">'
    f'<b>INFORMASI DATA:</b> Data terbaru Anda tersedia hingga kuartal <b>Q{latest_q_global}</b>. '
    f'Sistem secara otomatis membandingkan Kumulatif (YTD) tahun ini vs Kumulatif tahun lalu pada periode yang sama.'
    f'</div>', 
    unsafe_allow_html=True
)

# JALANKAN SCREENER
df_result = run_screener(df_raw)

# Debug Expander
with st.expander("🔍 Debug Data (Cek jika ada saham yang aneh)"):
    st.write("Data Mentah Sebelum Filter:")
    st.dataframe(df_raw[['Kode', 'Sektor', 'NI_YTD', 'NI_YTD_LY', 'Rev_YTD', 'CFO_YTD', 'DER']].head(20))

if df_result.empty:
    st.warning("Tidak ada saham yang lolos Hard Filters. Silakan cek data mentah di menu Debug di atas (kemungkinan nilai YoY minus atau CFO kurang dari 0.5).")
    st.stop()

sectors = df_result['Sektor'].unique().tolist()
tab_names = ["Semua Sektor"] + sectors
tabs = st.tabs(tab_names)

with tabs[0]:
    st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
    top_10 = df_result.head(10)
    for idx, row in top_10.iterrows():
        render_card(row, idx + 1, label_q)

for i, sector in enumerate(sectors):
    with tabs[i + 1]:
        st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
        df_sector = df_result[df_result['Sektor'] == sector].head(5)
        if df_sector.empty:
            st.info(f"Tidak ada saham sektor {sector} yang lolos filter.")
        else:
            for idx, row in df_sector.iterrows():
                render_card(row, idx + 1, label_q)

# --- DISQUALIFIED ---
st.markdown(section_title("Saham yang Gugur (Hard Filters)", "Gagal memenuhi syarat: Laba Turun, Rev Anjlok >20%, DER > 2, atau CFO < 0.5x"), unsafe_allow_html=True)

df_raw['NI_YoY'] = (df_raw['NI_YTD'] - df_raw['NI_YTD_LY']) / df_raw['NI_YTD_LY'].abs().replace(0, np.nan)
df_raw['Rev_YoY'] = (df_raw['Rev_YTD'] - df_raw['Rev_YTD_LY']) / df_raw['Rev_YTD_LY'].abs().replace(0, np.nan)
df_raw['CFO_to_NI'] = df_raw['CFO_YTD'] / df_raw['NI_YTD'].replace(0, np.nan)

failed = df_raw[
    (df_raw['NI_YoY'] < 0) | 
    (df_raw['Rev_YoY'] < -0.20) | 
    ((df_raw['DER'] > 2.0) & (df_raw['Tipe'] != 'Bank')) | 
    ((df_raw['CFO_to_NI'] < 0.5) & (df_raw['Tipe'] != 'Bank'))
].copy()

for _, t in failed.sort_values('Kode').head(10).iterrows():
    reason = []
    if t['NI_YoY'] < 0: reason.append(f"Laba Turun ({t['NI_YoY']*100:.1f}%)")
    if t['Rev_YoY'] < -0.20: reason.append(f"Rev Anjlok ({t['Rev_YoY']*100:.1f}%)")
    if t['DER'] > 2.0 and t['Tipe'] != 'Bank': reason.append(f"DER Tinggi ({t['DER']:.2f}x)")
    if t['CFO_to_NI'] < 0.5 and t['Tipe'] != 'Bank': reason.append(f"CFO Lemah ({t['CFO_to_NI']:.2f}x)")
    
    st.markdown(
        f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
        f'<div style="font-size:14px; font-weight:700; color:#ffffff;">{t["Kode"]} <span style="font-size:11px; color:#a3a3a3; font-weight:400; margin-left:8px;">({t["Sektor"]})</span></div>'
        f'<div style="font-size:13px; color:#a3a3a3;">Gugur karena: <b style="color:#fff;">{", ".join(reason)}</b></div>'
        f'</div>', 
        unsafe_allow_html=True
    )