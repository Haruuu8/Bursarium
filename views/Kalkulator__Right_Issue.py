import streamlit as st
if not st.session_state.get("authentication_status"):
    st.error("Silakan login dulu di halaman utama.")
    st.stop()

import os, sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant.theme import load_theme, page_header, section_title

st.set_page_config(page_title="Kalkulator Right Issue", layout="wide")
load_theme()

st.markdown(page_header("", "Kalkulator Right Issue", "Simulasi Risiko Dilusi (HMETD)"), unsafe_allow_html=True)

st.markdown(section_title("Data Right Issue", "Masukkan parameter aksi korporasi"), unsafe_allow_html=True)

# Form Input
c1, c2 = st.columns(2)
with c1:
    lembar_lama = st.number_input("Jumlah Saham Dimiliki (Lembar)", min_value=1, value=1000, step=100)
    harga_cum = st.number_input("Harga Saham Saat Ini (Cum-Date) - Rp", min_value=1.0, value=1000.0, step=50.0)
with c2:
    st.markdown("**Rasio Right Issue (Lama : Baru)**")
    r1, r2 = st.columns(2)
    with r1:
        rasio_lama = st.number_input("Saham Lama", min_value=1, value=1, step=1)
    with r2:
        rasio_baru = st.number_input("Saham Baru", min_value=1, value=1, step=1)
    
    harga_tebus = st.number_input("Harga Tebus (Exercise Price) - Rp", min_value=1.0, value=500.0, step=50.0)

# ============================================================
# KALKULASI
# ============================================================
if st.button("Hitung Risiko", type="primary", use_container_width=True):
    
    # 1. Lembar Baru yang berhak didapat
    lembar_baru = (lembar_lama / rasio_lama) * rasio_baru
    
    # 2. Biaya Penebusan
    biaya_tebus = lembar_baru * harga_tebus
    
    # 3. TERP (Theoretical Ex-Rights Price)
    total_lembar_baru_tebus = lembar_lama + lembar_baru
    nilai_total_baru = (lembar_lama * harga_cum) + (lembar_baru * harga_tebus)
    terp = nilai_total_baru / total_lembar_baru_tebus
    
    # 4. Nilai Portofolio Sebelum Right Issue
    nilai_awal = lembar_lama * harga_cum
    
    # ============================================================
    # SKENARIO 1: IKUT MENEBUS
    # ============================================================
    nilai_akhir_tebus = total_lembar_baru_tebus * terp
    modal_total_tebus = nilai_awal + biaya_tebus
    pnl_tebus = nilai_akhir_tebus - modal_total_tebus
    pnl_tebus_pct = (pnl_tebus / modal_total_tebus) * 100
    
    # ============================================================
    # SKENARIO 2: TIDAK MENEBUS (DILUSI)
    # ============================================================
    nilai_akhir_dilusi = lembar_lama * terp
    kerugian_dilusi = nilai_akhir_dilusi - nilai_awal
    kerugian_dilusi_pct = (kerugian_dilusi / nilai_awal) * 100

    # ============================================================
    # TAMPILKAN HASIL
    # ============================================================
    st.markdown(section_title("Hasil Simulasi"), unsafe_allow_html=True)
    
    # TERP
    st.markdown(
        f'<div style="background:#131a2a; border:1px solid #1e293b; border-left:4px solid #6366f1; border-radius:12px; padding:20px; margin-bottom:20px;">'
        f'<div style="font-size:12px; color:#94a3b8; font-weight:700;">THEORETICAL EX-RIGHTS PRICE (TERP)</div>'
        f'<div style="font-size:36px; font-weight:900; color:#a5b4fc; margin-top:4px;">Rp {terp:,.0f}</div>'
        f'<div style="font-size:12px; color:#cbd5e1; margin-top:8px;">Ini adalah harga wajar saham setelah right issue. Harga ini akan langsung berlaku di pasar pada tanggal Ex-Date.</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2)
    
    # KARTU 1: IKUT TEBUS
    with col1:
        st.markdown(
            f'<div style="background:#131a2a; border:1px solid #1e293b; border-top:4px solid #10b981; border-radius:12px; padding:20px; height:100%;">'
            f'<div style="font-size:16px; font-weight:800; color:#10b981; margin-bottom:12px;">✅ Skenario: Ikut Menebus</div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Lembar Baru Didapat</span> <b style="color:#fff;">{lembar_baru:,.0f} lembar</b></div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Biaya Tebus</span> <b style="color:#f43f5e;">Rp {biaya_tebus:,.0f}</b></div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Total Lembar Akhir</span> <b style="color:#fff;">{total_lembar_baru_tebus:,.0f} lembar</b></div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Total Modal Akhir</span> <b style="color:#fff;">Rp {modal_total_tebus:,.0f}</b></div>'
            f'<div style="border-top:1px solid #1e293b; margin:10px 0;"></div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Nilai Portofolio (TERP)</span> <b style="color:#fff;">Rp {nilai_akhir_tebus:,.0f}</b></div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between;"><span>Status</span> <b style="color:#10b981;">BEP (Tidak Untung/Rugi)</b></div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    # KARTU 2: TIDAK TEBUS (DILUSI)
    with col2:
        color_dilusi = "#f43f5e" if kerugian_dilusi < 0 else "#10b981"
        bg_alert = "rgba(244,63,94,0.1)" if kerugian_dilusi < 0 else "rgba(16,185,129,0.1)"
        
        st.markdown(
            f'<div style="background:#131a2a; border:1px solid #1e293b; border-top:4px solid {color_dilusi}; border-radius:12px; padding:20px; height:100%;">'
            f'<div style="font-size:16px; font-weight:800; color:{color_dilusi}; margin-bottom:12px;">❌ Skenario: Tidak Menebus (Dilusi)</div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Lembar Baru Didapat</span> <b style="color:#fff;">0 lembar</b></div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Biaya Tebus</span> <b style="color:#fff;">Rp 0</b></div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Total Lembar Akhir</span> <b style="color:#fff;">{lembar_lama:,.0f} lembar</b></div>'
            f'<div style="font-size:13px; color:#94a3b8; display:flex; justify-content:space-between; margin-bottom:6px;"><span>Nilai Portofolio (TERP)</span> <b style="color:#fff;">Rp {nilai_akhir_dilusi:,.0f}</b></div>'
            f'<div style="border-top:1px solid #1e293b; margin:10px 0;"></div>'
            f'<div style="background:{bg_alert}; padding:12px; border-radius:8px;">'
            f'<div style="font-size:12px; color:#cbd5e1; margin-bottom:4px;">Kerugian Delusi:</div>'
            f'<div style="font-size:24px; font-weight:800; color:{color_dilusi};">Rp {kerugian_dilusi:,.0f} ({kerugian_dilusi_pct:.2f}%)</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    # Edukasi Tambahan
    st.info("💡 **Apa itu Delusi?** Jika Anda tidak menebus HMETD (Right Issue), jumlah lembar saham Anda tetap. Namun, karena jumlah saham beredar perusahaan bertambah banyak, porsi kepemilikan Anda mengecil. Harga saham akan turun ke TERP, sehingga nilai portofolio Anda berkurang secara otomatis (seperti pada skenario merah di atas).")