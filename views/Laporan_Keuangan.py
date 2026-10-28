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
# 1. SIMULASI DATABASE (DENGAN KASUS REALISTIS)
# ============================================================
@st.cache_data(ttl=3600)
def load_dummy_data():
    np.random.seed(99)
    
    # Saya sengaja membuat beberapa kasus ekstrem untuk membuktikan filter bekerja
    data_saham = [
        # Kasus Normal / Bluechip
        ("BBCA", "Keuangan", "Bank", "IDR", 42000000000000, 27000000000000, 12000000000000, 75000000000000, 49000000000000, 25000000000000, 40000000000000, 22.5, 0.2, 22.0, 4.5),
        ("BBRI", "Keuangan", "Bank", "IDR", 35000000000000, 22000000000000, 10500000000000, 105000000000000, 70000000000000, 35000000000000, 15000000000000, 18.2, 0.8, 12.5, 2.0),
        ("ASII", "Industri", "Non-Bank", "IDR", 21000000000000, 13500000000000, 6000000000000, 150000000000000, 95000000000000, 45000000000000, 18000000000000, 12.0, 0.5, 9.0, 1.2),
        
        # Kasus CPIN (Anomali Revenue ekstrem, margin minus, CFO jelek)
        ("CPIN", "Konsumer", "Non-Bank", "IDR", 3200000000000, 2000000000000, 100000000000, 35000000000000, 22000000000000, 3500000000000, 1150000000000, 14.0, 0.6, 18.0, 2.2),
        
        # Kasus ITMG (Laba turun, Rev turun, DER tinggi, tapi ada di sektor Energi)
        ("ITMG", "Energi", "Non-Bank", "USD", 280000000, 180000000, 300000000, 1200000000, 750000000, 1500000000, 400000000, 3.6, 3.43, 5.0, 0.9),
        
        # Kasus ADRO (Bagus, CFO kuat)
        ("ADRO", "Energi", "Non-Bank", "USD", 1200000000, 700000000, 400000000, 4500000000, 2800000000, 1500000000, 1100000000, 25.0, 0.3, 6.0, 1.0),
        
        # Kasus Lainnya
        ("AMMN", "Basic Material", "Non-Bank", "USD", 80000000, 40000000, 15000000, 200000000, 120000000, 50000000, 60000000, 15.0, 0.5, 15.0, 3.5),
        ("TLKM", "Infrastruktur", "Non-Bank", "IDR", 18000000000000, 11000000000000, 5500000000000, 110000000000000, 72000000000000, 36000000000000, 22000000000000, 15.4, 0.4, 15.0, 2.5),
        ("ANTM", "Basic Material", "Non-Bank", "IDR", 3500000000000, 2000000000000, 1000000000000, 15000000000000, 9500000000000, 5000000000000, 800000000000, 8.5, 0.4, 12.0, 1.5),
        ("UNVR", "Konsumer", "Non-Bank", "IDR", 4500000000000, 3000000000000, 1400000000000, 28000000000000, 18000000000000, 9000000000000, 5500000000000, 35.0, 0.6, 30.0, 35.0)
    ]
    
    # Generate 40 saham tambahan secara acak agar ranking sektor jalan
    for i in range(40):
        sektor = np.random.choice(['Keuangan', 'Energi', 'Konsumer', 'Industri', 'Basic Material', 'Infrastruktur'])
        tipe = "Bank" if sektor == 'Keuangan' and np.random.rand() > 0.5 else "Non-Bank"
        curr = np.random.choice(['IDR', 'IDR', 'IDR', 'USD'])
        mult = 15500 if curr == 'USD' else 1 # Konversi kasar untuk simulasi
        
        ni_9m = np.random.uniform(100e9, 5000e9) * mult
        ni_6m = ni_9m * np.random.uniform(0.4, 0.7)
        ni_q3_ly = np.random.uniform(50e9, 4000e9) * mult
        
        rev_9m = ni_9m * np.random.uniform(2, 5)
        rev_6m = rev_9m * np.random.uniform(0.5, 0.8)
        rev_q3_ly = rev_9m * np.random.uniform(0.5, 0.9) # Bisa turun
        
        cfo_9m = ni_9m * np.random.uniform(0.4, 1.5)
        roe = np.random.uniform(5.4, 35.8) if tipe == "Bank" else np.random.uniform(-5.1, 28.7)
        der = np.random.uniform(3.5, 8.0) if tipe == "Bank" else np.random.uniform(0.1, 3.4)
        
        data_saham.append((
            f"STK{i:02d}", sektor, tipe, curr, 
            ni_9m, ni_6m, ni_q3_ly, 
            rev_9m, rev_6m, rev_q3_ly, 
            cfo_9m, roe, der, np.random.uniform(5, 40), np.random.uniform(0.5, 4.5)
        ))
        
    df = pd.DataFrame(data_saham, columns=[
        'Kode', 'Sektor', 'Tipe', 'Currency', 
        'NI_9M', 'NI_6M', 'NI_Q3_LY', 
        'Rev_9M', 'Rev_6M', 'Rev_Q3_LY', 
        'CFO_9M', 'ROE', 'DER', 'PER', 'PBV'
    ])
    
    df['Avg_Value_Daily'] = np.random.uniform(5e8, 2e12, len(df))
    return df

# ============================================================
# 2. LOGIKA SCREENER V3 (WINSORIZE + HARD FILTERS)
# ============================================================
def run_screener(df):
    d = df.copy()
    
    # A. Q3 Standalone
    d['NI_Q3'] = d['NI_9M'] - d['NI_6M']
    d['Rev_Q3'] = d['Rev_9M'] - d['Rev_6M']
    
    # B. Pertumbuhan YoY (Raw)
    d['NI_YoY_Raw'] = (d['NI_Q3'] - d['NI_Q3_LY']) / d['NI_Q3_LY'].abs()
    d['Rev_YoY_Raw'] = (d['Rev_Q3'] - d['Rev_Q3_LY']) / d['Rev_Q3_LY'].abs()
    
    # C. Winsorization (Membatasi ekstrem: -100% s/d +200%)
    d['NI_YoY'] = np.clip(d['NI_YoY_Raw'], -1.0, 2.0)
    d['Rev_YoY'] = np.clip(d['Rev_YoY_Raw'], -1.0, 2.0)
    
    # D. Margin & Kualitas Laba
    d['NPM_Q3'] = d['NI_Q3'] / d['Rev_Q3'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_Q3_LY'] / d['Rev_Q3_LY'].replace(0, np.nan)
    d['NPM_Change'] = (d['NPM_Q3'] - d['NPM_LY']).fillna(-1) # Jika kosong, beri nilai buruk
    d['CFO_to_NI'] = d['CFO_9M'] / d['NI_9M'].replace(0, np.nan)
    
    # E. FLAGS ANOMALI
    d['Flag_Anomali'] = ""
    d.loc[d['Rev_YoY_Raw'] > 3.0, 'Flag_Anomali'] += "CEK REV, "
    d.loc[d['NPM_Change'].abs() > 0.30, 'Flag_Anomali'] += "CEK MARGIN, "
    d.loc[d['NI_Q3_LY'] <= 0, 'Flag_Anomali'] += "LOW BASE, "
    
    # F. HARD FILTERS (Syarat Gugur)
    # 1. Laba YoY harus >= 0
    # 2. Revenue YoY tidak boleh turun lebih dari 20%
    # 3. DER <= 2.0 (Kecuali Bank)
    # 4. Kualitas Laba (CFO/NI) >= 0.5
    d = d[
        (d['NI_YoY_Raw'] >= 0) & 
        (d['Rev_YoY_Raw'] >= -0.20) & 
        ((d['DER'] <= 2.0) | (d['Tipe'] == 'Bank')) &
        (d['CFO_to_NI'] >= 0.5) &
        (d['Avg_Value_Daily'] > 1_000_000_000)
    ].copy()
    
    if d.empty: return d
    
    # G. Percentile Ranking
    def sector_rank(series, sector_series, ascending=True):
        global_rank = series.rank(method='min', pct=True, ascending=ascending) * 100
        sector_ranked = series.groupby(sector_series).rank(method='min', pct=True, ascending=ascending) * 100
        sector_counts = sector_series.map(sector_series.value_counts())
        return np.where(sector_counts >= 3, sector_ranked, global_rank)
    
    # Bobot baru: Growth (35%), Margin (20%), Quality (20%), ROE (10%), DER (5%), PER (10%)
    d['Rank_NI'] = sector_rank(d['NI_YoY'], d['Sektor'], True)
    d['Rank_Rev'] = sector_rank(d['Rev_YoY'], d['Sektor'], True)
    d['Rank_Margin'] = sector_rank(d['NPM_Change'], d['Sektor'], True)
    d['Rank_Quality'] = sector_rank(d['CFO_to_NI'], d['Sektor'], True)
    d['Rank_ROE'] = sector_rank(d['ROE'], d['Sektor'], True)
    
    d['Rank_DER'] = sector_rank(d['DER'], d['Sektor'], False)
    d.loc[d['Tipe'] == 'Bank', 'Rank_DER'] = 50 
    
    d['PER_Fixed'] = d['PER'].apply(lambda x: x if x > 0 else np.nan)
    d['Rank_PER'] = sector_rank(d['PER_Fixed'], d['Sektor'], False)
    
    d = d.fillna({'Rank_NI': 0, 'Rank_Rev': 0, 'Rank_Margin': 0, 'Rank_Quality': 0, 'Rank_ROE': 0, 'Rank_DER': 0, 'Rank_PER': 0})
    
    d['Score'] = (
        (d['Rank_NI'] * 0.20) + (d['Rank_Rev'] * 0.15) + 
        (d['Rank_Margin'] * 0.20) + (d['Rank_Quality'] * 0.20) + 
        (d['Rank_ROE'] * 0.10) + (d['Rank_DER'] * 0.05) + 
        (d['Rank_PER'] * 0.10)
    )
    
    # Tie-Breaker
    d['Score_Final'] = d['Score'] + (d['NI_Q3'].rank(pct=True) * 0.001)
    d['Score'] = d['Score_Final'].round(1)
    
    return d.sort_values('Score', ascending=False).reset_index(drop=True)

# ============================================================
# 3. UI RENDERING
# ============================================================
st.markdown(page_header("", "Financial Screener", "Screening Fundamental Q3 (Hard Filters & Winsorization)"), unsafe_allow_html=True)

df_raw = load_dummy_data()
df_result = run_screener(df_raw)

if df_result.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada saham yang lolos syarat gugur (Hard Filters).</div>', unsafe_allow_html=True)
    st.stop()

top_10 = df_result.head(10)

for idx, row in top_10.iterrows():
    # Formatter Angka Pintar (T, B, M)
    def format_rp(val, curr):
        if curr == 'USD': val = val * 15500 # Konversi ke IDR untuk tampilan setara
        abs_val = abs(val)
        if abs_val >= 1e12: return f"{val/1e12:,.1f} T"
        elif abs_val >= 1e9: return f"{val/1e9:,.1f} B"
        elif abs_val >= 1e6: return f"{val/1e6:,.1f} M"
        else: return f"{val:,.0f}"

    ni_q3_rp = format_rp(row['NI_Q3'], row['Currency'])
    curr_label = f" ({row['Currency']})" if row['Currency'] == 'USD' else ""
    
    ni_yoy = f"{row['NI_YoY']*100:+.1f}%"
    rev_yoy = f"{row['Rev_YoY']*100:+.1f}%"
    npm_chg = f"{row['NPM_Change']*100:+.2f}%"
    cfo_ni = f"{row['CFO_to_NI']:.2f}x"
    roe = f"{row['ROE']:.1f}%"
    der = f"{row['DER']:.2f}x" if row['Tipe'] != 'Bank' else "N/A (Bank)"
    per = f"{row['PER']:.1f}x" if row['PER'] > 0 else "N/A"
    pbv = f"{row['PBV']:.2f}x"
    
    # Flags HTML
    flag_html = ""
    if row['Tipe'] == 'Bank': flag_html += '<span style="background:#e5e5e5; color:#0a0a0a; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">BANK</span>'
    if row['Currency'] == 'USD': flag_html += '<span style="background:#404040; color:#ffffff; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">USD</span>'
    if row['Flag_Anomali']:
        flag_html += f'<span style="background:#737373; color:#ffffff; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px; font-weight:700;">⚠ {row["Flag_Anomali"].strip(", ")}</span>'
    
    rank = idx + 1
    
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
        
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba Q3{curr_label}</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_q3_rp}</div></div>'
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

# --- DISQUALIFIED / BOTTOM FEEDERS ---
st.markdown(section_title("Saham yang Gugur (Hard Filters)", "Gagal memenuhi syarat: Laba Turun, Rev Anjlok, DER > 2, atau CFO < 0.5x"), unsafe_allow_html=True)

df_raw['NI_Q3'] = df_raw['NI_9M'] - df_raw['NI_6M']
df_raw['Rev_Q3'] = df_raw['Rev_9M'] - df_raw['Rev_6M']
df_raw['CFO_to_NI'] = df_raw['CFO_9M'] / df_raw['NI_9M'].replace(0, np.nan)
df_raw['NI_YoY'] = (df_raw['NI_Q3'] - df_raw['NI_Q3_LY']) / df_raw['NI_Q3_LY'].abs()
df_raw['Rev_YoY'] = (df_raw['Rev_Q3'] - df_raw['Rev_Q3_LY']) / df_raw['Rev_Q3_LY'].abs()

failed = df_raw[
    (df_raw['NI_YoY'] < 0) | 
    (df_raw['Rev_YoY'] < -0.20) | 
    ((df_raw['DER'] > 2.0) & (df_raw['Tipe'] != 'Bank')) | 
    (df_raw['CFO_to_NI'] < 0.5)
].copy()

for _, t in failed.head(5).iterrows():
    reason = []
    if t['NI_YoY'] < 0: reason.append(f"Laba Turun ({t['NI_YoY']*100:.1f}%)")
    if t['Rev_YoY'] < -0.20: reason.append(f"Rev Anjlok ({t['Rev_YoY']*100:.1f}%)")
    if t['DER'] > 2.0 and t['Tipe'] != 'Bank': reason.append(f"DER Tinggi ({t['DER']:.2f}x)")
    if t['CFO_to_NI'] < 0.5: reason.append(f"CFO Lemah ({t['CFO_to_NI']:.2f}x)")
    
    st.markdown(
        f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
        f'<div style="font-size:14px; font-weight:700; color:#ffffff;">{t["Kode"]}</div>'
        f'<div style="font-size:13px; color:#a3a3a3;">Gugur karena: <b style="color:#fff;">{", ".join(reason)}</b></div>'
        f'</div>', 
        unsafe_allow_html=True
    )