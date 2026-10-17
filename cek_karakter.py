"""Cek karakter non-ASCII di views/*.py."""

import os


FILES = [
    "views/Dashboard.py",
    "views/Fundamental.py",
    "views/Technical.py",
    "views/Watchlist.py",
    "views/Valuation.py",
    "views/News.py",
]


def read(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8", errors="replace")


for f in FILES:
    if not os.path.exists(f):
        continue
    text = read(f)
    print(f"\n{'=' * 55}")
    print(f"FILE: {f}")
    print("=" * 55)

    # Cari karakter non-ASCII
    found = {}
    for i, ch in enumerate(text):
        if ord(ch) > 127:
            key = f"U+{ord(ch):04X}  {repr(ch)}"
            if key not in found:
                # Konteks 30 char sekitarnya
                ctx = text[max(0, i-20):i+20].replace("\n", " ")
                found[key] = ctx

    if not found:
        print("  ✓ Tidak ada karakter non-ASCII")
    else:
        for key, ctx in list(found.items())[:30]:  # max 30 unique
            print(f"  {key}")
            print(f"     ...{ctx}...")