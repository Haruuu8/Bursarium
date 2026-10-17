"""Fix 3: Watchlist header, News header, landing FITUR icons."""

import ast
import os
import re


def read(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8", errors="replace")


def write(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))


def verify(text, path):
    try:
        ast.parse(text)
        return True
    except SyntaxError as e:
        print(f"  ✗ Syntax error {path} line {e.lineno}: {e.msg}")
        return False


# ============================================================
# FIX 1 — WATCHLIST: hapus icon di page_header
# ============================================================
def fix_watchlist():
    path = "views/Watchlist.py"
    text = read(path)

    # Cari page_header dengan icon (apapun isinya)
    pattern = re.compile(
        r'page_header\(\s*"[^"]*"\s*,\s*"Watchlist"',
        re.MULTILINE,
    )
    new_text = pattern.sub('page_header("", "Watchlist"', text)

    if new_text == text:
        print("→ Watchlist: tidak ada perubahan")
        return
    if not verify(new_text, path):
        return
    write(path, new_text)
    print("✓ Watchlist: icon header dihapus")


# ============================================================
# FIX 2 — NEWS: ganti custom header jadi page_header biasa
# ============================================================
def fix_news():
    path = "views/News.py"
    text = read(path)

    # Cari blok custom header IDX News Flash (markdown besar)
    # Pattern: st.markdown( '<div ... IDX News Flash ... unsafe_allow_html=True )
    pattern = re.compile(
        r"st\.markdown\(\s*\n?"
        r"\s*'<div style=\"background:linear-gradient[^;]+?News Flash[^)]+?unsafe_allow_html=True\s*\n?\s*\)",
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        # Coba pattern alternatif: cari seluruh blok sampai unsafe_allow_html
        pattern2 = re.compile(
            r"# =+\s*\n# HEADER\s*\n# =+\s*\n(st\.markdown\(\s*\n.*?unsafe_allow_html=True\s*\n\))",
            re.DOTALL,
        )
        m2 = pattern2.search(text)
        if not m2:
            print("→ News: header pattern tidak ketemu")
            return
        # Ganti seluruh blok header
        new_block = (
            'st.markdown(page_header("", "IDX News Flash",\n'
            '                        "Keterbukaan informasi resmi emiten IDX"),\n'
            '            unsafe_allow_html=True)'
        )
        new_text = text[:m2.start(1)] + new_block + text[m2.end(1):]
    else:
        new_block = (
            'st.markdown(page_header("", "IDX News Flash",\n'
            '                        "Keterbukaan informasi resmi emiten IDX"),\n'
            '            unsafe_allow_html=True)'
        )
        new_text = text[:m.start()] + new_block + text[m.end():]

    # Pastikan page_header di-import
    if "page_header" not in new_text.split("def ")[0]:
        if "from quant.theme import" in new_text:
            new_text = new_text.replace(
                "from quant.theme import",
                "from quant.theme import page_header,",
                1,
            )

    if not verify(new_text, path):
        return
    write(path, new_text)
    print("✓ News: header disamakan dengan halaman lain")


# ============================================================
# FIX 3 — DAFTAR.py: hapus :material/xxx: dari FITUR
# ============================================================
def fix_landing():
    path = "Daftar.py"
    text = read(path)

    # Cari list FITUR dengan :material/...:
    pattern = re.compile(
        r'FITUR = \[\s*\n'
        r'(?:\s*\(":material/[^"]+:",\s*"[^"]+",\s*"[^"]+"\),\s*\n)+'
        r'\s*\]',
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        print("→ Daftar.py: FITUR pattern tidak ketemu")
        return

    new_fitur = '''FITUR = [
    ("Dashboard",    "Ringkasan market & watchlist harian"),
    ("Fundamental",  "Analisis rasio keuangan & valuasi emiten IDX"),
    ("Technical",    "Chart, RSI, support-resistance, pre-cross setup"),
    ("Watchlist",    "Pantau saham favorit Anda"),
    ("Valuation",    "Hitung valuasi & risk/reward otomatis"),
    ("News",         "Berita terkini seputar pasar IDX"),
]'''

    new_text = text[:m.start()] + new_fitur + text[m.end():]

    # Update loop FITUR (karena structure berubah dari 3-tuple jadi 2-tuple)
    old_loop = re.compile(
        r'for i, \(icon, nama, desk\) in enumerate\(FITUR\):',
    )
    new_text = old_loop.sub(
        "for i, (nama, desk) in enumerate(FITUR):",
        new_text,
    )

    # Update HTML template di dalam loop: hapus bagian icon
    old_icon_html = re.compile(
        r"f'<div style=\"display:flex; align-items:center; gap:12px; '\s*\n"
        r"\s*f'margin-bottom:8px;\">'\s*\n"
        r"\s*f'<div style=\"font-size:24px;\">\{icon\}</div>'\s*\n"
        r"\s*f'<div style=\"font-size:16px; font-weight:800; '\s*\n"
        r"\s*f'color:#ffffff;\">\{nama\}</div></div>'",
        re.MULTILINE,
    )
    new_text = old_icon_html.sub(
        "f'<div style=\"margin-bottom:8px;\">'\n"
        "                f'<div style=\"font-size:16px; font-weight:800; '\n"
        "                f'color:#ffffff;\">{nama}</div></div>'",
        new_text,
    )

    if not verify(new_text, path):
        return
    write(path, new_text)
    print("✓ Daftar.py: FITUR icon dihapus")


# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("FIX 3 HAL")
    print("=" * 55)
    fix_watchlist()
    fix_news()
    fix_landing()
    print("\n✓ Selesai")