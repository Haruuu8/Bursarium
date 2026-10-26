"""Slim down data_news_static.json — hapus field yang tidak penting."""
import json

with open("data_news_static.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

# Field yang dipertahankan (buang 'isi' yang panjang, 'no_pengumuman', dll)
KEEP_FIELDS = ["tanggal", "kode", "judul", "kategori", "tipe", "bobot", "lampiran"]

slimmed = []
for item in payload.get("data", []):
    slim_item = {k: item[k] for k in KEEP_FIELDS if k in item}
    # Potong judul max 200 karakter (biasanya cukup)
    if "judul" in slim_item:
        slim_item["judul"] = slim_item["judul"][:200]
    slimmed.append(slim_item)

new_payload = {
    "cached_at": payload.get("cached_at"),
    "generated_at": payload.get("generated_at"),
    "total": len(slimmed),
    "data": slimmed,
}

with open("data_news_static.json", "w", encoding="utf-8") as f:
    json.dump(new_payload, f, ensure_ascii=False, separators=(",", ":"))

import os
size_mb = os.path.getsize("data_news_static.json") / (1024 * 1024)
print(f"✅ Slimmed: {len(slimmed)} items, {size_mb:.2f} MB")