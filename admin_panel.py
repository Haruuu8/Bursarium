"""Admin Panel — Monokrom Style (Gambar & Form Selalu Muncul)"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant.theme import load_theme, page_header
from quant.auth import (
    list_pending, list_approved, approve_registration,
    reject_registration, list_all_users, 
    update_user_credentials, delete_user 
)

load_theme()

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", ""))

if not ADMIN_PASSWORD:
    st.error("ADMIN_PASSWORD env var / secret belum di-set.")
    st.stop()

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ==========================================
# FORM LOGIN ADMIN
# ==========================================
if not st.session_state.admin_logged_in:
    st.markdown(
        '<div style="background:#141414; border:1px solid #27272a; '
        'border-radius:12px; padding:32px 40px; margin-bottom:32px;">'
        '<div style="font-size:11px; color:#737373; font-weight:700; letter-spacing:1.5px; margin-bottom:12px;">'
        'KHUSUS ADMIN</div>'
        '<div style="font-size:36px; font-weight:800; color:#ffffff; letter-spacing:-0.04em;">Admin Panel</div>'
        '</div>', unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("admin_login"):
            st.markdown("<div style='text-align:center; margin-bottom:15px; color:#a3a3a3; font-size:14px;'>Masukkan password untuk melanjutkan</div>", unsafe_allow_html=True)
            pwd = st.text_input("Password Admin", type="password", label_visibility="collapsed", placeholder="Password...")
            submit = st.form_submit_button("LOGIN", use_container_width=True)
            if submit:
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Password salah")
    st.stop()

# ==========================================
# HEADER SETELAH LOGIN
# ==========================================
st.markdown(
    '<div style="background:#141414; border:1px solid #27272a; '
    'border-radius:12px; padding:32px 40px; margin-bottom:24px;">'
    '<div style="font-size:11px; color:#737373; font-weight:700; letter-spacing:1.5px; margin-bottom:12px;">'
    'APPROVE · REJECT · KELOLA USER</div>'
    '<div style="font-size:36px; font-weight:800; color:#ffffff; letter-spacing:-0.04em;">Admin Panel</div>'
    '</div>', unsafe_allow_html=True
)

col_logout, _ = st.columns([1, 4])
with col_logout:
    if st.button("LOGOUT ADMIN", use_container_width=True):
        st.session_state.admin_logged_in = False
        st.rerun()

# Tabs tanpa emoji
tab1, tab2, tab3 = st.tabs(["PENDING", "APPROVED", "STATISTIK"])

# ==========================================
# TAB 1: PENDING
# ==========================================
with tab1:
    pending = list_pending()
    if not pending:
        st.markdown(
            '<div style="background:#141414; border:1px solid #27272a; border-radius:8px; '
            'padding:24px; text-align:center; color:#737373;">'
            'Tidak ada registrasi pending saat ini.</div>', 
            unsafe_allow_html=True
        )
    else:
        # Banner Peringatan (Monokrom)
        st.markdown(
            f'<div style="background:#141414; border:1px solid #27272a; '
            f'border-radius:8px; padding:16px 20px; margin-bottom:24px; display:flex; align-items:center; gap:12px;">'
            f'<span style="font-size:16px; color:#ffffff; font-weight:900;">!</span>'
            f'<span style="color:#a3a3a3; font-size:14px;"><b>{len(pending)} registrasi</b> menunggu persetujuan Anda.</span>'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        for r in pending:
            reg_id = r.get("reg_id", "?")
            tele = r.get("telegram", "?")
            submitted = r.get("submitted_at", "?")[:19].replace("T", " ")
            bukti = r.get("bukti_file", "")

            # Card Header User Info
            st.markdown(
                f'<div style="background:#141414; border:1px solid #27272a; border-left:4px solid #ffffff; '
                f'border-radius:8px; padding:24px 28px; margin-bottom:16px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">'
                f'<div>'
                f'<div style="font-size:11px; color:#737373; font-weight:700; letter-spacing:1.5px; margin-bottom:6px;">{reg_id}</div>'
                f'<div style="font-size:22px; font-weight:700; color:#ffffff;">{tele}</div>'
                f'</div>'
                f'<div style="background:#1f1f1f; padding:6px 12px; border-radius:6px; font-size:12px; color:#a3a3a3; font-weight:500;">'
                f'{submitted}</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

            c1, c2 = st.columns([1, 1.5], gap="large")
            
            # ==========================================
            # KOLOM KIRI: BUKTI TRANSFER
            # ==========================================
            with c1:
                st.markdown("<div style='font-size:11px; color:#737373; font-weight:700; letter-spacing:1px; margin-bottom:10px;'>BUKTI TRANSFER</div>", unsafe_allow_html=True)
                
                if bukti:
                    # Cek apakah bukti berupa URL (Supabase Storage)
                    if bukti.startswith("http://") or bukti.startswith("https://"):
                        st.markdown('<div style="background:#141414; padding:10px; border-radius:8px; border:1px solid #27272a;">', unsafe_allow_html=True)
                        st.image(bukti, use_container_width=True, caption="")
                        st.markdown('</div>', unsafe_allow_html=True)
                    # Cek apakah bukti berupa file lokal
                    elif os.path.exists(bukti):
                        if bukti.lower().endswith((".jpg", ".jpeg", ".png")):
                            st.markdown('<div style="background:#141414; padding:10px; border-radius:8px; border:1px solid #27272a;">', unsafe_allow_html=True)
                            st.image(bukti, use_container_width=True, caption="")
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="background:#141414; border:1px solid #27272a; padding:16px; border-radius:8px; color:#a3a3a3; font-size:13px;">FILE: {os.path.basename(bukti)}</div>', unsafe_allow_html=True)
                            with open(bukti, "rb") as f:
                                st.download_button("DOWNLOAD BUKTI", f.read(), file_name=os.path.basename(bukti), key=f"dl_{reg_id}", use_container_width=True)
                    # Jika file lokal tapi terhapus
                    else:
                        st.markdown(
                            f'<div style="background:#141414; border:1px dashed #404040; border-radius:8px; '
                            f'padding:40px 20px; text-align:center; color:#737373; font-size:13px;">'
                            f'File gambar tidak ditemukan di server.<br><br><span style="font-size:10px; word-break:break-all;">{bukti}</span></div>', 
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown(
                        '<div style="background:#141414; border:1px dashed #404040; border-radius:8px; '
                        'padding:40px 20px; text-align:center; color:#737373; font-size:13px;">'
                        'Tidak ada lampiran bukti transfer.</div>', 
                        unsafe_allow_html=True
                    )
            
            # ==========================================
            # KOLOM KANAN: FORM AKSI
            # ==========================================
            with c2:
                st.markdown("<div style='font-size:11px; color:#737373; font-weight:700; letter-spacing:1px; margin-bottom:10px;'>TINDAKAN ADMIN</div>", unsafe_allow_html=True)
                
                with st.container(border=True):
                    with st.form(key=f"form_approve_{reg_id}"):
                        st.markdown("**Buat Kredensial User**")
                        st.markdown("<div style='font-size:12px; color:#737373; margin-bottom:12px;'>Biarkan kosong jika ingin generate otomatis.</div>", unsafe_allow_html=True)
                        
                        new_user = st.text_input("Username", key=f"u_{reg_id}")
                        new_pass = st.text_input("Password", key=f"p_{reg_id}")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            submit_approve = st.form_submit_button("APPROVE", type="primary", use_container_width=True)
                        with col_btn2:
                            submit_reject = st.form_submit_button("REJECT", use_container_width=True)
                        
                        if submit_approve:
                            result = approve_registration(reg_id, custom_username=new_user, custom_password=new_pass)
                            if result.get("success"):
                                st.success(f"Approved! Username: `{result['username']}` | Pass: `{result['password']}`")
                                st.balloons()
                                st.stop()
                            else:
                                st.error(f"Gagal: {result.get('error')}")
                                
                        if submit_reject:
                            reject_registration(reg_id, "Bukti tidak valid")
                            st.warning("Registrasi ditolak."); st.rerun()
            
            st.markdown("<hr style='border-color:#27272a; margin: 30px 0;'>", unsafe_allow_html=True)

# ==========================================
# TAB 2: APPROVED
# ==========================================
with tab2:
    approved = list_approved()
    if not approved:
        st.markdown(
            '<div style="background:#141414; border:1px solid #27272a; border-radius:8px; '
            'padding:24px; text-align:center; color:#737373;">'
            'Belum ada user yang di-approve.</div>', 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div style="font-size:14px; color:#a3a3a3; margin-bottom:20px;">'
            f'Total: <b style="color:#ffffff;">{len(approved)}</b> user aktif</div>', 
            unsafe_allow_html=True
        )
        
        for r in approved:
            reg_id = r.get("reg_id", "?")
            tele = r.get("telegram", "?")
            uname = r.get("username", "?")
            approved_at = r.get("approved_at", "?")[:19].replace("T", " ")

            with st.container():
                # Card Informasi User (Monokrom + Garis Putih Kiri)
                st.markdown(
                    f'<div style="background:#141414; border:1px solid #27272a; border-left:4px solid #ffffff; '
                    f'border-radius:8px; padding:24px 28px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">'
                    f'<div>'
                    f'<div style="font-size:20px; font-weight:700; color:#ffffff;">{uname}</div>'
                    f'<div style="font-size:14px; color:#a3a3a3; margin-top:4px;">{tele}</div>'
                    f'</div>'
                    f'<div style="text-align:right; font-size:12px; color:#737373;">'
                    f'Approved<br><b style="color:#a3a3a3;">{approved_at}</b>'
                    f'</div></div>', unsafe_allow_html=True
                )
                
                col_del, col_edit = st.columns([1, 2])
                with col_del:
                    if st.button(f"HAPUS USER", key=f"del_{reg_id}", type="primary", use_container_width=True):
                        if delete_user(reg_id):
                            st.success(f"User {uname} dihapus.")
                            st.rerun()
                        else:
                            st.error("Gagal menghapus.")
                
                with col_edit:
                    with st.expander("UBAH KREDENSIAL"):
                        with st.form(key=f"form_cred_{reg_id}"):
                            new_uname = st.text_input("Username Baru", value=uname)
                            new_pass = st.text_input("Password Baru", placeholder="Biarkan kosong jika tidak diubah", type="password")
                            
                            if st.form_submit_button("SIMPAN PERUBAHAN", type="primary"):
                                res = update_user_credentials(reg_id, new_username=new_uname, new_password=new_pass)
                                if res.get("success"):
                                    st.success(f"Berhasil diupdate!\n\nUsername: `{res['username']}`\n\nPassword: `{res['password']}`")
                                else:
                                    st.error(f"Gagal: {res.get('error')}")
                
                st.markdown("<hr style='border-color:#27272a; margin: 15px 0;'>", unsafe_allow_html=True)

# ==========================================
# TAB 3: STATISTIK
# ==========================================
with tab3:
    pending = list_pending()
    approved = list_approved()
    users = list_all_users()
    
    c1, c2, c3 = st.columns(3, gap="large")
    for col, label, val in [
        (c1, "PENDING", len(pending)),
        (c2, "APPROVED", len(approved)),
        (c3, "TOTAL AKTIF", len(users)),
    ]:
        with col:
            st.markdown(
                f'<div style="background:#141414; border:1px solid #27272a; '
                f'border-radius:8px; padding:24px 20px; text-align:center;">'
                f'<div style="font-size:11px; color:#737373; font-weight:700; letter-spacing:1.5px;">{label}</div>'
                f'<div style="font-size:36px; font-weight:800; color:#ffffff; margin-top:8px;">{val}</div></div>',
                unsafe_allow_html=True
            )