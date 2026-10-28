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

def format_idr(val):
    abs_val = abs(val)
    if abs_val >= 1e12: return f"Rp {val/1e12:,.1f} T"
    elif abs_val >= 1e9: return f"Rp {val/1e9:,.1f} B"
    elif abs_val >= 1e6: return f"Rp {val/1e6:,.1f} M"
    else: return f"Rp {val:,.0f}"

@st.cache_data(ttl=1800)
def load_clean_q3_data():
    try:
        df = pd.read_csv("data_q3_clean.csv")
        return df
    except FileNotFoundError:
        st.error("⚠️ File `data_q3_clean.csv` tidak ditemukan. Jalankan `py quant/find_q3.py` dulu.")
        st.stop()

def run_screener(df):
    d = df.copy()
    
    d['NI_YoY_Raw'] = (d['NI_YTD'] - d['NI_YTD_LY']) / d['NI_YTD_LY'].abs().replace(0, np.nan)
    d['Rev_YoY_Raw'] = (d['Rev_YTD'] - d['Rev_YTD_LY']) / d['Rev_YTD_LY'].abs().replace(0, np.nan)
    
    d['NPM_YTD'] = d['NI_YTD'] / d['Rev_YTD'].replace(0, np.nan)
    d['NPM_LY'] = d['NI_YTD_LY'] / d['Rev_YTD_LY'].replace(0, np.nan)
    d['NPM_Change'] = (d['NPM_YTD'] - d['NPM_LY']).fillna(-1)
    
    d['CFO_to_NI'] = d['CFO_YTD'] / d['NI_YTD'].replace(0, np.nan)
    
    d['Flag_Anomali'] = ""
    d.loc[d['Rev_YoY_Raw'] > 3.0, 'Flag_Anomali'] += "CEK REV, "
    d.loc[d['NPM_Change'].abs() > 0.30, 'Flag_Anomali'] += "CEK MARGIN, "
    d.loc[(d['NI_YoY_Raw'] > 0.5) & (d['ROE'] < 10), 'Flag_Anomali'] += "GROWTH LOW ROE, "
    
    d['is_failed'] = False
    d['fail_reason'] = ""
    
    for idx, row in d.iterrows():
        reason = []
        cfo_valid = row['CFO_YTD'] > 0
        
        if pd.isna(row['NI_YoY_Raw']) or row['NI_YoY_Raw'] < 0: reason.append("Laba Turun")
        if pd.isna(row['Rev_YoY_Raw']) or row['Rev_YoY_Raw'] < -0.20: reason.append("Rev Anjlok")
        if row['NI_YTD'] <= 0: reason.append("Masih Rugi")
        if row['NI_YoY_Raw'] > 3.0: reason.append("YoY Anomali (>300%)")
        if row['PER'] < 2.0: reason.append("PER Tidak Wajar")
        if row['PBV'] < 0.2: reason.append("PBV Tidak Wajar")
        
        if row['Tipe'] != 'Bank':
            if row['DER'] > 2.0 or row['DER'] < 0: reason.append("DER Tidak Sehat")
            if cfo_valid and row['CFO_to_NI'] < 0.5: reason.append("CFO Lemah")
        
        if reason:
            d.at[idx, 'is_failed'] = True
            d.at[idx, 'fail_reason'] = ", ".join(reason)
            
    df_pass = d[~d['is_failed']].copy()
    df_fail = d[d['is_failed']].copy()
    
    if df_pass.empty: return df_pass, df_fail
    
    # ABSOLUTE SCORING (DENGAN NORMALISASI CFO)
    d = df_pass
    
    def calc_score(row):
        w_roe, w_growth, w_per, w_qual, w_margin = 0.35, 0.20, 0.20, 0.15, 0.10
        
        s_roe = min(max(row['ROE'], 0), 25) / 25 * 100
        s_growth = min(max(row['NI_YoY_Raw']*100, 0), 30) / 30 * 100 if not pd.isna(row['NI_YoY_Raw']) else 0
        
        if row['PER'] <= 0: s_per = 0
        elif row['PER'] < 10: s_per = 100
        elif row['PER'] < 15: s_per = 80
        elif row['PER'] < 20: s_per = 60
        elif row['PER'] < 30: s_per = 40
        else: s_per = 20
        
        s_margin = min(max(row['NPM_Change']*100, 0), 10) / 10 * 100 if not pd.isna(row['NPM_Change']) else 0
        
        cfo_valid = not pd.isna(row['CFO_to_NI']) and row['CFO_to_NI'] > 0 and row['Tipe'] != 'Bank'
        
        if cfo_valid:
            s_qual = min(row['CFO_to_NI'], 1.5) / 1.5 * 100
            total_w = w_roe + w_growth + w_per + w_qual + w_margin
            score = (s_roe*w_roe + s_growth*w_growth + s_per*w_per + s_qual*w_qual + s_margin*w_margin) / total_w
        else:
            # Normalisasi ulang jika CFO kosong
            total_w = w_roe + w_growth + w_per + w_margin
            score = (s_roe*w_roe + s_growth*w_growth + s_per*w_per + s_margin*w_margin) / total_w
            
        return score

    d['Score_Raw'] = d.apply(calc_score, axis=1)
    d = d.sort_values(by=['Score_Raw', 'NI_YTD'], ascending=[False, False]).reset_index(drop=True)
    d['Score'] = d['Score_Raw'].round(2)
    return d, df_fail

def render_card(row, rank):
    ni_ytd_rp = format_idr(row['NI_YTD'])
    ni_q3_rp = format_idr(row['NI_Q3'])
    
    ni_yoy = f"{row['NI_YoY_Raw']*100:+.1f}%" if not pd.isna(row['NI_YoY_Raw']) else "N/A"
    ni_q3_yoy = f"{row['NI_Q3_YoY']*100:+.1f}%" if not pd.isna(row['NI_Q3_YoY']) else "N/A"
    rev_yoy = f"{row['Rev_YoY_Raw']*100:+.1f}%" if not pd.isna(row['Rev_YoY_Raw']) else "N/A"
    npm_chg = f"{row['NPM_Change']*100:+.2f}%" if row['NPM_Change'] != -1 else "N/A"
    
    cfo_ni = f"{row['CFO_to_NI']:.2f}x" if row['Tipe'] != 'Bank' and row['CFO_to_NI'] > 0 else "N/A"
    roe = f"{row['ROE']:.1f}%" if row['ROE'] else "N/A"
    der = f"{row['DER']:.2f}x" if row['Tipe'] != 'Bank' else "N/A"
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
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba YTD (9M)</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_ytd_rp}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba YTD YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba Q3</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_q3_rp}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Laba Q3 YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{ni_q3_yoy}</div></div>'
        
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Rev YTD YoY</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{rev_yoy}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Δ Margin</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{npm_chg}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">Kualitas Laba</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{cfo_ni}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">ROE</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{roe}</div></div>'
        
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">DER</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{der}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">PER</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{per}</div></div>'
        f'<div><div style="font-size:11px; color:#737373; text-transform:uppercase;">PBV</div><div style="font-size:15px; font-weight:700; color:#ffffff;">{pbv}</div></div>'
        f'<div></div>'
        f'</div>'
        
        f'<div style="text-align:center; background:#262626; border:1px solid #404040; border-radius:8px; padding:12px 24px; min-width:110px;">'
        f'<div style="font-size:11px; color:#a3a3a3; text-transform:uppercase; font-weight:700; letter-spacing:1px;">SCORE</div>'
        f'<div style="font-size:32px; font-weight:800; color:#ffffff; line-height:1.1;">{row["Score"]}</div>'
        f'</div>'
        
        f'</div>', 
        unsafe_allow_html=True
    )

# ============================================================
# UI UTAMA
# ============================================================
st.markdown(page_header("", "Q3 Fundamental Screener", "Peringkat Fundamental Q3 (Absolute Scoring)"), unsafe_allow_html=True)

df_raw = load_clean_q3_data()
df_pass, df_fail = run_screener(df_raw)

tab1, tab2, tab3 = st.tabs(["🏆 Peringkat Utama", "📊 Tabel Perbandingan", "❌ Saham Gugur"])

with tab1:
    if df_pass.empty:
        st.warning("Tidak ada saham yang lolos filter.")
    else:
        sectors = df_pass['Sektor'].unique().tolist()
        sector_tabs = st.tabs(["Semua Sektor"] + sectors)
        
        with sector_tabs[0]:
            for idx, row in df_pass.head(10).iterrows():
                render_card(row, idx + 1)
                
        for i, sector in enumerate(sectors):
            with sector_tabs[i + 1]:
                df_sec = df_pass[df_pass['Sektor'] == sector].head(5)
                for idx, row in df_sec.iterrows():
                    render_card(row, idx + 1)

with tab2:
    st.markdown("### Perbandingan Metrik Fundamental")
    st.markdown("Tabel ini menampilkan angka asli untuk membandingkan siapa yang paling unggul secara absolut.")
    
    if not df_pass.empty:
        df_compare = df_pass[['Kode', 'Sektor', 'Score', 'NI_YTD', 'NI_Q3', 'NI_Q3_YoY', 'ROE', 'PER', 'PBV', 'CFO_to_NI']].copy()
        
        df_compare['Laba YTD'] = df_compare['NI_YTD'].apply(format_idr)
        df_compare['Laba Q3'] = df_compare['NI_Q3'].apply(format_idr)
        df_compare['Q3 YoY'] = df_compare['NI_Q3_YoY'].apply(lambda x: f"{x*100:+.1f}%" if not pd.isna(x) else "N/A")
        df_compare['ROE'] = df_compare['ROE'].apply(lambda x: f"{x:.1f}%")
        df_compare['PER'] = df_compare['PER'].apply(lambda x: f"{x:.1f}x" if x > 0 else "N/A")
        df_compare['PBV'] = df_compare['PBV'].apply(lambda x: f"{x:.2f}x" if x > 0 else "N/A")
        df_compare['Kualitas Laba'] = df_compare['CFO_to_NI'].apply(lambda x: f"{x:.2f}x" if x > 0 else "N/A")
        
        df_compare = df_compare[['Kode', 'Sektor', 'Score', 'Laba YTD', 'Laba Q3', 'Q3 YoY', 'ROE', 'PER', 'PBV', 'Kualitas Laba']]
        st.dataframe(df_compare, use_container_width=True, hide_index=True)
        
with tab3:
    if df_fail.empty:
        st.success("Semua saham bersih!")
    else:
        for _, t in df_fail.iterrows():
            st.markdown(
                f'<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:12px 16px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">'
                f'<div style="font-size:14px; font-weight:700; color:#ffffff;">{t["Kode"]} <span style="font-size:11px; color:#a3a3a3; font-weight:400; margin-left:8px;">({t["Sektor"]})</span></div>'
                f'<div style="font-size:13px; color:#a3a3a3;">Gugur: <b style="color:#fff;">{t["fail_reason"]}</b></div>'
                f'</div>', 
                unsafe_allow_html=True
            )