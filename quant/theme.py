"""Theme High-Contrast Monokrom — Premium & Clean (Mobile Ready)."""

import streamlit as st
import pandas as pd

COLORS = {
    "bg": "#0a0a0a",
    "surface": "#171717",
    "elevated": "#262626",
    "border": "#27272a",
    "border_hi": "#404040",
    "text": "#ffffff",
    "muted": "#a3a3a3",
    "dim": "#737373",
}

THEME_CSS = """
<style>
/* ============================================================
   BUNUH WARNA BIRU/MERAH BAWAAN STREAMLIT
   ============================================================ */
:root, .stApp {
    --primary-color: #ffffff !important;
    --primary-color-rgb: 255, 255, 255 !important;
}

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
html { scroll-behavior: smooth; }

/* ============================================================
   BUNUH SPINNER (RUNNING) TOTAL
   ============================================================ */
.stSpinner, [data-testid="stSpinner"], [data-testid="stStatusWidget"], 
[data-testid="stSpinnerContainer"], [data-testid="stLoadingIndicator"],
[data-testid="stStatusWidgetContainer"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    width: 0 !important;
    position: absolute !important;
    z-index: -9999 !important;
}

/* ============================================================
   ALERTS (INFO, SUCCESS, WARNING) JADI HITAM
   ============================================================ */
[data-testid="stNotification"], [data-testid="stAlert"] {
    background-color: #171717 !important;
    color: #ffffff !important;
    border: 1px solid #27272a !important;
    border-radius: 8px !important;
}
[data-testid="stNotification"] p, [data-testid="stAlert"] p,
[data-testid="stNotification"] span, [data-testid="stAlert"] span {
    color: #ffffff !important;
    font-weight: 500 !important;
}
[data-testid="stNotification"] svg, [data-testid="stAlert"] svg {
    display: none !important;
}

@keyframes fadeInUp { from { opacity:0; transform:translateY(10px);} to { opacity:1; transform:translateY(0);} }

.stApp {
    background: #0a0a0a;
    background-image: radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.03) 0%, transparent 50%);
    color: #a3a3a3;
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent !important; }

.block-container {
    padding-top: 3rem !important;
    padding-bottom: 2rem !important;
    max-width: 1250px !important;
}

/* ============================================================
   GLOBAL FOOTER
   ============================================================ */
.block-container::after {
    content: "© 2026 Bursarium · @bursarium · Data by Yahoo Finance";
    display: block;
    margin-top: 80px;
    padding: 30px 0 20px 0;
    border-top: 1px solid #27272a;
    color: #737373;
    text-align: center;
    font-size: 12px;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
    pointer-events: none;
}

/* SIDEBAR */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebar"] {
    background: #050505 !important;
    border-right: 1px solid #27272a !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

/* BUTTONS */
.stButton > button, .stDownloadButton > button {
    background: #171717 !important;
    border: 1px solid #27272a !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 8px 20px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #262626 !important;
    border-color: #404040 !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button {
    background: #ffffff !important;
    border: 1px solid #ffffff !important;
    color: #0a0a0a !important;
}
.stButton > button[kind="primary"]:hover {
    background: #e5e5e5 !important;
    border-color: #e5e5e5 !important;
    box-shadow: 0 0 15px rgba(255, 255, 255, 0.2);
}

/* ============================================================
   INPUTS & TOMBOL PLUS MINUS (NUMBER INPUT) - FIX TOTAL
   ============================================================ */
/* 1. Container Paling Luar */
div[data-testid="stNumberInput"] > div {
    background-color: #171717 !important; 
    border: 1px solid #404040 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    display: flex !important;
    flex-wrap: nowrap !important;
    box-shadow: none !important;
}

/* 2. Bunuh Semua Warna Background Biru di Layer Dalam BaseWeb */
div[data-testid="stNumberInput"] div[data-baseweb="input"],
div[data-testid="stNumberInput"] div[data-baseweb="base-input"],
div[data-testid="stNumberInput"] > div > div {
    background-color: transparent !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* 3. Elemen Input Teks Asli */
div[data-testid="stNumberInput"] input {
    background-color: transparent !important;
    color: #ffffff !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    padding: 10px 14px !important;
    flex: 1 !important;
    min-width: 0 !important;
    font-weight: 600 !important;
}

/* 4. Tombol Plus & Minus */
div[data-testid="stNumberInput"] button {
    background-color: #262626 !important;
    color: #ffffff !important;
    border: none !important;
    border-left: 1px solid #404040 !important;
    padding: 0 12px !important;
    margin: 0 !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    height: 100% !important;
}

div[data-testid="stNumberInput"] button:hover {
    background-color: #404040 !important;
}

div[data-testid="stNumberInput"] button svg {
    fill: #ffffff !important;
    color: #ffffff !important;
}

/* ============================================================
   CUSTOM SEARCH BAR / TEXT INPUT (FIX TOTAL WARNA BIRU)
   ============================================================ */
/* Container Luar */
div[data-testid="stTextInput"] > div[data-baseweb="input"] {
    background-color: #171717 !important; 
    border: 1px solid #404040 !important;
    border-radius: 50px !important; /* Membulat seperti searchbar */
    padding: 0 !important;
    overflow: hidden !important;
    transition: all 0.3s ease !important;
    box-shadow: none !important;
}

/* Layer Dalam BaseWeb (Tempat warna biru gelap bersembunyi) */
div[data-testid="stTextInput"] > div[data-baseweb="input"] > div {
    background-color: transparent !important; 
    border: none !important;
    box-shadow: none !important;
}

/* Elemen Input Asli */
div[data-testid="stTextInput"] input {
    background-color: transparent !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 12px 20px !important;
    font-size: 15px !important;
    border: none !important;
    box-shadow: none !important;
}

/* Placeholder */
div[data-testid="stTextInput"] input::placeholder {
    color: #737373 !important; 
    font-weight: 400 !important;
}

/* Area Kanan (Counter max_chars seperti "4/6") */
div[data-testid="stTextInput"] > div[data-baseweb="input"] > div:last-child {
    background-color: #262626 !important; /* Background counter abu gelap */
    color: #a3a3a3 !important; /* Teks counter abu terang */
    border-left: 1px solid #404040 !important;
    padding: 0 16px !important;
    display: flex !important;
    align-items: center !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    border-radius: 0 50px 50px 0 !important; /* Ujung kanan membulat */
}

/* Efek saat diklik (Focus) */
div[data-testid="stTextInput"] > div[data-baseweb="input"]:focus-within {
    border-color: #ffffff !important; 
    box-shadow: 0 0 0 1px #ffffff !important; 
    background-color: #0a0a0a !important; 
}
div[data-testid="stTextInput"] input:focus {
    outline: none !important;
    box-shadow: none !important;
}

/* Selectbox */
.stSelectbox > div > div {
    background: #262626 !important;
    border: 1px solid #404040 !important;
    border-radius: 8px !important;
    color: #ffffff !important;
    padding: 10px 14px !important;
    box-shadow: none !important;
}
.stSelectbox > div > div:focus-within {
    border-color: #737373 !important;
    box-shadow: 0 0 0 1px #737373 !important;
}
ul[data-testid="stSelectboxVirtualDropdown"] {
    background-color: #171717 !important;
    border: 1px solid #27272a !important;
}
ul[data-testid="stSelectboxVirtualDropdown"] li {
    color: #ffffff !important;
}
ul[data-testid="stSelectboxVirtualDropdown"] li:hover,
ul[data-testid="stSelectboxVirtualDropdown"] li[aria-selected="true"] {
    background-color: #262626 !important;
    color: #ffffff !important;
}

/* ============================================================
   SLIDER & CHECKBOX
   ============================================================ */
[data-testid="stSlider"] [role="slider"] {
    background-color: #ffffff !important;
    border: 2px solid #0a0a0a !important;
    box-shadow: none !important;
}
[data-testid="stSlider"] div[data-baseweb="slider"] > div > div > div:nth-child(1) {
    background: #ffffff !important;
}
[data-testid="stSlider"] div[data-baseweb="slider"] > div > div > div:nth-child(2) {
    background: #404040 !important;
}
[data-testid="stSlider"] [data-testid="stThumbValue"],
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] {
    color: #ffffff !important;
    font-weight: 700 !important;
}

[data-testid="stCheckbox"] input:checked + div {
    background-color: #ffffff !important;
    border-color: #ffffff !important;
}
[data-testid="stCheckbox"] input:checked + div svg {
    fill: #0a0a0a !important;
    color: #0a0a0a !important;
}
[data-testid="stCheckbox"] label span {
    color: #ffffff !important;
    background-color: transparent !important;
}

/* TABS & EXPANDER */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: 1px solid #27272a !important;
}
.stTabs [data-baseweb="tab"] {
    color: #a3a3a3 !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #ffffff !important; }
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 2px solid #ffffff !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

[data-testid="stExpander"] {
    background: #171717 !important;
    border: 1px solid #27272a !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary {
    color: #ffffff !important;
    font-weight: 600 !important;
}
[data-testid="stExpander"] summary:hover {
    background-color: #262626 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary svg {
    fill: #ffffff !important;
    color: #ffffff !important;
}

/* MEDIA QUERY: PERBAIKAN MOBILE (HP) */
@media (max-width: 768px) {
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    .grid-4-col { grid-template-columns: repeat(2, 1fr) !important; gap: 12px !important; }
    .sector-card { flex-direction: column !important; align-items: flex-start !important; gap: 12px !important; }
    .sector-card-right { text-align: left !important; width: 100% !important; gap: 12px !important; justify-content: flex-start !important; }
}

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

def hero(title, subtitle, badge_text="", badge_color="#ffffff"):
    badge_html = ""
    if badge_text:
        badge_html = (
            f'<div style="display: inline-block; padding: 6px 14px; '
            f'background: #262626; color: #ffffff; '
            f'border: 1px solid #404040; '
            f'border-radius: 20px; font-size: 12px; font-weight: 700; '
            f'letter-spacing: 1px; margin-bottom: 16px;">'
            f'{badge_text}</div>'
        )
    return (
        f'<div class="hero-title" style="'
        f'background: linear-gradient(135deg, #171717 0%, #0a0a0a 100%); '
        f'border: 1px solid #27272a; border-radius: 16px; '
        f'padding: 40px 48px; margin-bottom: 32px; '
        f'box-shadow: 0 10px 30px -10px rgba(0,0,0,0.8); '
        f'animation: fadeInUp 0.5s ease-out;">'
        f'{badge_html}'
        f'<div style="font-size: 38px; font-weight: 800; color: #ffffff; '
        f'letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 12px;">'
        f'{title}</div>'
        f'<div style="font-size: 16px; color: #a3a3a3; line-height: 1.6; '
        f'max-width: 700px;">{subtitle}</div>'
        f'</div>'
    )

def page_header(icon, title, subtitle=""):
    icon_html = f'<div style="font-size: 28px; margin-right: 16px; filter: grayscale(1);">{icon}</div>' if icon else ''
    return (
        f'<div style="background: linear-gradient(135deg, #171717 0%, #0a0a0a 100%); '
        f'border: 1px solid #27272a; border-radius: 14px; '
        f'padding: 24px 30px; margin-bottom: 28px; '
        f'display: flex; align-items: center; '
        f'box-shadow: 0 4px 20px rgba(0,0,0,0.5); '
        f'animation: fadeInUp 0.4s ease-out;">'
        f'{icon_html}'
        f'<div>'
        f'<div style="font-size: 12px; color: #737373; letter-spacing: 1px; '
        f'font-weight: 800; margin-bottom: 4px; text-transform: uppercase;">{subtitle}</div>'
        f'<div style="font-size: 26px; font-weight: 800; color: #ffffff; '
        f'letter-spacing: -0.02em; line-height: 1.1;">{title}</div>'
        f'</div></div>'
    )

def section_title(title, subtitle=""):
    sub_html = f'<div style="font-size: 14px; color: #a3a3a3; margin-left: 18px; margin-top: 6px;">{subtitle}</div>' if subtitle else ''
    return (
        '<div style="margin: 36px 0 20px;">'
        '<div style="display: flex; align-items: center; gap: 14px;">'
        '<div style="width: 4px; height: 24px; '
        'background: #ffffff; '
        'border-radius: 2px;"></div>'
        f'<div style="font-size: 22px; font-weight: 700; color: #ffffff; '
        f'letter-spacing: -0.02em;">{title}</div>'
        '</div>'
        f'{sub_html}'
        '</div>'
    )

def card(content, padding="24px 28px", accent=None):
    border_style = f'border-left: 4px solid {accent}; ' if accent else ''
    return (
        '<div style="'
        'background: linear-gradient(180deg, #171717 0%, #0a0a0a 100%); '
        'border: 1px solid #27272a; border-radius: 12px; '
        f'{border_style}'
        f'padding: {padding}; margin-bottom: 20px; '
        'box-shadow: 0 4px 15px rgba(0,0,0,0.3);">'
        f'{content}'
        '</div>'
    )

def metric_box(label, value, sub="", accent="#ffffff"):
    sub_html = f'<div style="font-size: 13px; color: #a3a3a3; margin-top: 8px;">{sub}</div>' if sub else ''
    return (
        '<div style="'
        'background: #171717; '
        'border: 1px solid #27272a; border-radius: 10px; '
        'padding: 20px 24px;">'
        f'<div style="font-size: 12px; color: #a3a3a3; letter-spacing: 0.07em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 12px;">'
        f'{label}</div>'
        f'<div style="font-size: 28px; font-weight: 800; color: #ffffff; '
        f'letter-spacing: -0.02em;">{value}</div>'
        f'{sub_html}'
        '</div>'
    )

def stat_card(label, value, delta=None, sub="", accent="#ffffff"):
    delta_html = ""
    if delta is not None:
        try:
            v = float(delta)
            color = "#ffffff" if v >= 0 else "#737373"
            sign = "+" if v >= 0 else ""
            delta_html = (
                f'<div style="display: inline-block; padding: 4px 12px; '
                f'background: #262626; border: 1px solid #404040; '
                f'color: {color}; border-radius: 6px; '
                f'font-size: 13px; font-weight: 700; margin-left: 8px;">'
                f'{sign}{v:.2f}%</div>'
            )
        except Exception:
            pass
    sub_html = f'<div style="font-size: 13px; color: #a3a3a3; margin-top: 8px;">{sub}</div>' if sub else ''
    return (
        '<div style="'
        'background: #171717; '
        'border: 1px solid #27272a; border-radius: 10px; '
        f'border-left: 4px solid {accent}; '
        'padding: 20px 24px;">'
        f'<div style="font-size: 12px; color: #a3a3a3; letter-spacing: 0.07em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 12px;">'
        f'{label}</div>'
        f'<div style="display: flex; align-items: baseline;">'
        f'<span style="font-size: 28px; font-weight: 800; color: #ffffff; '
        f'letter-spacing: -0.02em;">{value}</span>'
        f'{delta_html}'
        '</div>'
        f'{sub_html}'
        '</div>'
    )

def info_banner(text, type="info"):
    return (
        f'<div style="background: #171717; '
        f'border: 1px solid #27272a; '
        f'border-left: 4px solid #ffffff; '
        f'border-radius: 10px; padding: 16px 20px; margin-bottom: 20px;">'
        f'<div style="font-size: 14px; color: #e5e5e5; line-height: 1.6;">'
        f'{text}</div>'
        '</div>'
    )

def badge(text, color="#ffffff"):
    return (
        f'<span style="display: inline-block; padding: 4px 12px; '
        f'background: #262626; color: #ffffff; '
        f'border: 1px solid #404040; border-radius: 6px; '
        f'font-size: 11px; font-weight: 800; letter-spacing: 0.5px; '
        f'text-transform: uppercase;">{text}</span>'
    )

def divider():
    return (
        '<div style="height: 1px; '
        'background: linear-gradient(90deg, transparent, #404040, transparent); '
        'margin: 32px 0;"></div>'
    )

def kv_row(label, value, accent="#ffffff"):
    return (
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; padding: 14px 0; '
        'border-bottom: 1px solid #27272a;">'
        f'<span style="font-size: 14px; color: #a3a3a3;">{label}</span>'
        f'<span style="font-size: 15px; font-weight: 700; color: {accent};">'
        f'{value}</span>'
        '</div>'
    )

def spacer(height="20px"):
    return f'<div style="height: {height};"></div>'

def empty_state(icon, title, subtitle=""):
    return (
        '<div style="text-align: center; padding: 60px 24px; '
        'background: #171717; border: 1px dashed #404040; '
        'border-radius: 14px;">'
        f'<div style="font-size: 40px; margin-bottom: 16px;">{icon}</div>'
        f'<div style="font-size: 18px; font-weight: 600; color: #ffffff; '
        f'margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 14px; color: #a3a3a3;">{subtitle}</div>'
        '</div>'
    )

def render_table(df, hide_index=True):
    html_table = df.to_html(index=not hide_index, border=0, classes="mono-table")
    html_table = html_table.replace('\n', '').replace('\r', '')
    
    css = """
    <style>
    .table-container {
        width: 100%;
        overflow-x: auto;
        margin-bottom: 24px;
        border-radius: 8px;
        border: 1px solid #27272a;
        background-color: #171717;
    }
    .mono-table {
        width: 100% !important;
        border-collapse: collapse !important;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
        margin: 0 !important;
        border: none !important;
    }
    .mono-table th {
        background-color: #262626 !important;
        color: #a3a3a3 !important;
        padding: 14px 16px !important;
        text-align: left !important;
        border: none !important;
        border-bottom: 1px solid #27272a !important;
        font-weight: 600 !important;
        white-space: nowrap;
    }
    .mono-table td {
        padding: 14px 16px !important;
        color: #ffffff !important;
        border: none !important;
        border-bottom: 1px solid #27272a !important;
        font-weight: 500 !important;
        background-color: transparent !important;
        white-space: nowrap;
    }
    .mono-table tr:last-child td {
        border-bottom: none !important;
    }
    .mono-table tr:hover td {
        background-color: #262626 !important;
    }
    
    [data-testid="stMarkdownContainer"] table {
        border: none !important;
    }
    [data-testid="stMarkdownContainer"] th, 
    [data-testid="stMarkdownContainer"] td {
        border: none !important;
    }
    </style>
    """
    
    html = f'<div class="table-container">{html_table}</div>'
    st.markdown(css + html, unsafe_allow_html=True)