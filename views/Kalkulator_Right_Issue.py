import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title

load_theme()

st.markdown(page_header("", "Kalkulator Right Issue", "Simulasi Risiko Dilusi (HMETD)"), unsafe_allow_html=True)

st.markdown(section_title("Data Right Issue", "Masukkan parameter saat ini (Cum-Date)"), unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    lot_lama = st.number_input("Jumlah Lot Dimiliki", min_value=1, value=10, step=1)
    harga_cum = st.number_input("Harga Saham Saat Ini (Cum-Date) - Rp", min_value=1.0, value=1000.0, step=50.0)
with c2:
    st.markdown('<div style="font-size: 14px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Rasio Right Issue (Lama : Baru)</div>', unsafe_allow_html=True)
    r1, r2 = st.columns(2)
    with r1:
        rasio_lama = st.number_input("Saham Lama", min_value=1, value=1, step=1)
    with r2:
        rasio_baru = st.number_input("Saham Baru", min_value=1, value=1, step=1)
    
    harga_tebus = st.number_input("Harga Tebus (Exercise Price) - Rp", min_value=1.0, value=500.0, step=50.0)

# ============================================================
# KALKULASI
# ============================================================
if st.button("Hitung Harga Teoritis (TERP)", type="primary", use_container_width=True):
    
    # 1. Lot Baru yang berhak didapat
    lot_baru = (lot_lama / rasio_lama) * rasio_baru
    lembar_lama = lot_lama * 100
    lembar_baru = lot_baru * 100
    
    # 2. Biaya Penebusan
    biaya_tebus = lembar_baru * harga_tebus
    
    # 3. TERP (Theoretical Ex-Rights Price)
    total_lembar_akhir = lembar_lama + lembar_baru
    nilai_total_baru = (lembar_lama * harga_cum) + (lembar_baru * harga_tebus)
    terp = nilai_total_baru / total_lembar_akhir
    nilai_awal = lembar_lama * harga_cum
    
    # ============================================================
    # TAMPILKAN HASIL UTAMA
    # ============================================================
    st.markdown(section_title("Hasil Perhitungan"), unsafe_allow_html=True)
    
    st.markdown(
        f'<div style="background:#0a0a0a; border:1px solid #262626; border-left:4px solid #ffffff; border-radius:8px; padding:24px; margin-bottom:20px;">'
        f'<div style="font-size:12px; color:#a3a3a3; font-weight:600; letter-spacing:1px; text-transform:uppercase;">Harga Teoritis Setelah Right Issue (TERP)</div>'
        f'<div style="font-size:42px; font-weight:700; color:#ffffff; margin-top:8px;">Rp {terp:,.0f}</div>'
        f'<div style="font-size:14px; color:#d4d4d4; margin-top:16px; line-height: 1.6;">Angka ini adalah harga "wajar" saham Anda besok saat pasar dibuka (Ex-Date). Harga di pasar bisa sama, lebih tinggi, atau <b>lebih rendah</b> dari angka ini.</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    # ============================================================
    # PANDUAN TEGAS
    # ============================================================
    st.markdown('<div style="font-size: 16px; font-weight: 600; color: #ffffff; margin: 24px 0 16px;">Panduan & Simulasi</div>', unsafe_allow_html=True)
    
    st.markdown(
        f'<div style="background: #0a0a0a; border: 1px solid #262626; border-left: 3px solid #ffffff; border-radius: 4px; padding: 12px 16px; margin-bottom: 24px;">'
        f'<div style="font-size: 13px; color: #d4d4d4; line-height: 1.5;">Besok saat pasar buka (Ex-Date), perhatikan harga sahamnya. Jika harganya jatuh di bawah <b>Rp {terp:,.0f}</b>, inilah yang harus Anda lakukan:</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2)
    
    # KARTU 1: KALAU HARGA JATUH (RUGI)
    with col1:
        st.markdown(
            f'<div style="background:#171717; border:1px solid #262626; border-top:4px solid #737373; border-radius:8px; padding:20px; height:100%;">'
            f'<div style="font-size:16px; font-weight:600; color:#ffffff; margin-bottom:12px;">Jika Harga Pasar &lt; Rp {terp:,.0f}</div>'
            f'<div style="font-size:13px; color:#a3a3a3; line-height:1.6; margin-bottom:16px;">'
            f'Pasar tidak suka right issue ini. Jika Anda tetap menebus, Anda membayar Rp {harga_tebus:,.0f} per lembar, padahal harga pasar sudah jatuh lebih rendah. Anda <b>langsung rugi</b> di hari pertama.'
            f'</div>'
            f'<div style="background:#0a0a0a; border: 1px solid #404040; padding:12px; border-radius:4px; font-size:13px; font-weight:600; color:#ffffff;">'
            f'REKOMENDASI: JUAL SAHAM / HMETD ANDA. Jangan tebus!'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    # KARTU 2: KALAU HARGA BERTAHAN (AMAN)
    with col2:
        st.markdown(
            f'<div style="background:#171717; border:1px solid #262626; border-top:4px solid #ffffff; border-radius:8px; padding:20px; height:100%;">'
            f'<div style="font-size:16px; font-weight:600; color:#ffffff; margin-bottom:12px;">Jika Harga Pasar &gt; Rp {terp:,.0f}</div>'
            f'<div style="font-size:13px; color:#a3a3a3; line-height:1.6; margin-bottom:16px;">'
            f'Pasar menerima right issue ini dengan baik. Anda bisa menebus saham baru seharga Rp {harga_tebus:,.0f} (yang lebih murah dari harga pasar). Ini adalah kesempatan Anda mendapat "diskon".'
            f'</div>'
            f'<div style="background:#ffffff; padding:12px; border-radius:4px; font-size:13px; font-weight:600; color:#000000;">'
            f'REKOMENDASI: TEBUS RIGHT ISSUE ANDA.'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div style="height:1px; background:#262626; margin:32px 0;"></div>', unsafe_allow_html=True)
    
    # ============================================================
    # SIMULASI UANG
    # ============================================================
    st.markdown('<div style="font-size: 16px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Simulasi Nilai Portofolio</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size: 12px; color: #737373; margin-bottom: 16px;">(Asumsi: Saat Ex-Date besok, harga pasar persis di angka TERP yaitu Rp {terp:,.0f})</div>', unsafe_allow_html=True)
    
    # Skenario Jika Menebus
    nilai_akhir_tebus = total_lembar_akhir * terp
    modal_total_tebus = nilai_awal + biaya_tebus
    pnl_tebus = nilai_akhir_tebus - modal_total_tebus
    
    # Skenario Jika Tidak Menebus
    nilai_akhir_dilusi = lembar_lama * terp
    kerugian_dilusi = nilai_akhir_dilusi - nilai_awal
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown(
            f'<div style="background:#0a0a0a; border:1px solid #262626; border-left:3px solid #ffffff; border-radius:8px; padding:16px;">'
            f'<div style="font-size:14px; font-weight:600; color:#ffffff; margin-bottom:12px;">Jika IKUT Menebus</div>'
            f'<div style="font-size:13px; color:#a3a3a3; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Biaya Tebus</span> <b style="color:#ffffff;">Rp {biaya_tebus:,.0f}</b></div>'
            f'<div style="font-size:13px; color:#a3a3a3; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Lot Jadi</span> <b style="color:#ffffff;">{lot_lama + lot_baru:,.0f} Lot</b></div>'
            f'<div style="font-size:13px; color:#a3a3a3; display:flex; justify-content:space-between; margin-top:12px; padding-top:12px; border-top:1px dashed #262626;"><span>Nilai Akhir</span> <b style="color:#ffffff;">Rp {nilai_akhir_tebus:,.0f}</b></div>'
            f'<div style="font-size:13px; color:#a3a3a3; display:flex; justify-content:space-between; margin-top:6px;"><span>Status PnL</span> <b style="color:{"#ffffff" if pnl_tebus >= 0 else "#737373"};">{"BEP (Tidak Untung/Rugi)" if abs(pnl_tebus) < 1 else f"{pnl_tebus:+,.0f}"}</b></div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    with col_b:
        st.markdown(
            f'<div style="background:#0a0a0a; border:1px solid #262626; border-left:3px solid #404040; border-radius:8px; padding:16px;">'
            f'<div style="font-size:14px; font-weight:600; color:#a3a3a3; margin-bottom:12px;">Jika TIDAK Menebus (Dilusi)</div>'
            f'<div style="font-size:13px; color:#a3a3a3; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Biaya Tebus</span> <b style="color:#737373;">Rp 0</b></div>'
            f'<div style="font-size:13px; color:#a3a3a3; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Lot Jadi</span> <b style="color:#737373;">{lot_lama:,.0f} Lot (Tetap)</b></div>'
            f'<div style="font-size:13px; color:#a3a3a3; display:flex; justify-content:space-between; margin-top:12px; padding-top:12px; border-top:1px dashed #262626;"><span>Nilai Akhir</span> <b style="color:#737373;">Rp {nilai_akhir_dilusi:,.0f}</b></div>'
            f'<div style="font-size:13px; color:#a3a3a3; display:flex; justify-content:space-between; margin-top:6px;"><span>Kerugian Dilusi</span> <b style="color:#737373;">Rp {kerugian_dilusi:,.0f}</b></div>'
            f'</div>',
            unsafe_allow_html=True
        )