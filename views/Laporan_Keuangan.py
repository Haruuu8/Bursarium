import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import pandas as pd
import numpy as np
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title

load_theme()

# ============================================================
# 1. SIMULASI DATABASE (DENGAN VARIASI ANGKA LEBIH REALISTIS)
# ============================================================
@st.cache_data(ttl=3600)
def load_dummy_data():
    np.random.seed(99)
    
    # List Saham (Campuran Bank & Non-Bank)
    data_saham = [
        # Bank
        ("BBCA", "Keuangan", "Bank"), ("BBRI", "Keuangan", "Bank"), 
        ("BMRI", "Keuangan", "Bank"), ("BBNI", "Keuangan", "Bank"),
        ("ARTO", "Keuangan", "Bank"), ("BRIS", "Keuangan", "Bank"),
        # Non-Bank
        ("ADRO", "Energi", "Non-Bank"), ("PTBA", "Energi", "Non-Bank"), 
        ("ITMG", "Energi", "Non-Bank"), ("AMMN", "Basic Material", "Non-Bank"),
        ("ANTM", "Basic Material", "Non-Bank"), ("INCO", "Basic Material", "Non-Bank"),
        ("TLKM", "Infrastruktur", "Non-Bank"), ("ASII", "Industri", "Non-Bank"),
        ("GOTO", "Teknologi", "Non-Bank"), ("BUKA", "Teknologi", "Non-Bank"),
        ("ICBP", "Konsumer", "Non-Bank"), ("UNVR", "Konsumer", "Non-Bank"),
        ("CPIN", "Konsumer", "Non-Bank"), ("SMGR", "Basic Material", "Non-Bank")
    ]
    
    rows = []
    for kode, sektor, tipe in data_saham:
        # Simulasi Data Acak (Desimal agar tidak "bulat")
        ni_9m = np.random.uniform(-1000, 40000)
        ni_6m = ni_9m * np.random.uniform(0.4, 0.7) # Pastikan 9M > 6M
        ni_q3_ly = np.random.uniform(-500, 15000)
        
        rev_9m = np.random.uniform(1000, 150000)
        rev_6m = rev_9m * np.random.uniform(0.5, 0.8)
        rev_q3_ly = np.random.uniform(500, 50000)
        
        cfo_9m = ni_9m * np.random.uniform(0.2, 1.5) # Ada yang < 1.0 (One-off)
        
        # Bank punya DER tinggi & PBV tertentu
        roe = np.random.uniform(5.432, 35.789) if tipe == "Bank" else np.random.uniform(-5.123, 28.765)
        der = np.random.uniform(3.5, 8.0) if tipe == "Bank" else np.random.uniform(0.12, 3.45)
        per = np.random.uniform(5.5, 45.2) if ni_9m > 0 else -1
        pbv = np.random.uniform(0.5, 4.5) if tipe == "Bank" else np.random.uniform(0.3, 6.2)
        avg_val = np.random.uniform(5e8, 2e12)
        
        rows.append({
            'Kode': kode, 'Sektor': sektor, 'Tipe': tipe,
            'NI_9M': ni_9m, 'NI_6M': ni_6m, 'NI_Q3_LY': ni_q3_ly,
            'Rev_9M': rev_9m, 'Rev_6M': rev_6m, 'Rev_Q3_LY': rev_q3_ly,
            'CFO_9M': cfo_9m, 'ROE': roe, 'DER': der, 'PER': per, 'PBV': pbv,
            'Avg_Value_Daily': avg_val
        })
        
    return pd.DataFrame(rows)

# ============================================================
# 2. LOGIKA SCREENER (DENGAN PENALTI & TIE-BREAKER)
# ============================================================
def run_screener(df):
    d = df.copy()
    
    # A. Q3 Standalone
    d['NI_Q3'] = d['NI_9M'] - d['NI_6M']
    d['Rev_Q3'] = d['Rev_9M'] - d['Rev_6M']
    
    # B. Pertumbuhan (YoY)
    # Deteksi Low Base (Tahun lalu rugi / sangat kecil)
    d['Low_Base'] = (d['NI_Q3_LY'] <= 0) | (d['NI_Q3_LY'] < (d['NI_Q3'] * 0.1))
    
    # Denominator pakai absolut agar minus jadi plus
    d['NI_YoY'] = (d['NI_Q3'] - d['NI_Q3_LY']) / d['NI_Q3_LY'].abs()
    d['Rev_YoY'] = (d['Rev_Q3'] - d['Rev_Q3_LY']) / d['Rev_Q3_LY'].abs()
    
    # C. Margin & Kualitas
    d['NPM_Q3'] = d['NI_Q3'] / d['Rev_Q3'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_Q3_LY'] / d['Rev_Q3_LY'].replace(0, np.nan)
    d['NPM_Change'] = d['NPM_Q3'] - d['NPM_LY']
    d['CFO_to_NI'] = d['CFO_9M'] / d['NI_9M'].replace(0, np.nan)
    
    # D. Filter Awal (Buang Sampah)
    d = d[
        (d['NI_9M'] > 0) & 
        (d['CFO_9M'] > 0) & 
        (d['Avg_Value_Daily'] > 1_000_000_000)
    ].copy()
    
    if d.empty: return d
    
    # E. Percentile Ranking (High Precision)
    def sector_rank(series, sector_series, ascending=True):
        global_rank = series.rank(method='min', pct=True, ascending=ascending) * 100
        sector_ranked = series.groupby(sector_series).rank(method='min', pct=True, ascending=ascending) * 100
        sector_counts = sector_series.map(sector_series.value_counts())
        return np.where(sector_counts >= 3, sector_ranked, global_rank)
    
    d['Rank_NI'] = sector_rank(d['NI_YoY'], d['Sektor'], True)
    d['Rank_Rev'] = sector_rank(d['Rev_YoY'], d['Sektor'], True)
    d['Rank_Margin'] = sector_rank(d['NPM_Change'], d['Sektor'], True)
    
    # Kualitas Laba: Jika CFO < 0.8x Laba, potong skor persentilnya 50%
    d['Rank_Quality'] = sector_rank(d['CFO_to_NI'], d['Sektor'], True)
    d.loc[d['CFO_to_NI'] < 0.8, 'Rank_Quality'] = d['Rank_Quality'] * 0.5
    
    d['Rank_ROE'] = sector_rank(d['ROE'], d['Sektor'], True)
    
    # Bank Handling: DER diabaikan untuk Bank (beri nilai netral 50)
    d['Rank_DER'] = sector_rank(d['DER'], d['Sektor'], False)
    d.loc[d['Tipe'] == 'Bank', 'Rank_DER'] = 50 
    
    # PER & PBV
    d['PER_Fixed'] = d['PER'].apply(lambda x: x if x > 0 else np.nan)
    d['Rank_PER'] = sector_rank(d['PER_Fixed'], d['Sektor'], False)
    
    # F. Skor Akhir & Tie-Breaker
    d = d.fillna({'Rank_NI': 0, 'Rank_Rev': 0, 'Rank_Margin': 0, 'Rank_Quality': 0, 'Rank_ROE': 0, 'Rank_DER': 0, 'Rank_PER': 0})
    
    d['Score'] = (
        (d['Rank_NI'] * 0.25) + (d['Rank_Rev'] * 0.15) + 
        (d['Rank_Margin'] * 0.15) + (d['Rank_Quality'] * 0.15) + 
        (d['Rank_ROE'] * 0.10) + (d['Rank_DER'] * 0.10) + 
        (d['Rank_PER'] * 0.10)
    )
    
    # TIE BREAKER: Tambahkan micro-desimal berdasarkan Laba Absolut
    # (Makin besar labanya, makin tinggi desimalnya)
    d['Score_Final'] = d['Score'] + (d['NI_Q3'].rank(pct=True) * 0.001)
    d['Score'] = d['Score_Final'].round(1)
    
    return d.sort_values('Score', ascending=False).reset_index(drop=True)

# ============================================================
# 3. UI RENDERING (CARD TOP 10 DENGAN FLAGS)
# ============================================================
st.markdown(page_header("", "Financial Screener", "Screening Fundamental Q3 Standalone"), unsafe_allow_html=True)

df_raw = load_dummy_data()
df_result = run_screener(df_raw)

if df_result.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada saham yang lolos filter.</div>', unsafe_allow_html=True)
    st.stop()

# Tampilkan Top 10 Card
top_10 = df_result.head(10)

for idx, row in top_10.iterrows():
    # Format Angka
    ni_yoy = f"{row['NI_YoY']*100:+.1f}%"
    rev_yoy = f"{row['Rev_YoY']*100:+.1f}%"
    npm_chg = f"{row['NPM_Change']*100:+.2f}%"
    cfo_ni = f"{row['CFO_to_NI']:.2f}x"
    roe = f"{row['ROE']:.1f}%"
    der = f"{row['DER']:.2f}x" if row['Tipe'] != 'Bank' else "N/A (Bank)"
    per = f"{row['PER']:.1f}x" if row['PER'] > 0 else "N/A"
    pbv = f"{row['PBV']:.2f}x"
    
    # Laba Q3 Standalone (Miliar Rp)
    ni_q3_rp = row['NI_Q3'] / 1000 
    
    # Flags & Icons
    flag_html = ""
    if row['Tipe'] == 'Bank':
        flag_html += '<span style="background:#e5e5e5; color:#0a0a0a; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:6px; font-weight:700;">BANK</span>'
    if row['Low_Base']:
        flag_html += '<span style="background:#737373; color:#ffffff; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:6px; font-weight:700;">LOW BASE</span>'
    
    warning_icon = " ⚠" if row['CFO_to_NI'] < 0.8 else ""
    rank = idx + 1
    
    st.markdown(
        f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; '
        f'border-radius:12px; padding:20px 24px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; '
        f'box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'
        
        # KIRI: Rank, Kode, Sektor, Flags
        f'<div style="min-width: 180px;">'
        f'<div style="font-size:12px; color:#737373; font-weight:800; letter-spacing:1px; margin-bottom:4px;">RANK #{rank}</div>'
        f'<div style="font-size:26px; font-weight:800; color:#ffffff; margin-bottom:4px;">{row["Kode"]}</div>'
        f'<div style="font-size:13px; color:#a3a3a3; margin-bottom:8px;">{row["Sektor"]}</div>'
        f'<div>{flag_html}</div>'
        f'</div>'
        
        # TENGAH: Metrik Grid
        f'<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px 24px; flex:1; max-width:700px;">'
        
        # Baris 1
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba Q3 (Rp)</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_q3_rp:,.1f} M</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Rev YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{rev_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Δ Margin</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{npm_chg}</div></div>'
        
        # Baris 2
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Kualitas Laba</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{cfo_ni}{warning_icon}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">ROE</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{roe}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">DER</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{der}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">PER / PBV</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{per} / {pbv}</div></div>'
        
        f'</div>'
        
        # KANAN: Skor
        f'<div style="text-align:center; background:#262626; border:1px solid #404040; border-radius:8px; padding:12px 24px; min-width:110px;">'
        f'<div style="font-size:11px; color:#a3a3a3; text-transform:uppercase; font-weight:700; letter-spacing:1px;">SCORE</div>'
        f'<div style="font-size:32px; font-weight:800; color:#ffffff; line-height:1.1;">{row["Score"]}</div>'
        f'</div>'
        
        f'</div>', 
        unsafe_allow_html=True
    )

# --- RED FLAGS SUMMARY ---
st.markdown(section_title("Peringatan Kualitas Laba", "Saham skor atas dengan CFO < 0.8x Laba (Berpotensi One-Off)"), unsafe_allow_html=True)
traps = df_result[(df_result['Score'] > 50) & (df_result['CFO_to_NI'] < 0.8)].copy()

if traps.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #ffffff; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">[OK] Aman. Tidak ada anomali kualitas laba yang signifikan pada peringkat atas.</div>', unsafe_allow_html=True)
else:
    for _, t in traps.iterrows():
        st.markdown(
            f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
            f'<div style="font-size:14px; font-weight:700; color:#ffffff;">{t["Kode"]} ⚠</div>'
            f'<div style="font-size:13px; color:#a3a3a3;">CFO/Laba: <b style="color:#fff;">{t["CFO_to_NI"]:.2f}x</b> (Laba YoY: {t["NI_YoY"]*100:+.1f}%)</div>'
            f'</div>', 
            unsafe_allow_html=True
        )