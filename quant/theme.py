"""Theme minimalis premium — Strict Monokrom (Zinc Dark Mode)."""

import streamlit as st

COLORS = {
    "bg": "#09090b",         # Zinc 950 (Background Utama)
    "surface": "#18181b",    # Zinc 900 (Card/Kotak)
    "elevated": "#27272a",   # Zinc 800 (Hover)
    "border": "#27272a",     # Zinc 800
    "border_hi": "#3f3f46",  # Zinc 700
    "text": "#fafafa",       # Zinc 50
    "body": "#d4d4d8",       # Zinc 300
    "muted": "#a1a1aa",      # Zinc 400
    "dim": "#71717a",        # Zinc 500
}

THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', 'Roboto', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
html { scroll-behavior: smooth; }

.stApp {
    background: #09090b;
    color: #d4d4d8;
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent !important; }

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* SIDEBAR */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebar"] {
    background: #09090b !important;
    border-right: 1px solid #27272a !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }

h1, h2, h3, h4, h5, h6 {
    color: #fafafa !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

/* BUTTONS */
.stButton > button, .stDownloadButton > button {
    background: #18181b !important;
    border: 1px solid #27272a !important;
    color: #fafafa !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 8px 16px !important;
    transition: all 150ms ease !important;
}
.stButton > button:hover {
    background: #27272a !important;
    border-color: #3f3f46 !important;
}
.stButton > button[kind="primary"] {
    background: #fafafa !important;
    border: 1px solid #fafafa !important;
    color: #09090b !important;
}
.stButton > button[kind="primary"]:hover {
    background: #e4e4e7 !important;
    border-color: #e4e4e7 !important;
}

.stFormSubmitButton > button {
    background: #fafafa !important;
    border: 1px solid #fafafa !important;
    color: #09090b !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}

/* INPUTS */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: #09090b !important;
    border: 1px solid #27272a !important;
    border-radius: 6px !important;
    color: #fafafa !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
}
.stSelectbox > div > div {
    background: #09090b !important;
    border: 1px solid #27272a !important;
    border-radius: 6px !important;
    color: #fafafa !important;
}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: #71717a !important;
    box-shadow: none !important;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: transparent !important;
    border-bottom: 1px solid #27272a !important;
}
.stTabs [data-baseweb="tab"] {
    color: #a1a1aa !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 16px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #fafafa !important; }
.stTabs [aria-selected="true"] {
    color: #fafafa !important;
    border-bottom: 2px solid #fafafa !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* EXPANDER, POPOVER, DATAFRAME */
[data-testid="stExpander"] {
    background: #18181b !important;
    border: 1px solid #27272a !important;
    border-radius: 8px !important;
}
[data-testid="stPopover"] > button {
    background: #fafafa !important;
    border: 1px solid #fafafa !important;
    color: #09090b !important;
    font-weight: 600 !important;
}
[data-testid="stPopoverBody"] {
    background: #18181b !important;
    border: 1px solid #3f3f46 !important;
    border-radius: 8px !important;
}
[data-testid="stDataFrame"], [data-testid="stMetric"] {
    background: #18181b !important;
    border: 1px solid #27272a !important;
    border-radius: 8px !important;
}

/* PAGE LINK */
[data-testid="stPageLink"] {
    padding: 8px 12px !important;
    border-radius: 6px !important;
    color: #a1a1aa !important;
}
[data-testid="stPageLink"]:hover { background: #18181b !important; color: #fafafa !important; }
[data-testid="stPageLink"][aria-current="page"] {
    background: #27272a !important; color: #fafafa !important;
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

def page_header(icon, title, subtitle=""):
    return (
        '<div style="background: #18181b; border: 1px solid #27272a; border-radius: 8px; '
        'padding: 20px 24px; margin-bottom: 24px;">'
        f'<div style="font-size: 11px; color: #a1a1aa; letter-spacing: 0.5px; '
        f'font-weight: 500; margin-bottom: 4px; text-transform: uppercase;">{subtitle}</div>'
        f'<div style="font-size: 22px; font-weight: 600; color: #fafafa; '
        f'letter-spacing: -0.02em; line-height: 1;">{title}</div>'
        '</div>'
    )

def section_title(title, subtitle=""):
    sub_html = f'<div style="font-size: 13px; color: #a1a1aa; margin-top: 6px;">{subtitle}</div>' if subtitle else ''
    return (
        '<div style="margin: 28px 0 16px;">'
        '<div style="display: flex; align-items: center; gap: 10px;">'
        '<div style="width: 3px; height: 18px; background: #fafafa; border-radius: 2px;"></div>'
        f'<div style="font-size: 18px; font-weight: 600; color: #fafafa;">{title}</div>'
        '</div>'
        f'{sub_html}'
        '</div>'
    )

def empty_state(icon, title, subtitle=""):
    return (
        '<div style="text-align: center; padding: 48px 24px; '
        'background: #18181b; border: 1px dashed #27272a; border-radius: 8px;">'
        f'<div style="font-size: 16px; font-weight: 500; color: #fafafa; margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 13px; color: #a1a1aa;">{subtitle}</div>'
        '</div>'
    )