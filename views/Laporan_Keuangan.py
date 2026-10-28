import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title, render_table, info_banner

load_theme()

# ============================================================
# 1. DUMMY DATA (SIMULASI DATA IDX)
# GANTI FUNGSI INI DENGAN QUERY DATABASE ANDA (Supabase/Parquet)
# ============================================================
@st.cache_data(ttl=3600)
def load_raw_data():
    np.random.seed(42)
    n = 40
    sectors = ['Keuangan', 'Konsumer', 'Energi', 'Teknologi', 'Infrastruktur', 'Industri']
    
    # Simulasi data mentah kumulatif (dalam Miliar Rupiah)
    df = pd.DataFrame({
        'Kode': [f"S{chr(65+i)}{i:02d}" for i in range(n)],
        'Sektor': np.random.choice(sectors, n),
        'NI_9M': np.random.uniform(-100, 2000, n),
        'NI_6M': np.random.uniform(-100, 1500, n),
        'NI_Q3_LY': np.random.uniform(-100, 1000, n),
        'Rev_9M': np.random.uniform(100, 5000, n),
        'Rev_6M': np.random.uniform(100, 4000, n),
        'Rev_Q3_LY': np.random.uniform(100, 3000, n),
        'CFO_9M': np.random.uniform(-50, 2500, n),
        'ROE': np.random.uniform(-10, 40, n),
        'DER': np.random.uniform(0.1, 3.5, n),
        'PER': np.random.uniform(5, 50, n),
        'PBV': np.random.uniform(0.5, 5.0, n),
        'Avg_Value_Daily': np.random.uniform(1e8, 1e11, n) # Rata-rata nilai transaksi harian
    })
    return df

# ============================================================
# 2. LOGIKA KALKULASI & SCORING
# ============================================================
def calculate_screener(df):
    d = df.copy()
    
    # --- A. Hitung Q3 Standalone ---
    d['NI_Q3'] = d['NI_9M'] - d['NI_6M']
    d['Rev_Q3'] = d['Rev_9M'] - d['Rev_6M']
    
    # --- B. Hitung Pertumbuhan (Growth) ---
    # Menggunakan absolute denominator agar jika tahun lalu rugi, pertumbuhan turn-around tetap terbaca positif
    d['NI_YoY'] = (d['NI_Q3'] - d['NI_Q3_LY']) / d['NI_Q3_LY'].abs()
    d['Rev_YoY'] = (d['Rev_Q3'] - d['Rev_Q3_LY']) / d['Rev_Q3_LY'].abs()
    
    # --- C. Hitung Margin & Kualitas Laba ---
    d['NPM_Q3'] = d['NI_Q3'] / d['Rev_Q3'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_Q3_LY'] / d['Rev_Q3_LY'].replace(0, np.nan)
    d['NPM_Change'] = d['NPM_Q3'] - d['NPM_LY']
    
    d['CFO_to_NI'] = d['CFO_9M'] / d['NI_9M'].replace(0, np.nan)
    
    # --- D. Filter Awal (Buang Sampah) ---
    # 1. Laba bersih 9M positif
    # 2. CFO 9M positif
    # 3. Likuiditas > 1 Miliar
    d = d[
        (d['NI_9M'] > 0) & 
        (d['CFO_9M'] > 0) & 
        (d['Avg_Value_Daily'] > 1_000_000_000)
    ].copy()
    
    if d.empty:
        return d
    
    # --- E. Percentile Ranking (0-100) ---
    # Fungsi helper untuk ranking per sektor (jika sektor < 3 saham, pakai ranking global)
    def sector_rank(series, sector_series, ascending=True):
        # Global rank sebagai fallback
        global_rank = series.rank(pct=True, ascending=ascending) * 100
        # Sector rank
        sector_ranked = series.groupby(sector_series).rank(pct=True, ascending=ascending) * 100
        # Gabungkan: Pakai sector rank jika sektor punya > 2 saham, sisanya global rank
        sector_counts = sector_series.map(sector_series.value_counts())
        return np.where(sector_counts >= 3, sector_ranked, global_rank)
    
    # Rank untuk metrik "Semakin besar semakin bagus"
    d['Rank_NI'] = sector_rank(d['NI_YoY'], d['Sektor'], ascending=True)
    d['Rank_Rev'] = sector_rank(d['Rev_YoY'], d['Sektor'], ascending=True)
    d['Rank_Margin'] = sector_rank(d['NPM_Change'], d['Sektor'], ascending=True)
    d['Rank_Quality'] = sector_rank(d['CFO_to_NI'], d['Sektor'], ascending=True)
    d['Rank_ROE'] = sector_rank(d['ROE'], d['Sektor'], ascending=True)
    
    # Rank untuk metrik "Semakin kecil semakin bagus" (Utang & Valuasi)
    d['Rank_DER'] = sector_rank(d['DER'], d['Sektor'], ascending=False)
    
    # PER: Kita asumsikan PER positif > 0. Jika negatif, ranknya otomatis jelek (0)
    d['PER_Fixed'] = d['PER'].apply(lambda x: x if x > 0 else np.nan)
    d['Rank_PER'] = sector_rank(d['PER_Fixed'], d['Sektor'], ascending=False)
    
    # --- F. Skor Gabungan (Bobot) ---
    # Isi NaN dengan 0 (skor terendah) jika data tidak tersedia
    d = d.fillna({
        'Rank_NI': 0, 'Rank_Rev': 0, 'Rank_Margin': 0, 
        'Rank_Quality': 0, 'Rank_ROE': 0, 'Rank_DER': 0, 'Rank_PER': 0
    })
    
    d['Score'] = (
        (d['Rank_NI'] * 0.25) +
        (d['Rank_Rev'] * 0.15) +
        (d['Rank_Margin'] * 0.15) +
        (d['Rank_Quality'] * 0.15) +
        (d['Rank_ROE'] * 0.10) +
        (d['Rank_DER'] * 0.10) +
        (d['Rank_PER'] * 0.10)
    ).round(2)
    
    # Urutkan berdasarkan skor tertinggi
    d = d.sort_values('Score', ascending=False).reset_index(drop=True)
    return d

# ============================================================
# 3. UI RENDERING
# ============================================================
st.markdown(page_header("", "Financial Report Screener", "Screening Laporan Keuangan Q3 (Percentile Ranking)"), unsafe_allow_html=True)

# Penjelasan Metodologi
st.markdown(
    '<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; '
    'border-radius:8px; padding:16px 20px; margin-bottom:24px; font-size:13px; color:#a3a3a3; line-height:1.6;">'
    '<b style="color:#ffffff;">METODOLOGI:</b> Data dihitung menggunakan Q3 Standalone (9M - 6M). '
    'Hanya saham dengan Laba 9M Positif, CFO 9M Positif, dan Likuiditas > Rp 1 Miliar yang masuk kriteria. '
    'Skor akhir menggunakan <i>Percentile Ranking (0-100)</i> per sektor untuk mencegah bias dari saham dengan basis kecil.'
    '</div>', unsafe_allow_html=True
)

df_raw = load_raw_data()
df_result = calculate_screener(df_raw)

if df_result.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada saham yang lolos filter awal (Laba positif, CFO positif, Likuiditas > 1M).</div>', unsafe_allow_html=True)
    st.stop()

# Tampilkan Top 20
st.markdown(section_title("Top 20 Saham (Skor Tertinggi)", "Berdasarkan kalkulasi bobot fundamental Q3"), unsafe_allow_html=True)

# Persiapkan tabel untuk ditampilkan
df_show = df_result.head(20).copy()

# Format kolom agar cantik dibaca (persentase dan angka)
df_show['NI_YoY'] = df_show['NI_YoY'].apply(lambda x: f"{x*100:+.1f}%" if pd.notnull(x) else "-")
df_show['Rev_YoY'] = df_show['Rev_YoY'].apply(lambda x: f"{x*100:+.1f}%" if pd.notnull(x) else "-")
df_show['NPM_Change'] = df_show['NPM_Change'].apply(lambda x: f"{x*100:+.2f}%" if pd.notnull(x) else "-")
df_show['CFO_to_NI'] = df_show['CFO_to_NI'].apply(lambda x: f"{x:.2f}x" if pd.notnull(x) else "-")
df_show['DER'] = df_show['DER'].apply(lambda x: f"{x:.2f}x" if pd.notnull(x) else "-")
df_show['PER'] = df_show['PER'].apply(lambda x: f"{x:.1f}x" if pd.notnull(x) and x > 0 else "N/A")

df_final = df_show[[
    'Kode', 'Sektor', 'Score', 'NI_YoY', 'Rev_YoY', 'NPM_Change', 'CFO_to_NI', 'ROE', 'DER', 'PER'
]].rename(columns={
    'NI_YoY': 'Laba YoY',
    'Rev_YoY': 'Rev YoY',
    'NPM_Change': 'Δ Margin',
    'CFO_to_NI': 'Kualitas Laba',
    'ROE': 'ROE (%)',
    'DER': 'DER',
    'PER': 'PER'
})

render_table(df_final)

# ============================================================
# 4. WARNING & JEBAKAN (Sesuai instruksi Anda)
# ============================================================
st.markdown(section_title("Waspadai Jebakan (Red Flags)", "Wajib dicek manual sebelum eksekusi"), unsafe_allow_html=True)

# Cek anomali: Laba naik tapi CFO jelek, atau Laba naik karena one-off (CFO jauh lebih kecil dari Laba)
traps = df_result[
    (df_result['Score'] > 60) & # Skor lumayan bagus
    (df_result['CFO_to_NI'] < 0.5) # Tapi kualitas laba buruk (CFO < 50% Laba Bersih)
].copy()

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        '<div style="background:#171717; border:1px solid #27272a; border-top:4px solid #ffffff; border-radius:8px; padding:20px; height:100%;">'
        '<div style="font-size:15px; font-weight:700; color:#ffffff; margin-bottom:12px;">1. Cek Kualitas Laba (One-Off)</div>'
        '<div style="font-size:13px; color:#a3a3a3; line-height:1.6;">'
        'Laba bisa melonjak karena penjualan aset, revaluasi, atau laba kurs. '
        'Jika <b>CFO / Laba Bersih < 0.5</b>, berarti laba tersebut tidak menghasilkan uang kas riil.'
        '</div></div>', 
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        '<div style="background:#171717; border:1px solid #27272a; border-top:4px solid #737373; border-radius:8px; padding:20px; height:100%;">'
        '<div style="font-size:15px; font-weight:700; color:#ffffff; margin-bottom:12px;">2. Basis Tahun Lalu (Low Base)</div>'
        '<div style="font-size:13px; color:#a3a3a3; line-height:1.6;">'
        'Saham dengan lonjakan YoY > 1000% seringkali hanya karena tahun lalu rugi/basis kecil. '
        'Selalu cek nilai absolut Laba 9M-nya, bukan hanya persentasenya.'
        '</div></div>', 
        unsafe_allow_html=True
    )

# Tampilkan tabel "Jebakan" jika ada
if not traps.empty:
    st.markdown('<div style="margin-top: 24px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 14px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Saham dengan Skor Tinggi tapi Kualitas Laba Buruk (CFO < 50% Laba):</div>', unsafe_allow_html=True)
    
    df_traps = traps[['Kode', 'Score', 'CFO_to_NI', 'NI_YoY']].copy()
    df_traps['CFO_to_NI'] = df_traps['CFO_to_NI'].apply(lambda x: f"{x:.2f}x")
    df_traps['NI_YoY'] = df_traps['NI_YoY'].apply(lambda x: f"{x*100:+.1f}%")
    render_table(df_traps)
else:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px; margin-top: 24px;">[OK] Tidak ada anomali kualitas laba pada 20 saham teratas. CFO mayoritas sejalan dengan Laba Bersih.</div>', unsafe_allow_html=True)