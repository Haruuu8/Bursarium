"""Theme Modern Fintech — High Contrast, Spacious, Premium."""

import streamlit as st

COLORS = {
    "bg": "#0B1120",         # Deep Navy (Background)
    "surface": "#1E293B",    # Slate 800 (Card)
    "border": "#334155",     # Slate 700
    "text": "#F8FAFC",       # White
    "muted": "#94A3B8",      # Slate 400
    "primary": "#6366F1",    # Indigo
    "success": "#10B981",    # Emerald
    "danger": "#EF4444",     # Rose
}

THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
html { scroll-behavior: smooth; }

@keyframes fadeInUp { from { opacity:0; transform:translateY(10px);} to { opacity:1; transform:translateY(0);} }

.stApp {
    background: #0B1120;
    background-image: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.05) 0%, transparent 50%);
    color: #F8FAFC;
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent !important; }

/* LEBIH LUAS & LEGA */
.block-container {
    padding-top: 3rem !important;
    padding-bottom: 5rem !important;
    max-width: 1300px !important;
}

/* SIDEBAR */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebar"] {
    background: #0B1120 !important;
    border-right: 1px solid #1E293B !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #F8FAFC !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

/* BUTTONS */
.stButton > button, .stDownloadButton > button {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #F8FAFC !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 8px 20px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #334155 !important;
    border-color: #475569 !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button {
    background: linear-gradient(135deg, #6366F1, #4F46E5) !important;
    border: none !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #818CF8, #6366F1) !important;
    box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

/* INPUTS */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stSelectbox > div > div {
    background: #0B1120 !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #F8FAFC !important;
    padding: 10px 14px !important;
}
.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: 1px solid #1E293B !important;
}
.stTabs [data-baseweb="tab"] {
    color: #94A3B8 !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #F8FAFC !important; }
.stTabs [aria-selected="true"] {
    color: #6366F1 !important;
    border-bottom: 2px solid #6366F1 !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* EXPANDER, POPOVER, DATAFRAME */
[data-testid="stExpander"] {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stPopover"] > button {
    background: #6366F1 !important;
    color: #fff !important;
    border: none !important;
}
[data-testid="stPopoverBody"] {
    background: #1E293B !important;
    border: 1px solid #475569 !important;
}
[data-testid="stDataFrame"], [data-testid="stMetric"] {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}

/* PAGE LINK */
[data-testid="stPageLink"] {
    padding: 10px 14px !important;
    border-radius: 8px !important;
    color: #94A3B8 !important;
}
[data-testid="stPageLink"]:hover { background: #1E293B !important; color: #F8FAFC !important; }
[data-testid="stPageLink"][aria-current="page"] {
    background: rgba(99, 102, 241, 0.1) !important;
    color: #6366F1 !important;
    font-weight: 700 !important;
    border-left: 3px solid #6366F1;
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

def hero(title, subtitle, badge_text="", badge_color="#6366F1"):
    badge_html = ""
    if badge_text:
        badge_html = (
            f'<div style="display: inline-block; padding: 6px 14px; '
            f'background: rgba({_rgb(badge_color)}, 0.15); color: {badge_color}; '
            f'border: 1px solid rgba({_rgb(badge_color)}, 0.3); '
            f'border-radius: 20px; font-size: 12px; font-weight: 700; '
            f'letter-spacing: 0.5px; margin-bottom: 16px;">'
            f'{badge_text}</div>'
        )
    return (
        f'<div class="hero-title" style="'
        f'background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); '
        f'border: 1px solid #334155; border-radius: 16px; '
        f'padding: 40px 48px; margin-bottom: 32px; '
        f'box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5); '
        f'animation: fadeInUp 0.5s ease-out;">'
        f'{badge_html}'
        f'<div style="font-size: 38px; font-weight: 800; color: #F8FAFC; '
        f'letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 12px;">'
        f'{title}</div>'
        f'<div style="font-size: 16px; color: #94A3B8; line-height: 1.6; '
        f'max-width: 700px;">{subtitle}</div>'
        f'</div>'
    )

def page_header(icon, title, subtitle=""):
    icon_html = f'<div style="font-size: 28px; margin-right: 16px; opacity: 0.9;">{icon}</div>' if icon else ''
    return (
        f'<div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); '
        f'border: 1px solid #334155; border-radius: 14px; '
        f'padding: 24px 30px; margin-bottom: 28px; '
        f'display: flex; align-items: center; '
        f'box-shadow: 0 4px 20px rgba(0,0,0,0.2); '
        f'animation: fadeInUp 0.4s ease-out;">'
        f'{icon_html}'
        f'<div>'
        f'<div style="font-size: 12px; color: #6366F1; letter-spacing: 1px; '
        f'font-weight: 800; margin-bottom: 4px; text-transform: uppercase;">{subtitle}</div>'
        f'<div style="font-size: 26px; font-weight: 800; color: #F8FAFC; '
        f'letter-spacing: -0.02em; line-height: 1.1;">{title}</div>'
        f'</div></div>'
    )

def section_title(title, subtitle=""):
    sub_html = f'<div style="font-size: 14px; color: #94A3B8; margin-left: 18px; margin-top: 6px;">{subtitle}</div>' if subtitle else ''
    return (
        '<div style="margin: 36px 0 20px;">'
        '<div style="display: flex; align-items: center; gap: 14px;">'
        '<div style="width: 4px; height: 24px; '
        'background: linear-gradient(180deg, #6366F1, #06b6d4); '
        'border-radius: 2px;"></div>'
        f'<div style="font-size: 22px; font-weight: 700; color: #F8FAFC; '
        f'letter-spacing: -0.02em;">{title}</div>'
        '</div>'
        f'{sub_html}'
        '</div>'
    )

def card(content, padding="24px 28px", accent=None):
    border_style = f'border-left: 4px solid {accent}; ' if accent else ''
    return (
        '<div style="'
        'background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%); '
        'border: 1px solid #334155; border-radius: 12px; '
        f'{border_style}'
        f'padding: {padding}; margin-bottom: 20px; '
        'box-shadow: 0 4px 15px rgba(0,0,0,0.1);">'
        f'{content}'
        '</div>'
    )

def metric_box(label, value, sub="", accent="#6366F1"):
    sub_html = f'<div style="font-size: 13px; color: #94A3B8; margin-top: 8px;">{sub}</div>' if sub else ''
    return (
        '<div style="'
        'background: #1E293B; '
        'border: 1px solid #334155; border-radius: 10px; '
        'padding: 20px 24px;">'
        f'<div style="font-size: 12px; color: #94A3B8; letter-spacing: 0.07em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 12px;">'
        f'{label}</div>'
        f'<div style="font-size: 28px; font-weight: 800; color: #F8FAFC; '
        f'letter-spacing: -0.02em;">{value}</div>'
        f'{sub_html}'
        '</div>'
    )

def stat_card(label, value, delta=None, sub="", accent="#6366F1"):
    delta_html = ""
    if delta is not None:
        try:
            v = float(delta)
            color = "#10B981" if v >= 0 else "#EF4444"
            sign = "+" if v >= 0 else ""
            delta_html = (
                f'<div style="display: inline-block; padding: 4px 12px; '
                f'background: rgba({_rgb(color)}, 0.15); '
                f'color: {color}; border-radius: 6px; '
                f'font-size: 13px; font-weight: 700; margin-left: 8px;">'
                f'{sign}{v:.2f}%</div>'
            )
        except Exception:
            pass
    sub_html = f'<div style="font-size: 13px; color: #94A3B8; margin-top: 8px;">{sub}</div>' if sub else ''
    return (
        '<div style="'
        'background: #1E293B; '
        'border: 1px solid #334155; border-radius: 10px; '
        f'border-left: 4px solid {accent}; '
        'padding: 20px 24px;">'
        f'<div style="font-size: 12px; color: #94A3B8; letter-spacing: 0.07em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 12px;">'
        f'{label}</div>'
        f'<div style="display: flex; align-items: baseline;">'
        f'<span style="font-size: 28px; font-weight: 800; color: #F8FAFC; '
        f'letter-spacing: -0.02em;">{value}</span>'
        f'{delta_html}'
        '</div>'
        f'{sub_html}'
        '</div>'
    )

def info_banner(text, type="info"):
    colors = {
        "info":    ("#6366F1", "ℹ"),
        "success": ("#10B981", "✓"),
        "warning": ("#F59E0B", "⚠"),
        "error":   ("#EF4444", "✕"),
    }
    color, icon = colors.get(type, colors["info"])
    rgb = _rgb(color)
    return (
        f'<div style="background: rgba({rgb}, 0.1); '
        f'border: 1px solid rgba({rgb}, 0.3); '
        f'border-left: 4px solid {color}; '
        f'border-radius: 10px; padding: 16px 20px; margin-bottom: 20px;">'
        f'<div style="display: flex; gap: 14px; align-items: flex-start;">'
        f'<span style="color: {color}; font-weight: 800; font-size: 16px; '
        f'flex-shrink: 0;">{icon}</span>'
        f'<div style="font-size: 14px; color: #E2E8F0; line-height: 1.6;">'
        f'{text}</div>'
        f'</div></div>'
    )

def badge(text, color="#6366F1"):
    rgb = _rgb(color)
    return (
        f'<span style="display: inline-block; padding: 4px 12px; '
        f'background: rgba({rgb}, 0.15); color: {color}; '
        f'border: 1px solid rgba({rgb}, 0.3); border-radius: 6px; '
        f'font-size: 11px; font-weight: 800; letter-spacing: 0.5px; '
        f'text-transform: uppercase;">{text}</span>'
    )

def divider():
    return (
        '<div style="height: 1px; '
        'background: linear-gradient(90deg, transparent, #334155, transparent); '
        'margin: 32px 0;"></div>'
    )

def kv_row(label, value, accent="#F8FAFC"):
    return (
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; padding: 14px 0; '
        'border-bottom: 1px solid #334155;">'
        f'<span style="font-size: 14px; color: #94A3B8;">{label}</span>'
        f'<span style="font-size: 15px; font-weight: 700; color: {accent};">'
        f'{value}</span>'
        '</div>'
    )

def spacer(height="20px"):
    return f'<div style="height: {height};"></div>'

def empty_state(icon, title, subtitle=""):
    return (
        '<div style="text-align: center; padding: 60px 24px; '
        'background: #1E293B; border: 1px dashed #475569; '
        'border-radius: 14px;">'
        f'<div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;">{icon}</div>'
        f'<div style="font-size: 18px; font-weight: 600; color: #F8FAFC; '
        f'margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 14px; color: #94A3B8;">{subtitle}</div>'
        '</div>'
    )