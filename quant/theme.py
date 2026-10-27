"""Theme minimalis premium — Clean & Professional (Dark Mode)."""

import streamlit as st


COLORS = {
    "bg": "#0f172a",         # Slate 900 (Background Utama)
    "surface": "#1e293b",    # Slate 800 (Card/Kotak)
    "elevated": "#334155",   # Slate 700 (Hover)
    "sidebar": "#0b1120",    # Lebih gelap dari bg
    "border": "#334155",     # Garis tepi standar
    "border_hi": "#475569",  # Garis tepi saat fokus
    "text": "#f8fafc",       # Putih tulang (Judul)
    "body": "#cbd5e1",       # Abu terang (Paragraf)
    "muted": "#94a3b8",      # Abu standard
    "dim": "#64748b",        # Abu gelap
    "primary": "#3b82f6",    # Biru profesional
    "cyan": "#0ea5e9",       # Cyan solid
    "success": "#10b981",    # Hijau
    "warning": "#f59e0b",    # Oranye
    "danger": "#ef4444",     # Merah
}


THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI',
                 'Roboto', 'Helvetica Neue', Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
html { scroll-behavior: smooth; }

/* Animasi minimalis */
@keyframes fadeIn { from { opacity:0;} to { opacity:1;} }

.stApp {
    background: #0f172a;
    color: #cbd5e1;
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent !important; }

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* ============================================================
   HIDE NAV DEFAULT STREAMLIT (pakai nav custom di sidebar)
   ============================================================ */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarNavSeparator"] { display: none !important; }
[data-testid="stSidebarNavItems"] { display: none !important; }
[data-testid="stSidebarNavLink"] { display: none !important; }
nav[data-testid="stSidebarNav"] { display: none !important; }
section[data-testid="stSidebar"] > div:first-child > div:first-child > div:first-child {
    padding-top: 1rem !important;
}

/* ============ SIDEBAR ============ */
[data-testid="stSidebar"] {
    background: #0b1120 !important;
    border-right: 1px solid #334155 !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }

h1, h2, h3, h4, h5, h6 {
    color: #f8fafc !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

[data-testid="stMarkdownContainer"] { animation: fadeIn 200ms ease-out; }

/* ============================================================
   BUTTONS
   ============================================================ */
.stButton > button, .stDownloadButton > button {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #f8fafc !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 8px 16px !important;
    transition: background 150ms ease, border-color 150ms ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: #334155 !important;
    border-color: #475569 !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: #3b82f6 !important;
    border: 1px solid #3b82f6 !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
    background: #2563eb !important;
    border-color: #2563eb !important;
}

.stFormSubmitButton > button {
    background: #3b82f6 !important;
    border: 1px solid #3b82f6 !important;
    color: #ffffff !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 16px !important;
    transition: background 150ms ease !important;
}
.stFormSubmitButton > button:hover {
    background: #2563eb !important;
}

/* ============================================================
   INPUTS
   ============================================================ */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    color: #f8fafc !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    transition: border-color 150ms ease !important;
}
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    color: #f8fafc !important;
    transition: border-color 150ms ease !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stDateInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 1px #3b82f6 !important;
    outline: none !important;
}

/* ============================================================
   TABS
   ============================================================ */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 1px solid #334155 !important;
    padding: 0 !important;
    margin-bottom: 24px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 0 !important;
    color: #94a3b8 !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 16px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    transition: color 150ms ease !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #cbd5e1 !important; }
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #3b82f6 !important;
    border-bottom: 2px solid #3b82f6 !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ============================================================
   EXPANDER
   ============================================================ */
[data-testid="stExpander"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    transition: border-color 150ms ease !important;
}
[data-testid="stExpander"]:hover {
    border-color: #475569 !important;
}

/* ============================================================
   POPOVER LOGIN
   ============================================================ */
[data-testid="stPopover"] > button {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #f8fafc !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 18px !important;
    border-radius: 6px !important;
    transition: background 150ms ease !important;
    width: 100% !important;
}
[data-testid="stPopover"] > button:hover {
    background: #334155 !important;
}
[data-testid="stPopoverBody"] {
    background: #1e293b !important;
    border: 1px solid #475569 !important;
    border-radius: 8px !important;
    padding: 20px !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4) !important;
}

/* ============================================================
   DATAFRAME & METRIC
   ============================================================ */
[data-testid="stDataFrame"] {
    border-radius: 8px !important;
    overflow: hidden !important;
    border: 1px solid #334155 !important;
}

[data-testid="stMetric"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    padding: 16px 20px !important;
}

/* ============================================================
   ICON & PAGE LINK
   ============================================================ */
[data-testid="stIconMaterial"] {
    color: #94a3b8 !important;
    font-size: 18px !important;
    transition: color 150ms ease !important;
}
[data-testid="stPageLink"] {
    padding: 8px 12px !important;
    border-radius: 6px !important;
    margin-bottom: 2px !important;
    transition: background 150ms ease !important;
    color: #94a3b8 !important;
    text-decoration: none !important;
}
[data-testid="stPageLink"]:hover {
    background: #1e293b !important;
    color: #f8fafc !important;
}
[data-testid="stPageLink"][aria-current="page"] {
    background: #1e293b !important;
    color: #3b82f6 !important;
    font-weight: 600 !important;
}

/* ============================================================
   SCROLLBAR
   ============================================================ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb {
    background: #334155; border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: #475569; }

/* ============================================================
   HIDE STREAMLIT BRANDING
   ============================================================ */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stAppDeployButton"] { display: none !important; }
[data-testid="stMarkdown"] > div > p:empty { display: none; }

/* ============================================================ */
/* 🔥 MOBILE RESPONSIVE 🔥 */
/* ============================================================ */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
    position: fixed !important;
    top: 15px !important;
    left: 15px !important;
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    align-items: center;
    justify-content: center;
}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stSidebarCollapsedControl"] svg {
    display: none !important;
}
[data-testid="stExpandSidebarButton"]::after,
[data-testid="stSidebarCollapsedControl"]::after {
    content: "☰";
    font-size: 20px;
    color: #f8fafc;
    line-height: 1;
}
@media (max-width: 991px) {
    .block-container {
        padding-top: 4rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.1rem !important; }
    p, li, .stMarkdown { font-size: 13px !important; line-height: 1.5 !important; }
    span[style*="font-size: 30px"], span[style*="font-size:30px"] { font-size: 24px !important; }
}
</style>
"""


def load_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


def hero(title, subtitle, badge_text="", badge_color="#3b82f6"):
    badge_html = ""
    if badge_text:
        rgb = _rgb(badge_color)
        badge_html = (
            f'<div style="display: inline-block; padding: 4px 12px; '
            f'background: rgba({rgb}, 0.1); color: {badge_color}; '
            f'border: 1px solid rgba({rgb}, 0.2); '
            f'border-radius: 6px; font-size: 11px; font-weight: 600; '
            f'letter-spacing: 0.5px; margin-bottom: 16px;">'
            f'{badge_text}</div>'
        )
    return (
        '<div class="hero-title" style="'
        'background: #1e293b; '
        'border: 1px solid #334155; border-radius: 12px; '
        'padding: 32px 40px; margin-bottom: 24px;">'
        f'{badge_html}'
        f'<div style="font-size: 32px; font-weight: 700; color: #f8fafc; '
        f'letter-spacing: -0.03em; line-height: 1.2; margin-bottom: 8px;">'
        f'{title}</div>'
        f'<div style="font-size: 14px; color: #94a3b8; line-height: 1.6; '
        f'max-width: 640px;">{subtitle}</div>'
        '</div>'
    )


def page_header(icon, title, subtitle=""):
    icon = (icon or "").strip()
    if icon:
        icon_html = (
            f'<div style="width: 48px; height: 48px; '
            f'background: #1e293b; border: 1px solid #334155; '
            f'border-radius: 10px; display: flex; align-items: center; '
            f'justify-content: center; font-size: 22px; color: #cbd5e1;">{icon}</div>'
        )
    else:
        icon_html = ""

    return (
        '<div style="'
        'background: #1e293b; '
        'border: 1px solid #334155; border-radius: 12px; '
        'padding: 20px 24px; margin-bottom: 24px; '
        'display: flex; align-items: center; gap: 16px;">'
        f'{icon_html}'
        '<div>'
        f'<div style="font-size: 11px; color: #94a3b8; letter-spacing: 0.5px; '
        f'font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">'
        f'{subtitle}</div>'
        f'<div style="font-size: 22px; font-weight: 600; color: #f8fafc; '
        f'letter-spacing: -0.02em; line-height: 1;">{title}</div>'
        '</div></div>'
    )


def section_title(title, subtitle=""):
    sub_html = (
        f'<div style="font-size: 13px; color: #94a3b8; margin-left: 0; '
        f'margin-top: 6px;">{subtitle}</div>'
    ) if subtitle else ''
    return (
        '<div style="margin: 28px 0 16px;">'
        '<div style="display: flex; align-items: center; gap: 10px;">'
        '<div style="width: 3px; height: 18px; '
        'background: #3b82f6; border-radius: 2px;"></div>'
        f'<div style="font-size: 18px; font-weight: 600; color: #f8fafc; '
        f'letter-spacing: -0.01em;">{title}</div>'
        '</div>'
        f'{sub_html}'
        '</div>'
    )


def card(content, padding="20px 24px", accent=None):
    border_style = f'border-left: 3px solid {accent}; ' if accent else ''
    return (
        '<div style="'
        'background: #1e293b; '
        'border: 1px solid #334155; border-radius: 10px; '
        f'{border_style}'
        f'padding: {padding}; margin-bottom: 16px;">'
        f'{content}'
        '</div>'
    )


def metric_box(label, value, sub="", accent="#3b82f6"):
    sub_html = (
        f'<div style="font-size: 12px; color: #94a3b8; margin-top: 6px;">{sub}</div>'
    ) if sub else ''
    return (
        '<div style="'
        'background: #1e293b; '
        'border: 1px solid #334155; border-radius: 10px; '
        'padding: 16px 20px;">'
        f'<div style="font-size: 12px; color: #94a3b8; '
        f'font-weight: 500; margin-bottom: 8px;">'
        f'{label}</div>'
        f'<div style="font-size: 22px; font-weight: 600; color: #f8fafc; '
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
                f'<div style="display: inline-block; padding: 2px 8px; '
                f'background: rgba({_rgb(color)}, 0.1); '
                f'color: {color}; border-radius: 4px; '
                f'font-size: 12px; font-weight: 600; margin-left: 8px;">'
                f'{sign}{v:.2f}%</div>'
            )
        except Exception:
            pass
    sub_html = (
        f'<div style="font-size: 12px; color: #94a3b8; margin-top: 6px;">{sub}</div>'
    ) if sub else ''
    return (
        '<div style="'
        'background: #1e293b; '
        'border: 1px solid #334155; border-radius: 10px; '
        'padding: 16px 20px;">'
        f'<div style="font-size: 12px; color: #94a3b8; '
        f'font-weight: 500; margin-bottom: 8px;">'
        f'{label}</div>'
        f'<div style="display: flex; align-items: baseline;">'
        f'<span style="font-size: 22px; font-weight: 600; color: #f8fafc; '
        f'letter-spacing: -0.02em;">{value}</span>'
        f'{delta_html}'
        '</div>'
        f'{sub_html}'
        '</div>'
    )


def info_banner(text, type="info"):
    colors = {
        "info":    ("#3b82f6", "ℹ"),
        "success": ("#10b981", "✓"),
        "warning": ("#f59e0b", "⚠"),
        "error":   ("#ef4444", "✕"),
    }
    color, icon = colors.get(type, colors["info"])
    rgb = _rgb(color)
    return (
        f'<div style="background: rgba({rgb}, 0.05); '
        f'border: 1px solid rgba({rgb}, 0.2); '
        f'border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">'
        f'<div style="display: flex; gap: 12px; align-items: flex-start;">'
        f'<span style="color: {color}; font-weight: bold; font-size: 14px; '
        f'flex-shrink: 0;">{icon}</span>'
        f'<div style="font-size: 13px; color: #cbd5e1; line-height: 1.5;">'
        f'{text}</div>'
        '</div></div>'
    )


def badge(text, color="#3b82f6"):
    rgb = _rgb(color)
    return (
        f'<span style="display: inline-block; padding: 2px 8px; '
        f'background: rgba({rgb}, 0.1); color: {color}; '
        f'border: 1px solid rgba({rgb}, 0.2); border-radius: 4px; '
        f'font-size: 11px; font-weight: 600; letter-spacing: 0.5px; '
        f'text-transform: uppercase;">{text}</span>'
    )


def divider():
    return (
        '<div style="height: 1px; '
        'background: #334155; '
        'margin: 24px 0;"></div>'
    )


def kv_row(label, value, accent="#f8fafc"):
    return (
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; padding: 10px 0; '
        'border-bottom: 1px solid #334155;">'
        f'<span style="font-size: 13px; color: #94a3b8;">{label}</span>'
        f'<span style="font-size: 14px; font-weight: 500; color: {accent};">'
        f'{value}</span>'
        '</div>'
    )


def spacer(height="16px"):
    return f'<div style="height: {height};"></div>'


def empty_state(icon, title, subtitle=""):
    return (
        '<div style="text-align: center; padding: 48px 24px; '
        'background: #1e293b; border: 1px dashed #334155; '
        'border-radius: 12px;">'
        f'<div style="font-size: 32px; margin-bottom: 12px; opacity: 0.8;">{icon}</div>'
        f'<div style="font-size: 16px; font-weight: 600; color: #f8fafc; '
        f'margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 13px; color: #94a3b8;">{subtitle}</div>'
        '</div>'
    )