"""Inject render_user_sidebar() ke views/Dashboard.py."""

import ast
import re


PATH = "views/Dashboard.py"

INJECT = (
    '\n# ============================================================\n'
    '# SIDEBAR (user card + logout + menu)\n'
    '# ============================================================\n'
    'try:\n'
    '    from quant.nav import render_user_sidebar\n'
    '    render_user_sidebar()\n'
    'except Exception as _e:\n'
    '    import streamlit as _st\n'
    '    _st.sidebar.error(f"Sidebar error: {_e}")\n\n'
)


with open(PATH, "rb") as f:
    raw = f.read()
if raw.startswith(b"\xef\xbb\xbf"):
    raw = raw[3:]
text = raw.decode("utf-8", errors="replace")

if "render_user_sidebar" in text:
    print("→ Sudah ada. Skip.")
else:
    # Cari guard login
    pattern = re.compile(
        r'(if not st\.session_state\.get\("authentication_status"\):\s*\n'
        r'\s+st\.error\([^\n]*\)\s*\n'
        r'\s+st\.stop\(\)\s*\n)',
    )
    m = pattern.search(text)
    if m:
        pos = m.end()
        text = text[:pos] + INJECT + text[pos:]
        print(f"✓ Injected setelah guard (pos {pos})")
    else:
        # Cari setelah set_page_config
        pattern2 = re.compile(r'(st\.set_page_config\([^)]*\)\s*\n)')
        m2 = pattern2.search(text)
        if m2:
            pos = m2.end()
            text = text[:pos] + INJECT + text[pos:]
            print(f"✓ Injected setelah set_page_config (pos {pos})")
        else:
            print("✗ Tidak ada guard / set_page_config. Manual edit perlu.")
            exit(1)

    # Verify
    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"✗ Syntax error line {e.lineno}: {e.msg}")
        exit(1)

    with open(PATH, "wb") as f:
        f.write(text.encode("utf-8"))
    print("✓ File disimpan")