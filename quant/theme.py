"""Theme minimalis premium — Strict Monokrom (Hitam, Putih, Abu)."""

import streamlit as st

COLORS = {
    "bg": "#000000",         # Hitam pekat
    "surface": "#0a0a0a",    # Hitam keabu-abuan (Card)
    "elevated": "#171717",   # Abu sangat gelap (Hover)
    "border": "#262626",     # Garis tepi halus
    "border_hi": "#404040",  # Garis tepi saat fokus
    "text": "#ffffff",       # Putih bersih
    "body": "#d4d4d4",       # Abu terang
    "muted": "#a3a3a3",      # Abu standard
    "dim": "#737373",        # Abu gelap
}

THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI',
                 'Roboto', 'Helvetica Neue', Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
html { scroll-behavior: smooth; }

.stApp {
    background: #000000;
    color: #d4d4d4;
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent !important; }

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* ============ SIDEBAR ============ */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebar"] {
    background: #000000 !important;
    border-right: 1px solid #262626 !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }

h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

/* ============ BUTTONS ============ */
.stButton > button, .stDownloadButton > button {
    background: #0a0a0a !important;
    border: 1px solid #262626 !important;
    color: #ffffff !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 8px 16px !important;
    transition: all 150ms ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: #171717 !important;
    border-color: #404040 !important;
}

/* Tombol Utama (Primary) - Putih Teks Hitam */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: #ffffff !important;
    border: 1px solid #ffffff !important;
    color: #000000 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #e5e5e5 !important;
    border-color: #e5e5e5 !important;
}

.stFormSubmitButton > button {
    background: #ffffff !important;
    border: 1px solid #ffffff !important;
    color: #000000 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 16px !important;
}
.stFormSubmitButton > button:hover {
    background: #e5e5e5 !important;
}

/* ============ INPUTS ============ */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: #0a0a0a !important;
    border: 1px solid #262626 !important;
    border-radius: 6px !important;
    color: #ffffff !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
}
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #0a0a0a !important;
    border: 1px solid #262626 !important;
    border-radius: 6px !important;
    color: #ffffff !important;
}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: #a3a3a3 !important;
    box-shadow: none !important;
}

/* ============ TABS ============ */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: transparent !important;
    border-bottom: 1px solid #262626 !important;
}
.stTabs [data-baseweb="tab"] {
    color: #737373 !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 16px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #ffffff !important; }
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 2px solid #ffffff !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ============ EXPANDER, POPOVER, METRIC ============ */
[data-testid="stExpander"] {
    background: #0a0a0a !important;
    border: 1px solid #262626 !important;
    border-radius: 6px !important;
}
[data-testid="stPopover"] > button {
    background: #ffffff !important;
    border: 1px solid #ffffff !important;
    color: #000000 !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    width: 100% !important;
}
[data-testid="stPopoverBody"] {
    background: #0a0a0a !important;
    border: 1px solid #404040 !important;
    border-radius: 6px !important;
}
[data-testid="stDataFrame"], [data-testid="stMetric"] {
    background: #0a0a0a !important;
    border: 1px solid #262626 !important;
    border-radius: 6px !important;
}

/* ============ ICON & PAGE LINK (Hapus Emoji di Sidebar) ============ */
[data-testid="stIconMaterial"] { color: #737373 !important; }
[data-testid="stPageLink"] {
    padding: 8px 12px !important;
    border-radius: 6px !important;
    color: #a3a3a3 !important;
}
[data-testid="stPageLink"]:hover { background: #171717 !important; color: #ffffff !important; }
[data-testid="stPageLink"][aria-current="page"] {
    background: #262626 !important; color: #ffffff !important;
}

/* Hapus branding */
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


def hero(title, subtitle, badge_text=""):
    badge_html = (
        f'<div style="display: inline-block; padding: 4px 12px; '
        f'background: #171717; color: #a3a3a3; '
        f'border: 1px solid #262626; border-radius: 6px; '
        f'font-size: 11px; font-weight: 500; margin-bottom: 16px;">'
        f'{badge_text}</div>'
    ) if badge_text else ""
    
    return (
        '<div style="background: #0a0a0a; border: 1px solid #262626; border-radius: 8px; '
        'padding: 32px 40px; margin-bottom: 24px;">'
        f'{badge_html}'
        f'<div style="font-size: 32px; font-weight: 600; color: #ffffff; '
        f'letter-spacing: -0.03em; line-height: 1.2; margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 14px; color: #a3a3a3; line-height: 1.6; '
        f'max-width: 640px;">{subtitle}</div>'
        '</div>'
    )


def page_header(icon, title, subtitle=""):
    # Ikon dibiarkan kosong (tidak pakai emoji)
    return (
        '<div style="background: #0a0a0a; border: 1px solid #262626; border-radius: 8px; '
        'padding: 20px 24px; margin-bottom: 24px;">'
        f'<div style="font-size: 11px; color: #737373; letter-spacing: 0.5px; '
        f'font-weight: 500; margin-bottom: 4px; text-transform: uppercase;">{subtitle}</div>'
        f'<div style="font-size: 22px; font-weight: 600; color: #ffffff; '
        f'letter-spacing: -0.02em; line-height: 1;">{title}</div>'
        '</div>'
    )


def section_title(title, subtitle=""):
    sub_html = f'<div style="font-size: 13px; color: #a3a3a3; margin-top: 6px;">{subtitle}</div>' if subtitle else ''
    return (
        '<div style="margin: 28px 0 16px;">'
        '<div style="display: flex; align-items: center; gap: 10px;">'
        '<div style="width: 3px; height: 18px; background: #ffffff; border-radius: 2px;"></div>'
        f'<div style="font-size: 18px; font-weight: 600; color: #ffffff;">{title}</div>'
        '</div>'
        f'{sub_html}'
        '</div>'
    )


def card(content, padding="20px 24px"):
    return (
        f'<div style="background: #0a0a0a; border: 1px solid #262626; '
        f'border-radius: 8px; padding: {padding}; margin-bottom: 16px;">'
        f'{content}</div>'
    )


def metric_box(label, value, sub=""):
    sub_html = f'<div style="font-size: 12px; color: #737373; margin-top: 6px;">{sub}</div>' if sub else ''
    return (
        '<div style="background: #0a0a0a; border: 1px solid #262626; border-radius: 8px; padding: 16px 20px;">'
        f'<div style="font-size: 12px; color: #a3a3a3; font-weight: 500; margin-bottom: 8px;">{label}</div>'
        f'<div style="font-size: 22px; font-weight: 600; color: #ffffff;">{value}</div>'
        f'{sub_html}</div>'
    )


def stat_card(label, value, delta=None, sub=""):
    # Mengubah angka positif/negatif menjadi putih/abu (strict monokrom)
    delta_html = ""
    if delta is not None:
        try:
            v = float(delta)
            # Positif = Putih, Negatif = Abu Gelap
            color = "#ffffff" if v >= 0 else "#737373" 
            sign = "+" if v >= 0 else ""
            delta_html = (
                f'<div style="display: inline-block; padding: 2px 8px; '
                f'background: #171717; color: {color}; border: 1px solid #262626; '
                f'border-radius: 4px; font-size: 12px; font-weight: 600; margin-left: 8px;">'
                f'{sign}{v:.2f}%</div>'
            )
        except Exception:
            pass
    sub_html = f'<div style="font-size: 12px; color: #737373; margin-top: 6px;">{sub}</div>' if sub else ''
    return (
        '<div style="background: #0a0a0a; border: 1px solid #262626; border-radius: 8px; padding: 16px 20px;">'
        f'<div style="font-size: 12px; color: #a3a3a3; font-weight: 500; margin-bottom: 8px;">{label}</div>'
        f'<div style="display: flex; align-items: baseline;">'
        f'<span style="font-size: 22px; font-weight: 600; color: #ffffff;">{value}</span>'
        f'{delta_html}</div>'
        f'{sub_html}</div>'
    )


def info_banner(text, type="info"):
    # Mengganti emoji dengan teks kurung siku
    labels = {
        "info":    "[INFO]",
        "success": "[OK]",
        "warning": "[WARN]",
        "error":   "[ERR]",
    }
    label = labels.get(type, "[INFO]")
    
    return (
        f'<div style="background: #0a0a0a; border: 1px solid #262626; '
        f'border-left: 3px solid #ffffff; border-radius: 4px; padding: 12px 16px; margin-bottom: 16px;">'
        f'<div style="display: flex; gap: 12px; align-items: flex-start;">'
        f'<span style="color: #ffffff; font-weight: 600; font-size: 12px; '
        f'flex-shrink: 0; letter-spacing: 0.5px;">{label}</span>'
        f'<div style="font-size: 13px; color: #d4d4d4; line-height: 1.5;">{text}</div>'
        f'</div></div>'
    )


def badge(text):
    return (
        f'<span style="display: inline-block; padding: 2px 8px; '
        f'background: #171717; color: #ffffff; border: 1px solid #262626; '
        f'border-radius: 4px; font-size: 11px; font-weight: 500; text-transform: uppercase;">{text}</span>'
    )


def divider():
    return '<div style="height: 1px; background: #262626; margin: 24px 0;"></div>'


def kv_row(label, value):
    return (
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; padding: 10px 0; border-bottom: 1px solid #262626;">'
        f'<span style="font-size: 13px; color: #a3a3a3;">{label}</span>'
        f'<span style="font-size: 14px; font-weight: 500; color: #ffffff;">{value}</span>'
        '</div>'
    )


def spacer(height="16px"):
    return f'<div style="height: {height};"></div>'


def empty_state(icon, title, subtitle=""):
    # Ikon emoji sengaja dihapus
    return (
        '<div style="text-align: center; padding: 48px 24px; '
        'background: #0a0a0a; border: 1px dashed #262626; border-radius: 8px;">'
        f'<div style="font-size: 16px; font-weight: 500; color: #ffffff; margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 13px; color: #a3a3a3;">{subtitle}</div>'
        '</div>'
    )