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
from quant.theme import load_theme, page_header, section_title, render_table

load_theme()

# ============================================================
# 1. SIMULASI DATABASE (900+ SAHAM & NEWS)
# ============================================================
@st.cache_data(ttl=3600)
def load_simulated_database():
    np.random.seed(42)
    random.seed(42)
    
    # 1. Generate 900 Kode Saham IDX Acak (4 Huruf)
    def generate_ticker():
        return ''.join(random.choices(string.ascii_uppercase, k=4))
    
    all_tickers = list(set([generate_ticker() for _ in range(950)]))[:900]
    
    # 2. Simulasi Data Fundamental (900 Saham)
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
    
    # 3. Simulasi Berita (Hanya 150 saham yang ada beritanya)
    news_tickers = random.sample(all_tickers, 150)
    
    headlines_pos = [
        "Laba Bersih Q3 Naik {}% YoY, Kinerja Sangat Solid",
        "Lonjakan Laba {}% Didorong Penjualan Ekspor",
        "Pendapatan Tumbuh {}%, Laba Meroket",
        "Cetak Rekor Baru! Laba Naik {}%",
        "Kinerja Cemerlang, Laba Bersih Melonjak {}%"
    ]
    
    headlines_neg = [
        "Laba Anjlok {}%, Beban Operasional Membengkak",
        "Rugi Bersih {}%, Pendapatan Turun Drastis",
        "Kinerja Melemah, Laba Merosot {}%"
    ]
    
    news_data = []
    for t in news_tickers:
        # 70% Berita Positif, 30% Negatif
        if random.random() < 0.7:
            h = random.choice(headlines_pos).format(round(random.uniform(10, 500), 1))
            sentiment = "POSITIVE"
        else:
            h = random.choice(headlines_neg).format(round(random.uniform(5, 80), 1))
            sentiment = "NEGATIVE"
            
        news_data.append({
            'Kode': t,
            'Headline': h,
            'Sentiment': sentiment,
            'Date': pd.Timestamp('2026-10-28') - pd.Timedelta(days=random.randint(0, 5))
        })
        
    df_news = pd.DataFrame(news_data)
    
    return df_fin, df_news

# ============================================================
# 2. LOGIKA SCREENER
# ============================================================
def run_screener(df_fin, df_news):
    # --- TAHAP 1: FILTER BERITA KENAIKAN ---
    # Kita ambil berita positif saja
    df_news_pos = df_news[df_news['Sentiment'] == 'POSITIVE'].copy()
    
    if df_news_pos.empty:
        return pd.DataFrame(), df_news_pos
        
    # Ambil daftar saham yang kena berita positif
    target_tickers = df_news_pos['Kode'].unique()
    
    # --- TAHAP 2: AMBIL DATA BESAR (FINANCIAL) HANYA UNTUK SAHAM TERSEBUT ---
    d = df_fin[df_fin['Kode'].isin(target_tickers)].copy()
    
    # Hitung Q3 Standalone
    d['NI_Q3'] = d['NI_9M'] - d['NI_6M']
    d['Rev_Q3'] = d['Rev_9M'] - d['Rev_6M']
    
    # Hitung Pertumbuhan
    d['NI_YoY'] = (d['NI_Q3'] - d['NI_Q3_LY']) / d['NI_Q3_LY'].abs()
    d['Rev_YoY'] = (d['Rev_Q3'] - d['Rev_Q3_LY']) / d['Rev_Q3_LY'].abs()
    
    # Margin & Kualitas
    d['NPM_Q3'] = d['NI_Q3'] / d['Rev_Q3'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_Q3_LY'] / d['Rev_Q3_LY'].replace(0, np.nan)
    d['NPM_Change'] = d['NPM_Q3'] - d['NPM_LY']
    d['CFO_to_NI'] = d['CFO_9M'] / d['NI_9M'].replace(0, np.nan)
    
    # --- TAHAP 3: FILTER AWAL (BUANG SAMPAH) ---
    d = d[
        (d['NI_9M'] > 0) & 
        (d['CFO_9M'] > 0) & 
        (d['Avg_Value_Daily'] > 1_000_000_000)
    ].copy()
    
    if d.empty: return d, df_news_pos
    
    # --- TAHAP 4: PERCENTILE RANKING ---
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
    
    # --- TAHAP 5: SKOR AKHIR ---
    d = d.fillna({'Rank_NI': 0, 'Rank_Rev': 0, 'Rank_Margin': 0, 'Rank_Quality': 0, 'Rank_ROE': 0, 'Rank_DER': 0, 'Rank_PER': 0})
    d['Score'] = (
        (d['Rank_NI'] * 0.25) + (d['Rank_Rev'] * 0.15) + 
        (d['Rank_Margin'] * 0.15) + (d['Rank_Quality'] * 0.15) + 
        (d['Rank_ROE'] * 0.10) + (d['Rank_DER'] * 0.10) + 
        (d['Rank_PER'] * 0.10)
    ).round(1)
    
    return d.sort_values('Score', ascending=False).reset_index(drop=True), df_news_pos

# ============================================================
# 3. UI RENDERING
# ============================================================
st.markdown(page_header("", "Financial News Screener", "Scan Berita Kenaikan → Kalkulasi Skor Fundamental"), unsafe_allow_html=True)

# Load Data
df_fin_all, df_news_all = load_simulated_database()

# Jalankan Screener
df_result, df_news_pos = run_screener(df_fin_all, df_news_all)

if df_result.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada saham yang lolos kriteria.</div>', unsafe_allow_html=True)
    st.stop()

# --- TAHAP 1: TAMPILKAN BERITA TRIGGER ---
st.markdown(section_title("1. Berita Kenaikan Terbaru (Trigger)", "Saham yang memiliki berita positif & masuk kriteria"), unsafe_allow_html=True)

# Tampilkan 5 berita terbaru dari saham yang lolos skor
top_tickers = df_result.head(10)['Kode'].tolist()
df_news_display = df_news_pos[df_news_pos['Kode'].isin(top_tickers)].sort_values('Date', ascending=False).head(5)

if not df_news_display.empty:
    for _, row in df_news_display.iterrows():
        st.markdown(
            f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; '
            f'border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<span style="font-size:12px; font-weight:700; color:#0a0a0a; background:#ffffff; padding:2px 8px; border-radius:4px; margin-right:12px;">{row["Kode"]}</span>'
            f'<span style="font-size:14px; color:#e5e5e5;">{row["Headline"]}</span>'
            f'</div>'
            f'<div style="font-size:12px; color:#737373;">{row["Date"].strftime("%d %b")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
else:
    st.caption("Tidak ada berita trigger untuk saham di Top 10 saat ini.")

st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)

# --- TAHAP 2: KARTU TOP 1 ---
top = df_result.iloc[0]
st.markdown(
    f'<div style="background: linear-gradient(135deg, #171717 0%, #0a0a0a 100%); '
    f'border: 1px solid #404040; border-left: 6px solid #ffffff; '
    f'border-radius: 12px; padding: 24px 30px; margin-bottom: 32px; '
    f'box-shadow: 0 10px 30px -10px rgba(0,0,0,0.8); display: flex; justify-content: space-between; align-items: center;">'
    
    f'<div>'
    f'<div style="font-size: 12px; color: #a3a3a3; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">Top 1 Performer</div>'
    f'<div style="font-size: 36px; font-weight: 800; color: #ffffff; margin-bottom: 4px;">{top["Kode"]}</div>'
    f'<div style="font-size: 14px; color: #a3a3a3;">Sektor: {top["Sektor"]} &nbsp;|&nbsp; Laba YoY: <b style="color:#fff;">+{top["NI_YoY"]*100:.1f}%</b></div>'
    f'</div>'
    
    f'<div style="text-align: center; background: #262626; border: 1px solid #404040; border-radius: 8px; padding: 16px 24px;">'
    f'<div style="font-size: 11px; color: #a3a3a3; text-transform: uppercase; font-weight: 700;">Overall Score</div>'
    f'<div style="font-size: 42px; font-weight: 800; color: #ffffff; line-height: 1;">{top["Score"]}</div>'
    f'</div>'
    
    f'</div>', unsafe_allow_html=True
)

# --- TAHAP 3: TABEL TOP 10 ---
st.markdown(section_title("2. Top 10 Saham (Hasil Screener)", "Berdasarkan skor persentil fundamental Q3 Standalone"), unsafe_allow_html=True)

df_show = df_result.head(10).copy()
df_show['NI_YoY'] = df_show['NI_YoY'].apply(lambda x: f"{x*100:+.1f}%")
df_show['Rev_YoY'] = df_show['Rev_YoY'].apply(lambda x: f"{x*100:+.1f}%")
df_show['NPM_Change'] = df_show['NPM_Change'].apply(lambda x: f"{x*100:+.2f}%")
df_show['CFO_to_NI'] = df_show['CFO_to_NI'].apply(lambda x: f"{x:.2f}x")
df_show['DER'] = df_show['DER'].apply(lambda x: f"{x:.2f}x")
df_show['PER'] = df_show['PER'].apply(lambda x: f"{x:.1f}x" if x > 0 else "N/A")

df_final = df_show[['Kode', 'Sektor', 'Score', 'NI_YoY', 'Rev_YoY', 'NPM_Change', 'CFO_to_NI', 'ROE', 'DER', 'PER']].rename(columns={
    'NI_YoY': 'Laba YoY', 'Rev_YoY': 'Rev YoY', 'NPM_Change': 'Δ Margin', 'CFO_to_NI': 'Kualitas Laba'
})
render_table(df_final)

# --- TAHAP 4: RED FLAGS ---
st.markdown(section_title("Waspada Jebakan (One-Off Items)", "Saham dengan skor bagus tapi kualitas laba buruk (CFO < 50% Laba)"), unsafe_allow_html=True)
traps = df_result[(df_result['Score'] > 50) & (df_result['CFO_to_NI'] < 0.5)].copy()

if traps.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">[OK] Aman. Tidak ada anomali kualitas laba pada saham peringkat atas.</div>', unsafe_allow_html=True)
else:
    df_traps = traps[['Kode', 'Score', 'CFO_to_NI', 'NI_YoY']].copy()
    df_traps['CFO_to_NI'] = df_traps['CFO_to_NI'].apply(lambda x: f"{x:.2f}x")
    df_traps['NI_YoY'] = df_traps['NI_YoY'].apply(lambda x: f"{x*100:+.1f}%")
    render_table(df_traps)