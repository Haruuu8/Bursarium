"""Hapus inject render_user_sidebar() dari views/*.py."""

import ast
import os
import re


FILES = [
    "views/Dashboard.py",
    "views/Fundamental.py",
    "views/Technical.py",
    "views/Watchlist.py",
    "views/Valuation.py",
    "views/News.py",
]

# Pattern blok yang mau dihapus
PATTERN = re.compile(
    r'\n# =+\n'
    r'# SIDEBAR \(user card \+ logout \+ menu\)\n'
    r'# =+\n'
    r'try:\n'
    r'    from quant\.nav import render_user_sidebar\n'
    r'    render_user_sidebar\(\)\n'
    r'except Exception[^\n]*:\n'
    r'(?:    [^\n]*\n)*'
    r'\n?',
    re.MULTILINE,
)


def clean(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")

    if "render_user_sidebar" not in text:
        print(f"→ skip (tidak ada inject): {path}")
        return

    new_text = PATTERN.sub("\n", text)

    if new_text == text:
        # Fallback: hapus baris per baris
        lines = text.split("\n")
        out = []
        skip = False
        for line in lines:
            if "# SIDEBAR (user card + logout + menu)" in line:
                skip = True
                continue
            if skip:
                # Skip sampai ketemu baris yang bukan bagian dari try block
                if line.startswith("    ") or line.strip() == "" or \
                   "render_user_sidebar" in line or \
                   "from quant.nav" in line or \
                   "try:" in line or "except" in line or \
                   line.startswith("# ==="):
                    continue
                else:
                    skip = False
            out.append(line)
        new_text = "\n".join(out)

    # Verify
    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"✗ {path}: line {e.lineno} — {e.msg}")
        return

    with open(path, "wb") as f:
        f.write(new_text.encode("utf-8"))
    print(f"✓ Cleaned: {path}")


if __name__ == "__main__":
    print("=" * 55)
    print("HAPUS INJECT SIDEBAR DARI views/*.py")
    print("=" * 55)
    for f in FILES:
        if os.path.exists(f):
            clean(f)
        else:
            print(f"✗ Not found: {f}")
    print("\n✓ Selesai")