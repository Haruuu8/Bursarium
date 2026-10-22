"""Script auto-fetch berita IDX — dijalankan oleh GitHub Actions.

Letak: quant/fetch_news_auto.py (reuse folder quant/, tidak perlu folder baru)
Jalankan manual: python -m quant.fetch_news_auto
"""

import os
import sys
import json
import time
from datetime import datetime

# Tambahkan root ke path agar bisa import quant.idx_news
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from quant.idx_news import fetch_announcements

OUTPUT_FILE = os.path.join(ROOT, "data_news_static.json")


def main():
    print(f"[{datetime.now()}] Mulai ambil berita IDX...")
    data = fetch_announcements(days=30, max_items=5000)

    if not data:
        print("❌ GAGAL: Tidak ada data terambil (Cloudflare/blokir IDX).")
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "cached_at": time.time(),
            "generated_at": datetime.now().isoformat(),
            "total": len(data),
            "data": data,
        }, f, ensure_ascii=False, indent=2, default=str)

    newest = data[0]["tanggal"] if data else "?"
    print(f"✅ BERHASIL: {len(data)} berita → {OUTPUT_FILE}")
    print(f"   Terbaru: {newest}")


if __name__ == "__main__":
    main()