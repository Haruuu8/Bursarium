"""Theme Notion-Style — Flat, Soft Dark, Minimalist."""

import streamlit as st

COLORS = {
    "bg": "#191919",         # Background utama (seperti Notion)
    "surface": "#202020",    # Card / Kotak (sedikit lebih terang)
    "elevated": "#2c2c2c",   # Hover state
    "border": "#2c2c2c",     # Garis tepi sangat halus
    "text": "#e0e0e0",       # Teks utama (putih tulang)
    "muted": "#9a9a9a",      # Teks sekunder
    "primary": "#2383e2",    # Notion Blue
}

THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, Helvetica, Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
html { scroll-behavior: smooth; }

/* Animasi Fade-in */
@keyframes fadeIn { from { opacity:0;} to { opacity:1;} }

.stApp {
    background: #191919;
    color: #e0e0e0;
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent !important; }

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1100px !important;
}

/* SIDEBAR */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebar"] {
    background: #191919 !important;
    border-right: 1px solid #2c2c2c !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }

h1, h2, h3, h4, h5, h6 {
    color: #e0e0e0 !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
}

/* BUTTONS (Notion Style) */
.stButton > button, .stDownloadButton > button {
    background: #2c2c2c !important;
    border: none !important;
    color: #e0e0e0 !important;
    border-radius: 4px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 6px 14px !important;
    transition: background 0.2s ease !important;
}
.stButton > button:hover {
    background: #3a3a3a !important;
}
/* Tombol Primary (Biru Notion) */
.stButton > button[kind="primary"], .stFormSubmitButton > button {
    background: #2383e2 !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
    background: #1a6dc0 !important;
}

/* INPUTS (Flat, Soft Background) */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stSelectbox > div > div {
    background: #202020 !important;
    border: 1px solid #2c2c2c !important;
    border-radius: 4px !important;
    color: #e0e0e0 !important;
    padding: 8px 12px !important;
    transition: border-color 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: #2383e2 !important;
    outline: none !important;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: transparent !important;
    border-bottom: 1px solid #2c2c2c !important;
}
.stTabs [data-baseweb="tab"] {
    color: #9a9a9a !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 8px 12px !important;
    border-radius: 4px 4px 0 0 !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.2s ease, background 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #e0e0e0 !important;
    background: #202020 !important;
}
.stTabs [aria-selected="true"] {
    color: #e0e0e0 !important;
    border-bottom: 2px solid #e0e0e0 !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* EXPANDER, POPOVER, DATAFRAME */
[data-testid="stExpander"] {
    background: #202020 !important;
    border: 1px solid #2c2c2c !important;
    border-radius: 6px !important;
}
[data-testid="stPopover"] > button {
    background: #2383e2 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 4px !important;
}
[data-testid="stPopoverBody"] {
    background: #202020 !important;
    border: 1px solid #2c2c2c !important;
    border-radius: 6px !important;
}
[data-testid="stDataFrame"], [data-testid="stMetric"] {
    background: #202020 !important;
    border: 1px solid #2c2c2c !important;
    border-radius: 6px !important;
}

/* PAGE LINK */
[data-testid="stPageLink"] {
    padding: 6px 10px !important;
    border-radius: 4px !important;
    color: #9a9a9a !important;
    transition: background 0.2s ease, color 0.2s ease !important;
}
[data-testid="stPageLink"]:hover {
    background: #2c2c2c !important;
    color: #e0e0e0 !important;
}
[data-testid="stPageLink"][aria-current="page"] {
    background: #2c2c2c !important;
    color: #e0e0e0 !important;
    font-weight: 600 !important;
}

/* HIDE BRANDING */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stAppDeployButton"] { display: none !important; }
</style>
"""

def load_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)

def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"

# ============================================================
# KOMPONEN UI KUSTOM (Notion Style)
# ============================================================

def hero(title, subtitle, badge_text="", badge_color="#2383e2"):
    badge_html = ""
    if badge_text:
        badge_html = (
            f'<div style="display: inline-block; padding: 2px 8px; '
            f'background: #2c2c2c; color: #e0e0e0; '
            f'border-radius: 4px; font-size: 12px; font-weight: 500; '
            f'margin-bottom: 12px;">'
            f'{badge_text}</div>'
        )
    return (
        f'<div class="hero-title" style="'
        f'padding: 24px 0; margin-bottom: 20px; '
        f'animation: fadeIn 0.3s ease-out;">'
        f'{badge_html}'
        f'<div style="font-size: 40px; font-weight: 700; color: #e0e0e0; '
        f'letter-spacing: -0.02em; line-height: 1.1; margin-bottom: 8px;">'
        f'{title}</div>'
        f'<div style="font-size: 16px; color: #9a9a9a; line-height: 1.5; '
        f'max-width: 640px;">{subtitle}</div>'
        f'</div>'
    )


def page_header(icon, title, subtitle=""):
    icon_html = f'<div style="font-size: 24px; margin-right: 12px; opacity: 0.8;">{icon}</div>' if icon else ''
    return (
        f'<div style="padding: 12px 0; margin-bottom: 24px; '
        f'display: flex; align-items: center; '
        f'animation: fadeIn 0.3s ease-out;">'
        f'{icon_html}'
        f'<div>'
        f'<div style="font-size: 12px; color: #9a9a9a; font-weight: 500; margin-bottom: 2px;">{subtitle}</div>'
        f'<div style="font-size: 26px; font-weight: 600; color: #e0e0e0; '
        f'letter-spacing: -0.02em; line-height: 1.1;">{title}</div>'
        f'</div></div>'
    )


def section_title(title, subtitle=""):
    sub_html = f'<div style="font-size: 14px; color: #9a9a9a; margin-top: 4px;">{subtitle}</div>' if subtitle else ''
    return (
        '<div style="margin: 32px 0 16px;">'
        f'<div style="font-size: 20px; font-weight: 600; color: #e0e0e0;">{title}</div>'
        f'{sub_html}'
        '</div>'
    )


def card(content, padding="16px 20px", accent=None):
    return (
        '<div style="'
        'background: #202020; '
        'border: 1px solid #2c2c2c; border-radius: 6px; '
        f'padding: {padding}; margin-bottom: 12px;">'
        f'{content}'
        '</div>'
    )


def metric_box(label, value, sub="", accent="#e0e0e0"):
    sub_html = f'<div style="font-size: 12px; color: #9a9a9a; margin-top: 6px;">{sub}</div>' if sub else ''
    return (
        '<div style="'
        'background: #202020; '
        'border: 1px solid #2c2c2c; border-radius: 6px; '
        'padding: 16px 20px;">'
        f'<div style="font-size: 13px; color: #9a9a9a; '
        f'font-weight: 500; margin-bottom: 8px;">'
        f'{label}</div>'
        f'<div style="font-size: 24px; font-weight: 600; color: #e0e0e0;">{value}</div>'
        f'{sub_html}'
        '</div>'
    )


def stat_card(label, value, delta=None, sub="", accent="#e0e0e0"):
    delta_html = ""
    if delta is not None:
        try:
            v = float(delta)
            color = "#e0e0e0" if v >= 0 else "#9a9a9a"
            sign = "+" if v >= 0 else ""
            delta_html = (
                f'<div style="display: inline-block; padding: 2px 6px; '
                f'background: #2c2c2c; color: {color}; '
                f'border-radius: 4px; font-size: 12px; font-weight: 500; margin-left: 8px;">'
                f'{sign}{v:.2f}%</div>'
            )
        except Exception:
            pass
    sub_html = f'<div style="font-size: 12px; color: #9a9a9a; margin-top: 6px;">{sub}</div>' if sub else ''
    return (
        '<div style="'
        'background: #202020; '
        'border: 1px solid #2c2c2c; border-radius: 6px; '
        'padding: 16px 20px;">'
        f'<div style="font-size: 13px; color: #9a9a9a; '
        f'font-weight: 500; margin-bottom: 8px;">'
        f'{label}</div>'
        f'<div style="display: flex; align-items: baseline;">'
        f'<span style="font-size: 24px; font-weight: 600; color: #e0e0e0;">{value}</span>'
        f'{delta_html}'
        '</div>'
        f'{sub_html}'
        '</div>'
    )


def info_banner(text, type="info"):
    return (
        f'<div style="background: #202020; '
        f'border: 1px solid #2c2c2c; '
        f'border-left: 3px solid #e0e0e0; '
        f'border-radius: 6px; padding: 12px 16px; margin-bottom: 16px;">'
        f'<div style="font-size: 13px; color: #e0e0e0; line-height: 1.5;">'
        f'{text}</div>'
        '</div>'
    )


def badge(text, color="#2383e2"):
    return (
        f'<span style="display: inline-block; padding: 2px 8px; '
        f'background: #2c2c2c; color: #e0e0e0; '
        f'border-radius: 4px; '
        f'font-size: 12px; font-weight: 500;">{text}</span>'
    )


def divider():
    return '<div style="height: 1px; background: #2c2c2c; margin: 24px 0;"></div>'


def kv_row(label, value, accent="#e0e0e0"):
    return (
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; padding: 10px 0; '
        'border-bottom: 1px solid #2c2c2c;">'
        f'<span style="font-size: 14px; color: #9a9a9a;">{label}</span>'
        f'<span style="font-size: 14px; font-weight: 500; color: {accent};">'
        f'{value}</span>'
        '</div>'
    )


def spacer(height="16px"):
    return f'<div style="height: {height};"></div>'


def empty_state(icon, title, subtitle=""):
    return (
        '<div style="text-align: center; padding: 48px 24px; '
        'background: #202020; border: 1px dashed #2c2c2c; border-radius: 6px;">'
        f'<div style="font-size: 16px; font-weight: 500; color: #e0e0e0; margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 14px; color: #9a9a9a;">{subtitle}</div>'
        '</div>'
    )