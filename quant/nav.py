"""Sidebar user card + tombol logout + menu — untuk semua halaman."""

import streamlit as st


MENU = [
    ("Dashboard",   "views/Dashboard.py",   ":material/dashboard:"),
    ("Fundamental", "views/Fundamental.py", ":material/analytics:"),
    ("Technical",   "views/Technical.py",   ":material/trending_up:"),
    ("Watchlist",   "views/Watchlist.py",   ":material/star:"),
    ("Valuation",   "views/Valuation.py",   ":material/payments:"),
    ("News",        "views/News.py",        ":material/newspaper:"),
    ("Money Flow",  "views/Money_Flow.py",  ":material/water_drop:"),
    ("Right Issue", "views/Kalkulator_Right_Issue.py", ":material/calculate:"),
]


def render_user_sidebar():
    """Render user card + logout + menu di sidebar."""
    with st.sidebar:
        name = st.session_state.get("name", "User")
        username = st.session_state.get("username", "user")

        # ---------- User card (Monokrom) ----------
        st.markdown(
            f'<div style="padding:16px; background:#171717; '
            f'border:1px solid #27272a; border-radius:8px; '
            f'margin-bottom:16px;">'
            f'<div style="font-size:11px; color:#a3a3a3; font-weight:700; '
            f'letter-spacing:1px;">LOGGED IN</div>'
            f'<div style="font-size:16px; color:#ffffff; font-weight:800; '
            f'margin-top:8px; letter-spacing:-0.02em;">{name}</div>'
            f'<div style="font-size:12px; color:#737373; margin-top:4px;">'
            f'@{username}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # ---------- Logout (Monokrom) ----------
        if st.button("Logout", use_container_width=True,
                     key="_sidebar_logout_btn"):
            for k in ["authentication_status", "name", "username"]:
                st.session_state[k] = None
            st.rerun()

        # ---------- Menu ----------
        st.markdown(
            '<div style="font-size:10px; color:#737373; font-weight:800; '
            'letter-spacing:1.5px; margin:24px 0 8px 6px;">MENU</div>',
            unsafe_allow_html=True
        )
        for label, path, icon in MENU:
            try:
                st.page_link(path, label=label, icon=icon)
            except Exception:
                pass