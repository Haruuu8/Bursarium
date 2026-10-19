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

c1, c2 = st.columns(2)
with c1:
    lot_lama = st.number_input("Jumlah Lot Dimiliki", min_value=1, value=10, step=1)
    harga_cum = st.number_input("Harga Saham Sebelum Right Issue (Cum-Date) - Rp", min_value=1.0, value=600.0, step=50.0)
with c2:
    st.markdown("**Rasio Right Issue (Lama : Baru)**")
    r1, r2 = st.columns(2)
    with r1:
        rasio_lama = st.number_input("Saham Lama", min_value=1, value=1, step=1)
    with r2:
        rasio_baru = st.number_input("Saham Baru", min_value=1, value=1, step=1)
    
    harga_tebus = st.number_input("Harga Tebus (Exercise Price) - Rp", min_value=1.0, value=400.0, step=50.0)

st.markdown("---")
st.markdown("**Simulasi Harga Pasar Aktual**")
st.caption("Masukkan harga saham saat ini di pasar (setelah Ex-Date). Ini penting karena harga pasar seringkali berbeda dengan TERP.")
harga_pasar = st.number_input("Harga Pasar Aktual (Rp)", min_value=1.0, value=372.0, step=50.0)

# ============================================================
# KALKULASI
# ============================================================
if st.button("Hitung Risiko", type="primary", use_container_width=True):
    
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
    # TAMPILKAN ANGKA
    # ============================================================
    st.markdown(section_title("Hasil Simulasi"), unsafe_allow_html=True)
    
    col_terp, col_pasar = st.columns(2)
    with col_terp:
        st.metric("TEORITIS (TERP)", f"Rp {terp:,.0f}")
    with col_pasar:
        st.metric("HARGA PASAR AKTUAL", f"Rp {harga_pasar:,.0f}")

    # ============================================================
    # KETERANGAN GAMBLANG (SESUAI PERMINTAAN ANDA)
    # ============================================================
    st.markdown("---")
    
    # Skenario 1: Harga Pasar Jatuh di Bawah TERP (seperti kasus 372 vs 466)
    if harga_pasar < terp:
        st.error(f"🚨 **PASAR PANIK!** Harga pasar (Rp {harga_pasar:,.0f}) jatuh jauh di bawah TERP (Rp {terp:,.0f}). Ini artinya pasar tidak suka dengan aksi right issue ini.")
        
        if harga_tebus >= harga_pasar:
            st.warning(f"⛔ **REKOMENDASI: JANGAN TEBUS RIGHT ISSUE!**\n\nKarena Harga Tebus (Rp {harga_tebus:,.0f}) lebih mahal dari Harga Pasar (Rp {harga_pasar:,.0f}), jika Anda menebus, Anda langsung rugi. Lebih baik jual HMETD Anda di pasar, atau beli saham langsung di pasar dengan harga yang lebih murah (Rp {harga_pasar:,.0f}).")
        else:
            st.success(f"✅ **REKOMENDASI: ANDA BISA PERTIMBANGKAN TEBUS.**\n\nHarga Tebus (Rp {harga_tebus:,.0f}) masih lebih murah dari Harga Pasar (Rp {harga_pasar:,.0f}). Namun, karena pasar sedang turun, pastikan Anda yakin dengan fundamental perusahaan.")
            
    # Skenario 2: Harga Pasar Normal (di atas TERP)
    else:
        st.success(f"✅ **PASAR NORMAL.** Harga pasar (Rp {harga_pasar:,.0f}) sesuai atau di atas TERP (Rp {terp:,.0f}).")
        
        if harga_tebus < harga_pasar:
            st.info(f"💡 **REKOMENDASI: TEBUS RIGHT ISSUE.**\n\nHarga Tebus (Rp {harga_tebus:,.0f}) lebih murah dari Harga Pasar (Rp {harga_pasar:,.0f}). Anda mendapat 'diskon' jika menebus saham baru ini.")
        else:
            st.warning(f"⚠️ **HARGA TEBUS TERLALU MAHAL.**\n\nHarga Tebus (Rp {harga_tebus:,.0f}) lebih mahal dari Harga Pasar (Rp {harga_pasar:,.0f}). Lebih baik tidak menebus dan beli langsung di pasar.")

    # ============================================================
    # SIMULASI UANG
    # ============================================================
    st.markdown("### Simulasi Uang")
    
    # Skenario Jika Menebus
    nilai_akhir_tebus = total_lembar_akhir * harga_pasar
    modal_total_tebus = nilai_awal + biaya_tebus
    pnl_tebus = nilai_akhir_tebus - modal_total_tebus
    
    # Skenario Jika Tidak Menebus
    nilai_akhir_dilusi = lembar_lama * harga_pasar
    kerugian_dilusi = nilai_akhir_dilusi - nilai_awal
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            f'<div style="background:#131a2a; border:1px solid #1e293b; border-left:4px solid #10b981; border-radius:8px; padding:16px;">'
            f'<div style="font-size:14px; font-weight:800; color:#10b981; margin-bottom:8px;">Jika IKUT Menebus</div>'
            f'<div style="font-size:13px; color:#cbd5e1; margin-bottom:4px;">Biaya tebus: Rp {biaya_tebus:,.0f}</div>'
            f'<div style="font-size:13px; color:#cbd5e1; margin-bottom:4px;">Total Lot jadi: {lot_lama + lot_baru:,.0f} Lot</div>'
            f'<div style="font-size:14px; font-weight:700; color:{"#10b981" if pnl_tebus >= 0 else "#f43f5e"}; margin-top:8px;">Hasil: {"Untung" if pnl_tebus >= 0 else "Rugi"} Rp {abs(pnl_tebus):,.0f}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    with col2:
        st.markdown(
            f'<div style="background:#131a2a; border:1px solid #1e293b; border-left:4px solid #f43f5e; border-radius:8px; padding:16px;">'
            f'<div style="font-size:14px; font-weight:800; color:#f43f5e; margin-bottom:8px;">Jika TIDAK Menebus (Dilusi)</div>'
            f'<div style="font-size:13px; color:#cbd5e1; margin-bottom:4px;">Biaya tebus: Rp 0</div>'
            f'<div style="font-size:13px; color:#cbd5e1; margin-bottom:4px;">Total Lot jadi: {lot_lama:,.0f} Lot (Tetap)</div>'
            f'<div style="font-size:14px; font-weight:700; color:{"#10b981" if kerugian_dilusi >= 0 else "#f43f5e"}; margin-top:8px;">Hasil: {"Untung" if kerugian_dilusi >= 0 else "Rugi"} Rp {abs(kerugian_dilusi):,.0f}</div>'
            f'</div>',
            unsafe_allow_html=True
        )