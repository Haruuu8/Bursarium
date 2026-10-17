"""Fix 3 hal: hapus kotak icon di sector cards, hapus glow di News header,
fix kotak kode di Technical."""

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
        print(f"  ✗ Syntax error di {path} line {e.lineno}: {e.msg}")
        return False


# ============================================================
# FIX 1 — DASHBOARD: hapus div kotak icon di sector cards
# ============================================================
def fix_dashboard():
    path = "views/Dashboard.py"
    text = read(path)

    # Pattern: div dengan icon di dalam card sektor
    pattern = re.compile(
        r"\s*f'<div style=\"font-size: 24px; width: 44px; height: 44px; '\s*\n"
        r"\s*f'display: flex; align-items: center; justify-content: center; '\s*\n"
        r"\s*f'border-radius: 10px; background: #0a0e1a; flex-shrink: 0; '\s*\n"
        r"\s*f'border: 1px solid #1f2a3d;\">\{icon\}</div>'\s*\n",
        re.MULTILINE,
    )

    new_text = pattern.sub("\n", text)

    if new_text == text:
        # Coba pattern alternatif (single line)
        pattern2 = re.compile(
            r"\s*f'<div[^>]*>\{icon\}</div>'\s*\n",
        )
        new_text = pattern2.sub("\n", text)

    if new_text == text:
        print("→ Dashboard: tidak ada perubahan (pattern tidak match)")
        return

    if not verify(new_text, path):
        return

    write(path, new_text)
    print("✓ Dashboard: kotak icon dihapus")


# ============================================================
# FIX 2 — NEWS: hapus glow radial kuning di header
# ============================================================
def fix_news():
    path = "views/News.py"
    text = read(path)

    # Pattern: div glow dengan radial-gradient
    pattern = re.compile(
        r"\s*'<div style=\"position:absolute; right:-40px; top:-40px; '\s*\n"
        r"\s*'width:200px; height:200px; '\s*\n"
        r"\s*'background:radial-gradient\(circle, rgba\(245,158,11,0\.15\), transparent 70%\);'\s*\n"
        r"\s*'\"></div>'\s*\n",
        re.MULTILINE,
    )

    new_text = pattern.sub("\n", text)

    if new_text == text:
        print("→ News: tidak ada perubahan (pattern tidak match)")
        return

    if not verify(new_text, path):
        return

    write(path, new_text)
    print("✓ News: glow header dihapus")


# ============================================================
# FIX 3 — TECHNICAL: ganti kotak kode jadi gradient konsisten
# ============================================================
def fix_technical():
    path = "views/Technical.py"
    text = read(path)

    # Cari kotak "BB" (background abu-abu #1e293b)
    old_pattern = re.compile(
        r"background: #1e293b; '\s*\n"
        r"\s*f'border-radius: 16px; display: flex; align-items: center; '\s*\n"
        r"\s*f'justify-content: center; font-size: 24px; font-weight: 800; '\s*\n"
        r"\s*f'color: #06b6d4;",
        re.MULTILINE,
    )

    if not old_pattern.search(text):
        print("→ Technical: tidak ada perubahan (pattern tidak match)")
        return

    # Ganti ke gradient + text putih (konsisten dengan Dashboard)
    new_text = old_pattern.sub(
        "background: linear-gradient(135deg, #6366f1, #06b6d4); '\n"
        "    f'border-radius: 16px; display: flex; align-items: center; '\n"
        "    f'justify-content: center; font-size: 24px; font-weight: 800; '\n"
        "    f'color: #ffffff;",
        text,
    )

    if not verify(new_text, path):
        return

    write(path, new_text)
    print("✓ Technical: kotak kode diubah gradient ungu-cyan")


# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("FIX 3 HAL")
    print("=" * 55)
    fix_dashboard()
    fix_news()
    fix_technical()
    print("\n✓ Selesai")