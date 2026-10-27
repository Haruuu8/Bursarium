"""Theme minimalis premium — Modern Dark (Slate & Blue Accent)."""

import streamlit as st

COLORS = {
    "bg": "#0b0f19",         # Deep Navy (Background Utama)
    "surface": "#151b2b",    # Slate (Card/Kotak)
    "elevated": "#1e293b",   # Hover
    "border": "#232d42",     # Garis tepi halus
    "border_hi": "#334155",  # Garis tepi fokus
    "text": "#f8fafc",       # Putih bersih
    "body": "#cbd5e1",       # Abu terang (Paragraf)
    "muted": "#94a3b8",      # Abu standard
    "dim": "#64748b",        # Abu gelap
    "primary": "#3b82f6",    # Biru elegan
    "cyan": "#06b6d4",       # Cyan
    "success": "#10b981",    # Hijau
    "danger": "#ef4444",     # Merah
}

THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', 'Roboto', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
html { scroll-behavior: smooth; }

/* Animasi Fade-in */
@keyframes fadeInUp { from { opacity:0; transform:translateY(10px);} to { opacity:1; transform:translateY(0);} }
@keyframes fadeIn   { from { opacity:0;} to { opacity:1;} }

.stApp {
    background: #0b0f19;
    background-image: radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.05) 0%, transparent 50%);
    color: #cbd5e1;
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
    background: #070a12 !important;
    border-right: 1px solid #1e293b !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }

h1, h2, h3, h4, h5, h6 {
    color: #f8fafc !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

/* BUTTONS */
.stButton > button, .stDownloadButton > button {
    background: #151b2b !important;
    border: 1px solid #232d42 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 8px 16px !important;
    transition: all 0.2s ease-in-out !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: #1e293b !important;
    border-color: #3b82f6 !important;
    color: #ffffff !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    border: none !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
}

/* INPUTS */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stSelectbox > div > div {
    background: #0b0f19 !important;
    border: 1px solid #232d42 !important;
    border-radius: 8px !important;
    color: #f8fafc !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    background: transparent !important;
    border-bottom: 1px solid #232d42 !important;
}
.stTabs [data-baseweb="tab"] {
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #f8fafc !important; background: #151b2b; border-radius: 8px 8px 0 0; }
.stTabs [aria-selected="true"] {
    color: #3b82f6 !important;
    border-bottom: 2px solid #3b82f6 !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* EXPANDER, POPOVER, DATAFRAME */
[data-testid="stExpander"] {
    background: #151b2b !important;
    border: 1px solid #232d42 !important;
    border-radius: 10px !important;
}
[data-testid="stPopover"] > button {
    background: #151b2b !important;
    border: 1px solid #232d42 !important;
    color: #f8fafc !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}
[data-testid="stPopoverBody"] {
    background: #151b2b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stDataFrame"], [data-testid="stMetric"] {
    background: #151b2b !important;
    border: 1px solid #232d42 !important;
    border-radius: 10px !important;
}

/* PAGE LINK */
[data-testid="stPageLink"] {
    padding: 10px 14px !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stPageLink"]:hover { background: #1e293b !important; color: #f8fafc !important; }
[data-testid="stPageLink"][aria-current="page"] {
    background: rgba(59, 130, 246, 0.1) !important;
    color: #3b82f6 !important;
    font-weight: 700 !important;
    border-left: 3px solid #3b82f6;
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
# KOMPONEN UI KUSTOM
# ============================================================

def hero(title, subtitle, badge_text="", badge_color="#3b82f6"):
    badge_html = ""
    if badge_text:
        badge_html = (
            f'<div style="display: inline-block; padding: 6px 14px; '
            f'background: rgba(59, 130, 246, 0.15); color: #60a5fa; '
            f'border: 1px solid rgba(59, 130, 246, 0.3); '
            f'border-radius: 20px; font-size: 11px; font-weight: 700; '
            f'letter-spacing: 1px; margin-bottom: 16px;">'
            f'{badge_text}</div>'
        )
    return (
        f'<div class="hero-title" style="'
        f'background: linear-gradient(135deg, #151b2b 0%, #0f1420 100%); '
        f'border: 1px solid #232d42; border-radius: 16px; '
        f'padding: 36px 40px; margin-bottom: 28px; '
        f'box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5); '
        f'animation: fadeInUp 0.5s ease-out;">'
        f'{badge_html}'
        f'<div style="font-size: 36px; font-weight: 800; color: #f8fafc; '
        f'letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 12px;">'
        f'{title}</div>'
        f'<div style="font-size: 15px; color: #94a3b8; line-height: 1.6; '
        f'max-width: 640px;">{subtitle}</div>'
        f'</div>'
    )


def page_header(icon, title, subtitle=""):
    icon_html = f'<div style="font-size: 24px; margin-right: 16px;">{icon}</div>' if icon else ''
    return (
        f'<div style="background: linear-gradient(135deg, #151b2b 0%, #0f1420 100%); '
        f'border: 1px solid #232d42; border-radius: 12px; '
        f'padding: 20px 24px; margin-bottom: 24px; '
        f'display: flex; align-items: center; '
        f'animation: fadeInUp 0.4s ease-out;">'
        f'{icon_html}'
        f'<div>'
        f'<div style="font-size: 11px; color: #3b82f6; letter-spacing: 1px; '
        f'font-weight: 700; margin-bottom: 4px; text-transform: uppercase;">{subtitle}</div>'
        f'<div style="font-size: 24px; font-weight: 800; color: #f8fafc; '
        f'letter-spacing: -0.02em; line-height: 1.1;">{title}</div>'
        f'</div></div>'
    )


def section_title(title, subtitle=""):
    sub_html = f'<div style="font-size: 13px; color: #94a3b8; margin-left: 17px; margin-top: 4px;">{subtitle}</div>' if subtitle else ''
    return (
        '<div style="margin: 32px 0 16px;">'
        '<div style="display: flex; align-items: center; gap: 13px;">'
        '<div style="width: 4px; height: 22px; '
        'background: linear-gradient(180deg, #3b82f6, #06b6d4); '
        'border-radius: 2px;"></div>'
        f'<div style="font-size: 20px; font-weight: 700; color: #f8fafc; '
        f'letter-spacing: -0.02em;">{title}</div>'
        '</div>'
        f'{sub_html}'
        '</div>'
    )


def card(content, padding="20px 24px", accent=None):
    border_style = f'border-left: 4px solid {accent}; ' if accent else ''
    return (
        '<div style="'
        'background: linear-gradient(180deg, #151b2b 0%, #0f1420 100%); '
        'border: 1px solid #232d42; border-radius: 12px; '
        f'{border_style}'
        f'padding: {padding}; margin-bottom: 16px; '
        'transition: transform 0.2s ease, border-color 0.2s ease; '
        '">'
        f'{content}'
        '</div>'
    )


def metric_box(label, value, sub="", accent="#3b82f6"):
    sub_html = f'<div style="font-size: 12px; color: #94a3b8; margin-top: 8px;">{sub}</div>' if sub else ''
    return (
        '<div style="'
        'background: #151b2b; '
        'border: 1px solid #232d42; border-radius: 10px; '
        'padding: 18px 22px;">'
        f'<div style="font-size: 11px; color: #94a3b8; letter-spacing: 0.07em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 10px;">'
        f'{label}</div>'
        f'<div style="font-size: 24px; font-weight: 800; color: #f8fafc; '
        f'letter-spacing: -0.02em;">{value}</div>'
        f'{sub_html}'
        '</div>'
    )


def stat_card(label, value, delta=None, sub="", accent="#3b82f6"):
    delta_html = ""
    if delta is not None:
        try:
            v = float(delta)
            color = "#10b981" if v >= 0 else "#ef4444"
            sign = "+" if v >= 0 else ""
            delta_html = (
                f'<div style="display: inline-block; padding: 3px 10px; '
                f'background: rgba({_rgb(color)}, 0.12); '
                f'color: {color}; border-radius: 6px; '
                f'font-size: 12px; font-weight: 700; margin-left: 8px;">'
                f'{sign}{v:.2f}%</div>'
            )
        except Exception:
            pass
    sub_html = f'<div style="font-size: 12px; color: #94a3b8; margin-top: 8px;">{sub}</div>' if sub else ''
    return (
        '<div style="'
        'background: #151b2b; '
        'border: 1px solid #232d42; border-radius: 10px; '
        f'border-left: 4px solid {accent}; '
        'padding: 18px 22px;">'
        f'<div style="font-size: 11px; color: #94a3b8; letter-spacing: 0.07em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 10px;">'
        f'{label}</div>'
        f'<div style="display: flex; align-items: baseline;">'
        f'<span style="font-size: 24px; font-weight: 800; color: #f8fafc; '
        f'letter-spacing: -0.02em;">{value}</span>'
        f'{delta_html}'
        '</div>'
        f'{sub_html}'
        '</div>'
    )


def info_banner(text, type="info"):
    colors = {
        "info":    ("#3b82f6", "[i]"),
        "success": ("#10b981", "[v]"),
        "warning": ("#f59e0b", "[!]"),
        "error":   ("#ef4444", "[x]"),
    }
    color, icon = colors.get(type, colors["info"])
    rgb = _rgb(color)
    return (
        f'<div style="background: rgba({rgb}, 0.08); '
        f'border: 1px solid rgba({rgb}, 0.25); '
        f'border-left: 4px solid {color}; '
        f'border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;">'
        f'<div style="display: flex; gap: 12px; align-items: flex-start;">'
        f'<span style="color: {color}; font-weight: 800; font-size: 14px; '
        f'flex-shrink: 0;">{icon}</span>'
        f'<div style="font-size: 13px; color: #cbd5e1; line-height: 1.5;">'
        f'{text}</div>'
        f'</div></div>'
    )


def badge(text, color="#3b82f6"):
    rgb = _rgb(color)
    return (
        f'<span style="display: inline-block; padding: 4px 12px; '
        f'background: rgba({rgb}, 0.12); color: {color}; '
        f'border: 1px solid rgba({rgb}, 0.3); border-radius: 6px; '
        f'font-size: 11px; font-weight: 800; letter-spacing: 0.5px; '
        f'text-transform: uppercase;">{text}</span>'
    )


def divider():
    return (
        '<div style="height: 1px; '
        'background: linear-gradient(90deg, transparent, #232d42, transparent); '
        'margin: 28px 0;"></div>'
    )


def kv_row(label, value, accent="#f8fafc"):
    return (
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; padding: 12px 0; '
        'border-bottom: 1px solid #232d42;">'
        f'<span style="font-size: 13px; color: #94a3b8;">{label}</span>'
        f'<span style="font-size: 14px; font-weight: 700; color: {accent};">'
        f'{value}</span>'
        '</div>'
    )


def spacer(height="16px"):
    return f'<div style="height: {height};"></div>'


def empty_state(icon, title, subtitle=""):
    return (
        '<div style="text-align: center; padding: 60px 24px; '
        'background: #151b2b; border: 1px dashed #334155; '
        'border-radius: 12px;">'
        f'<div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;">{icon}</div>'
        f'<div style="font-size: 16px; font-weight: 600; color: #f8fafc; '
        f'margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 13px; color: #94a3b8;">{subtitle}</div>'
        '</div>'
    )