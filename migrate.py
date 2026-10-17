"""Migrasi pages/ → views/ + update semua referensi."""

import os
import shutil


def main():
    # 1. Rename folder
    if os.path.exists("pages") and not os.path.exists("views"):
        shutil.move("pages", "views")
        print("✓ Renamed: pages/ → views/")
    elif os.path.exists("views"):
        print("→ views/ sudah ada, skip rename")
    else:
        print("✗ pages/ tidak ditemukan")
        return

    # 2. Update references di semua file .py
    targets = ["Daftar.py", "quant/nav.py"]
    for f in os.listdir("views"):
        if f.endswith(".py"):
            targets.append(os.path.join("views", f))

    for path in targets:
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            raw = f.read()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        text = raw.decode("utf-8", errors="replace")

        original = text
        text = text.replace('"pages/', '"views/')
        text = text.replace("'pages/", "'views/")
        text = text.replace('"pages\\\\', '"views\\\\')

        if text != original:
            with open(path, "wb") as f:
                f.write(text.encode("utf-8"))
            print(f"✓ Updated: {path}")

    print("\n✓ Migrasi selesai")


if __name__ == "__main__":
    main()