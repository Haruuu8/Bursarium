"""Sidebar user card + tombol logout + menu — untuk semua halaman."""

import streamlit as st


MENU = [
    ("Dashboard",   "views/Dashboard.py",   "🏠"),
    ("Fundamental", "views/Fundamental.py", "📊"),
    ("Technical",   "views/Technical.py",   "📈"),
    ("Watchlist",   "views/Watchlist.py",   "⭐"),
    ("Valuation",   "views/Valuation.py",   "💰"),
    ("News",        "views/News.py",        "📰"),
    ("MoneyFlow",   "views/MoneyFlow.py",   "💸"),
    ("Kalkulator Right Issue", "views/Kalkulator_Right_Issue.py", "🧮"),
]


def render_user_sidebar():
    """Render user card + logout + menu di sidebar."""
    with st.sidebar:
        name = st.session_state.get("name", "User")
        username = st.session_state.get("username", "user")

        # ---------- User card ----------
        st.markdown(
            f'<div style="padding:14px; background:rgba(16,185,129,0.08); '
            f'border:1px solid rgba(16,185,129,0.3); border-radius:10px; '
            f'margin-bottom:14px;">'
            f'<div style="font-size:11px; color:#10b981; font-weight:700; '
            f'letter-spacing:0.5px;">LOGGED IN</div>'
            f'<div style="font-size:15px; color:#ffffff; font-weight:800; '
            f'margin-top:6px; letter-spacing:-0.02em;">{name}</div>'
            f'<div style="font-size:11px; color:#94a3b8; margin-top:2px;">'
            f'@{username}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # ---------- Logout ----------
        if st.button("🚪 Logout", use_container_width=True,
                     key="_sidebar_logout_btn"):
            for k in ["authentication_status", "name", "username"]:
                st.session_state[k] = None
            st.rerun()

        # ---------- Menu ----------
        st.markdown(
            '<div style="font-size:10px; color:#64748b; font-weight:800; '
            'letter-spacing:1.5px; margin:18px 0 8px 6px;">MENU</div>',
            unsafe_allow_html=True
        )
        for label, path, icon in MENU:
            try:
                st.page_link(path, label=label, icon=icon)
            except Exception:
                pass