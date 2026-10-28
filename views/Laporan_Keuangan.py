import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import pandas as pd
import numpy as np
import random
import string

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title

load_theme()

# ============================================================
# 1. SIMULASI DATABASE (900+ SAHAM & NEWS)
# ============================================================
@st.cache_data(ttl=3600)
def load_simulated_database():
    np.random.seed(42)
    random.seed(42)
    
    # Generate 900 Kode Saham IDX Acak
    def generate_ticker():
        return ''.join(random.choices(string.ascii_uppercase, k=4))
    
    all_tickers = list(set([generate_ticker() for _ in range(950)]))[:900]
    sectors = ['Keuangan', 'Konsumer', 'Energi', 'Teknologi', 'Infrastruktur', 'Industri', 'Basic Material', 'Kesehatan', 'Properti']
    
    df_fin = pd.DataFrame({
        'Kode': all_tickers,
        'Sektor': np.random.choice(sectors, len(all_tickers)),
        'NI_9M': np.random.uniform(-500, 35000, len(all_tickers)),
        'NI_6M': np.random.uniform(-400, 25000, len(all_tickers)),
        'NI_Q3_LY': np.random.uniform(-200, 15000, len(all_tickers)),
        'Rev_9M': np.random.uniform(500, 120000, len(all_tickers)),
        'Rev_6M': np.random.uniform(400, 80000, len(all_tickers)),
        'Rev_Q3_LY': np.random.uniform(300, 40000, len(all_tickers)),
        'CFO_9M': np.random.uniform(-200, 30000, len(all_tickers)),
        'ROE': np.random.uniform(-15, 35, len(all_tickers)),
        'DER': np.random.uniform(0.1, 4.0, len(all_tickers)),
        'PER': np.random.uniform(4, 60, len(all_tickers)),
        'Avg_Value_Daily': np.random.uniform(1e8, 1.5e12, len(all_tickers))
    })
    
    # Simulasi Berita (Hanya 150 saham)
    news_tickers = random.sample(all_tickers, 150)
    headlines_pos = [
        "Laba Bersih Q3 Naik {}% YoY, Kinerja Sangat Solid",
        "Lonjakan Laba {}% Didorong Penjualan Ekspor",
        "Pendapatan Tumbuh {}%, Laba Meroket",
        "Cetak Rekor Baru! Laba Naik {}%",
        "Kinerja Cemerlang, Laba Bersih Melonjak {}%"
    ]
    
    news_data = []
    for t in news_tickers:
        if random.random() < 0.7:
            h = random.choice(headlines_pos).format(round(random.uniform(10, 500), 1))
            sentiment = "POSITIVE"
        else:
            h = "Laba Anjlok, Kinerja Memburuk"
            sentiment = "NEGATIVE"
        news_data.append({'Kode': t, 'Headline': h, 'Sentiment': sentiment, 'Date': pd.Timestamp('2026-10-28')})
        
    df_news = pd.DataFrame(news_data)
    return df_fin, df_news

# ============================================================
# 2. LOGIKA SCREENER
# ============================================================
def run_screener(df_fin, df_news):
    # Filter Berita Positif
    df_news_pos = df_news[df_news['Sentiment'] == 'POSITIVE'].copy()
    if df_news_pos.empty: return pd.DataFrame()
        
    # Ambil data keuangan hanya untuk saham yang ada berita positif
    target_tickers = df_news_pos['Kode'].unique()
    d = df_fin[df_fin['Kode'].isin(target_tickers)].copy()
    
    # Hitung Q3 Standalone
    d['NI_Q3'] = d['NI_9M'] - d['NI_6M']
    d['Rev_Q3'] = d['Rev_9M'] - d['Rev_6M']
    
    # Pertumbuhan
    d['NI_YoY'] = (d['NI_Q3'] - d['NI_Q3_LY']) / d['NI_Q3_LY'].abs()
    d['Rev_YoY'] = (d['Rev_Q3'] - d['Rev_Q3_LY']) / d['Rev_Q3_LY'].abs()
    
    # Margin & Kualitas
    d['NPM_Q3'] = d['NI_Q3'] / d['Rev_Q3'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_Q3_LY'] / d['Rev_Q3_LY'].replace(0, np.nan)
    d['NPM_Change'] = d['NPM_Q3'] - d['NPM_LY']
    d['CFO_to_NI'] = d['CFO_9M'] / d['NI_9M'].replace(0, np.nan)
    
    # Filter Awal
    d = d[
        (d['NI_9M'] > 0) & 
        (d['CFO_9M'] > 0) & 
        (d['Avg_Value_Daily'] > 1_000_000_000)
    ].copy()
    
    if d.empty: return d
    
    # Percentile Ranking
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
    
    # Skor Akhir
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
st.markdown(page_header("", "Financial News Screener", "Top 10 Saham Berdasarkan Skor Fundamental Q3"), unsafe_allow_html=True)

df_fin_all, df_news_all = load_simulated_database()
df_result = run_screener(df_fin_all, df_news_all)

if df_result.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada saham yang lolos kriteria.</div>', unsafe_allow_html=True)
    st.stop()

# Tampilkan Top 10 dalam bentuk Card
top_10 = df_result.head(10)

for idx, row in top_10.iterrows():
    # Format angka
    ni_yoy = f"{row['NI_YoY']*100:+.1f}%"
    rev_yoy = f"{row['Rev_YoY']*100:+.1f}%"
    npm_chg = f"{row['NPM_Change']*100:+.2f}%"
    cfo_ni = f"{row['CFO_to_NI']:.2f}x"
    roe = f"{row['ROE']:.1f}%"
    der = f"{row['DER']:.2f}x"
    per = f"{row['PER']:.1f}x" if row['PER'] > 0 else "N/A"
    
    # Rank Badge (1, 2, 3, dst)
    rank = idx + 1
    
    st.markdown(
        f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; '
        f'border-radius:12px; padding:20px 24px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; '
        f'box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'
        
        # KIRI: Rank, Kode, Sektor
        f'<div style="min-width: 150px;">'
        f'<div style="font-size:12px; color:#737373; font-weight:800; letter-spacing:1px; margin-bottom:4px;">RANK #{rank}</div>'
        f'<div style="font-size:26px; font-weight:800; color:#ffffff; margin-bottom:2px;">{row["Kode"]}</div>'
        f'<div style="font-size:13px; color:#a3a3a3;">{row["Sektor"]}</div>'
        f'</div>'
        
        # TENGAH: Metrik Grid
        f'<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px 24px; flex:1; max-width:650px;">'
        
        # Baris 1
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">Laba YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">Rev YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{rev_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">Δ Margin</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{npm_chg}</div></div>'
        
        # Baris 2
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">Kualitas Laba</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{cfo_ni}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">ROE</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{roe}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase; letter-spacing:0.5px;">DER / PER</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{der} / {per}</div></div>'
        
        f'</div>'
        
        # KANAN: Skor
        f'<div style="text-align:center; background:#262626; border:1px solid #404040; border-radius:8px; padding:12px 24px; min-width:110px;">'
        f'<div style="font-size:11px; color:#a3a3a3; text-transform:uppercase; font-weight:700; letter-spacing:1px;">SCORE</div>'
        f'<div style="font-size:32px; font-weight:800; color:#ffffff; line-height:1.1;">{row["Score"]}</div>'
        f'</div>'
        
        f'</div>', 
        unsafe_allow_html=True
    )

# --- RED FLAGS (JEBAKAN) ---
st.markdown(section_title("Waspada Jebakan (One-Off Items)", "Saham dengan skor tinggi tapi kualitas laba buruk (CFO < 50% Laba)"), unsafe_allow_html=True)
traps = df_result[(df_result['Score'] > 50) & (df_result['CFO_to_NI'] < 0.5)].copy()

if traps.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">[OK] Aman. Tidak ada anomali kualitas laba pada saham peringkat atas.</div>', unsafe_allow_html=True)
else:
    # Tampilkan sebagai list card kecil
    for _, t in traps.head(3).iterrows():
        st.markdown(
            f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
            f'<div style="font-size:14px; font-weight:700; color:#ffffff;">{t["Kode"]}</div>'
            f'<div style="font-size:13px; color:#a3a3a3;">CFO/Laba: <b style="color:#fff;">{t["CFO_to_NI"]:.2f}x</b> (Laba YoY: {t["NI_YoY"]*100:+.1f}%)</div>'
            f'</div>', 
            unsafe_allow_html=True
        )