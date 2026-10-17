"""Fix mojibake + emoji dengan exact codepoint sequence."""

import ast
import os


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
# 1. Mojibake multi-char → ganti atau hapus
# ============================================================
REPLACE_MAP = [
    # === ARROW (â†' = →) ===
    ("\u00e2\u2020\u2019", "→"),

    # === STAR (â˜… = ⭐) → HAPUS ===
    ("\u00e2\u02dc\u2026", ""),

    # === WARNING (âš ï¸ = ⚠️) → ⚠ ===
    ("\u00e2\u0161\u00a0\u00ef\u00b8\u008f", "⚠"),

    # === GEAR (âš™ï¸ = ⚙️) → ⚙ ===
    ("\u00e2\u0161\u2122\u00ef\u00b8\u008f", "⚙"),

    # === SEARCH (ðŸ" = 🔍) → HAPUS ===
    ("\u00f0\u0178\u201d\u008d", ""),

    # === SEEDLING (ðŸŒ± = 🌱) → HAPUS ===
    ("\u00f0\u0178\u0152\u00b1", ""),

    # === RED FLAG (ðŸš© = 🚩) → HAPUS ===
    ("\u00f0\u0178\u0161\u00a9", ""),

    # === CARD (ðŸŽ´ = 🎴) → HAPUS ===
    ("\u00f0\u0178\u017d\u00b4", ""),

    # === Bullet / other emoji variants ===
    ("\u00f0\u0178\u201c\u008a", ""),   # 📊
    ("\u00f0\u0178\u201c\u0088", ""),   # 📈
    ("\u00f0\u0178\u201c\u0089", ""),   # 📉
    ("\u00f0\u0178\u201c\u00b0", ""),   # 📰
    ("\u00f0\u0178\u2019\u00b0", ""),   # 💰
    ("\u00f0\u0178\u201c\u00a5", ""),   # 📥

    # === Single control chars (sisa) ===
    ("\u0090", ""),
    ("\u008f", ""),
    ("\u008d", ""),
    ("\u0080", ""),
    ("\u0081", ""),
    ("\u0082", ""),
    ("\u0083", ""),
    ("\u0084", ""),
    ("\u0085", ""),
    ("\u0086", ""),
    ("\u0087", ""),
    ("\u0088", ""),
    ("\u0089", ""),
    ("\u008a", ""),
    ("\u008b", ""),
    ("\u008c", ""),
    ("\u008e", ""),
    ("\u0091", ""),
    ("\u0092", ""),
    ("\u0093", ""),
    ("\u0094", ""),
    ("\u0095", ""),
    ("\u0096", ""),
    ("\u0097", ""),
    ("\u0098", ""),
    ("\u0099", ""),
    ("\u009a", ""),
    ("\u009b", ""),
    ("\u009c", ""),
    ("\u009d", ""),
    ("\u009e", ""),
    ("\u009f", ""),

    # === Sisa mojibake single char (dari emoji yang tidak full match) ===
    ("\u0178", ""),   # Ÿ
    ("\u00f0", ""),   # ð
    ("\u00e2", ""),   # â (sisa)
    ("\u0161", ""),   # š
    ("\u017d", ""),   # Ž
    ("\u0152", ""),   # Œ
    ("\u00b1", ""),   # ± (sisa dari ðŸŒ±)
    ("\u00a9", ""),   # © (sisa dari ðŸš©)
    ("\u00b4", ""),   # ´
    ("\u00ef", ""),   # ï (sisa)
    ("\u00b8", ""),   # ¸ (sisa)
    ("\u02dc", ""),   # ˜
    ("\u2122", ""),   # ™ (sisa)
    ("\u2020", ""),   # † (sisa)
    ("\u2020", ""),
    ("\u00a0", " "),  # nbsp → spasi biasa

    # === Emoji asli ===
    ("\U0001F7E2", ""),  # 🟢
    ("\U0001F7E1", ""),  # 🟡
    ("\U0001F7E0", ""),  # 🟠
    ("\U0001F534", ""),  # 🔴
    ("\U0001F7E3", ""),  # 🟣
    ("\U0001F535", ""),  # 🔵
]


def clean(text):
    for bad, good in REPLACE_MAP:
        text = text.replace(bad, good)
    # Rapikan multiple space
    while "  " in text:
        text = text.replace("  ", " ")
    # Rapikan spasi sebelum tanda baca
    text = text.replace(" .", ".").replace(" ,", ",")
    text = text.replace(" ;", ";").replace(" :", ":")
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
    print("FIX MOJIBAKE FINAL")
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