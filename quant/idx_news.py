"""
IDX NEWS — Scraper keterbukaan informasi dari IDX.

Endpoint: /primary/NewsAnnouncement/GetAllAnnouncement
- Pagination via pageNumber + pageSize
- Response: {Items, ItemCount, PageSize, PageNumber, PageCount}
"""

import os
import json
import time
from datetime import datetime, timedelta

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    curl_requests = None
    HAS_CURL_CFFI = False

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

try:
    import requests as std_requests
except ImportError:
    std_requests = None

import pandas as pd


CACHE_DIR = "data_idx_news"
BASE = "https://www.idx.co.id"
ENDPOINT = f"{BASE}/primary/NewsAnnouncement/GetAllAnnouncement"
CACHE_TTL_HOURS = 3
FAILED_CACHE_TTL_SEC = 300   # 5 menit cooldown kalau IDX gagal


# ============================================================
# KATEGORI
# ============================================================
KATEGORI = {
    "PENGENDALI": {
        "warna": "#10b981", "icon": "👑", "tipe": "good", "bobot": 10,
        "kata": [
            "perubahan pengendali", "pengambilalihan", "akuisisi",
            "takeover", "pengendali baru", "change of control",
            "calon pengendali", "pemegang saham pengendali baru",
            "penawaran tender", "tender wajib",
            "pengambilalihan saham", "peralihan pengendali",
            "pihak pengendali baru",
        ],
    },
    "PMTHMETD": {
        "warna": "#10b981", "icon": "💎", "tipe": "good", "bobot": 9,
        "kata": [
            "penambahan modal tanpa hak memesan efek terlebih dahulu",
            "pmthmetd", "private placement", "penempatan saham baru",
            "tanpa hmetd", "tanpa hak memesan", "penerbitan saham baru",
            "penambahan modal tanpa hmetd", "suntikan modal",
        ],
    },
    "INVESTOR_BARU": {
        "warna": "#10b981", "icon": "🎯", "tipe": "good", "bobot": 8,
        "kata": [
            "investor strategis", "investor baru", "masuknya investor",
            "pemegang saham baru", "strategic investor",
            "pengungkapan kepemilikan saham", "kepemilikan saham ≥ 5%",
            "kepemilikan saham 5%", "kepemilikan ≥5%",
            "pemilik manfaat baru", "beneficial owner baru",
        ],
    },
    "TENDER": {
        "warna": "#10b981", "icon": "📢", "tipe": "good", "bobot": 8,
        "kata": [
            "tender offer", "penawaran tender", "tender wajib",
            "penawaran pembelian saham",
        ],
    },
    "GO_PRIVATE": {
        "warna": "#10b981", "icon": "🚪", "tipe": "good", "bobot": 7,
        "kata": [
            "go private", "privatisasi", "delisting sukarela",
            "penghapusan pencatatan saham secara sukarela",
            "voluntary delisting",
        ],
    },
    "DIVIDEN": {
        "warna": "#10b981", "icon": "💰", "tipe": "good", "bobot": 6,
        "kata": [
            "dividen", "dividend", "pembagian dividen",
            "cash dividend", "dividen tunai", "dividen interim",
            "dividen final",
        ],
    },
    "BUYBACK": {
        "warna": "#10b981", "icon": "🔁", "tipe": "good", "bobot": 6,
        "kata": [
            "buyback", "pembelian kembali saham",
            "pembelian kembali saham yang telah dikeluarkan",
            "share buyback", "repurchase",
        ],
    },
    "LABA_NAIK": {
        "warna": "#10b981", "icon": "📈", "tipe": "good", "bobot": 5,
        "kata": [
            "laba bersih naik", "profit naik", "pertumbuhan laba",
            "kenaikan laba", "rekor laba", "laba meningkat",
            "net profit naik", "laba bersih meningkat",
        ],
    },
    "KONTRAK": {
        "warna": "#10b981", "icon": "🤝", "tipe": "good", "bobot": 5,
        "kata": [
            "kontrak baru", "perjanjian kerjasama", "penandatanganan kontrak",
            "perolehan kontrak", "kontrak signifikan", "proyek baru",
            "memenangkan tender", "kerjasama strategis",
        ],
    },
    "SUSPENSI": {
        "warna": "#f43f5e", "icon": "🛑", "tipe": "warning", "bobot": 10,
        "kata": [
            "suspensi", "penghentian sementara perdagangan",
            "suspensi saham", "freeze", "pembekuan",
        ],
    },
    "DELISTING": {
        "warna": "#f43f5e", "icon": "❌", "tipe": "warning", "bobot": 10,
        "kata": [
            "delisting", "penghapusan pencatatan saham",
            "delisting paksa", "force delisting", "pencatatan saham dicabut",
        ],
    },
    "PKPU": {
        "warna": "#f43f5e", "icon": "⚖️", "tipe": "warning", "bobot": 10,
        "kata": [
            "pailit", "pkpu", "penundaan kewajiban pembayaran utang",
            "gagal bayar", "default", "kepailitan",
        ],
    },
    "RUGI": {
        "warna": "#f43f5e", "icon": "📉", "tipe": "warning", "bobot": 6,
        "kata": [
            "rugi bersih", "mengalami kerugian", "penurunan laba",
            "laba turun", "penurunan pendapatan", "revenue turun",
            "merugi", "laba bersih negatif",
        ],
    },
    "OPINI_AUDIT": {
        "warna": "#f43f5e", "icon": "📋", "tipe": "warning", "bobot": 8,
        "kata": [
            "opini disclaimer", "opini tidak menyatakan pendapat",
            "opini adverse", "wajar dengan pengecualian",
            "qualified opinion",
        ],
    },
    "SANKSI": {
        "warna": "#f43f5e", "icon": "⚠️", "tipe": "warning", "bobot": 7,
        "kata": [
            "sanksi", "denda", "peringatan tertulis", "teguran",
            "pelanggaran", "penalti",
        ],
    },
    "RESIGN": {
        "warna": "#f59e0b", "icon": "🚶", "tipe": "warning", "bobot": 5,
        "kata": [
            "pengunduran diri", "resign", "mengundurkan diri",
            "berhenti dari jabatan", "pemberhentian direksi",
            "pemberhentian komisaris", "pergantian direksi",
            "pergantian komisaris",
        ],
    },
    "GANTI_AUDITOR": {
        "warna": "#f59e0b", "icon": "🔍", "tipe": "warning", "bobot": 5,
        "kata": [
            "pergantian auditor", "penggantian akuntan publik",
            "pergantian kantor akuntan", "resignasi auditor",
        ],
    },
    "RUPSLB": {
        "warna": "#a5b4fc", "icon": "🏛️", "tipe": "neutral", "bobot": 4,
        "kata": [
            "rupslb", "rapat umum pemegang saham luar biasa",
            "luar biasa", "egms",
        ],
    },
    "RUPS": {
        "warna": "#a5b4fc", "icon": "🏛️", "tipe": "neutral", "bobot": 4,
        "kata": [
            "rups tahunan", "rapat umum pemegang saham tahunan",
            "agms", "rups",
        ],
    },
    "TRANSAKSI_MATERIAL": {
        "warna": "#a5b4fc", "icon": "📑", "tipe": "neutral", "bobot": 6,
        "kata": [
            "transaksi material", "transaksi afiliasi",
            "perjanjian pengikatan jual beli", "ppjb",
            "conditional sale and purchase agreement", "cspa",
            "sale and purchase agreement",
            "perjanjian jual beli saham", "pengalihan saham",
            "divestasi",
        ],
    },
    "PERUBAHAN_USAHA": {
        "warna": "#a5b4fc", "icon": "🏭", "tipe": "neutral", "bobot": 6,
        "kata": [
            "perubahan kegiatan usaha utama", "perubahan bidang usaha",
            "perubahan maksud dan tujuan", "perubahan anggaran dasar",
            "diversifikasi usaha", "masuk ke sektor baru",
        ],
    },
    "PUBLIKASI": {
        "warna": "#a5b4fc", "icon": "📄", "tipe": "neutral", "bobot": 2,
        "kata": [
            "laporan keuangan", "public expose", "laporan tahunan",
            "laporan bulanan", "annual report", "laporan keberlanjutan",
        ],
    },
    "AKSI_KORPORASI": {
        "warna": "#a5b4fc", "icon": "⚙️", "tipe": "neutral", "bobot": 4,
        "kata": [
            "stock split", "pemecahan saham", "right issue",
            "penawaran umum terbatas", "waran", "obligasi",
            "sukuk", "medium term notes", "mtn", "convertible bond",
            "hmetd", "hak memesan efek terlebih dahulu",
        ],
    },
    "RESTRUKTURISASI": {
        "warna": "#a5b4fc", "icon": "🔄", "tipe": "neutral", "bobot": 5,
        "kata": [
            "restrukturisasi", "restrukturisasi utang",
            "penjadwalan ulang", "rescheduling", "refinancing",
            "kredit sindikasi",
        ],
    },
    "BACKDOOR_LISTING": {
        "warna": "#a5b4fc", "icon": "🚪", "tipe": "neutral", "bobot": 8,
        "kata": [
            "backdoor listing", "back door listing",
            "perubahan pengendali dan kegiatan usaha",
        ],
    },
    "PENGHARGAAN": {
        "warna": "#a5b4fc", "icon": "🏆", "tipe": "neutral", "bobot": 2,
        "kata": [
            "penghargaan", "award", "sertifikasi", "iso", "rating",
        ],
    },
}


def klasifikasi(judul, isi=""):
    teks = (str(judul) + " " + str(isi)).lower()
    hasil = []
    for kat, info in KATEGORI.items():
        for kw in info["kata"]:
            if kw in teks:
                hasil.append(kat)
                break
    if not hasil:
        hasil.append("PUBLIKASI")
    return hasil


def get_tipe(kategori_list):
    tipe_set = set()
    for k in kategori_list:
        tipe_set.add(KATEGORI.get(k, {}).get("tipe", "neutral"))
    if "warning" in tipe_set:
        return "warning"
    if "good" in tipe_set:
        return "good"
    return "neutral"


def get_bobot(kategori_list):
    if not kategori_list:
        return 0
    return max(KATEGORI.get(k, {}).get("bobot", 0) for k in kategori_list)


# ============================================================
# HTTP
# ============================================================
def _fetch_page(page_number, page_size, date_from, date_to):
    """Fetch 1 halaman. Return dict response atau None."""
    params = {
        "keywords": "",
        "pageNumber": page_number,
        "pageSize": page_size,
        "dateFrom": date_from,
        "dateTo": date_to,
        "lang": "id",
    }

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/keterbukaan-informasi",
    }

    for attempt in range(3):
        try:
            if HAS_CURL_CFFI:
                r = curl_requests.get(ENDPOINT, params=params,
                                       headers=headers,
                                       impersonate="chrome", timeout=30)
            elif cloudscraper is not None:
                s = cloudscraper.create_scraper()
                r = s.get(ENDPOINT, params=params, headers=headers, timeout=30)
            elif std_requests is not None:
                r = std_requests.get(ENDPOINT, params=params,
                                      headers=headers, timeout=30)
            else:
                return None

            if r.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f"    429, tunggu {wait}s...")
                time.sleep(wait)
                continue

            if r.status_code != 200:
                print(f"    HTTP {r.status_code} page {page_number}")
                return None

            ct = r.headers.get("Content-Type", "")
            if "json" not in ct.lower():
                time.sleep(5)
                continue

            return r.json()

        except Exception as e:
            print(f"    Exception page {page_number}: {e}")
            if attempt < 2:
                time.sleep(5)
                continue
            return None

    return None


def _parse_item(item, seen_ids):
    """Parse 1 item. Return dict atau None."""
    ann_id = item.get("Id") or item.get("AnnouncementNo")
    if not ann_id:
        return None
    if ann_id in seen_ids:
        return None
    seen_ids.add(ann_id)

    judul = item.get("Title") or item.get("Perihal") or ""
    if not judul:
        return None

    tgl = item.get("PublishDate") or ""
    kode = (item.get("Code") or "").strip()
    no_peng = item.get("AnnouncementNo") or ""
    isi = item.get("Perihal") or ""

    lamp_url = ""
    attachments = item.get("Attachments") or []
    if attachments and isinstance(attachments, list):
        first = attachments[0]
        lamp_url = first.get("FullSavePath") or ""

    kategori_list = klasifikasi(judul, isi)
    tipe = get_tipe(kategori_list)
    bobot = get_bobot(kategori_list)

    return {
        "tanggal": str(tgl),
        "kode": str(kode),
        "no_pengumuman": str(no_peng),
        "judul": str(judul),
        "isi": str(isi)[:500],
        "kategori": kategori_list,
        "tipe": tipe,
        "bobot": bobot,
        "lampiran": lamp_url,
    }


def fetch_announcements(days=90, max_items=20000, page_size=500):
    """
    Fetch semua pengumuman dengan pagination.
    Endpoint ini support pageNumber → tidak perlu loop per hari.
    """
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)

    date_to_str = date_to.strftime("%Y%m%d")
    date_from_str = date_from.strftime("%Y%m%d")

    all_items = []
    seen_ids = set()

    page = 1
    max_pages = 40

    while page <= max_pages and len(all_items) < max_items:
        data = _fetch_page(page, page_size, date_from_str, date_to_str)
        if data is None:
            print(f"    Halaman {page}: gagal")
            break

        items = data.get("Items", []) or []
        page_count = data.get("PageCount", 1)
        item_count = data.get("ItemCount", 0)

        if not items:
            break

        for item in items:
            parsed = _parse_item(item, seen_ids)
            if parsed:
                all_items.append(parsed)

        print(f"    Halaman {page}/{page_count}: "
              f"{len(items)} items, total {len(all_items)}/{item_count}")

        if page >= page_count:
            break

        page += 1
        time.sleep(1.5)

    all_items.sort(key=lambda x: x.get("tanggal", ""), reverse=True)
    return all_items


# ============================================================
# CACHE — success
# ============================================================
def _cache_path(days):
    return os.path.join(CACHE_DIR, f"news_cache_{days}d.json")


def load_cache(days):
    path = _cache_path(days)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        # Support format lama (list) & baru (dict)
        if isinstance(payload, dict) and "cached_at" in payload:
            age = time.time() - payload["cached_at"]
            if age >= CACHE_TTL_HOURS * 3600:
                return None
            return payload.get("data", [])
        # Format lama: fallback ke mtime
        age = time.time() - os.path.getmtime(path)
        if age >= CACHE_TTL_HOURS * 3600:
            return None
        return payload
    except Exception:
        return None


def save_cache(data, days):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(days)
    # ✅ FIX: simpan timestamp DI DALAM JSON, bukan pakai mtime
    payload = {
        "cached_at": time.time(),
        "data": data,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, default=str)
    except Exception:
        pass


# ============================================================
# CACHE — failure
# ============================================================
def _failed_path(days):
    return os.path.join(CACHE_DIR, f"news_failed_{days}d.json")


def _mark_failed(days):
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(_failed_path(days), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time()}, f)
    except Exception:
        pass


def _is_recently_failed(days):
    path = _failed_path(days)
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return (time.time() - data.get("ts", 0)) < FAILED_CACHE_TTL_SEC
    except Exception:
        return False


def _clear_failed(days):
    try:
        os.remove(_failed_path(days))
    except Exception:
        pass


# ============================================================
# SCAN
# ============================================================
def _apply_filter(df, good_only):
    if df.empty:
        return df
    if good_only:
        df = df[df["tipe"] == "good"].copy()
    try:
        df["tanggal_dt"] = pd.to_datetime(df["tanggal"], errors="coerce")
        df = df.sort_values("tanggal_dt", ascending=False,
                             na_position="last").reset_index(drop=True)
    except Exception:
        pass
    return df


def scan_news(days=30, force_refresh=False, filter_good_only=False):
    # 1. Coba cache
    if not force_refresh:
        cached = load_cache(days)
        if cached is not None:
            df = pd.DataFrame(cached)
            # ✅ FIX: validate tanggal terbaru harus < 3 hari
            if not df.empty and "tanggal" in df.columns:
                try:
                    newest = pd.to_datetime(df["tanggal"], errors="coerce").max()
                    if pd.notna(newest):
                        age_days = (pd.Timestamp.now() - newest).days
                        if age_days > 3:
                            # Cache valid secara timestamp tapi data terlalu tua
                            # → force fetch fresh
                            cached = None
                            df = None
                except Exception:
                    pass
            if cached is not None and df is not None:
                return _apply_filter(df, filter_good_only)

        # 2. Cooldown kalau baru gagal
        if _is_recently_failed(days):
            print(f"    [cache] skip fetch (gagal <{FAILED_CACHE_TTL_SEC}s lalu)")
            return pd.DataFrame()

    # 3. Fetch fresh
    hasil = fetch_announcements(days=days, max_items=20000)

    if not hasil:
        # Fallback cache lama (meski stale) — tapi hanya kalau
        # cache-nya < 7 hari (jangan terlalu tua)
        cached = load_cache(days)
        if cached is not None:
            df = pd.DataFrame(cached)
            try:
                newest = pd.to_datetime(df["tanggal"], errors="coerce").max()
                age_days = (pd.Timestamp.now() - newest).days if pd.notna(newest) else 999
                if age_days <= 7:
                    return _apply_filter(df, filter_good_only)
            except Exception:
                pass
        _mark_failed(days)
        return pd.DataFrame()

    _clear_failed(days)
    save_cache(hasil, days)
    df = pd.DataFrame(hasil)
    return _apply_filter(df, filter_good_only)


def get_stats(df):
    if df.empty:
        return {"total": 0, "good": 0, "warning": 0, "neutral": 0,
                "by_kategori": {}, "katalis_tinggi": 0}
    by_kat = {}
    for kat_list in df["kategori"]:
        for k in kat_list:
            by_kat[k] = by_kat.get(k, 0) + 1

    n_katalis = 0
    if "bobot" in df.columns:
        n_katalis = int((df["bobot"] >= 7).sum())

    return {
        "total": len(df),
        "good": int((df["tipe"] == "good").sum()),
        "warning": int((df["tipe"] == "warning").sum()),
        "neutral": int((df["tipe"] == "neutral").sum()),
        "by_kategori": by_kat,
        "katalis_tinggi": n_katalis,
    }