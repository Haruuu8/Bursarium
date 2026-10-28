import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title, render_table, card, info_banner

load_theme()

# ============================================================
# DUMMY DATA (GANTI DENGAN QUERY DATABASE ANDA NANTINYA)
# ============================================================
@st.cache_data(ttl=1800)
def load_data_laporan():
    # Simulasi data berita / laporan keuangan emiten
    data = {
        "Kode": ["BBCA", "BBRI", "GOTO", "ASII", "TLKM", "ADRO", "ANTM", "UNVR", "ICBP", "BMRI"],
        "Headline Berita": [
            "Laba Bersih Q3 2026 Naik 25.5% YoY, Kinerja Solid",
            "Pendapatan Bunga Naik 12%, Laba Melonjak 18%",
            "Kerugian Menyusut Drastis, Pendapatan Naik 40%",
            "Penjualan Mobil Naik 20%, Laba Bersih +15%",
            "EBITDA Margin Meningkat, Laba Tumbuh 10%",
            "Laba Bersih Meroket 45% Didorong Harga Batu Bara",
            "Lonjakan Laba 30% Berkat Efisiensi Biaya",
            "Penjualan Turun 5%, Laba Bersih Anjlok -10%",
            "Pendapatan Tumbuh 8.5%, Laba Naik 6%",
            "Laba Bersih Tumbuh 20% Ditopang Kredit Macet Turun"
        ],
        "Laba Bersih (%)": [25.5, 18.0, -5.0, 15.0, 10.0, 45.0, 30.0, -10.0, 6.0, 20.0],
        "Pendapatan (%)": [18.2, 12.0, 40.0, 20.0, 5.0, 25.0, 15.0, -5.0, 8.5, 14.0],
        "EPS (%)": [24.0, 17.5, 0.0, 14.5, 9.0, 44.0, 29.0, -11.0, 5.5, 19.0],
        "Margin (%)": [35.0, 25.0, -2.0, 12.0, 30.0, 18.0, 22.0, 20.0, 15.0, 28.0]
    }
    df = pd.DataFrame(data)
    
    # ========================================================
    # KALKULASI SCORE (BOBOT)
    # ========================================================
    # Normalisasi sederhana (kita asumsikan skor maksimal pertumbuhan adalah 50% untuk perhitungan)
    def normalize(val, max_val=50):
        # Kalau minus, skornya 0 (tidak dapat poin)
        if val <= 0: return 0
        # Kalau di atas max_val, dianggap max_val
        return min((val / max_val) * 100, 100)

    df["Score"] = (
        (df["Laba Bersih (%)"].apply(normalize) * 0.40) +
        (df["Pendapatan (%)"].apply(normalize) * 0.30) +
        (df["EPS (%)"].apply(normalize) * 0.20) +
        (df["Margin (%)"].apply(normalize) * 0.10)
    ).round(1)

    # Urutkan dari skor tertinggi
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)
    return df

# ============================================================
# HEADER & LOAD DATA
# ============================================================
st.markdown(page_header("", "Financial Growth Screener", "Screening Laporan Keuangan & Berita Fundamental"), unsafe_allow_html=True)

df_news = load_data_laporan()

# ============================================================
# TOP PERFORMER (Saham dengan skor tertinggi)
# ============================================================
top_stock = df_news.iloc[0]

st.markdown(section_title("Top Performer", "Saham dengan pertumbuhan fundamental terbaik saat ini"), unsafe_allow_html=True)

st.markdown(
    f'<div style="background: linear-gradient(135deg, #171717 0%, #0a0a0a 100%); '
    f'border: 1px solid #404040; border-left: 6px solid #ffffff; '
    f'border-radius: 12px; padding: 30px; margin-bottom: 32px; '
    f'box-shadow: 0 10px 30px -10px rgba(0,0,0,0.8);">'
    f'<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">'
    
    # Kiri: Info Saham
    f'<div style="flex: 1;">'
    f'<div style="font-size: 32px; font-weight: 800; color: #ffffff; margin-bottom: 8px;">{top_stock["Kode"]}</div>'
    f'<div style="font-size: 16px; color: #a3a3a3; line-height: 1.5; max-width: 600px;">{top_stock["Headline Berita"]}</div>'
    f'<div style="margin-top: 20px; display: flex; gap: 24px; flex-wrap: wrap;">'
    f'<div><div style="font-size: 11px; color: #737373; text-transform: uppercase; letter-spacing: 1px;">Laba Bersih</div><div style="font-size: 18px; font-weight: 700; color: #ffffff;">+{top_stock["Laba Bersih (%)"]}%</div></div>'
    f'<div><div style="font-size: 11px; color: #737373; text-transform: uppercase; letter-spacing: 1px;">Pendapatan</div><div style="font-size: 18px; font-weight: 700; color: #ffffff;">+{top_stock["Pendapatan (%)"]}%</div></div>'
    f'<div><div style="font-size: 11px; color: #737373; text-transform: uppercase; letter-spacing: 1px;">EPS</div><div style="font-size: 18px; font-weight: 700; color: #ffffff;">+{top_stock["EPS (%)"]}%</div></div>'
    f'</div>'
    f'</div>'
    
    # Kanan: Skor
    f'<div style="text-align: center; background: #262626; padding: 20px 30px; border-radius: 8px; border: 1px solid #404040;">'
    f'<div style="font-size: 12px; color: #a3a3a3; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; margin-bottom: 8px;">Growth Score</div>'
    f'<div style="font-size: 48px; font-weight: 800; color: #ffffff; line-height: 1;">{top_stock["Score"]}</div>'
    f'<div style="font-size: 14px; color: #737373; margin-top: 4px;">/ 100</div>'
    f'</div>'
    
    f'</div></div>',
    unsafe_allow_html=True
)

# ============================================================
# TABEL SEMUA LAPORAN
# ============================================================
st.markdown(section_title("Daftar Seluruh Laporan", "Diurutkan berdasarkan Growth Score tertinggi"), unsafe_allow_html=True)

# Filter minimum score
min_score = st.slider("Filter Minimal Score", min_value=0, max_value=100, value=0, step=10)

df_filtered = df_news[df_news["Score"] >= min_score].copy()

if df_filtered.empty:
    st.markdown('<div style="background:#171717; border:1px solid #27272a; border-left:4px solid #737373; border-radius:8px; padding:16px 20px; color:#e5e5e5; font-size:14px;">Tidak ada laporan yang memenuhi skor minimal tersebut.</div>', unsafe_allow_html=True)
else:
    # Format Tabel
    df_show = df_filtered.copy()
    df_show["Laba Bersih (%)"] = df_show["Laba Bersih (%)"].apply(lambda x: f"{x:+.1f}%" if pd.notnull(x) else "-")
    df_show["Pendapatan (%)"] = df_show["Pendapatan (%)"].apply(lambda x: f"{x:+.1f}%" if pd.notnull(x) else "-")
    df_show["EPS (%)"] = df_show["EPS (%)"].apply(lambda x: f"{x:+.1f}%" if pd.notnull(x) else "-")
    df_show["Margin (%)"] = df_show["Margin (%)"].apply(lambda x: f"{x:+.1f}%" if pd.notnull(x) else "-")
    
    # Rename kolom untuk tabel
    df_show = df_show[["Kode", "Headline Berita", "Laba Bersih (%)", "Pendapatan (%)", "EPS (%)", "Margin (%)", "Score"]]
    df_show = df_show.rename(columns={
        "Laba Bersih (%)": "Laba",
        "Pendapatan (%)": "Rev",
    })
    
    render_table(df_show)
    st.caption("**Score** dihitung dari rata-rata tertimbang: Laba (40%), Pendapatan (30%), EPS (20%), dan Margin (10%). Hanya pertumbuhan positif yang dihitung.")