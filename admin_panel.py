"""Admin Panel — HANYA bisa diakses via ?admin=SECRET_KEY di URL."""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant.theme import load_theme, page_header
from quant.auth import (
    list_pending, list_approved, approve_registration,
    reject_registration, list_all_users, reset_user_password, 
    update_username, delete_user
)

load_theme()

# Baca dari Secrets Cloud dulu, kalau tidak ada baru baca dari Env Lokal
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", ""))

if not ADMIN_PASSWORD:
    st.error("⚠ ADMIN_PASSWORD env var / secret belum di-set.")
    st.stop()

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.markdown(page_header("🔐", "Admin Panel", "Khusus admin"),
                unsafe_allow_html=True)
    with st.form("admin_login"):
        pwd = st.text_input("Password Admin", type="password")
        submit = st.form_submit_button("Login", type="primary")
        if submit:
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ Password salah")
    st.stop()


st.markdown(page_header("🔐", "Admin Panel",
                        "Approve · Reject · Kelola User"),
            unsafe_allow_html=True)
if st.button("🚪 Logout Admin"):
    st.session_state.admin_logged_in = False
    st.rerun()
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["⏳ Pending", "✅ Approved", "📊 Statistik"])


with tab1:
    pending = list_pending()
    if not pending:
        st.info("Tidak ada registrasi pending.")
    else:
        st.markdown(
            f'<div style="background:rgba(245,158,11,0.08); '
            f'border:1px solid rgba(245,158,11,0.3); '
            f'border-radius:10px; padding:12px 18px; margin-bottom:20px;">'
            f'<b style="color:#f59e0b;">⚠ {len(pending)} registrasi</b> '
            f'menunggu approval.</div>', unsafe_allow_html=True
        )
        for r in pending:
            reg_id = r.get("reg_id", "?")
            tele = r.get("telegram", "?")
            submitted = r.get("submitted_at", "?")[:19]
            bukti = r.get("bukti_file", "")

            st.markdown(
                f'<div style="background:#0d1424; border:1px solid #1e2942; '
                f'border-left:3px solid #f59e0b; border-radius:12px; '
                f'padding:20px 24px; margin-bottom:14px;">'
                f'<div style="font-size:11px; color:#f59e0b; '
                f'font-weight:800; margin-bottom:8px;">🆕 {reg_id}</div>'
                f'<div style="font-size:20px; font-weight:800; '
                f'color:#ffffff;">✈️ {tele}</div>'
                f'<div style="font-size:11px; color:#7d8ba3; '
                f'margin-top:10px;">Submitted: {submitted}</div></div>',
                unsafe_allow_html=True
            )

            if bukti and os.path.exists(bukti):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    if bukti.lower().endswith((".jpg", ".jpeg", ".png")):
                        st.image(bukti, width=300, caption="Bukti Transfer")
                    else:
                        st.info(f"📎 {os.path.basename(bukti)}")
                        with open(bukti, "rb") as f:
                            st.download_button("Download", f.read(),
                                                file_name=os.path.basename(bukti),
                                                key=f"dl_{reg_id}")
                with c2:
                    if st.button("✅ APPROVE", key=f"ap_{reg_id}",
                                  type="primary", use_container_width=True):
                        result = approve_registration(reg_id)
                        if result.get("success"):
                            st.success(
                                f"✅ Approved!\n\n"
                                f"Username: `{result['username']}`\n\n"
                                f"Password: `{result['password']}`\n\n"
                                f"Kirim ke Telegram: **{result['telegram']}**"
                            )
                            st.balloons()
                            st.stop()
                        else:
                            st.error(f"Gagal: {result.get('error')}")
                with c3:
                    if st.button("❌ REJECT", key=f"rj_{reg_id}",
                                  use_container_width=True):
                        reject_registration(reg_id, "Bukti tidak valid")
                        st.warning("Rejected"); st.rerun()
                st.markdown("---")


with tab2:
    approved = list_approved()
    if not approved:
        st.info("Belum ada user yang di-approve.")
    else:
        st.markdown(
            f'<div style="font-size:13px; color:#94a3b8; margin-bottom:16px;">'
            f'Total: <b style="color:#10b981;">{len(approved)}</b> user aktif</div>', 
            unsafe_allow_html=True
        )
        
        for r in approved:
            reg_id = r.get("reg_id", "?")
            tele = r.get("telegram", "?")
            uname = r.get("username", "?")
            approved_at = r.get("approved_at", "?")[:19]

            with st.container():
                # Card Informasi User
                st.markdown(
                    f'<div style="background:#0d1424; border:1px solid #1e2942; '
                    f'border-left:3px solid #10b981; border-radius:12px; '
                    f'padding:16px 20px; margin-bottom:10px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<div>'
                    f'<div style="font-size:16px; font-weight:800; color:#ffffff;">{uname}</div>'
                    f'<div style="font-size:12px; color:#94a3b8; margin-top:2px;">{tele}</div>'
                    f'<div style="font-size:10px; color:#7d8ba3; margin-top:4px;">Approved: {approved_at}</div>'
                    f'</div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
                
                # Tombol Aksi (Reset & Hapus)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"🔄 Reset Password", key=f"reset_{reg_id}", use_container_width=True):
                        res = reset_user_password(reg_id)
                        if res.get("success"):
                            st.success(
                                f"✅ Password Baru untuk **{res['username']}**:\n\n"
                                f"Password: `{res['password']}`\n\n"
                                f"Kirim ke: **{res['telegram']}**"
                            )
                        else:
                            st.error(f"Gagal: {res.get('error')}")
                with col2:
                    if st.button(f"🗑️ Hapus User", key=f"del_{reg_id}", type="primary", use_container_width=True):
                        if delete_user(reg_id):
                            st.success(f"User {uname} berhasil dihapus.")
                            st.rerun()
                        else:
                            st.error("Gagal menghapus user.")
                
                # Form Ubah Username (disembunyikan dalam expander)
                with st.expander("✏️ Ubah Username"):
                    with st.form(key=f"form_uname_{reg_id}"):
                        new_uname = st.text_input("Username Baru", value=uname)
                        if st.form_submit_button("Simpan Username"):
                            if new_uname.strip() and new_uname != uname:
                                res = update_username(reg_id, new_uname.strip())
                                if res.get("success"):
                                    st.success(f"Username berhasil diubah menjadi: {res['new_username']}")
                                    st.rerun()
                                else:
                                    st.error(f"Gagal: {res.get('error')}")
                            elif new_uname == uname:
                                st.info("Username tidak berubah.")
                            else:
                                st.error("Username tidak boleh kosong.")
                
                st.markdown("<hr style='margin: 10px 0; border-color: #1e2942;'>", unsafe_allow_html=True)


with tab3:
    pending = list_pending()
    approved = list_approved()
    users = list_all_users()
    c1, c2, c3 = st.columns(3)
    for col, label, val, color in [
        (c1, "PENDING", len(pending), "#f59e0b"),
        (c2, "APPROVED", len(approved), "#10b981"),
        (c3, "AKTIF", len(users), "#06b6d4"),
    ]:
        with col:
            st.markdown(
                f'<div style="background:linear-gradient(180deg, #0d1424, #0a1020); '
                f'border:1px solid #1e2942; border-left:3px solid {color}; '
                f'border-radius:12px; padding:20px 24px;">'
                f'<div style="font-size:11px; color:#7d8ba3; '
                f'font-weight:700;">{label}</div>'
                f'<div style="font-size:32px; font-weight:900; '
                f'color:{color}; margin-top:8px;">{val}</div></div>',
                unsafe_allow_html=True
            )