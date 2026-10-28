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
# 1. LOAD DATA DARI DATABASE ASLI ANDA
# ============================================================
@st.cache_data(ttl=1800)
def load_financial_data():
    # ------------------------------------------------------------------
    # BAGIAN 1: SILAKAN UBAH QUERY INI SESUAI DATABASE ANDA
    # ------------------------------------------------------------------
    try:
        # CONTOH A: Jika file Parquet ada di folder 'data'
        # df = pd.read_parquet("data/laporan_keuangan.parquet")
        
        # CONTOH B: Jika dari Supabase (sesuaikan dengan fungsi Anda)
        # from quant.auth import supabase
        # res = supabase.table("laporan_keuangan").select("*").execute()
        # df = pd.DataFrame(res.data)
        
        # UNTUK TESTING: Saya asumsikan Anda punya file parquet dengan nama ini
        df = pd.read_parquet("laporan_keuangan.parquet") 
        
    except FileNotFoundError:
        st.error("⚠️ File data laporan keuangan tidak ditemukan! Silakan sesuaikan path/query di dalam fungsi `load_financial_data()`.")
        st.stop()

    # ------------------------------------------------------------------
    # BAGIAN 2: MAPPING KOLOM (INI DIA "KEYWORD" YANG ANDA MAKSUD)
    # ------------------------------------------------------------------
    # Ubah nama kolom di SEBELAH KANAN agar sesuai dengan nama di database Anda.
    # (Kiri = nama yang dibutuhkan kode, Kanan = nama kolom di database Anda)
    kolom_mapping = {
        'Kode': 'ticker',                 # misal di DB namanya 'ticker'
        'Sektor': 'sector',               # misal 'sector'
        'Tipe': 'type',                   # 'Bank' atau 'Non-Bank'
        'Currency': 'currency',           # 'IDR' atau 'USD'
        
        'NI_9M': 'net_income_9m',         # misal 'net_income_9m'
        'NI_6M': 'net_income_6m', 
        'NI_Q3_LY': 'net_income_q3_ly', 
        
        'Rev_9M': 'revenue_9m', 
        'Rev_6M': 'revenue_6m', 
        'Rev_Q3_LY': 'revenue_q3_ly', 
        
        'CFO_9M': 'cfo_9m', 
        'ROE': 'roe', 
        'DER': 'der', 
        'PER': 'per', 
        'PBV': 'pbv',
        'Avg_Value_Daily': 'avg_value_daily'
    }
    
    # Lakukan rename
    df = df.rename(columns={v: k for k, v in kolom_mapping.items() if v in df.columns})
    
    # Pastikan kolom wajib ada
    wajib = ['Kode', 'Sektor', 'NI_9M', 'NI_6M', 'NI_Q3_LY', 'Rev_9M', 'Rev_6M', 'Rev_Q3_LY', 'CFO_9M', 'ROE', 'DER']
    missing = [c for c in wajib if c not in df.columns]
    if missing:
        st.error(f"⚠️ Kolom berikut tidak ditemukan di database: {', '.join(missing)}. Silakan periksa kembali 'kolom_mapping' di kode Anda.")
        st.stop()

    # ------------------------------------------------------------------
    # BAGIAN 3: AUTO-KONVERSI USD KE IDR (JIKA ADA)
    # ------------------------------------------------------------------
    if 'Currency' in df.columns:
        KURS_USD = 15500
        cols_to_convert = ['NI_9M', 'NI_6M', 'NI_Q3_LY', 'Rev_9M', 'Rev_6M', 'Rev_Q3_LY', 'CFO_9M']
        for col in cols_to_convert:
            df[col] = np.where(df['Currency'] == 'USD', df[col] * KURS_USD, df[col])
    else:
        # Jika tidak ada kolom currency, anggap semua IDR
        df['Currency'] = 'IDR'

    # Pastikan tipe data Bank terisi
    if 'Tipe' not in df.columns:
        df['Tipe'] = 'Non-Bank' # Default jika tidak ada info bank

    return df

# ============================================================
# 2. LOGIKA SCREENER
# ============================================================
def run_screener(df):
    d = df.copy()
    
    d['NI_Q3'] = d['NI_9M'] - d['NI_6M']
    d['Rev_Q3'] = d['Rev_9M'] - d['Rev_6M']
    
    d['NI_YoY_Raw'] = (d['NI_Q3'] - d['NI_Q3_LY']) / d['NI_Q3_LY'].abs()
    d['Rev_YoY_Raw'] = (d['Rev_Q3'] - d['Rev_Q3_LY']) / d['Rev_Q3_LY'].abs()
    
    d['NI_YoY'] = np.clip(d['NI_YoY_Raw'], -1.0, 2.0)
    d['Rev_YoY'] = np.clip(d['Rev_YoY_Raw'], -1.0, 2.0)
    
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
    ni_yoy = f"{row['NI_YoY']*100:+.1f}%"
    rev_yoy = f"{row['Rev_YoY']*100:+.1f}%"
    npm_chg = f"{row['NPM_Change']*100:+.2f}%"
    cfo_ni = f"{row['CFO_to_NI']:.2f}x" if row['Tipe'] != 'Bank' else "N/A (Bank)"
    roe = f"{row['ROE']:.1f}%"
    der = f"{row['DER']:.2f}x" if row['Tipe'] != 'Bank' else "N/A (Bank)"
    per = f"{row['PER']:.1f}x" if row['PER'] > 0 else "N/A"
    pbv = f"{row['PBV']:.2f}x"
    
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
st.markdown(page_header("", "Financial Screener", "Peringkat Fundamental Q3 Berdasarkan Sektor (IDR)"), unsafe_allow_html=True)

# LOAD DATA ASLI
df_raw = load_financial_data()

if df_raw.empty:
    st.stop()

# JALANKAN SCREENER
df_result = run_screener(df_raw)

if df_result.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada saham yang lolos syarat gugur (Hard Filters).</div>', unsafe_allow_html=True)
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
df_raw['NI_YoY'] = (df_raw['NI_Q3'] - df_raw['NI_Q3_LY']) / df_raw['NI_Q3_LY'].abs()
df_raw['Rev_YoY'] = (df_raw['Rev_Q3'] - df_raw['Rev_Q3_LY']) / df_raw['Rev_Q3_LY'].abs()

failed = df_raw[
    (df_raw['NI_YoY'] < 0) | 
    (df_raw['Rev_YoY'] < -0.20) | 
    ((df_raw['DER'] > 2.0) & (df_raw['Tipe'] != 'Bank')) | 
    ((df_raw['CFO_to_NI'] < 0.5) & (df_raw['Tipe'] != 'Bank'))
].copy()

for _, t in failed.head(10).iterrows():
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