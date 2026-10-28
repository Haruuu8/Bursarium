import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import pandas as pd
import numpy as np
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title

load_theme()

# ============================================================
# 1. FUNGSI LOAD DATA (SILAKAN SESUAIKAN DENGAN DATABASE ANDA)
# ============================================================
@st.cache_data(ttl=1800)
def load_news_data():
    """
    [GANTI BAGIAN INI]
    Ambil data berita dari database/file Anda (misal: Supabase, Parquet, atau API).
    Pastikan ada kolom 'Kode' (ticker IDX) dan 'Headline' atau 'Title'.
    """
    # CONTOH: Jika Anda menyimpannya di file CSV/Parquet
    # df_news = pd.read_parquet("data/news.parquet")
    
    # --- SIMULASI DATA BERITA ASLI (Hapus ini jika sudah pakai database asli) ---
    data = {
        'Kode': ['BBCA', 'BBRI', 'ADRO', 'AMMN', 'GOTO', 'ASII', 'TLKM', 'ANTM', 'BRMS', 'NCKL'],
        'Headline': [
            'Laba Bersih Q3 BBCA Naik 25.5% YoY, Kinerja Solid',
            'Pendapatan BBRI Tumbuh 12%, Laba Melonjak 18%',
            'Laba Bersih ADRO Meroket 45% Didorong Harga Batu Bara',
            'Cetak Rekor Baru! Laba AMMN Naik 300%',
            'GOTO Masih Merugi, Pendapatan Naik 40%',
            'Penjualan Mobil ASII Naik 20%, Laba Bersih +15%',
            'TLKM: EBITDA Margin Meningkat, Laba Tumbuh 10%',
            'Lonjakan Laba ANTM 30% Berkat Efisiensi Biaya',
            'Kinerja Cemerlang, Laba BRMS Melonjak 150%',
            'NCKL Cetak Rekor Baru! Laba Naik 85%'
        ],
        'Date': pd.to_datetime(['2026-10-28'] * 10)
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=1800)
def load_financial_data():
    """
    [GANTI BAGIAN INI]
    Ambil data laporan keuangan dari database/file Anda (Parquet/Supabase).
    Pastikan kolom sesuai dengan standar Q3 kumulatif (9M).
    """
    # CONTOH: df_fin = pd.read_parquet("data/laporan_keuangan.parquet")
    
    # --- SIMULASI DATA KEUANGAN ASLI IDX (Hapus ini jika sudah pakai database asli) ---
    data = {
        'Kode': ['BBCA', 'BBRI', 'ADRO', 'AMMN', 'GOTO', 'ASII', 'TLKM', 'ANTM', 'BRMS', 'NCKL'],
        'Sektor': ['Keuangan', 'Keuangan', 'Energi', 'Basic Material', 'Teknologi', 'Industri', 'Infrastruktur', 'Basic Material', 'Basic Material', 'Basic Material'],
        'NI_9M': [42000, 35000, 12000, 8000, -15000, 21000, 18000, 3500, 1500, 2500],
        'NI_6M': [27000, 22000, 7000, 4000, -9000, 13500, 11000, 2000, 700, 1200],
        'NI_Q3_LY': [12000, 10500, 4000, 1500, -6000, 6000, 5500, 1000, 300, 800],
        'Rev_9M': [75000, 105000, 45000, 20000, 8000, 150000, 110000, 15000, 8000, 12000],
        'Rev_6M': [49000, 70000, 28000, 12000, 5000, 95000, 72000, 9500, 5000, 7500],
        'Rev_Q3_LY': [25000, 35000, 15000, 5000, 3000, 45000, 36000, 5000, 2500, 4000],
        'CFO_9M': [40000, 15000, 11000, 6000, -12000, 18000, 22000, 800, 1000, 1800],
        'ROE': [22.5, 18.2, 25.0, 15.0, -10.0, 12.0, 15.4, 8.5, 12.0, 14.0],
        'DER': [0.2, 0.8, 0.3, 0.5, 0.1, 0.5, 0.4, 0.4, 0.6, 0.4],
        'PER': [22.0, 12.5, 6.0, 15.0, -5.0, 9.0, 15.0, 12.0, 10.0, 11.0],
        'Avg_Value_Daily': [1.5e12, 1.2e12, 5e11, 8e11, 1.5e12, 7e11, 8e11, 4e11, 2e11, 3e11]
    }
    return pd.DataFrame(data)

# ============================================================
# 2. LOGIKA SCREENER
# ============================================================
def run_screener(df_fin, df_news):
    # 1. Filter Berita yang Mengandung Kata Kunci Kenaikan
    keywords = r"naik|tumbuh|melonjak|rekor|laba bersih|positif|meroket"
    df_news_pos = df_news[df_news['Headline'].str.contains(keywords, case=False, na=False)].copy()
    
    if df_news_pos.empty:
        return pd.DataFrame()
        
    # 2. Ambil Kode Saham Unik dari Berita Positif
    target_tickers = df_news_pos['Kode'].unique()
    
    # 3. Filter Data Keuangan HANYA untuk saham yang ada di berita
    d = df_fin[df_fin['Kode'].isin(target_tickers)].copy()
    if d.empty: return pd.DataFrame()
    
    # 4. Hitung Q3 Standalone & Metrik
    d['NI_Q3'] = d['NI_9M'] - d['NI_6M']
    d['Rev_Q3'] = d['Rev_9M'] - d['Rev_6M']
    
    d['NI_YoY'] = (d['NI_Q3'] - d['NI_Q3_LY']) / d['NI_Q3_LY'].abs()
    d['Rev_YoY'] = (d['Rev_Q3'] - d['Rev_Q3_LY']) / d['Rev_Q3_LY'].abs()
    
    d['NPM_Q3'] = d['NI_Q3'] / d['Rev_Q3'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_Q3_LY'] / d['Rev_Q3_LY'].replace(0, np.nan)
    d['NPM_Change'] = d['NPM_Q3'] - d['NPM_LY']
    d['CFO_to_NI'] = d['CFO_9M'] / d['NI_9M'].replace(0, np.nan)
    
    # 5. Filter Awal (Buang Sampah)
    d = d[
        (d['NI_9M'] > 0) & 
        (d['CFO_9M'] > 0) & 
        (d['Avg_Value_Daily'] > 1_000_000_000)
    ].copy()
    
    if d.empty: return d
    
    # 6. Percentile Ranking per Sektor
    def sector_rank(series, sector_series, ascending=True):
        global_rank = series.rank(pct=True, ascending=ascending) * 100
        sector_ranked = series.groupby(sector_series).rank(pct=True, ascending=ascending) * 100
        sector_counts = sector_series.map(sector_series.value_counts())
        return np.where(sector_counts >= 3, sector_ranked, global_rank)
    
    d['Rank_NI'] = sector_rank(d['NI_YoY'], d['Sektor'], True)
    d['Rank_Rev'] = sector_rank(d['Rev_YoY'], d['Sektor'], True)
    d['Rank_Margin'] = sector_rank(d['NPM_Change'], d['Sektor'], True)
    d['Rank_Quality'] = sector_rank(d['CFO_to_NI'], d['Sektor'], True)
    d['Rank_ROE'] = sector_rank(d['ROE'], d['Sektor'], True)
    d['Rank_DER'] = sector_rank(d['DER'], d['Sektor'], False)
    
    d['PER_Fixed'] = d['PER'].apply(lambda x: x if x > 0 else np.nan)
    d['Rank_PER'] = sector_rank(d['PER_Fixed'], d['Sektor'], False)
    
    # 7. Skor Akhir
    d = d.fillna({'Rank_NI': 0, 'Rank_Rev': 0, 'Rank_Margin': 0, 'Rank_Quality': 0, 'Rank_ROE': 0, 'Rank_DER': 0, 'Rank_PER': 0})
    d['Score'] = (
        (d['Rank_NI'] * 0.25) + (d['Rank_Rev'] * 0.15) + 
        (d['Rank_Margin'] * 0.15) + (d['Rank_Quality'] * 0.15) + 
        (d['Rank_ROE'] * 0.10) + (d['Rank_DER'] * 0.10) + 
        (d['Rank_PER'] * 0.10)
    ).round(1)
    
    return d.sort_values('Score', ascending=False).reset_index(drop=True)

# ============================================================
# 3. UI RENDERING (CARD TOP 10)
# ============================================================
st.markdown(page_header("", "Financial News Screener", "Screening Berita Positif & Fundamental Q3"), unsafe_allow_html=True)

# Load Data
df_fin_all = load_financial_data()
df_news_all = load_news_data()

# Jalankan Screener
df_result = run_screener(df_fin_all, df_news_all)

if df_result.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada saham yang memenuhi kriteria (Berita positif + Fundamental bagus).</div>', unsafe_allow_html=True)
    st.stop()

# Tampilkan Top 10 Card
top_10 = df_result.head(10)

for idx, row in top_10.iterrows():
    ni_yoy = f"{row['NI_YoY']*100:+.1f}%"
    rev_yoy = f"{row['Rev_YoY']*100:+.1f}%"
    npm_chg = f"{row['NPM_Change']*100:+.2f}%"
    cfo_ni = f"{row['CFO_to_NI']:.2f}x"
    roe = f"{row['ROE']:.1f}%"
    der = f"{row['DER']:.2f}x"
    per = f"{row['PER']:.1f}x" if row['PER'] > 0 else "N/A"
    rank = idx + 1
    
    st.markdown(
        f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; '
        f'border-radius:12px; padding:20px 24px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; '
        f'box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'
        
        f'<div style="min-width: 150px;">'
        f'<div style="font-size:12px; color:#737373; font-weight:800; letter-spacing:1px; margin-bottom:4px;">RANK #{rank}</div>'
        f'<div style="font-size:26px; font-weight:800; color:#ffffff; margin-bottom:2px;">{row["Kode"]}</div>'
        f'<div style="font-size:13px; color:#a3a3a3;">{row["Sektor"]}</div>'
        f'</div>'
        
        f'<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px 24px; flex:1; max-width:650px;">'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">Laba YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">Rev YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{rev_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">Δ Margin</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{npm_chg}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">Kualitas Laba</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{cfo_ni}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">ROE</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{roe}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">DER / PER</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{der} / {per}</div></div>'
        f'</div>'
        
        f'<div style="text-align:center; background:#262626; border:1px solid #404040; border-radius:8px; padding:12px 24px; min-width:110px;">'
        f'<div style="font-size:11px; color:#a3a3a3; text-transform:uppercase; font-weight:700; letter-spacing:1px;">SCORE</div>'
        f'<div style="font-size:32px; font-weight:800; color:#ffffff; line-height:1.1;">{row["Score"]}</div>'
        f'</div>'
        
        f'</div>', 
        unsafe_allow_html=True
    )

# --- RED FLAGS ---
st.markdown(section_title("Waspada Jebakan (One-Off Items)", "Saham dengan skor tinggi tapi kualitas laba buruk (CFO < 50% Laba)"), unsafe_allow_html=True)
traps = df_result[(df_result['Score'] > 50) & (df_result['CFO_to_NI'] < 0.5)].copy()

if traps.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">[OK] Aman. Tidak ada anomali kualitas laba pada saham peringkat atas.</div>', unsafe_allow_html=True)
else:
    for _, t in traps.head(3).iterrows():
        st.markdown(
            f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
            f'<div style="font-size:14px; font-weight:700; color:#ffffff;">{t["Kode"]}</div>'
            f'<div style="font-size:13px; color:#a3a3a3;">CFO/Laba: <b style="color:#fff;">{t["CFO_to_NI"]:.2f}x</b> (Laba YoY: {t["NI_YoY"]*100:+.1f}%)</div>'
            f'</div>', 
            unsafe_allow_html=True
        )