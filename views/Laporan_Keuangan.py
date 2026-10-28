import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title

load_theme()

# ============================================================
# 1. FUNGSI FORMAT (Diletakkan di atas agar bisa dipakai di mana saja)
# ============================================================
def format_idr(val):
    abs_val = abs(val)
    if abs_val >= 1e12: return f"Rp {val/1e12:,.1f} T"
    elif abs_val >= 1e9: return f"Rp {val/1e9:,.1f} B"
    elif abs_val >= 1e6: return f"Rp {val/1e6:,.1f} M"
    else: return f"Rp {val:,.0f}"

# ============================================================
# 2. LOAD DATA
# ============================================================
@st.cache_data(ttl=1800)
def load_clean_q3_data():
    try:
        df = pd.read_csv("data_q3_clean.csv")
        return df
    except FileNotFoundError:
        st.error("⚠️ File `data_q3_clean.csv` tidak ditemukan. Silakan jalankan `python quant/find_q3.py` terlebih dahulu di terminal.")
        st.stop()

# ============================================================
# 3. LOGIKA SCREENER & HARD FILTER
# ============================================================
def run_screener(df):
    d = df.copy()
    
    # Hitung YoY
    d['NI_YoY_Raw'] = (d['NI_YTD'] - d['NI_YTD_LY']) / d['NI_YTD_LY'].abs().replace(0, np.nan)
    d['Rev_YoY_Raw'] = (d['Rev_YTD'] - d['Rev_YTD_LY']) / d['Rev_YTD_LY'].abs().replace(0, np.nan)
    
    # Winsorization (Batas -100% s/d +200%)
    d['NI_YoY'] = np.clip(d['NI_YoY_Raw'], -1.0, 2.0).fillna(-1)
    d['Rev_YoY'] = np.clip(d['Rev_YoY_Raw'], -1.0, 2.0).fillna(-1)
    
    # Margin & Kualitas Laba
    d['NPM_YTD'] = d['NI_YTD'] / d['Rev_YTD'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_YTD_LY'] / d['Rev_YTD_LY'].replace(0, np.nan)
    d['NPM_Change'] = (d['NPM_YTD'] - d['NPM_LY']).fillna(-1)
    
    d['CFO_to_NI'] = d['CFO_YTD'] / d['NI_YTD'].replace(0, np.nan)
    
    # Flag Anomali
    d['Flag_Anomali'] = ""
    d.loc[d['Rev_YoY_Raw'] > 3.0, 'Flag_Anomali'] += "CEK REV, "
    d.loc[d['NPM_Change'].abs() > 0.30, 'Flag_Anomali'] += "CEK MARGIN, "
    
    # Evaluasi Filter (Hard Filters)
    d['is_failed'] = False
    d['fail_reason'] = ""
    
    for idx, row in d.iterrows():
        reason = []
        cfo_valid = row['CFO_YTD'] > 0 # Valid hanya jika CFO > 0
        
        # Filter Laba & Rev (Tangani NaN)
        if pd.isna(row['NI_YoY_Raw']) or row['NI_YoY_Raw'] < 0: 
            reason.append(f"Laba Turun (N/A)" if pd.isna(row['NI_YoY_Raw']) else f"Laba Turun ({row['NI_YoY_Raw']*100:.1f}%)")
        if pd.isna(row['Rev_YoY_Raw']) or row['Rev_YoY_Raw'] < -0.20: 
            reason.append(f"Rev Anjlok (N/A)" if pd.isna(row['Rev_YoY_Raw']) else f"Rev Anjlok ({row['Rev_YoY_Raw']*100:.1f}%)")
        
        # Filter Laba Negatif Mutlak
        if row['NI_YTD'] <= 0:
            reason.append(f"Masih Rugi ({format_idr(row['NI_YTD'])})")
            
        # Filter DER & CFO
        if row['Tipe'] != 'Bank':
            if row['DER'] > 2.0 or row['DER'] < 0:
                reason.append(f"DER Tidak Sehat ({row['DER']:.2f}x)")
            if cfo_valid and row['CFO_to_NI'] < 0.5:
                reason.append(f"CFO Lemah ({row['CFO_to_NI']:.2f}x)")
        
        if reason:
            d.at[idx, 'is_failed'] = True
            d.at[idx, 'fail_reason'] = ", ".join(reason)
            
    df_pass = d[~d['is_failed']].copy()
    df_fail = d[d['is_failed']].copy()
    
    if df_pass.empty: return df_pass, df_fail
    
    # Blended Ranking (50% Global, 50% Sektor)
    def blended_rank(series, sector_series, ascending=True):
        global_rank = series.rank(method='min', pct=True, ascending=ascending) * 100
        sector_ranked = series.groupby(sector_series).rank(method='min', pct=True, ascending=ascending) * 100
        sector_counts = sector_series.map(sector_series.value_counts())
        return np.where(sector_counts >= 3, (global_rank * 0.5) + (sector_ranked * 0.5), global_rank)
    
    d = df_pass
    d['Rank_NI'] = blended_rank(d['NI_YoY'], d['Sektor'], True)
    d['Rank_Rev'] = blended_rank(d['Rev_YoY'], d['Sektor'], True)
    d['Rank_Margin'] = blended_rank(d['NPM_Change'], d['Sektor'], True)
    
    # Bank tidak punya metrik CFO & DER standar, beri rank netral (50)
    d['Rank_Quality'] = blended_rank(d['CFO_to_NI'], d['Sektor'], True)
    d.loc[d['Tipe'] == 'Bank', 'Rank_Quality'] = 50 
    
    d['Rank_ROE'] = blended_rank(d['ROE'], d['Sektor'], True)
    d['Rank_DER'] = blended_rank(d['DER'], d['Sektor'], False)
    d.loc[d['Tipe'] == 'Bank', 'Rank_DER'] = 50 
    
    d['PER_Fixed'] = d['PER'].apply(lambda x: x if x > 0 else np.nan)
    d['Rank_PER'] = blended_rank(d['PER_Fixed'], d['Sektor'], False)
    
    d = d.fillna({'Rank_NI': 0, 'Rank_Rev': 0, 'Rank_Margin': 0, 'Rank_Quality': 0, 'Rank_ROE': 0, 'Rank_DER': 0, 'Rank_PER': 0})
    
    # Skor Akhir
    d['Score_Raw'] = (
        (d['Rank_NI'] * 0.20) + (d['Rank_Rev'] * 0.15) + 
        (d['Rank_Margin'] * 0.20) + (d['Rank_Quality'] * 0.20) + 
        (d['Rank_ROE'] * 0.10) + (d['Rank_DER'] * 0.05) + 
        (d['Rank_PER'] * 0.10)
    )
    
    # Penalti Skor Bank (-10 poin) karena ketiadaan CFO/NPL
    d.loc[d['Tipe'] == 'Bank', 'Score_Raw'] = d.loc[d['Tipe'] == 'Bank', 'Score_Raw'] - 10
    
    # Tie-Breaker
    d = d.sort_values(by=['Score_Raw', 'CFO_to_NI', 'ROE', 'NI_YTD'], ascending=[False, False, False, False]).reset_index(drop=True)
    d['Score'] = d['Score_Raw'].round(2)
    return d, df_fail

# ============================================================
# 4. RENDER KARTU
# ============================================================
def render_card(row, rank):
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
st.markdown(page_header("", "Q3 Fundamental Screener", "Peringkat Fundamental Q3 Berdasarkan Sektor"), unsafe_allow_html=True)

df_raw = load_clean_q3_data()

if df_raw.empty:
    st.warning("Data kosong.")
    st.stop()

# Info Box
st.markdown(
    f'<div style="background:#262626; border:1px solid #404040; border-left:4px solid #ffffff; '
    f'border-radius:8px; padding:12px 16px; margin-bottom:24px; font-size:14px; color:#e5e5e5;">'
    f'<b>INFORMASI:</b> Memproses <b>{len(df_raw)} saham</b> yang terdeteksi sudah memiliki data Q3 2026 dan lolos seleksi awal.'
    f'</div>', 
    unsafe_allow_html=True
)

df_pass, df_fail = run_screener(df_raw)

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
            render_card(row, idx + 1)

    for i, sector in enumerate(sectors):
        with tabs[i + 1]:
            st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
            df_sector = df_pass[df_pass['Sektor'] == sector].head(5)
            for idx, row in df_sector.iterrows():
                render_card(row, idx + 1)

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