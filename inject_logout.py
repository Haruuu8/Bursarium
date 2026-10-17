"""Inject render_user_sidebar() ke semua pages/*.py."""

import ast
import os
import re


PAGES = [
    "pages/Dashboard.py",
    "pages/Fundamental.py",
    "pages/Technical.py",
    "pages/Watchlist.py",
    "pages/Valuation.py",
    "pages/News.py",
]

INJECT_BLOCK = (
    '\n# ============================================================\n'
    '# SIDEBAR (user card + logout + menu)\n'
    '# ============================================================\n'
    'try:\n'
    '    from quant.nav import render_user_sidebar\n'
    '    render_user_sidebar()\n'
    'except Exception:\n'
    '    pass\n\n'
)


def inject(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Skip kalau sudah ada
    if "render_user_sidebar" in text:
        print(f"→ skip (sudah ada): {path}")
        return

    # Cari posisi setelah guard login (st.stop() setelah auth check)
    pattern = re.compile(
        r'(if not st\.session_state\.get\("authentication_status"\):\s*\n'
        r'\s+st\.error\([^\n]*\)\s*\n'
        r'\s+st\.stop\(\)\s*\n)',
    )
    m = pattern.search(text)
    if m:
        pos = m.end()
        text = text[:pos] + INJECT_BLOCK + text[pos:]
    else:
        # Fallback: sisipkan setelah st.set_page_config
        pattern2 = re.compile(r'(st\.set_page_config\([^)]*\)\s*\n)')
        m2 = pattern2.search(text)
        if not m2:
            print(f"✗ {path}: tidak ada guard / set_page_config")
            return
        pos = m2.end()
        text = text[:pos] + INJECT_BLOCK + text[pos:]

    # Verify syntax
    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"✗ {path}: line {e.lineno} — {e.msg}")
        return

    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    print(f"✓ Injected: {path}")


if __name__ == "__main__":
    print("=" * 55)
    print("INJECT SIDEBAR (user card + logout + menu)")
    print("=" * 55)
    for p in PAGES:
        if os.path.exists(p):
            inject(p)
        else:
            print(f"✗ Not found: {p}")
    print("\n✓ Selesai")