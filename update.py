"""
UPDATE HARIAN - versi CEPAT (20 worker).
Menggunakan Scrapling AsyncStealthySession (bypass Cloudflare).

Fitur:
- Update IHSG dari Yahoo Finance (pakai curl_cffi workaround)
- Skip otomatis kalau weekend DAN data sudah lengkap
- Fetch tetap jalan kalau weekend tapi ada data yang belum ter-fetch
- Cek jam publish IDX (~17:00 WIB)
- Fetch hanya data baru (bukan download ulang)
- Buffer 14 hari untuk jaga-jaga
- 20 concurrent worker
"""

import asyncio
import os
import csv
import random
from datetime import datetime
import pandas as pd
from scrapling.fetchers import AsyncStealthySession


# ============================================================
# KONFIGURASI
# ============================================================
TAHUN = 2026

MAX_WORKERS = 20
MAX_TABS = 10

LOOKBACK_DAYS = 14
OUTPUT_DIR = "data_ohlcv_idx"
CSV_DAFTAR = "daftar_saham.csv"
FILE_FAILED = "failed_update.txt"
BASE = "https://www.idx.co.id"
JAM_PUBLISH_IDX = 17

JITTER_MIN = 0.02
JITTER_MAX = 0.10


# ============================================================
# HELPER: NORMALISASI TIMESTAMP
# ============================================================
def _to_naive(ts):
    if ts is None:
        return None
    try:
        ts = pd.Timestamp(ts)
    except Exception:
        return None
    if ts.tz is not None:
        try:
            from zoneinfo import ZoneInfo
            ts = ts.tz_convert(ZoneInfo("Asia/Jakarta")).tz_localize(None)
        except Exception:
            ts = ts.tz_localize(None)
    return ts


# ============================================================
# UPDATE IHSG (FIXED with curl_cffi)
# ============================================================
def update_ihsg_data():
    """Fetch IHSG dari Yahoo Finance, update data_ohlcv_idx/IHSG.csv."""
    try:
        import yfinance as yf
    except ImportError:
        print("[!] yfinance tidak terinstall. Skip update IHSG.")
        return False

    # Coba pakai curl_cffi session (bypass bot detection Yahoo)
    session = None
    try:
        from curl_cffi import requests as cffi_requests
        session = cffi_requests.Session(impersonate="chrome")
        print("  [i] Menggunakan sesi curl_cffi (impersonate Chrome)")
    except ImportError:
        print("  [i] curl_cffi tidak terinstall, pakai sesi default")

    print("\n" + "=" * 55)
    print("UPDATE IHSG (Yahoo Finance)")
    print("=" * 55)

    try:
        df = yf.download(
            "^JKSE",
            start="2022-01-01",
            progress=False,
            session=session,
        )
        if df is None or df.empty:
            print("[!] Gagal fetch IHSG dari Yahoo Finance.")
            return False

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        df.columns = [str(c).strip().title() for c in df.columns]
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)

        cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
        cols = [c for c in cols if c in df.columns]

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ihsg_path = os.path.join(OUTPUT_DIR, "IHSG.csv")
        df[cols].to_csv(ihsg_path, index=False)
        df[cols].to_csv("data_ihsg.csv", index=False)

        last = df["Date"].max()
        last_close = df["Close"].iloc[-1]
        print(f"[OK] IHSG update s/d {last.date()} (close {last_close:,.2f})")
        return True
    except Exception as e:
        print(f"[!] Error update IHSG: {e}")
        return False


# ============================================================
# BACA DAFTAR SAHAM
# ============================================================
def get_ticker_list():
    if not os.path.exists(CSV_DAFTAR):
        print(f"  [!] File '{CSV_DAFTAR}' tidak ada.")
        return []

    tickers = []
    with open(CSV_DAFTAR, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            for key in ["Kode", "Kode Saham", "Code", "KodeEmiten", "kode"]:
                if key in row and row[key]:
                    kode = row[key].strip().upper()
                    if kode and len(kode) <= 6 and kode.isalnum():
                        tickers.append(kode)
                    break

    return sorted(set(tickers))


def tanggal_terakhir(kode):
    fp = os.path.join(OUTPUT_DIR, f"{kode}.csv")
    if not os.path.exists(fp):
        return None
    try:
        df = pd.read_csv(fp, usecols=["Date"])
        if df.empty:
            return None
        ts = pd.to_datetime(df["Date"]).max()
        ts = _to_naive(ts)
        if ts is None:
            return None
        return ts.normalize()
    except Exception:
        return None


# ============================================================
# FETCH
# ============================================================
async def fetch_ohlcv(session, kode, length, retry=2):
    url = (
        f"{BASE}/primary/ListedCompany/GetTradingInfoSS"
        f"?code={kode}&length={length}"
    )
    for attempt in range(retry):
        try:
            page = await session.fetch(url)
            if page.status != 200:
                if attempt < retry - 1:
                    await asyncio.sleep(0.5)
                    continue
                return kode, None, f"HTTP {page.status}"

            data = page.json()
            replies = data.get("replies", [])
            if not replies:
                return kode, None, "replies kosong"

            df = pd.DataFrame(replies)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"]).apply(_to_naive)
            return kode, df, None
        except Exception as e:
            if attempt < retry - 1:
                await asyncio.sleep(0.5)
                continue
            return kode, None, f"{type(e).__name__}: {e}"
    return kode, None, "unknown error"


# ============================================================
# MERGE
# ============================================================
def merge_dan_simpan(kode, df_baru):
    fp = os.path.join(OUTPUT_DIR, f"{kode}.csv")

    if os.path.exists(fp):
        df_lama = pd.read_csv(fp)
        df_lama["Date"] = pd.to_datetime(df_lama["Date"]).apply(_to_naive)
        df = pd.concat([df_lama, df_baru], ignore_index=True)
    else:
        df = df_baru.copy()

    df = df[df["Date"].notna()]
    df = df.drop_duplicates(subset=["Date"], keep="last")
    df = df.sort_values("Date").reset_index(drop=True)

    if df.empty:
        return 0

    df.to_csv(fp, index=False)
    return len(df)


# ============================================================
# HARI BURSA TERAKHIR
# ============================================================
def get_hari_bursa_terakhir():
    now = _now_wib()
    hari_ini = pd.Timestamp(now.date())
    jam = now.hour
    dow = hari_ini.weekday()

    if dow == 5:
        return hari_ini - pd.Timedelta(days=1)
    if dow == 6:
        return hari_ini - pd.Timedelta(days=2)

    if jam >= JAM_PUBLISH_IDX:
        return hari_ini
    else:
        if dow == 0:
            return hari_ini - pd.Timedelta(days=3)
        else:
            return hari_ini - pd.Timedelta(days=1)


def _now_wib():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Jakarta"))
    except Exception:
        try:
            import pytz
            return datetime.now(pytz.timezone("Asia/Jakarta"))
        except ImportError:
            return datetime.now()


# ============================================================
# MAIN
# ============================================================
async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    now_wib = _now_wib()
    print("=" * 55)
    print(f"UPDATE HARIAN (FAST MODE) - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)
    print(f"Waktu WIB      : {now_wib.strftime('%Y-%m-%d %H:%M')}")
    print(f"Jam publish IDX: {JAM_PUBLISH_IDX}:00 WIB")
    print(f"Workers        : {MAX_WORKERS} concurrent")
    print(f"Browser tabs   : {MAX_TABS}")

    # ========== Update IHSG SELALU di awal ==========
    update_ihsg_data()

    hari_ini = pd.Timestamp(now_wib.date())
    dow = hari_ini.weekday()
    dow_nama = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'][dow]

    tickers = get_ticker_list()
    if not tickers:
        print("\nTidak ada saham.")
        return
    print(f"\nTotal saham dari CSV: {len(tickers)}")

    batas_update = get_hari_bursa_terakhir()
    print(f"Hari bursa terakhir: {batas_update.date()} "
          f"({['Senin','Selasa','Rabu','Kamis','Jumat','Sabtu','Minggu'][batas_update.weekday()]})")

    if batas_update.date() < hari_ini.date() and dow < 5:
        print(f"  [i] Data hari ini ({hari_ini.date()}) belum publish.")
        print(f"      Coba lagi setelah jam {JAM_PUBLISH_IDX}:00 WIB.")

    perlu_update = []
    sudah_uptodate = []
    for kode in tickers:
        tgl = tanggal_terakhir(kode)
        if tgl is None or tgl < batas_update:
            perlu_update.append(kode)
        else:
            sudah_uptodate.append(kode)

    print(f"\nPerlu update   : {len(perlu_update)}")
    print(f"Sudah terbaru  : {len(sudah_uptodate)}")

    if not perlu_update:
        print("\n[OK] Semua saham sudah up-to-date.")
        if dow >= 5:
            print(f"     (Weekend {dow_nama}, tidak ada data baru untuk di-fetch)")
        return

    if dow >= 5:
        print(f"\n[i] Weekend ({dow_nama}), tapi {len(perlu_update)} saham belum punya "
              f"data {batas_update.date()}.")
        print(f"    Lanjut fetch data hari bursa terakhir...")

    print(f"\nMulai fetch dengan {MAX_WORKERS} worker...\n")
    t0 = datetime.now()

    async with AsyncStealthySession(
        headless=True,
        solve_cloudflare=True,
        max_pages=MAX_TABS,
        disable_resources=True,
    ) as session:

        sem = asyncio.Semaphore(MAX_WORKERS)
        counter = {"done": 0, "ok": 0, "skip": 0, "err": 0}
        lock = asyncio.Lock()
        total = len(perlu_update)

        async def worker(kode):
            async with sem:
                await asyncio.sleep(random.uniform(JITTER_MIN, JITTER_MAX))

                length = LOOKBACK_DAYS if tanggal_terakhir(kode) else 1095
                kode, df_baru, err = await fetch_ohlcv(session, kode, length)

                if df_baru is None or df_baru.empty:
                    status = "error" if err else "skip"
                    return kode, 0, err or "tidak ada data", status

                tgl_lama = tanggal_terakhir(kode)
                if tgl_lama is not None:
                    df_baru = df_baru[df_baru["Date"] > tgl_lama]

                if df_baru.empty:
                    return kode, 0, "tidak ada baris baru", "skip"

                n = merge_dan_simpan(kode, df_baru)
                return kode, n, None, "ok"

        tasks = [worker(k) for k in perlu_update]
        berhasil, gagal, tidak_ada_baru = [], [], []

        for coro in asyncio.as_completed(tasks):
            kode, nbaris, err, status = await coro

            async with lock:
                counter["done"] += 1
                if status == "ok":
                    counter["ok"] += 1
                    berhasil.append(kode)
                elif status == "skip":
                    counter["skip"] += 1
                    tidak_ada_baru.append(kode)
                else:
                    counter["err"] += 1
                    gagal.append(kode)

                if counter["done"] % 50 == 0 or counter["done"] == total:
                    elapsed = (datetime.now() - t0).total_seconds()
                    rate = counter["done"] / elapsed if elapsed > 0 else 0
                    eta = (total - counter["done"]) / rate if rate > 0 else 0
                    print(f"  [{counter['done']}/{total}] "
                          f"OK={counter['ok']} skip={counter['skip']} err={counter['err']} "
                          f"| {rate:.1f}/s | ETA {eta:.0f}s")

    if gagal:
        with open(FILE_FAILED, "w", encoding="utf-8") as f:
            for k in sorted(set(gagal)):
                f.write(f"{k}\n")
        print(f"\n[!] {len(gagal)} saham gagal -> {FILE_FAILED}")
    else:
        if os.path.exists(FILE_FAILED):
            os.remove(FILE_FAILED)

    elapsed = (datetime.now() - t0).total_seconds()
    print("\n" + "=" * 55)
    print(f"Selesai dalam      : {elapsed:.1f} detik")
    print(f"Berhasil update    : {len(berhasil)}")
    print(f"Tidak ada baris    : {len(tidak_ada_baru)}")
    print(f"Sudah up-to-date   : {len(sudah_uptodate)}")
    print(f"Gagal              : {len(gagal)}")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())