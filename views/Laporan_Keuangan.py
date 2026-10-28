import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import pandas as pd
import numpy as np
import json
import glob
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title

load_theme()

# ============================================================
# 1. FUNGSI LOAD BERITA (OPSIONAL, JIKA ADA)
# ============================================================
@st.cache_data(ttl=1800)
def load_news_data():
    """
    Silakan ganti dengan query ke database berita asli Anda.
    Jika tidak dipakai, biarkan kosong (return DataFrame kosong).
    """
    # CONTOH: df = pd.read_parquet("data/news.parquet")
    # return df
    
    # SEMENTARA KOSONG (Karena kita fokus scan semua saham Q3 dari Fundamental)
    return pd.DataFrame(columns=['Kode', 'Headline'])

# ============================================================
# 2. LOAD DATA FUNDAMENTAL (HANYA YANG PUNYA DATA Q3)
# ============================================================
@st.cache_data(ttl=1800)
def load_fundamental_data_q3_only():
    folder_path = "data_fundamental"
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    
    if not json_files:
        st.error(f"⚠️ Tidak ada file JSON di folder `{folder_path}`.")
        st.stop()

    data_list = []
    
    for file in json_files:
        with open(file, 'r', encoding='utf-8') as f:
            try:
                d = json.load(f)
            except Exception:
                continue
                
        kode = d.get("kode")
        sektor = d.get("sektor") or "Unknown"
        
        # Ambil Rasio
        rasio = d.get("rasio_kunci", {})
        roe_raw = rasio.get("roe")
        roe = (roe_raw * 100) if roe_raw is not None and abs(roe_raw) < 1 else roe_raw
        
        der = rasio.get("de")
        per = rasio.get("pe")
        pbv = rasio.get("pb")
        
        arus_kas = d.get("arus_kas", {})
        cfo = arus_kas.get("arus_kas_operasi")
        
        q_rev = d.get("quarterly", {}).get("revenue", {})
        q_ni = d.get("quarterly", {}).get("net_income", {})
        
        years = [int(k.split("-")[0]) for k in q_rev.keys() if "-" in k]
        if not years:
            continue
            
        latest_year = max(years)
        prev_year = latest_year - 1
        
        def get_q(data, year, q): return data.get(f"{year}-Q{q}", 0)
        
        # --- KUNCI PERUBAHAN: CEK APAKAH DATA Q3 ADA ---
        q3_rev = get_q(q_rev, latest_year, 3)
        q3_ni = get_q(q_ni, latest_year, 3)
        
        # Jika Q3 revenue dan net income 0, berarti saham ini belum rilis Q3
        if q3_rev == 0 and q3_ni == 0:
            continue 
            
        # Jika ada, hitung YTD (Q1+Q2+Q3)
        rev_ytd = sum([get_q(q_rev, latest_year, q) for q in range(1, 4)])
        ni_ytd = sum([get_q(q_ni, latest_year, q) for q in range(1, 4)])
        
        rev_ytd_ly = sum([get_q(q_rev, prev_year, q) for q in range(1, 4)])
        ni_ytd_ly = sum([get_q(q_ni, prev_year, q) for q in range(1, 4)])
        
        industri = str(d.get("industri", "")).lower()
        sektor_str = str(sektor).lower()
        is_bank = "bank" in sektor_str or "bank" in industri
        tipe = "Bank" if is_bank else "Non-Bank"
        
        data_list.append({
            'Kode': kode, 'Sektor': sektor, 'Tipe': tipe,
            'NI_YTD': ni_ytd, 'NI_YTD_LY': ni_ytd_ly,
            'Rev_YTD': rev_ytd, 'Rev_YTD_LY': rev_ytd_ly,
            'CFO_YTD': cfo if cfo is not None else np.nan,
            'ROE': roe if roe else 0, 'DER': der if der else 0,
            'PER': per if per else 0, 'PBV': pbv if pbv else 0,
            'Avg_Value_Daily': 2_000_000_000
        })
        
    df = pd.DataFrame(data_list)
    if df.empty:
        return df
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

# ============================================================
# 3. LOGIKA SCREENER & HARD FILTER
# ============================================================
def run_screener(df):
    d = df.copy()
    
    # Hitung YoY Murni (Q1+Q2+Q3 vs Q1+Q2+Q3 tahun lalu)
    d['NI_YoY_Raw'] = (d['NI_YTD'] - d['NI_YTD_LY']) / d['NI_YTD_LY'].abs().replace(0, np.nan)
    d['Rev_YoY_Raw'] = (d['Rev_YTD'] - d['Rev_YTD_LY']) / d['Rev_YTD_LY'].abs().replace(0, np.nan)
    
    d['NI_YoY'] = np.clip(d['NI_YoY_Raw'], -1.0, 2.0).fillna(-1)
    d['Rev_YoY'] = np.clip(d['Rev_YoY_Raw'], -1.0, 2.0).fillna(-1)
    
    d['NPM_YTD'] = d['NI_YTD'] / d['Rev_YTD'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_YTD_LY'] / d['Rev_YTD_LY'].replace(0, np.nan)
    d['NPM_Change'] = (d['NPM_YTD'] - d['NPM_LY']).fillna(-1)
    
    d['CFO_to_NI'] = d['CFO_YTD'] / d['NI_YTD'].replace(0, np.nan)
    
    d['Flag_Anomali'] = ""
    d.loc[d['Rev_YoY_Raw'] > 3.0, 'Flag_Anomali'] += "CEK REV, "
    d.loc[d['NPM_Change'].abs() > 0.30, 'Flag_Anomali'] += "CEK MARGIN, "
    d.loc[d['NI_YTD_LY'] <= 0, 'Flag_Anomali'] += "RUGI THN LALU, "
    
    # Evaluasi Filter
    d['is_failed'] = False
    d['fail_reason'] = ""
    
    for idx, row in d.iterrows():
        reason = []
        cfo_valid = row['CFO_YTD'] > 0
        
        if row['NI_YoY_Raw'] < 0: 
            reason.append(f"Laba Turun ({row['NI_YoY_Raw']*100:.1f}%)")
        if row['Rev_YoY_Raw'] < -0.20: 
            reason.append(f"Rev Anjlok ({row['Rev_YoY_Raw']*100:.1f}%)")
        if row['DER'] > 2.0 and row['Tipe'] != 'Bank': 
            reason.append(f"DER Tinggi ({row['DER']:.2f}x)")
        if cfo_valid and row['CFO_to_NI'] < 0.5 and row['Tipe'] != 'Bank': 
            reason.append(f"CFO Lemah ({row['CFO_to_NI']:.2f}x)")
        
        if reason:
            d.at[idx, 'is_failed'] = True
            d.at[idx, 'fail_reason'] = ", ".join(reason)
            
    df_pass = d[~d['is_failed']].copy()
    df_fail = d[d['is_failed']].copy()
    
    if df_pass.empty: return df_pass, df_fail
    
    # Ranking
    def blended_rank(series, sector_series, ascending=True):
        global_rank = series.rank(method='min', pct=True, ascending=ascending) * 100
        sector_ranked = series.groupby(sector_series).rank(method='min', pct=True, ascending=ascending) * 100
        sector_counts = sector_series.map(sector_series.value_counts())
        return np.where(sector_counts >= 3, (global_rank * 0.5) + (sector_ranked * 0.5), global_rank)
    
    d = df_pass
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
    
    d.loc[d['Tipe'] == 'Bank', 'Score_Raw'] = d.loc[d['Tipe'] == 'Bank', 'Score_Raw'] - 10
    
    d = d.sort_values(by=['Score_Raw', 'CFO_to_NI', 'ROE', 'NI_YTD'], ascending=[False, False, False, False]).reset_index(drop=True)
    d['Score'] = d['Score_Raw'].round(2)
    return d, df_fail

# ============================================================
# 4. FUNGSI FORMAT & RENDER KARTU
# ============================================================
def format_idr(val):
    abs_val = abs(val)
    if abs_val >= 1e12: return f"Rp {val/1e12:,.1f} T"
    elif abs_val >= 1e9: return f"Rp {val/1e9:,.1f} B"
    elif abs_val >= 1e6: return f"Rp {val/1e6:,.1f} M"
    else: return f"Rp {val:,.0f}"

def render_card(row, rank, headline=None):
    ni_ytd_rp = format_idr(row['NI_YTD'])
    ni_yoy = f"{row['NI_YoY']*100:+.1f}%" if row['NI_YoY'] != -1 else "N/A"
    rev_yoy = f"{row['Rev_YoY']*100:+.1f}%" if row['Rev_YoY'] != -1 else "N/A"
    npm_chg = f"{row['NPM_Change']*100:+.2f}%" if row['NPM_Change'] != -1 else "N/A"
    
    cfo_ni = f"{row['CFO_to_NI']:.2f}x" if row['Tipe'] != 'Bank' and row['CFO_to_NI'] > 0 else "N/A"
    roe = f"{row['ROE']:.1f}%" if row['ROE'] else "N/A"
    der = f"{row['DER']:.2f}x" if row['Tipe'] != 'Bank' else "N/A (Bank)"
    per = f"{row['PER']:.1f}x" if row['PER'] > 0 else "N/A"
    pbv = f"{row['PBV']:.2f}x" if row['PBV'] > 0 else "N/A"
    
    flag_html = ""
    if row['Tipe'] == 'Bank': 
        flag_html += '<span style="background:#e5e5e5; color:#0a0a0a; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">BANK</span>'
    if row['Tipe'] != 'Bank' and row['CFO_to_NI'] < 0.8 and row['CFO_to_NI'] > 0:
        flag_html += '<span style="background:#737373; color:#ffffff; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">⚠ CFO LEMAH</span>'
    if row['Flag_Anomali']:
        flag_html += f'<span style="background:#525252; color:#ffffff; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">⚠ {row["Flag_Anomali"].strip(", ")}</span>'
    
    # Render Headline jika ada
    headline_html = ""
    if headline:
        headline_html = f'<div style="font-size:13px; color:#e5e5e5; font-style:italic; border-left:2px solid #525252; padding-left:8px; margin-top:8px;">"{headline}"</div>'
    
    st.markdown(
        f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; '
        f'border-radius:12px; padding:20px 24px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; '
        f'box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'
        
        f'<div style="min-width: 250px; flex: 1;">'
        f'<div style="font-size:12px; color:#737373; font-weight:800; letter-spacing:1px; margin-bottom:4px;">RANK #{rank}</div>'
        f'<div style="font-size:26px; font-weight:800; color:#ffffff; margin-bottom:4px;">{row["Kode"]}</div>'
        f'<div style="font-size:13px; color:#a3a3a3; margin-bottom:8px;">{row["Sektor"]}</div>'
        f'<div style="display:flex; flex-wrap:wrap; gap:4px;">{flag_html}</div>'
        f'{headline_html}'
        f'</div>'
        
        f'<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px 24px; flex:1; max-width:700px;">'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba YTD (Q3)</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_ytd_rp}</div></div>'
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
# 5. UI RENDERING UTAMA
# ============================================================
st.markdown(page_header("", "Q3 Fundamental Screener", "Menampilkan Seluruh Saham yang Telah Rilis Laporan Q3"), unsafe_allow_html=True)

# Load Berita (Opsional)
df_news = load_news_data()

# Load Fundamental (Hanya yang ada Q3)
df_raw = load_fundamental_data_q3_only()

if df_raw.empty:
    st.warning("⚠️ Tidak ada satu pun saham di database fundamental Anda yang memiliki data Q3. Pastikan scraper sudah mengambil data Q3.")
    st.stop()

# Tampilkan Info
st.markdown(
    f'<div style="background:#262626; border:1px solid #404040; border-left:4px solid #ffffff; '
    f'border-radius:8px; padding:12px 16px; margin-bottom:24px; font-size:14px; color:#e5e5e5;">'
    f'<b>INFORMASI:</b> Ditemukan <b>{len(df_raw)} saham</b> di database Anda yang sudah memiliki data laporan Q3. '
    f'Sistem akan memproses seluruh saham tersebut.'
    f'</div>', 
    unsafe_allow_html=True
)

# Jalankan Screener
df_pass, df_fail = run_screener(df_raw)

# Fungsi bantu ambil berita (jika ada)
def get_headline(kode):
    if df_news.empty: return None
    news = df_news[df_news['Kode'] == kode]['Headline'].values
    return news[0] if len(news) > 0 else None

# 1. TAMPILKAN YANG LOLOS
if df_pass.empty:
    st.warning("Tidak ada saham Q3 yang lolos Hard Filter.")
else:
    sectors = df_pass['Sektor'].unique().tolist()
    tab_names = ["Semua Sektor"] + sectors
    tabs = st.tabs(tab_names)

    with tabs[0]:
        st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
        for idx, row in df_pass.head(10).iterrows():
            render_card(row, idx + 1, get_headline(row['Kode']))

    for i, sector in enumerate(sectors):
        with tabs[i + 1]:
            st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
            df_sector = df_pass[df_pass['Sektor'] == sector].head(5)
            for idx, row in df_sector.iterrows():
                render_card(row, idx + 1, get_headline(row['Kode']))

# 2. TAMPILKAN YANG GUGUR
if not df_fail.empty:
    st.markdown(section_title("Saham yang Gugur (Hard Filters)", "Saham Q3 yang gagal masuk kriteria fundamental"), unsafe_allow_html=True)
    for _, t in df_fail.iterrows():
        st.markdown(
            f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
            f'<div style="font-size:14px; font-weight:700; color:#ffffff;">{t["Kode"]} <span style="font-size:11px; color:#a3a3a3; font-weight:400; margin-left:8px;">({t["Sektor"]})</span></div>'
            f'<div style="font-size:13px; color:#a3a3a3;">Gugur karena: <b style="color:#fff;">{t["fail_reason"]}</b></div>'
            f'</div>', 
            unsafe_allow_html=True
        )

# Debug
with st.expander("🔍 Debug Data Fundamental Q3"):
    st.write("Data yang diproses:")
    st.dataframe(df_raw[['Kode', 'Sektor', 'NI_YTD', 'NI_YTD_LY', 'Rev_YTD', 'CFO_YTD', 'DER', 'PER', 'ROE']])