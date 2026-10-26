"""
IDX NEWS — Scraper keterbukaan informasi IDX.

Strategi: 
- PRIORITAS 1: Baca data statis dari `data_news_static.json` (hasil auto-fetch).
- PRIORITAS 2: Baca cache lokal.
- PRIORITAS 3: Fetch langsung (hanya jika force_refresh=True).
"""

import os
import json
import time
from datetime import datetime, timedelta

import pandas as pd

# Prioritas 1: curl_cffi (profil Firefox)
try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    curl_requests = None
    HAS_CURL_CFFI = False

# Prioritas 2: cloudscraper (profil Firefox)
try:
    import cloudscraper
except ImportError:
    cloudscraper = None

# Prioritas 3: requests biasa (fallback terakhir)
try:
    import requests as std_requests
except ImportError:
    std_requests = None


# ============================================================
# CONFIG
# ============================================================
CACHE_DIR = "data_idx_news"
BASE = "https://www.idx.co.id"
ENDPOINT = f"{BASE}/primary/NewsAnnouncement/GetAllAnnouncement"
CACHE_TTL_HOURS = 3
FAILED_CACHE_TTL_SEC = 300

STATIC_NEWS_FILE = "data_news_static.json"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{BASE}/id/perusahaan-tercatat/keterbukaan-informasi",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "dnt": "1",
    "priority": "u=1, i",
}


# ============================================================
# KATEGORI (Lengkap, tidak diubah)
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
# FETCH — dengan sesi Firefox (tanpa cookie hardcoded)
# ============================================================
def _fetch_page(page_number, page_size, date_from_yyyymmdd, date_to_yyyymmdd):
    params = {
        "keywords": "",
        "pageNumber": page_number,
        "pageSize": page_size,
        "dateFrom": date_from_yyyymmdd,
        "dateTo": date_to_yyyymmdd,
        "lang": "id",
    }

    for attempt in range(3):
        # === 1. curl_cffi dengan profil Firefox ===
        if HAS_CURL_CFFI:
            try:
                r = curl_requests.get(
                    ENDPOINT, params=params,
                    headers=HEADERS,
                    impersonate="firefox",
                    timeout=30,
                )
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 429:
                    time.sleep(15 * (attempt + 1))
                    continue
                else:
                    print(f"    curl_cffi HTTP {r.status_code}")
            except Exception as e:
                print(f"    curl_cffi exception: {e}")

        # === 2. cloudscraper dengan profil Firefox ===
        if cloudscraper is not None:
            try:
                scraper = cloudscraper.create_scraper(
                    browser={'browser': 'firefox', 'platform': 'windows'}
                )
                r = scraper.get(
                    ENDPOINT, params=params,
                    headers=HEADERS,
                    timeout=30,
                )
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 429:
                    time.sleep(15 * (attempt + 1))
                    continue
                else:
                    print(f"    cloudscraper HTTP {r.status_code}")
            except Exception as e:
                print(f"    cloudscraper exception: {e}")

        # === 3. requests biasa (fallback terakhir) ===
        if std_requests is not None:
            try:
                r = std_requests.get(
                    ENDPOINT, params=params,
                    headers=HEADERS,
                    timeout=30,
                )
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 429:
                    time.sleep(15 * (attempt + 1))
                    continue
                else:
                    print(f"    requests HTTP {r.status_code}")
            except Exception as e:
                print(f"    requests exception: {e}")

        if attempt < 2:
            time.sleep(3)

    return None


def _parse_item(item, seen_ids):
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


def fetch_announcements(days=30, max_items=20000, page_size=100):
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)

    date_to_str = date_to.strftime("%Y%m%d")
    date_from_str = date_from.strftime("%Y%m%d")

    all_items = []
    seen_ids = set()
    page_number = 1
    max_pages = 100

    while page_number <= max_pages and len(all_items) < max_items:
        data = _fetch_page(page_number, page_size,
                            date_from_str, date_to_str)
        if data is None:
            print(f"    Gagal fetch page {page_number}")
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

        print(f"    Page {page_number}/{page_count}: "
              f"{len(items)} items, total {len(all_items)}/{item_count}")

        if page_number >= page_count:
            break

        page_number += 1
        time.sleep(1.5)

    all_items.sort(key=lambda x: x.get("tanggal", ""), reverse=True)
    return all_items


# ============================================================
# CACHE
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
        if isinstance(payload, dict) and "cached_at" in payload:
            age = time.time() - payload["cached_at"]
            if age >= CACHE_TTL_HOURS * 3600:
                return None
            return payload.get("data", [])
        age = time.time() - os.path.getmtime(path)
        if age >= CACHE_TTL_HOURS * 3600:
            return None
        return payload
    except Exception:
        return None


def save_cache(data, days):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(days)
    payload = {
        "cached_at": time.time(),
        "data": data,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, default=str)
    except Exception:
        pass


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
# STATIC FILE READER (BARU)
# ============================================================
def load_static_news():
    """Baca data berita dari file JSON statis (hasil auto-fetch)."""
    if not os.path.exists(STATIC_NEWS_FILE):
        return None, None
    try:
        with open(STATIC_NEWS_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            return payload.get("data", []), payload.get("generated_at")
        return payload, None
    except Exception:
        return None, None


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
    # ─── 1. SELALU BACA FILE STATIS DULU (Paling Prioritas) ───
    static_data, generated_at = load_static_news()
    if static_data:
        print(f"[news] pakai data statis (update: {generated_at})")
        return _apply_filter(pd.DataFrame(static_data), filter_good_only)

    # ─── 2. Kalau file statis hilang, baru pakai cache lokal ───
    if not force_refresh:
        cached = load_cache(days)
        if cached is not None:
            return _apply_filter(pd.DataFrame(cached), filter_good_only)

    # ─── 3. Kalau benar-benar tidak ada data, baru tembak IDX ───
    hasil = fetch_announcements(days=days, max_items=20000)
    if not hasil:
        _mark_failed(days)
        return pd.DataFrame()

    _clear_failed(days)
    save_cache(hasil, days)
    return _apply_filter(pd.DataFrame(hasil), filter_good_only)


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