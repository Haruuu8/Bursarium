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
    background: #0a1020 !important;
    border-right: 1px solid #1e2942 !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }

h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
}

[data-testid="stVerticalBlock"] > [style*="flex-direction: column"] >
[data-testid="stVerticalBlock"] {
    animation: fadeInUp 320ms cubic-bezier(0.16, 1, 0.3, 1);
}
[data-testid="stMarkdownContainer"] { animation: fadeIn 260ms ease-out; }

/* ============================================================
   BUTTONS
   ============================================================ */
.stButton > button, .stDownloadButton > button {
    background: #131a2e !important;
    border: 1px solid #1e2942 !important;
    color: #e6ebf5 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 8px 16px !important;
    transition: background 180ms ease, border-color 180ms ease,
                color 180ms ease, transform 120ms ease,
                box-shadow 180ms ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: #1a2340 !important;
    border-color: #2c3a5c !important;
    color: #ffffff !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}
.stButton > button:active, .stDownloadButton > button:active {
    transform: translateY(0);
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: 1px solid #6366f1 !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #7075f5, #5b52ea) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
}

.stFormSubmitButton > button {
    background: #131a2e !important;
    border: 1px solid #1e2942 !important;
    color: #e6ebf5 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 16px !important;
    transition: background 180ms ease, border-color 180ms ease,
                transform 120ms ease, box-shadow 180ms ease !important;
}
.stFormSubmitButton > button:hover {
    background: #1a2340 !important;
    border-color: #2c3a5c !important;
    color: #ffffff !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}
.stFormSubmitButton > button[kind="primary"],
.stFormSubmitButton > button[data-testid="baseButton-primaryFormSubmit"] {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: 1px solid #6366f1 !important;
    color: #ffffff !important;
}
.stFormSubmitButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #7075f5, #5b52ea) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
}

/* ============================================================
   INPUTS
   ============================================================ */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: #0d1424 !important;
    border: 1px solid #1e2942 !important;
    border-radius: 10px !important;
    color: #e6ebf5 !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    transition: border-color 180ms ease, box-shadow 180ms ease !important;
}
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #0d1424 !important;
    border: 1px solid #1e2942 !important;
    border-radius: 10px !important;
    color: #e6ebf5 !important;
    transition: border-color 180ms ease, box-shadow 180ms ease !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stDateInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.14) !important;
    outline: none !important;
}

/* ============================================================
   TABS
   ============================================================ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 1px solid #1e2942 !important;
    padding: 0 !important;
    margin-bottom: 24px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 0 !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 10px 16px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    position: relative !important;
    transition: color 180ms ease !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #e6ebf5 !important; }
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #06b6d4 !important;
    border-bottom: none !important;
    box-shadow: none !important;
}
.stTabs [aria-selected="true"]::after {
    content: "" !important;
    position: absolute !important;
    bottom: 0 !important; left: 0 !important; right: 0 !important;
    height: 2px !important;
    background: linear-gradient(90deg,
        rgba(6, 182, 212, 0.1) 0%,
        #06b6d4 50%,
        rgba(6, 182, 212, 0.1) 100%) !important;
    animation: fadeIn 200ms ease-out;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none !important; height: 0 !important;
    width: 0 !important; opacity: 0 !important;
}
.stTabs [role="tabpanel"] {
    animation: fadeInUp 260ms cubic-bezier(0.16, 1, 0.3, 1);
}

/* ============================================================
   EXPANDER
   ============================================================ */
[data-testid="stExpander"] {
    background: #0d1424 !important;
    border: 1px solid #1e2942 !important;
    border-radius: 12px !important;
    transition: border-color 180ms ease, box-shadow 180ms ease !important;
}
[data-testid="stExpander"]:hover {
    border-color: #2c3a5c !important;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

/* ============================================================
   POPOVER LOGIN
   ============================================================ */
[data-testid="stPopover"] > button {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: 1px solid #6366f1 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 10px 18px !important;
    border-radius: 10px !important;
    transition: all 180ms ease !important;
    width: 100% !important;
}
[data-testid="stPopover"] > button:hover {
    background: linear-gradient(135deg, #7075f5, #5b52ea) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4) !important;
    transform: translateY(-1px);
}
[data-testid="stPopoverBody"] {
    background: #0d1424 !important;
    border: 1px solid #2c3a5c !important;
    border-radius: 12px !important;
    padding: 20px !important;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5) !important;
}

/* ============================================================
   DATAFRAME
   ============================================================ */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid #1e2942 !important;
    animation: fadeInUp 300ms cubic-bezier(0.16, 1, 0.3, 1);
}

/* ============================================================
   SLIDER
   ============================================================ */
.stSlider [role="slider"] {
    background: #06b6d4 !important;
    transition: transform 120ms ease, box-shadow 180ms ease !important;
}
.stSlider [role="slider"]:hover {
    transform: scale(1.15);
    box-shadow: 0 0 0 6px rgba(6, 182, 212, 0.12);
}

/* ============================================================
   MODAL & METRIC
   ============================================================ */
[data-testid="stModal"] { animation: fadeIn 200ms ease-out; }
[data-testid="stModal"] > div > div {
    animation: scaleIn 280ms cubic-bezier(0.16, 1, 0.3, 1);
}

[data-testid="stMetric"] {
    background: linear-gradient(180deg, #0d1424 0%, #0a1020 100%) !important;
    border: 1px solid #1e2942 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    transition: transform 180ms ease, border-color 180ms ease,
                box-shadow 180ms ease !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    border-color: #2c3a5c !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

/* ============================================================
   MATERIAL SYMBOLS ICON — konsisten monokrom
   ============================================================ */
[data-testid="stIconMaterial"],
span[class*="material-symbols"] {
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24 !important;
    color: #94a3b8 !important;
    font-size: 18px !important;
    transition: color 180ms ease !important;
}

/* Page link di sidebar */
[data-testid="stPageLink"] {
    padding: 10px 12px !important;
    border-radius: 10px !important;
    margin-bottom: 3px !important;
    transition: background 180ms ease !important;
    color: #94a3b8 !important;
    text-decoration: none !important;
}
[data-testid="stPageLink"]:hover {
    background: rgba(99, 102, 241, 0.08) !important;
    color: #e6ebf5 !important;
}
[data-testid="stPageLink"]:hover [data-testid="stIconMaterial"] {
    color: #06b6d4 !important;
}
[data-testid="stPageLink"][aria-current="page"] {
    background: rgba(99, 102, 241, 0.14) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}
[data-testid="stPageLink"][aria-current="page"] [data-testid="stIconMaterial"] {
    color: #06b6d4 !important;
    font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24 !important;
}

[data-testid="stPageLink-NavLink"] {
    padding: 10px 12px !important;
    border-radius: 10px !important;
    color: #94a3b8 !important;
    text-decoration: none !important;
    transition: background 180ms ease, color 180ms ease !important;
}
[data-testid="stPageLink-NavLink"]:hover {
    background: rgba(99, 102, 241, 0.08) !important;
    color: #e6ebf5 !important;
}

/* ============================================================
   SCROLLBAR
   ============================================================ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #070b16; }
::-webkit-scrollbar-thumb {
    background: #2c3a5c; border-radius: 3px;
    transition: background 180ms ease;
}
::-webkit-scrollbar-thumb:hover { background: #3a4d75; }

/* ============================================================
   HIDE STREAMLIT BRANDING
   ============================================================ */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stAppDeployButton"] { display: none !important; }

/* Sembunyikan stray text node */
[data-testid="stMarkdown"] > div > p:empty {
    display: none;
}


/* ============================================================ */
/* 🔥 TAMBAHAN CSS UNTUK MOBILE (RESPONSIVE & STACKING) 🔥 */
/* ============================================================ */

/* 1. Memaksa Tombol Sidebar (Hamburger) Muncul di HP */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
    position: fixed !important;
    top: 15px !important;
    left: 15px !important;
    background-color: #6366f1 !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.6) !important;
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
    font-size: 24px;
    font-weight: bold;
    color: white;
    line-height: 1;
}

/* 2. PERBAIKAN DESAIN KHUSUS LAYAR HP (Maksimal 991px agar HP layar lebar kena) */
@media (max-width: 991px) {
    /* Perkecil padding halaman */
    .block-container {
        padding-top: 4rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }

    /* Perkecil ukuran judul */
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
    p, li, .stMarkdown { font-size: 13px !important; line-height: 1.5 !important; }

    /* ========================================================
       FIX GAMBAR 1: BUY ON SUPPORT / BREAKOUT
       (Paksa jadi rata kiri dan tumpuk ke bawah)
       ======================================================== */
    
    /* Paksa semua container yang memakai flex-row menjadi kolom */
    div[style*="display: flex; justify-content: space-between"],
    div[style*="display:flex; justify-content:space-between"],
    div[style*="justify-content:space-between"] {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 8px !important;
    }
    
    /* Paksa teks Harga Saat Ini agar RATA KIRI */
    div[style*="text-align: right"],
    div[style*="text-align:right"] {
        text-align: left !important;
        min-width: 100% !important;
        margin-top: 8px !important;
    }

    /* ========================================================
       FIX GAMBAR 2: VALUASI
       (Paksa jadi 2 kolom menyamping dan rata kiri)
       ======================================================== */
       
    /* Ubah semua Grid (baik 3 atau 4 kolom) menjadi 2 kolom (1fr 1fr) */
    div[style*="grid-template-columns: repeat(4, 1fr)"],
    div[style*="grid-template-columns:repeat(4, 1fr)"],
    div[style*="grid-template-columns: repeat(3, 1fr)"],
    div[style*="grid-template-columns:repeat(3, 1fr)"],
    div[style*="display: grid"],
    div[style*="display:grid"] {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important; /* 2 Kolom */
        gap: 12px !important;
        align-items: start !important;
        justify-items: start !important;
    }

    /* Paksa semua teks (termasuk Harga ke Fair Value) agar rata kiri */
    div[style*="text-align: center"],
    div[style*="text-align:center"] {
        text-align: left !important;
    }

    /* ========================================================
       PENYESUAIAN UKURAN LAINNYA
       ======================================================== */
    span[style*="font-size: 30px"], span[style*="font-size:30px"],
    span[style*="font-size: 26px"], span[style*="font-size:26px"],
    span[style*="font-size: 24px"], span[style*="font-size:24px"] {
        font-size: 20px !important;
    }

    div[style*="padding: 20px 24px"], div[style*="padding:20px 24px"],
    div[style*="padding: 22px 26px"], div[style*="padding:22px 26px"] {
        padding: 14px 16px !important;
    }
}
</style>
"""


def load_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


def hero(title, subtitle, badge_text="", badge_color="#06b6d4"):
    badge_html = ""
    if badge_text:
        rgb = _rgb(badge_color)
        badge_html = (
            f'<div style="display: inline-block; padding: 6px 14px; '
            f'background: rgba({rgb}, 0.12); color: {badge_color}; '
            f'border: 1px solid rgba({rgb}, 0.32); '
            f'border-radius: 20px; font-size: 11px; font-weight: 700; '
            f'letter-spacing: 1.2px; margin-bottom: 14px;">'
            f'● {badge_text}</div>'
        )
    return (
        '<div class="hero-title" style="'
        'background: linear-gradient(135deg, #0d1424 0%, #0a1020 100%); '
        'border: 1px solid #1e2942; border-radius: 20px; '
        'padding: 36px 40px; margin-bottom: 28px;">'
        f'{badge_html}'
        f'<div style="font-size: 36px; font-weight: 900; color: #ffffff; '
        f'letter-spacing: -0.04em; line-height: 1.05; margin-bottom: 10px;">'
        f'{title}</div>'
        f'<div style="font-size: 14px; color: #94a3b8; line-height: 1.5; '
        f'max-width: 640px;">{subtitle}</div>'
        '</div>'
    )


def page_header(icon, title, subtitle=""):
    icon = (icon or "").strip()
    if icon:
        icon_html = (
            f'<div style="width: 54px; height: 54px; '
            f'background: linear-gradient(135deg, #6366f1, #06b6d4); '
            f'border-radius: 14px; display: flex; align-items: center; '
            f'justify-content: center; font-size: 25px; '
            f'box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);">{icon}</div>'
        )
    else:
        icon_html = ""

    return (
        '<div style="'
        'background: linear-gradient(135deg, #0d1424 0%, #0a1020 100%); '
        'border: 1px solid #1e2942; border-radius: 16px; '
        'padding: 22px 26px; margin-bottom: 24px; '
        'display: flex; align-items: center; gap: 18px;">'
        f'{icon_html}'
        '<div>'
        f'<div style="font-size: 11px; color: #7d8ba3; letter-spacing: 1.3px; '
        f'font-weight: 700; margin-bottom: 5px; text-transform: uppercase;">'
        f'{subtitle}</div>'
        f'<div style="font-size: 24px; font-weight: 800; color: #ffffff; '
        f'letter-spacing: -0.03em; line-height: 1;">{title}</div>'
        '</div></div>'
    )


def section_title(title, subtitle=""):
    sub_html = (
        f'<div style="font-size: 12px; color: #7d8ba3; margin-left: 17px; '
        f'margin-top: 4px;">{subtitle}</div>'
    ) if subtitle else ''
    return (
        '<div style="margin: 30px 0 16px;">'
        '<div style="display: flex; align-items: center; gap: 13px;">'
        '<div style="width: 4px; height: 22px; '
        'background: linear-gradient(180deg, #6366f1, #06b6d4); '
        'border-radius: 2px;"></div>'
        f'<div style="font-size: 18px; font-weight: 800; color: #ffffff; '
        f'letter-spacing: -0.02em;">{title}</div>'
        '</div>'
        f'{sub_html}'
        '</div>'
    )


def card(content, padding="20px 24px", accent=None):
    border_style = f'border-left: 3px solid {accent}; ' if accent else ''
    return (
        '<div style="'
        'background: linear-gradient(180deg, #0d1424 0%, #0a1020 100%); '
        'border: 1px solid #1e2942; border-radius: 14px; '
        f'{border_style}'
        f'padding: {padding}; margin-bottom: 14px;">'
        f'{content}'
        '</div>'
    )


def metric_box(label, value, sub="", accent="#6366f1"):
    sub_html = (
        f'<div style="font-size: 11px; color: #7d8ba3; margin-top: 8px;">{sub}</div>'
    ) if sub else ''
    return (
        '<div style="'
        'background: linear-gradient(180deg, #0d1424 0%, #0a1020 100%); '
        'border: 1px solid #1e2942; border-radius: 12px; '
        'padding: 16px 20px;">'
        f'<div style="font-size: 11px; color: #7d8ba3; letter-spacing: 0.07em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 10px;">'
        f'{label}</div>'
        f'<div style="font-size: 24px; font-weight: 800; color: #ffffff; '
        f'letter-spacing: -0.02em;">{value}</div>'
        f'{sub_html}'
        '</div>'
    )


def stat_card(label, value, delta=None, sub="", accent="#6366f1"):
    delta_html = ""
    if delta is not None:
        try:
            v = float(delta)
            color = "#10b981" if v >= 0 else "#f43f5e"
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
    sub_html = (
        f'<div style="font-size: 11px; color: #7d8ba3; margin-top: 8px;">{sub}</div>'
    ) if sub else ''
    return (
        '<div style="'
        'background: linear-gradient(180deg, #0d1424 0%, #0a1020 100%); '
        'border: 1px solid #1e2942; border-radius: 12px; '
        f'border-left: 3px solid {accent}; '
        'padding: 16px 20px;">'
        f'<div style="font-size: 11px; color: #7d8ba3; letter-spacing: 0.07em; '
        f'font-weight: 600; text-transform: uppercase; margin-bottom: 10px;">'
        f'{label}</div>'
        f'<div style="display: flex; align-items: baseline;">'
        f'<span style="font-size: 24px; font-weight: 800; color: #ffffff; '
        f'letter-spacing: -0.02em;">{value}</span>'
        f'{delta_html}'
        '</div>'
        f'{sub_html}'
        '</div>'
    )


def info_banner(text, type="info"):
    colors = {
        "info":    ("#06b6d4", "ℹ"),
        "success": ("#10b981", "✓"),
        "warning": ("#f59e0b", "⚠"),
        "error":   ("#f43f5e", "✕"),
    }
    color, icon = colors.get(type, colors["info"])
    rgb = _rgb(color)
    return (
        f'<div style="background: rgba({rgb}, 0.08); '
        f'border: 1px solid rgba({rgb}, 0.28); '
        f'border-left: 3px solid {color}; '
        f'border-radius: 10px; padding: 12px 18px; margin-bottom: 14px;">'
        f'<div style="display: flex; gap: 10px; align-items: flex-start;">'
        f'<span style="color: {color}; font-weight: 800; font-size: 14px; '
        f'flex-shrink: 0;">{icon}</span>'
        f'<div style="font-size: 13px; color: #cbd5e1; line-height: 1.5;">'
        f'{text}</div>'
        '</div></div>'
    )


def badge(text, color="#06b6d4"):
    rgb = _rgb(color)
    return (
        f'<span style="display: inline-block; padding: 3px 10px; '
        f'background: rgba({rgb}, 0.12); color: {color}; '
        f'border: 1px solid rgba({rgb}, 0.32); border-radius: 6px; '
        f'font-size: 10px; font-weight: 800; letter-spacing: 0.5px; '
        f'text-transform: uppercase;">{text}</span>'
    )


def divider():
    return (
        '<div style="height: 1px; '
        'background: linear-gradient(90deg, transparent, #2c3a5c, transparent); '
        'margin: 24px 0;"></div>'
    )


def kv_row(label, value, accent="#e6ebf5"):
    return (
        '<div style="display: flex; justify-content: space-between; '
        'align-items: center; padding: 9px 0; '
        'border-bottom: 1px solid #1e2942;">'
        f'<span style="font-size: 13px; color: #94a3b8;">{label}</span>'
        f'<span style="font-size: 14px; font-weight: 700; color: {accent};">'
        f'{value}</span>'
        '</div>'
    )


def spacer(height="16px"):
    return f'<div style="height: {height};"></div>'


def empty_state(icon, title, subtitle=""):
    return (
        '<div style="text-align: center; padding: 60px 20px; '
        'background: #0d1424; border: 1px dashed #2c3a5c; '
        'border-radius: 14px;">'
        f'<div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;">{icon}</div>'
        f'<div style="font-size: 16px; font-weight: 700; color: #e6ebf5; '
        f'margin-bottom: 8px;">{title}</div>'
        f'<div style="font-size: 13px; color: #7d8ba3;">{subtitle}</div>'
        '</div>'
    )