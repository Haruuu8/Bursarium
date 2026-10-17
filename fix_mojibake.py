"""Fix semua mojibake + emoji di views/*.py."""

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


# Step 1: Mojibake → simbol bersih
REPLACE_MAP = [
    # Arrows
    ("â†’", "→"), ("â†'", "→"),
    ("â†‘", "↑"), ("â†“", "↓"),
    ("â†—", "↗"), ("â†˜", "↘"), ("â†™", "↙"),
    # Math
    ("â‰¥", "≥"), ("â‰¤", "≤"), ("â‰ˆ", "≈"),
    ("Ã—", "×"), ("Â·", "·"),
    # Dashes / punctuation
    ("â€”", "—"), ("â€“", "–"), ("â€¦", "…"),
    ("â€œ", '"'), ("â€\x9d", '"'), ("â€™", "'"),
    # Check / cross / bullet
    ("âœ“", "✓"), ("âœ•", "✕"), ("âœ—", "✗"), ("âœ…", "✓"),
    ("â—", "●"), ("â— ", "●"),
    ("â–²", "▲"), ("â–¼", "▼"),
    # Warning
    ("âš ï¸ ", "⚠"), ("âš ï¸", "⚠"), ("âš¡", "⚡"),
]


# Step 2: Orphan mojibake → hapus
DELETE_PATTERNS = [
    r'ðŸ[^\w\s]{0,3}',
    r'ð[^\w\s]{1,3}',
    r'â[^\w\s]{1,3}',
    r'â˜…', r'â­', r'âš',
]


# Step 3: Emoji ranges → hapus
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0001F000-\U0001F02F"
    "\U0001F0A0-\U0001F0FF"
    "\U0001F100-\U0001F1FF"
    "\U0001F200-\U0001F2FF"
    "]+[\uFE0F\u200D\\s]*"
)


def clean(text):
    for bad, good in REPLACE_MAP:
        text = text.replace(bad, good)
    for pat in DELETE_PATTERNS:
        text = re.sub(pat, "", text)
    text = EMOJI_RE.sub("", text)
    # Rapikan double space sisa
    text = re.sub(r"  +", " ", text)
    return text


FILES = [
    "views/Dashboard.py",
    "views/Fundamental.py",
    "views/Technical.py",
    "views/Watchlist.py",
    "views/Valuation.py",
    "views/News.py",
]


if __name__ == "__main__":
    print("=" * 55)
    print("FIX MOJIBAKE + EMOJI")
    print("=" * 55)
    for f in FILES:
        if not os.path.exists(f):
            print(f"✗ {f} — not found")
            continue
        text = read(f)
        new = clean(text)
        if new == text:
            print(f"→ skip: {f}")
            continue
        if not verify(new, f):
            continue
        write(f, new)
        print(f"✓ {f}")
    print("\n✓ Selesai")