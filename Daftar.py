"""Entry point — Landing page + admin routing + navigasi halaman."""
import os
import sys
import yaml
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant.theme import load_theme, hero, section_title, info_banner
from quant.auth import submit_registration, get_all_approved_users_for_auth

st.set_page_config(page_title="Bursarium", layout="wide")
load_theme()

try:
    import streamlit_authenticator as stauth
except ImportError:
    st.error("Install: py -m pip install streamlit-authenticator bcrypt")
    st.stop()

if "logout" not in st.session_state:
    st.session_state["logout"] = False

# ============ ADMIN ROUTING ============
ADMIN_SECRET = st.secrets.get("ADMIN_SECRET", os.environ.get("ADMIN_SECRET", ""))
admin_key = st.query_params.get("admin", "")
if admin_key:
    if not ADMIN_SECRET or admin_key != ADMIN_SECRET:
        st.markdown('<div style="text-align:center; padding:120px 20px;"><div style="font-size:80px; font-weight:900; color:#1e2942; letter-spacing:-0.05em;">404</div><div style="font-size:16px; color:#64748b; margin-top:12px;">Halaman tidak ditemukan</div></div>', unsafe_allow_html=True)
        st.stop()
    exec(open("admin_panel.py", encoding="utf-8-sig").read())
    st.stop()

# ============ CONFIG ============
if "CONFIG_YAML" in st.secrets:
    config = yaml.safe_load(st.secrets["CONFIG_YAML"])
else:
    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

# Ambil user dari Database Supabase
db_users = get_all_approved_users_for_auth()
if db_users:
    config["credentials"]["usernames"].update(db_users)

# ============ INISIALISASI AUTHENTICATOR ============
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# ============ KALAU SUDAH LOGIN → NAVIGASI HALAMAN ============
if st.session_state.get("authentication_status"):
    pages = [
        st.Page("views/Dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page("views/Fundamental.py", title="Fundamental", icon=":material/analytics:"),
        st.Page("views/Technical.py", title="Technical", icon=":material/trending_up:"),
        st.Page("views/Watchlist.py", title="Watchlist", icon=":material/star:"),
        st.Page("views/Valuation.py", title="Valuation", icon=":material/payments:"),
        st.Page("views/News.py", title="News", icon=":material/newspaper:"),
    ]
    
    # PENTING: Tidak pakai position="hidden" agar tombol ☰ (3 garis) muncul
    pg = st.navigation(pages) 
    
    # Tampilkan info user di sidebar (jika ada)
    from quant.nav import render_user_sidebar
    render_user_sidebar() 
    
    pg.run()
    st.stop()

# ============ KALAU BELUM LOGIN → LANDING PAGE ============
# HERO SECTION
st.markdown(hero("📊 Bursarium", "Platform analisis saham IDX — fundamental, teknikal, screening, dan valuasi dalam satu tempat. Semua yang Anda butuhkan untuk ambil keputusan trading.", badge_text="PLATFORM ANALISIS SAHAM", badge_color="#06b6d4"), unsafe_allow_html=True)

# MEMBUAT TAB UNTUK LOGIN DAN DAFTAR
tab_login, tab_daftar = st.tabs(["🔐 Login", "📝 Daftar Sekarang"])

# ==========================================
# ISI TAB 1: LOGIN
# ==========================================
with tab_login:
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div style="text-align:center; margin-bottom:20px;"><div style="font-size:24px; font-weight:800; color:#ffffff;">Masuk ke Akun Anda</div><div style="font-size:13px; color:#94a3b8;">Silakan login untuk mengakses dashboard</div></div>', unsafe_allow_html=True)
        
        authenticator.login(location="main")
        
        if st.session_state.get("authentication_status") is False:
            st.error("❌ Username atau password salah")
        
        st.markdown('<div style="text-align:center; margin-top:20px; font-size:13px; color:#94a3b8;">Belum punya akun? Silakan klik tab <b>Daftar Sekarang</b> di atas.</div>', unsafe_allow_html=True)

# ==========================================
# ISI TAB 2: DAFTAR & MARKETING
# ==========================================
with tab_daftar:
    st.markdown(section_title("✨ Yang Anda Dapatkan"), unsafe_allow_html=True)
    FITUR = [
        ("Dashboard", "Ringkasan market & watchlist harian"), 
        ("Fundamental", "Analisis rasio keuangan & valuasi emiten IDX"), 
        ("Technical", "Chart, RSI, support-resistance, pre-cross setup"), 
        ("Watchlist", "Pantau saham favorit Anda"), 
        ("Valuation", "Hitung valuasi & risk/reward otomatis"), 
        ("News", "Berita terkini seputar pasar IDX")
    ]
    cols = st.columns(2)
    for i, (nama, desk) in enumerate(FITUR):
        with cols[i % 2]:
            st.markdown(f'<div style="background:#0d1424; border:1px solid #1e2942; border-left:3px solid #6366f1; border-radius:12px; padding:18px 22px; margin-bottom:12px;"><div style="font-size:16px; font-weight:800; color:#ffffff; margin-bottom:8px;">{nama}</div><div style="font-size:13px; color:#94a3b8; line-height:1.5;">{desk}</div></div>', unsafe_allow_html=True)

    st.markdown(section_title("💰 Harga"), unsafe_allow_html=True)
    st.markdown(f'<div style="background:linear-gradient(135deg, #131a2e 0%, #0a1020 100%); border:1px solid #2c3a5c; border-radius:16px; padding:32px 36px; text-align:center; margin-bottom:12px;"><div style="font-size:12px; color:#a5a8d8; font-weight:800; letter-spacing:2px; margin-bottom:12px;">AKSES PENUH PLATFORM</div><div style="font-size:48px; font-weight:900; color:#ffffff; letter-spacing:-0.04em; line-height:1;">Rp 200.000<span style="font-size:16px; color:#94a3b8; font-weight:600; margin-left:8px;">/ bulan</span></div><div style="font-size:13px; color:#94a3b8; margin-top:14px;">Akses semua fitur tanpa batas · Bayar bulanan · Cancel kapan saja</div></div>', unsafe_allow_html=True)

    st.markdown(section_title("📝 Form Pendaftaran"), unsafe_allow_html=True)
    st.markdown(info_banner("Transfer <b>Rp 200.000</b> ke salah satu e-wallet di bawah, lalu upload bukti. Akun di-approve manual dalam <b>1×24 jam</b>. Username & password dikirim via Telegram.", "info"), unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f'<div style="background:linear-gradient(135deg, #131a2e 0%, #0a1020 100%); border:1px solid #2c3a5c; border-radius:14px; padding:24px 28px; margin-bottom:20px;"><div style="font-size:11px; color:#a5a8d8; font-weight:800; letter-spacing:1.5px; margin-bottom:18px;">TRANSFER KE SALAH SATU</div><div style="display:flex; justify-content:space-between; align-items:center; padding:14px 0; border-bottom:1px solid #1e2942;"><div style="font-size:15px; font-weight:700; color:#e6ebf5;">OVO</div><div style="font-size:20px; font-weight:900; color:#ffffff; font-family:monospace; letter-spacing:1px;">082369477717</div></div><div style="display:flex; justify-content:space-between; align-items:center; padding:14px 0 0 0;"><div style="font-size:15px; font-weight:700; color:#e6ebf5;">GoPay</div><div style="font-size:20px; font-weight:900; color:#ffffff; font-family:monospace; letter-spacing:1px;">082369477717</div></div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3); border-radius:12px; padding:16px 20px; height:100%;"><div style="font-size:11px; font-weight:800; color:#f59e0b; letter-spacing:0.5px; margin-bottom:12px;">⚠ PENTING</div><div style="font-size:12px; color:#cbd5e1; line-height:1.9;">Transfer <b style="color:#fbbf24;">tepat</b> Rp 200.000<br>Bukti harus jelas:<br>• Tanggal<br>• Nominal<br>• Status berhasil</div></div>', unsafe_allow_html=True)

    with st.form("form_daftar", clear_on_submit=False):
        telegram = st.text_input("Username Telegram * (untuk kirim username & password)", placeholder="Contoh: @johndoe", max_chars=64)
        bukti = st.file_uploader("Bukti Transfer * (JPG/PNG/PDF, max 5 MB)", type=["jpg", "jpeg", "png", "pdf"])
        setuju = st.checkbox("Saya sudah transfer dan data yang saya isi benar *")
        submit = st.form_submit_button("🚀 Kirim Pendaftaran", type="primary", use_container_width=True)
        if submit:
            errors = []
            tele_clean = telegram.strip().lstrip("@")
            import re
            if not tele_clean: errors.append("Username Telegram wajib diisi")
            elif not re.match(r"^[a-zA-Z0-9_]{4,32}$", tele_clean): errors.append("Username Telegram tidak valid (4-32 karakter, hanya huruf/angka/underscore)")
            if bukti is None: errors.append("Bukti transfer wajib diupload")
            if not setuju: errors.append("Centang persetujuan")
            if errors:
                for e in errors: st.error(f"❌ {e}")
            else:
                file_bytes = bukti.getvalue()
                if len(file_bytes) > 5 * 1024 * 1024: st.error("❌ File terlalu besar (max 5 MB)")
                else:
                    try:
                        reg_id = submit_registration(telegram="@" + tele_clean, bukti_bytes=file_bytes, bukti_filename=bukti.name)
                        st.success(f"✅ Pendaftaran BERHASIL!\n\nID Registrasi: **{reg_id}**\n\nAkun di-approve 1×24 jam. Username & password dikirim via Telegram.")
                        st.balloons()
                    except Exception as e: st.error(f"❌ Gagal submit: {e}")

st.markdown('<div style="text-align:center; padding:40px 20px 20px; font-size:12px; color:#64748b;">© 2026 Bursarium · IDX Analysis</div>', unsafe_allow_html=True)