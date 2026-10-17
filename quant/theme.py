"""Theme minimalis premium — smooth animation, dark mode."""

import streamlit as st


COLORS = {
    "bg": "#070b16", "surface": "#0d1424", "elevated": "#131a2e",
    "sidebar": "#0a1020",
    "border": "#1e2942", "border_hi": "#2c3a5c",
    "text": "#ffffff", "body": "#e6ebf5", "muted": "#94a3b8", "dim": "#64748b",
    "primary": "#6366f1", "cyan": "#06b6d4",
    "success": "#10b981", "warning": "#f59e0b", "danger": "#f43f5e",
}


THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 'Roboto', 'Helvetica Neue', Arial, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
html { scroll-behavior: smooth; }

@keyframes fadeInUp { from { opacity:0; transform:translateY(12px);} to { opacity:1; transform:translateY(0);} }
@keyframes fadeIn   { from { opacity:0;} to { opacity:1;} }
@keyframes scaleIn  { from { opacity:0; transform:scale(0.96);} to { opacity:1; transform:scale(1);} }

.stApp {
    background: #070b16;
    background-image:
        radial-gradient(1200px 600px at 15% -10%, rgba(99,102,241,0.06), transparent 60%),
        radial-gradient(900px 500px at 90% 5%, rgba(6,182,212,0.05), transparent 55%);
    color: #e6ebf5;
}
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent !important; }

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* ============ SIDEBAR ============ */
[data-testid="stSidebar"] {
    background: #0a1020 !important;
    border-right: 1px solid #1e2942 !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }

h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
}

/* ============================================================
   BUTTONS & INPUTS (Sama seperti sebelumnya)
   ============================================================ */
.stButton > button {
    background: #131a2e !important; border: 1px solid #1e2942 !important;
    color: #e6ebf5 !important; border-radius: 10px !important;
    font-weight: 600 !important; font-size: 13px !important; padding: 8px 16px !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: 1px solid #6366f1 !important; color: #ffffff !important;
}
.stTextInput > div > div > input {
    background: #0d1424 !important; border: 1px solid #1e2942 !important;
    border-radius: 10px !important; color: #e6ebf5 !important; padding: 10px 14px !important;
}

/* ============================================================
   TABS
   ============================================================ */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 1px solid #1e2942 !important; margin-bottom: 24px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #94a3b8 !important; font-weight: 600 !important; font-size: 13px !important;
}
.stTabs [aria-selected="true"] { color: #06b6d4 !important; }
.stTabs [data-baseweb="tab-highlight"] { background: #06b6d4 !important; }

/* ============================================================
   HIDE STREAMLIT BRANDING
   ============================================================ */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stAppDeployButton"] { display: none !important; }

/* ============================================================
   TOMBOL SIDEBAR DI HP
   ============================================================ */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important; visibility: visible !important;
    z-index: 999999 !important; position: fixed !important;
    top: 15px !important; left: 15px !important;
    background-color: #6366f1 !important; border-radius: 8px !important;
    padding: 8px 12px !important; box-shadow: 0 4px 15px rgba(0,0,0,0.6) !important;
}
[data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapsedControl"] svg { display: none !important; }
[data-testid="stExpandSidebarButton"]::after, [data-testid="stSidebarCollapsedControl"]::after {
    content: "☰"; font-size: 24px; font-weight: bold; color: white;
}
</style>
"""


def load_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


# (Fungsi hero, page_header, section_title, card, dll biarkan sama seperti aslinya)
def hero(title, subtitle, badge_text="", badge_color="#06b6d4"):
    badge_html = ""
    if badge_text:
        rgb = _rgb(badge_color)
        badge_html = (f'<div style="display: inline-block; padding: 6px 14px; background: rgba({rgb}, 0.12); color: {badge_color}; border: 1px solid rgba({rgb}, 0.32); border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 1.2px; margin-bottom: 14px;">● {badge_text}</div>')
    return (f'<div class="hero-title" style="background: linear-gradient(135deg, #0d1424 0%, #0a1020 100%); border: 1px solid #1e2942; border-radius: 20px; padding: 36px 40px; margin-bottom: 28px;">{badge_html}<div style="font-size: 36px; font-weight: 900; color: #ffffff; letter-spacing: -0.04em; line-height: 1.05; margin-bottom: 10px;">{title}</div><div style="font-size: 14px; color: #94a3b8; line-height: 1.5; max-width: 640px;">{subtitle}</div></div>')

def page_header(icon, title, subtitle=""):
    icon = (icon or "").strip()
    icon_html = (f'<div style="width: 54px; height: 54px; background: linear-gradient(135deg, #6366f1, #06b6d4); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 25px; box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);">{icon}</div>') if icon else ""
    return (f'<div style="background: linear-gradient(135deg, #0d1424 0%, #0a1020 100%); border: 1px solid #1e2942; border-radius: 16px; padding: 22px 26px; margin-bottom: 24px; display: flex; align-items: center; gap: 18px;">{icon_html}<div><div style="font-size: 11px; color: #7d8ba3; letter-spacing: 1.3px; font-weight: 700; margin-bottom: 5px; text-transform: uppercase;">{subtitle}</div><div style="font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.03em; line-height: 1;">{title}</div></div></div>')

def section_title(title, subtitle=""):
    sub_html = (f'<div style="font-size: 12px; color: #7d8ba3; margin-left: 17px; margin-top: 4px;">{subtitle}</div>') if subtitle else ''
    return (f'<div style="margin: 30px 0 16px;"><div style="display: flex; align-items: center; gap: 13px;"><div style="width: 4px; height: 22px; background: linear-gradient(180deg, #6366f1, #06b6d4); border-radius: 2px;"></div><div style="font-size: 18px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">{title}</div></div>{sub_html}</div>')

def empty_state(icon, title, subtitle=""):
    return (f'<div style="text-align: center; padding: 60px 20px; background: #0d1424; border: 1px dashed #2c3a5c; border-radius: 14px;"><div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;">{icon}</div><div style="font-size: 16px; font-weight: 700; color: #e6ebf5; margin-bottom: 8px;">{title}</div><div style="font-size: 13px; color: #7d8ba3;">{subtitle}</div></div>')