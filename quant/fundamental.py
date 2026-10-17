"""
quant/fundamental.py — Scrape fundamental IDX (tls_client + curl_cffi).
Output: data_fundamental/{kode}.json untuk Streamlit.

Fitur:
- Report list asc+desc (cover ~876 saham)
- Cache XLSX lokal (~10x lebih cepat di run ke-2)
- Session per-thread (thread-safe untuk batch parallel)
- Normalisasi EPS (handle skala juta rupiah)
- Batch runner dengan workers
"""
import os, io, json, csv, zipfile, re, time, random, threading, hashlib
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
import tls_client
from curl_cffi import requests as curl_requests

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

BASE = "https://www.idx.co.id"
API_REPORT = f"{BASE}/primary/ListedCompany/GetFinancialReport"
OUTPUT_DIR = Path("data_fundamental")
OHLCV_DIR = Path("data_ohlcv_idx")
XLSX_CACHE_DIR = Path("data_xlsx_fundamental")
OUTPUT_DIR.mkdir(exist_ok=True)
XLSX_CACHE_DIR.mkdir(exist_ok=True)

_thread_local = threading.local()


def get_session():
    """Session tls_client per-thread (thread-safe)."""
    s = getattr(_thread_local, "session", None)
    if s is None:
        s = tls_client.Session(
            client_identifier="firefox_120",
            random_tls_extension_order=True,
        )
        _thread_local.session = s
    return s


HEADERS = {
    "Referer": f"{BASE}/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
}
DL_HEADERS = {
    "Referer": f"{BASE}/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan",
    "Accept": "*/*",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

SNAPSHOT_CANDIDATES = [(2026, "tw2"), (2026, "tw1"), (2025, "audit")]
QUARTERLY_PERIODS = [
    (2024, "tw1", "2024-Q1"), (2024, "tw2", "2024-Q2"),
    (2024, "tw3", "2024-Q3"), (2024, "audit", "2024-Q4"),
    (2025, "tw1", "2025-Q1"), (2025, "tw2", "2025-Q2"),
    (2025, "tw3", "2025-Q3"), (2025, "audit", "2025-Q4"),
    (2026, "tw1", "2026-Q1"), (2026, "tw2", "2026-Q2"),
]
RIWAYAT_YEARS = [2022, 2023, 2024, 2025]

FIELDS = {
    "aset": ["jumlah aset", "total aset"],
    "aset_lancar": ["jumlah aset lancar"],
    "aset_tidak_lancar": ["jumlah aset tidak lancar"],
    "kas": ["kas dan setara kas", "kas dan bank"],
    "piutang_usaha": ["piutang usaha", "piutang dagang"],
    "persediaan": ["persediaan"],
    "aset_tetap": ["aset tetap"],
    "liabilitas": ["jumlah liabilitas", "total liabilitas"],
    "liabilitas_jangka_pendek": ["jumlah liabilitas jangka pendek"],
    "liabilitas_jangka_panjang": ["jumlah liabilitas jangka panjang"],
    "utang_usaha": ["utang usaha", "utang dagang"],
    "utang_bank": ["utang bank"],
    "ekuitas": ["jumlah ekuitas", "total ekuitas"],
    "ekuitas_induk": ["ekuitas yang diatribusikan kepada pemilik entitas induk",
                       "ekuitas yang dapat diatribusikan"],
    "modal_saham": ["modal saham"],
    "saldo_laba": ["saldo laba"],
    "pendapatan": ["jumlah pendapatan", "total pendapatan", "penjualan neto",
                    "pendapatan usaha", "pendapatan bunga bersih",
                    "pendapatan bunga dan syariah",
                    "jumlah pendapatan bunga dan syariah",
                    "pendapatan bunga", "pendapatan syariah"],
    "beban_pokok": ["beban pokok pendapatan", "beban pokok penjualan"],
    "laba_kotor": ["laba kotor"],
    "beban_operasi": ["jumlah beban operasional", "total beban operasional"],
    "laba_operasi": ["laba operasi", "laba usaha"],
    "laba_sebelum_pajak": ["laba (rugi) sebelum pajak penghasilan",
                            "jumlah laba (rugi) sebelum pajak",
                            "laba sebelum pajak penghasilan"],
    "beban_pajak": ["beban pajak", "pendapatan (beban) pajak"],
    "laba_bersih": ["jumlah laba (rugi) tahun berjalan",
                     "laba (rugi) tahun berjalan",
                     "laba bersih tahun berjalan",
                     "jumlah laba (rugi) periode berjalan"],
    "laba_induk": ["laba (rugi) yang dapat diatribusikan ke entitas induk",
                    "laba (rugi) yang dapat diatribusikan kepada pemilik entitas induk"],
    "eps_basic": ["laba (rugi) per saham dasar", "laba per saham dasar"],
    "eps_diluted": ["laba (rugi) per saham dilusian", "laba per saham dilusian"],
    "arus_kas_operasi": ["arus kas dari aktivitas operasi", "kas neto dari aktivitas operasi"],
    "arus_kas_investasi": ["arus kas dari aktivitas investasi", "kas neto dari aktivitas investasi"],
    "arus_kas_pendanaan": ["arus kas dari aktivitas pendanaan", "kas neto dari aktivitas pendanaan"],
    "capex": ["perolehan aset tetap", "pembelian aset tetap"],
    "dividen_dibayar": ["dividen dibayar", "dividends paid"],
}
EXACT_ONLY = {
    "aset": ["jumlah aset", "total aset"],
    "aset_lancar": ["jumlah aset lancar", "total aset lancar"],
    "aset_tidak_lancar": ["jumlah aset tidak lancar", "total aset tidak lancar"],
    "liabilitas": ["jumlah liabilitas", "total liabilitas"],
    "liabilitas_jangka_pendek": ["jumlah liabilitas jangka pendek", "total liabilitas jangka pendek"],
    "liabilitas_jangka_panjang": ["jumlah liabilitas jangka panjang", "total liabilitas jangka panjang"],
    "ekuitas": ["jumlah ekuitas", "total ekuitas"],
}
KAS_BLACKLIST = ["penurunan", "kenaikan", "perubahan", "neto", "bersih dari",
                  "digunakan", "diperoleh", "dari aktivitas", "akhir periode", "awal periode"]
BLACKLIST_LBL = ["lainnya", "lain-lain", "lain lain", "komprehensif lain", "subjumlah"]

_RL_CACHE = {}


def _to_num(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip().replace(",", "").replace(" ", "")
    if not s: return None
    neg = s.startswith("(") and s.endswith(")")
    if neg: s = s[1:-1]
    try:
        val = float(s)
        return -val if neg else val
    except Exception:
        return None


def _extract_cookies():
    try:
        c = get_session().cookies
        if hasattr(c, "get_dict"): return c.get_dict()
        if hasattr(c, "items"): return dict(c)
        return dict(c) if c else {}
    except Exception:
        return {}


def _normalize_url(url):
    if not url: return url
    if not url.startswith("http"): url = f"{BASE}{url}"
    url = re.sub(r"([^:])//+", r"\1/", url)
    return url


def get_report_list(year, periode, verbose=False):
    key = (year, periode)
    if key in _RL_CACHE: return _RL_CACHE[key]

    rl = {}
    for sort_order in ["asc", "desc"]:
        params = {
            "indexFrom": 1, "pageSize": 500, "year": year, "periode": periode,
            "reportType": "rdf", "EmitenType": "s",
            "SortColumn": "KodeEmiten", "SortOrder": sort_order,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{API_REPORT}?{query}"
        if verbose: print(f"  [API] {year} {periode} ({sort_order})")
        for attempt in range(3):
            try:
                r = get_session().get(url, headers=HEADERS, timeout_seconds=60)
            except Exception as e:
                if verbose: print(f"    attempt {attempt+1}: {e}")
                time.sleep(3); continue
            if r.status_code == 200:
                try:
                    for it in (r.json().get("Results") or []):
                        k = str(it.get("KodeEmiten", "")).strip().upper()
                        if k and k not in rl: rl[k] = it
                except Exception: pass
                break
            if r.status_code == 429:
                time.sleep(20 * (attempt + 1)); continue
            break
        time.sleep(1.5)

    _RL_CACHE[key] = rl
    return rl


def _xlsx_cache_path(url):
    h = hashlib.md5(url.encode()).hexdigest()
    return XLSX_CACHE_DIR / f"{h}.xlsx"


def download_xlsx(url, verbose=False):
    if not url: return None
    url = _normalize_url(url)

    # Cek cache
    cp = _xlsx_cache_path(url)
    if cp.exists():
        try:
            content = cp.read_bytes()
            if content[:2] == b"PK" and zipfile.is_zipfile(io.BytesIO(content)):
                return content
        except Exception:
            pass

    cookies = _extract_cookies()
    if verbose: print(f"    [dl] {url[:80]}...")
    for attempt in range(3):
        try:
            r = curl_requests.get(url, headers=DL_HEADERS, cookies=cookies,
                                   impersonate="firefox", timeout=90)
            if r.status_code == 200 and r.content and r.content[:2] == b"PK":
                if zipfile.is_zipfile(io.BytesIO(r.content)):
                    try:
                        cp.write_bytes(r.content)
                    except Exception:
                        pass
                    if verbose: print(f"    [dl OK] {len(r.content)} bytes")
                    return r.content
            if verbose: print(f"    [dl HTTP {r.status_code}]")
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1)); continue
        except Exception as e:
            if verbose: print(f"    [dl err] {e}")
            time.sleep(3)
    return None


def parse_xlsx(content_bytes):
    try:
        xls = pd.ExcelFile(io.BytesIO(content_bytes))
    except Exception:
        return {}
    hasil = {}
    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
        except Exception:
            continue
        if df.empty: continue
        for _, row in df.iterrows():
            if len(row) < 2: continue
            label = row.iloc[0]
            if pd.isna(label): continue
            ll = str(label).lower().strip()
            if len(ll) < 4: continue
            if any(b in ll for b in BLACKLIST_LBL): continue
            for field, kws in FIELDS.items():
                if field in hasil: continue
                matched = False
                if field in EXACT_ONLY:
                    for ex in EXACT_ONLY[field]:
                        if ll == ex: matched = True; break
                        if ll.startswith(ex + " "):
                            rest = ll[len(ex):].strip()
                            if not any(rest.startswith(x) for x in
                                       ["lancar", "tidak", "current", "non", "jangka"]):
                                matched = True; break
                elif field == "kas":
                    for kw in kws:
                        if ll == kw or ll.startswith(kw + " ") or ll.startswith(kw + ":"):
                            matched = True; break
                    if matched and any(b in ll for b in KAS_BLACKLIST): matched = False
                else:
                    matched = any(kw in ll for kw in kws)
                if not matched: continue
                is_ps = "per saham" in ll or field.startswith("eps")
                min_abs = 0.0000001 if is_ps else 1000
                for col in range(1, min(len(row), 10)):
                    num = _to_num(row.iloc[col])
                    if num is not None and num != 0 and abs(num) >= min_abs:
                        hasil[field] = num
                        break

    if "laba_induk" in hasil and "laba_bersih" not in hasil:
        hasil["laba_bersih"] = hasil["laba_induk"]

    # Normalisasi EPS: kalau < 1, kemungkinan dalam satuan juta rupiah
    for eps_field in ["eps_basic", "eps_diluted"]:
        v = hasil.get(eps_field)
        if v is not None and 0 < abs(v) < 1:
            hasil[eps_field] = v * 1_000_000

    return hasil


def fetch_one_period(kode, year, periode, verbose=False):
    rl = get_report_list(year, periode, verbose=verbose)
    row = rl.get(kode)
    if not row: return None
    atts = row.get("Attachments") or []
    xurl = None
    for att in atts:
        fn = (att.get("File_Name") or "").lower()
        ft = (att.get("File_Type") or "").lower()
        if "financialstatement" in fn and ft in (".xlsx", "xlsx"):
            xurl = att.get("File_Path"); break
    if not xurl: return None
    content = download_xlsx(xurl, verbose=verbose)
    if not content: return None
    return parse_xlsx(content)


def compute_ratios(d):
    def sd(a, b): return a / b if a and b and b != 0 else None
    laba = d.get("laba_induk") or d.get("laba_bersih")
    ek = d.get("ekuitas_induk") or d.get("ekuitas")
    return {
        "roe": sd(laba, ek), "roa": sd(laba, d.get("aset")),
        "der": sd(d.get("liabilitas"), d.get("ekuitas")),
        "dar": sd(d.get("liabilitas"), d.get("aset")),
        "current_ratio": sd(d.get("aset_lancar"), d.get("liabilitas_jangka_pendek")),
        "margin_laba_bersih": sd(laba, d.get("pendapatan")),
        "margin_laba_kotor": sd(d.get("laba_kotor"), d.get("pendapatan")),
        "margin_laba_operasi": sd(d.get("laba_operasi"), d.get("pendapatan")),
    }


def fetch_yfinance(kode):
    if not HAS_YF: return {}
    try:
        t = yf.Ticker(f"{kode}.JK")
        info = t.info or {}
    except Exception:
        return {}
    if not info: return {}
    harga = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
    return {
        "harga": harga,
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "free_float_pct": (info.get("floatShares") / info.get("sharesOutstanding") * 100
                            if info.get("floatShares") and info.get("sharesOutstanding") else None),
        "pe": info.get("trailingPE"),
        "pb": info.get("priceToBook"),
        "ps": info.get("priceToSalesTrailing12Months"),
        "sektor": info.get("sector"),
        "industri": info.get("industry"),
        "nama": info.get("longName") or info.get("shortName"),
    }


def compute_akumulasi(kode):
    p = OHLCV_DIR / f"{kode}.csv"
    if not p.exists(): return {}
    try:
        df = pd.read_csv(p)
        df.columns = [str(c).strip() for c in df.columns]
        ren = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ("date", "tanggal"): ren[c] = "Date"
            elif cl in ("open", "openprice"): ren[c] = "Open"
            elif cl in ("high", "highprice"): ren[c] = "High"
            elif cl in ("low", "lowprice"): ren[c] = "Low"
            elif cl in ("close", "closeprice"): ren[c] = "Close"
            elif cl == "volume": ren[c] = "Volume"
        df = df.rename(columns=ren)
        df = df.loc[:, ~df.columns.duplicated(keep="first")]
        df["Date"] = pd.to_datetime(df["Date"], format="mixed", errors="coerce", utc=True).dt.tz_localize(None)
        df = df.dropna(subset=["Date"]).sort_values("Date")
    except Exception:
        return {}
    if len(df) < 20: return {}
    d = df.tail(20)
    high = d["High"].astype(float); low = d["Low"].astype(float)
    close = d["Close"].astype(float); vol = d["Volume"].astype(float)
    hl = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / hl
    mfm = mfm.fillna(0)
    mfv = mfm * vol
    cmf = float(mfv.sum() / vol.sum()) if vol.sum() else 0.0
    full = df.tail(40)
    vt = 1.0
    if len(full) >= 40:
        vr = full["Volume"].tail(20).mean()
        vp = full["Volume"].head(20).mean()
        if vp: vt = float(vr / vp)
    if len(df) >= 21:
        pn = float(df["Close"].iloc[-1]); pt = float(df["Close"].iloc[-21])
        chg = (pn - pt) / pt * 100 if pt else 0.0
    else:
        chg = 0.0
    score = 5.0
    score += min(cmf * 15, 2) if cmf > 0 else max(cmf * 15, -2)
    if vt > 1.2 and chg > 0: score += 1
    elif vt > 1.2 and chg < 0: score -= 1
    if chg > 5: score += 0.5
    elif chg < -5: score -= 0.5
    score = max(0, min(10, score))
    if score >= 6.5: tipe, label = "ACCUMULATION", "AKUMULASI"
    elif score <= 3.5: tipe, label = "DISTRIBUTION", "DISTRIBUSI"
    else: tipe, label = "NEUTRAL", "NETRAL"
    return {"score": round(score, 1), "label": label, "tipe": tipe,
            "cmf": round(cmf, 4), "vol_trend": round(vt, 3),
            "price_chg_20d": round(chg, 2)}


def build_one(kode, verbose=False):
    kode = kode.strip().upper()

    snap = None; snap_periode = None
    for y, p in SNAPSHOT_CANDIDATES:
        d = fetch_one_period(kode, y, p, verbose=verbose)
        if d and d.get("aset"):
            snap = d; snap_periode = f"{y}-{p}"; break
    if not snap:
        return None

    q_rev, q_eps, q_ni = {}, {}, {}
    for y, p, lbl in QUARTERLY_PERIODS:
        if f"{y}-{p}" == snap_periode: d = snap
        else: d = fetch_one_period(kode, y, p, verbose=False)
        if d:
            if d.get("pendapatan") is not None: q_rev[lbl] = d["pendapatan"]
            if d.get("eps_basic") is not None: q_eps[lbl] = d["eps_basic"]
            if d.get("laba_induk") is not None: q_ni[lbl] = d["laba_induk"]

    r_eps, r_rev = {}, {}
    for y in RIWAYAT_YEARS:
        if f"{y}-audit" == snap_periode: d = snap
        else: d = fetch_one_period(kode, y, "audit", verbose=False)
        if d:
            if d.get("eps_basic") is not None: r_eps[str(y)] = d["eps_basic"]
            if d.get("pendapatan") is not None: r_rev[str(y)] = d["pendapatan"]

    ratios = compute_ratios(snap)
    yfd = fetch_yfinance(kode)
    akum = compute_akumulasi(kode)

    data = {
        "kode": kode,
        "nama": yfd.get("nama"),
        "sektor": yfd.get("sektor"),
        "industri": yfd.get("industri"),
        "harga": yfd.get("harga"),
        "update": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periode_terbaru": snap_periode,
        "rasio_kunci": {
            "pe": yfd.get("pe"), "pb": yfd.get("pb"), "ps": yfd.get("ps"),
            "roe": ratios.get("roe"), "eps": snap.get("eps_basic"),
            "de": ratios.get("der"), "margin_net": ratios.get("margin_laba_bersih"),
            "current_ratio": ratios.get("current_ratio"), "roa": ratios.get("roa"),
        },
        "quarterly": {"revenue": q_rev, "eps": q_eps, "net_income": q_ni},
        "riwayat": {"eps": r_eps, "revenue_per_share": r_rev},
        "statistik": {
            "market_cap": yfd.get("market_cap"),
            "enterprise_value": yfd.get("enterprise_value"),
            "shares_outstanding": yfd.get("shares_outstanding"),
            "free_float_pct": yfd.get("free_float_pct"),
        },
        "akumulasi": akum,
        "neraca": {k: snap.get(k) for k in
                   ["aset", "aset_lancar", "kas", "piutang_usaha", "persediaan",
                    "aset_tetap", "liabilitas", "liabilitas_jangka_pendek",
                    "utang_usaha", "utang_bank", "ekuitas", "ekuitas_induk",
                    "modal_saham", "saldo_laba"]},
        "laba_rugi": {k: snap.get(k) for k in
                       ["pendapatan", "beban_pokok", "laba_kotor", "beban_operasi",
                        "laba_operasi", "laba_sebelum_pajak", "beban_pajak",
                        "laba_bersih", "laba_induk", "eps_basic", "eps_diluted"]},
        "arus_kas": {k: snap.get(k) for k in
                      ["arus_kas_operasi", "arus_kas_investasi", "arus_kas_pendanaan",
                       "capex", "dividen_dibayar"]},
    }

    with open(OUTPUT_DIR / f"{kode}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return data


def main(tickers, verbose=False):
    print(f"Fetch {len(tickers)} saham (tls_client + curl_cffi)\n")

    periods = set(SNAPSHOT_CANDIDATES)
    for y, p, _ in QUARTERLY_PERIODS: periods.add((y, p))
    for y in RIWAYAT_YEARS: periods.add((y, "audit"))

    print(f"Pre-fetch {len(periods)} report list...")
    for y, p in sorted(periods):
        rl = get_report_list(y, p)
        print(f"  {y} {p}: {len(rl)} saham", flush=True)
    print()

    ok, err = 0, 0
    t0 = time.time()
    for i, k in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {k}...", end=" ", flush=True)
        try:
            d = build_one(k, verbose=verbose)
            if d:
                ok += 1
                nq = len(d["quarterly"]["revenue"])
                nr = len(d["riwayat"]["eps"])
                print(f"OK ({d['periode_terbaru']}) Q:{nq} R:{nr}")
            else:
                err += 1
                print("SKIP (no XLSX)")
        except Exception as e:
            err += 1
            print(f"ERR: {e}")
        time.sleep(random.uniform(0.3, 0.8))

    print(f"\nSelesai: OK={ok}, ERR={err} | {time.time()-t0:.0f}s")


def batch(tickers, workers=5, delay=0.3, skip_existing=True):
    """Batch fetch dengan workers (paralel)."""
    if skip_existing:
        before = len(tickers)
        tickers = [t for t in tickers if not (OUTPUT_DIR / f"{t}.json").exists()]
        print(f"Skip existing: {before - len(tickers)}, sisa {len(tickers)}")

    print(f"Batch {len(tickers)} saham, {workers} workers\n")

    periods = set(SNAPSHOT_CANDIDATES)
    for y, p, _ in QUARTERLY_PERIODS: periods.add((y, p))
    for y in RIWAYAT_YEARS: periods.add((y, "audit"))

    print(f"Pre-fetch {len(periods)} report list...")
    for y, p in sorted(periods):
        rl = get_report_list(y, p)
        print(f"  {y} {p}: {len(rl)}", flush=True)
    print()

    ok, err = 0, 0
    lock = threading.Lock()
    counter = {"n": 0}
    t0 = time.time()

    def worker(kode):
        time.sleep(random.uniform(0, delay))
        try:
            d = build_one(kode, verbose=False)
            return kode, d is not None, None
        except Exception as e:
            return kode, False, str(e)[:100]

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(worker, k): k for k in tickers}
        for fut in as_completed(futures):
            k, s, e = fut.result()
            with lock:
                counter["n"] += 1
                n = counter["n"]
            if s:
                ok += 1
            else:
                err += 1
            if n % 20 == 0 or n == len(tickers):
                elapsed = time.time() - t0
                rate = n / elapsed if elapsed > 0 else 0
                eta = (len(tickers) - n) / rate if rate > 0 else 0
                print(f"[{n}/{len(tickers)}] OK={ok} err={err} | {rate:.1f}/s | ETA {eta:.0f}s", flush=True)

    print(f"\nSelesai: OK={ok}, ERR={err} | {time.time()-t0:.0f}s")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        with open("daftar_saham.csv", "r", encoding="utf-8-sig") as f:
            tickers = []
            for row in csv.DictReader(f):
                for k in ["Kode", "kode"]:
                    if k in row and row[k]:
                        tickers.append(row[k].strip().upper()); break
        batch(tickers, workers=20, delay=0.3)
    else:
        tickers = sys.argv[1:] if len(sys.argv) > 1 else ["BBCA"]
        main([t.upper() for t in tickers])
