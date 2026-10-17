"""Hapus semua emoji dari views/*.py — sidebar pakai Material Symbols tetap."""

import ast
import os
import re


# Pattern: emoji ranges + trailing whitespace
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"    # Misc Symbols and Pictographs
    "\U0001F600-\U0001F64F"    # Emoticons
    "\U0001F680-\U0001F6FF"    # Transport & Map
    "\U0001F700-\U0001F77F"    # Alchemical
    "\U0001F900-\U0001F9FF"    # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FAFF"    # Symbols & Pictographs Extended-A
    "\U00002600-\U000026FF"    # Misc Symbols
    "\U00002700-\U000027BF"    # Dingbats
    "\U00002B00-\U00002BFF"    # Misc Symbols and Arrows
    "\U0001F000-\U0001F02F"    # Mahjong
    "\U0001F0A0-\U0001F0FF"    # Playing Cards
    "\U0001F100-\U0001F1FF"    # Enclosed
    "\U0001F200-\U0001F2FF"    # Enclosed Ideographic
    "]+"
    "[\\s\\uFE0F\\u200D]*"     # trailing spaces + variation selectors
)

FILES = [
    "views/Dashboard.py",
    "views/Fundamental.py",
    "views/Technical.py",
    "views/Watchlist.py",
    "views/Valuation.py",
    "views/News.py",
]


def process(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")

    before = len(EMOJI_PATTERN.findall(text))
    new_text = EMOJI_PATTERN.sub("", text)
    after = len(EMOJI_PATTERN.findall(new_text))
    removed = before - after

    if removed == 0:
        print(f"→ skip (tidak ada emoji): {path}")
        return

    # Verify syntax
    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"✗ {path}: line {e.lineno} — {e.msg}")
        return

    with open(path, "wb") as f:
        f.write(new_text.encode("utf-8"))
    print(f"✓ {path}: {removed} emoji dihapus")


if __name__ == "__main__":
    print("=" * 55)
    print("HAPUS EMOJI DARI views/*.py")
    print("=" * 55)
    for f in FILES:
        if os.path.exists(f):
            process(f)
        else:
            print(f"✗ Not found: {f}")
    print("\n✓ Selesai")