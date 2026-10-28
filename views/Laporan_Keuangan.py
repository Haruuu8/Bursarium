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
# 1. LOAD DATA DARI FILE JSON HASIL SCRAPER
# ============================================================
@st.cache_data(ttl=1800)
def load_fundamental_data():
    folder_path = "data_fundamental"
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    
    if not json_files:
        st.error(f"⚠️ Tidak ada file JSON di folder `{folder_path}`. Pastikan scraper fundamental sudah dijalankan.")
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
        
        # Ekstrak Rasio Kunci
        rasio = d.get("rasio_kunci", {})
        roe = rasio.get("roe")
        der = rasio.get("de")
        per = rasio.get("pe")
        pbv = rasio.get("pb")
        
        # Ekstrak Arus Kas (CFO)
        arus_kas = d.get("arus_kas", {})
        cfo = arus_kas.get("arus_kas_operasi")
        
        # Ekstrak Data Kuartalan
        q_rev = d.get("quarterly", {}).get("revenue", {})
        q_ni = d.get("quarterly", {}).get("net_income", {})
        
        # Cari tahun terbaru yang ada di data (misal 2026 atau 2025)
        years = [int(k.split("-")[0]) for k in q_rev.keys() if "-" in k]
        if not years:
            continue
        latest_year = max(years)
        prev_year = latest_year - 1
        
        # Fungsi bantu ambil nilai, default 0
        def get_q(data, year, q):
            return data.get(f"{year}-Q{q}", 0)
            
        # Hitung Kumulatif 9 Bulan (Q1 + Q2 + Q3)
        rev_9m = get_q(q_rev, latest_year, 1) + get_q(q_rev, latest_year, 2) + get_q(q_rev, latest_year, 3)
        ni_9m = get_q(q_ni, latest_year, 1) + get_q(q_ni, latest_year, 2) + get_q(q_ni, latest_year, 3)
        
        # Hitung Kumulatif 6 Bulan (Q1 + Q2)
        rev_6m = get_q(q_rev, latest_year, 1) + get_q(q_rev, latest_year, 2)
        ni_6m = get_q(q_ni, latest_year, 1) + get_q(q_ni, latest_year, 2)
        
        # Ambil data Q3 Tahun Lalu
        rev_q3_ly = get_q(q_rev, prev_year, 3)
        ni_q3_ly = get_q(q_ni, prev_year, 3)
        
        # Tentukan Tipe (Bank / Non-Bank)
        industri = str(d.get("industri", "")).lower()
        sektor_str = str(sektor).lower()
        is_bank = "bank" in sektor_str or "bank" in industri
        tipe = "Bank" if is_bank else "Non-Bank"
        
        # Coba ambil nilai transaksi harian dari file OHLCV jika ada (opsional)
        # Jika tidak ada, kita beri nilai default besar agar tidak gugur di filter likuiditas
        avg_val = 2_000_000_000 
        
        data_list.append({
            'Kode': kode,
            'Sektor': sektor,
            'Tipe': tipe,
            'NI_9M': ni_9m,
            'NI_6M': ni_6m,
            'NI_Q3_LY': ni_q3_ly,
            'Rev_9M': rev_9m,
            'Rev_6M': rev_6m,
            'Rev_Q3_LY': rev_q3_ly,
            'CFO_9M': cfo if cfo else 0,
            'ROE': roe if roe else 0,
            'DER': der if der else 0,
            'PER': per if per else 0,
            'PBV': pbv if pbv else 0,
            'Avg_Value_Daily': avg_val
        })
        
    df = pd.DataFrame(data_list)
    
    # Bersihkan data NaN / Inf
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    return df

# ============================================================
# 2. LOGIKA SCREENER (SAMA SEPERTI SEBELUMNYA)
# ============================================================
def run_screener(df):
    d = df.copy()
    
    d['NI_Q3'] = d['NI_9M'] - d['NI_6M']
    d['Rev_Q3'] = d['Rev_9M'] - d['Rev_6M']
    
    d['NI_YoY_Raw'] = (d['NI_Q3'] - d['NI_Q3_LY']) / d['NI_Q3_LY'].abs().replace(0, np.nan)
    d['Rev_YoY_Raw'] = (d['Rev_Q3'] - d['Rev_Q3_LY']) / d['Rev_Q3_LY'].abs().replace(0, np.nan)
    
    d['NI_YoY'] = np.clip(d['NI_YoY_Raw'], -1.0, 2.0).fillna(-1)
    d['Rev_YoY'] = np.clip(d['Rev_YoY_Raw'], -1.0, 2.0).fillna(-1)
    
    d['NPM_Q3'] = d['NI_Q3'] / d['Rev_Q3'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_Q3_LY'] / d['Rev_Q3_LY'].replace(0, np.nan)
    d['NPM_Change'] = (d['NPM_Q3'] - d['NPM_LY']).fillna(-1)
    d['CFO_to_NI'] = d['CFO_9M'] / d['NI_9M'].replace(0, np.nan)
    
    d['Flag_Anomali'] = ""
    d.loc[d['Rev_YoY_Raw'] > 3.0, 'Flag_Anomali'] += "CEK REV, "
    d.loc[d['NPM_Change'].abs() > 0.30, 'Flag_Anomali'] += "CEK MARGIN, "
    d.loc[d['NI_Q3_LY'] <= 0, 'Flag_Anomali'] += "RUGI THN LALU, "
    
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
    
    # Penalti Skor Bank
    d.loc[d['Tipe'] == 'Bank', 'Score_Raw'] = d.loc[d['Tipe'] == 'Bank', 'Score_Raw'] - 10
    
    d = d.sort_values(by=['Score_Raw', 'CFO_to_NI', 'ROE', 'NI_Q3'], ascending=[False, False, False, False]).reset_index(drop=True)
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

def render_card(row, rank):
    ni_q3_rp = format_idr(row['NI_Q3'])
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
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba Q3</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_q3_rp}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba Q3 YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Rev Q3 YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{rev_yoy}</div></div>'
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
st.markdown(page_header("", "Financial Screener", "Peringkat Fundamental Q3 Berdasarkan Sektor (Data IDX)"), unsafe_allow_html=True)

# LOAD DATA
df_raw = load_fundamental_data()

# JALANKAN SCREENER
df_result = run_screener(df_raw)

if df_result.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada saham yang lolos syarat gugur (Hard Filters) berdasarkan data fundamental Anda.</div>', unsafe_allow_html=True)
    st.stop()

sectors = df_result['Sektor'].unique().tolist()
tab_names = ["Semua Sektor"] + sectors
tabs = st.tabs(tab_names)

with tabs[0]:
    st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
    top_10 = df_result.head(10)
    for idx, row in top_10.iterrows():
        render_card(row, idx + 1)

for i, sector in enumerate(sectors):
    with tabs[i + 1]:
        st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
        df_sector = df_result[df_result['Sektor'] == sector].head(5)
        if df_sector.empty:
            st.info(f"Tidak ada saham sektor {sector} yang lolos filter.")
        else:
            for idx, row in df_sector.iterrows():
                render_card(row, idx + 1)

# --- DISQUALIFIED ---
st.markdown(section_title("Saham yang Gugur (Hard Filters)", "Gagal memenuhi syarat: Laba Q3 Turun, Rev Q3 Anjlok >20%, DER > 2, atau CFO < 0.5x"), unsafe_allow_html=True)

df_raw['NI_Q3'] = df_raw['NI_9M'] - df_raw['NI_6M']
df_raw['Rev_Q3'] = df_raw['Rev_9M'] - df_raw['Rev_6M']
df_raw['CFO_to_NI'] = df_raw['CFO_9M'] / df_raw['NI_9M'].replace(0, np.nan)
df_raw['NI_YoY'] = (df_raw['NI_Q3'] - df_raw['NI_Q3_LY']) / df_raw['NI_Q3_LY'].abs().replace(0, np.nan)
df_raw['Rev_YoY'] = (df_raw['Rev_Q3'] - df_raw['Rev_Q3_LY']) / df_raw['Rev_Q3_LY'].abs().replace(0, np.nan)

failed = df_raw[
    (df_raw['NI_YoY'] < 0) | 
    (df_raw['Rev_YoY'] < -0.20) | 
    ((df_raw['DER'] > 2.0) & (df_raw['Tipe'] != 'Bank')) | 
    ((df_raw['CFO_to_NI'] < 0.5) & (df_raw['Tipe'] != 'Bank'))
].copy()

# Tampilkan 10 teratas yang gugur
for _, t in failed.sort_values('Kode').head(10).iterrows():
    reason = []
    if t['NI_YoY'] < 0: reason.append(f"Laba Q3 Turun ({t['NI_YoY']*100:.1f}%)")
    if t['Rev_YoY'] < -0.20: reason.append(f"Rev Q3 Anjlok ({t['Rev_YoY']*100:.1f}%)")
    if t['DER'] > 2.0 and t['Tipe'] != 'Bank': reason.append(f"DER Tinggi ({t['DER']:.2f}x)")
    if t['CFO_to_NI'] < 0.5 and t['Tipe'] != 'Bank': reason.append(f"Kualitas Laba Lemah ({t['CFO_to_NI']:.2f}x)")
    
    st.markdown(
        f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
        f'<div style="font-size:14px; font-weight:700; color:#ffffff;">{t["Kode"]} <span style="font-size:11px; color:#a3a3a3; font-weight:400; margin-left:8px;">({t["Sektor"]})</span></div>'
        f'<div style="font-size:13px; color:#a3a3a3;">Gugur karena: <b style="color:#fff;">{", ".join(reason)}</b></div>'
        f'</div>', 
        unsafe_allow_html=True
    )