"""
quant/fundamental.py — Scraper Fundamental IDX (LENGKAP & AKURAT)

Fitur:
- Q1/Q2/Q3/Q4 STANDALONE (bukan kumulatif) 
- Revenue detection untuk bank, asuransi, multifinance, manufaktur
- 40+ field: neraca, laba rugi, arus kas, rasio
- Perhitungan TTM (Trailing Twelve Months) untuk P/E dan EPS
- Prioritas Net Interest Income untuk Bank
- Cache XLSX lokal (super cepat di run ke-2)
- CACHE INCREMENTAL: Tidak mendownload ulang data yang sudah ada.
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
PARSED_CACHE_DIR = Path("data_parsed_fundamental")
REPORT_LIST_CACHE_DIR = Path("data_report_list")

for d in [OUTPUT_DIR, XLSX_CACHE_DIR, PARSED_CACHE_DIR, REPORT_LIST_CACHE_DIR]:
    d.mkdir(exist_ok=True)

_thread_local = threading.local()


def get_session():
    s = getattr(_thread_local, "session", None)
    if s is None:
        s = tls_client.Session(client_identifier="firefox_120",
                                random_tls_extension_order=True)
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

# Prioritaskan Q3 2026
SNAPSHOT_CANDIDATES = [(2026, "tw3"), (2026, "tw2"), (2026, "tw1"), (2025, "audit")]

# Hanya 6 periode yang dibutuhkan Screener Q3 (tidak ambil history)
QUARTERLY_PERIODS = [
    (2025, "tw1", "2025-Q1", 1),
    (2025, "tw2", "2025-Q2", 2),
    (2025, "tw3", "2025-Q3", 3),
    (2026, "tw1", "2026-Q1", 1),
    (2026, "tw2", "2026-Q2", 2),
    (2026, "tw3", "2026-Q3", 3),
]
RIWAYAT_YEARS = []

# ============================================================
# FIELD DETECTION
# ============================================================
FIELDS = {
    "aset": ["jumlah aset", "total aset", "total assets"],
    "aset_lancar": ["jumlah aset lancar", "total aset lancar", "total current assets"],
    "aset_tidak_lancar": ["jumlah aset tidak lancar", "total aset tidak lancar"],
    "kas": ["kas dan setara kas", "kas dan bank", "cash and cash equivalents"],
    "piutang_usaha": ["piutang usaha", "piutang dagang", "trade receivables",
                       "piutang pembiayaan"],
    "persediaan": ["persediaan", "inventories"],
    "aset_tetap": ["aset tetap", "property, plant"],
    "liabilitas": ["jumlah liabilitas", "total liabilitas", "total liabilities"],
    "liabilitas_jangka_pendek": ["jumlah liabilitas jangka pendek",
                                   "total liabilitas jangka pendek"],
    "liabilitas_jangka_panjang": ["jumlah liabilitas jangka panjang",
                                    "total liabilitas jangka panjang"],
    "utang_usaha": ["utang usaha", "utang dagang", "trade payables"],
    "utang_bank": ["utang bank", "pinjaman bank", "bank loans"],
    "ekuitas": ["jumlah ekuitas", "total ekuitas", "total equity"],
    "ekuitas_induk": ["ekuitas yang diatribusikan kepada pemilik entitas induk",
                       "ekuitas yang dapat diatribusikan",
                       "equity attributable to owners"],
    "modal_saham": ["modal saham", "share capital"],
    "saldo_laba": ["saldo laba", "retained earnings"],
    "pendapatan": [
        "pendapatan bunga bersih", "jumlah pendapatan bunga dan syariah", 
        "pendapatan bunga dan syariah",
        "jumlah pendapatan", "total pendapatan", "penjualan neto",
        "penjualan bersih", "penjualan", "total penjualan",
        "pendapatan usaha", "pendapatan operasional", "pendapatan operasi",
        "pendapatan bruto", "pendapatan neto",
        "pendapatan bunga", "pendapatan syariah", "pendapatan premi", "premi bruto",
        "premi neto", "pendapatan premi bruto",
        "pendapatan pembiayaan", "pendapatan sewa",
        "pendapatan jasa", "pendapatan kontrak",
        "revenue", "sales", "total revenue",
    ],
    "beban_pokok": ["beban pokok pendapatan", "beban pokok penjualan",
                     "harga pokok penjualan", "hpp", "cost of goods sold",
                     "cost of revenue"],
    "laba_kotor": ["laba kotor", "gross profit"],
    "beban_operasi": ["jumlah beban operasional", "total beban operasional",
                       "beban operasi", "beban usaha"],
    "laba_operasi": ["laba operasi", "laba usaha", "operating profit",
                      "operating income"],
    "laba_sebelum_pajak": ["laba (rugi) sebelum pajak penghasilan",
                            "jumlah laba (rugi) sebelum pajak",
                            "laba sebelum pajak penghasilan",
                            "laba sebelum pajak", "profit before tax"],
    "beban_pajak": ["beban pajak", "pendapatan (beban) pajak",
                     "beban pajak penghasilan", "income tax expense"],
    "laba_bersih": ["jumlah laba (rugi) tahun berjalan",
                     "laba (rugi) tahun berjalan",
                     "laba bersih tahun berjalan",
                     "jumlah laba (rugi) periode berjalan",
                     "laba bersih", "net income", "net profit"],
    "laba_induk": ["laba (rugi) yang dapat diatribusikan ke entitas induk",
                    "laba (rugi) yang dapat diatribusikan kepada pemilik entitas induk",
                    "laba yang dapat diatribusikan kepada pemilik entitas induk",
                    "net income attributable to"],
    "eps_basic": ["laba (rugi) per saham dasar", "laba per saham dasar",
                    "basic earnings per share", "eps dasar"],
    "eps_diluted": ["laba (rugi) per saham dilusian", "laba per saham dilusian",
                      "diluted earnings per share", "eps dilusian"],
    "arus_kas_operasi": ["arus kas dari aktivitas operasi",
                          "kas neto dari aktivitas operasi",
                          "net cash from operating"],
    "arus_kas_investasi": ["arus kas dari aktivitas investasi",
                            "kas neto dari aktivitas investasi",
                            "net cash from investing"],
    "arus_kas_pendanaan": ["arus kas dari aktivitas pendanaan",
                            "kas neto dari aktivitas pendanaan",
                            "net cash from financing"],
    "capex": ["perolehan aset tetap", "pembelian aset tetap",
               "capex", "capital expenditure"],
    "dividen_dibayar": ["dividen dibayar", "dividends paid",
                         "pembayaran dividen"],
}

EXACT_ONLY = {
    "aset": ["jumlah aset", "total aset"],
    "aset_lancar": ["jumlah aset lancar", "total aset lancar"],
    "aset_tidak_lancar": ["jumlah aset tidak lancar", "total aset tidak lancar"],
    "liabilitas": ["jumlah liabilitas", "total liabilitas"],
    "liabilitas_jangka_pendek": ["jumlah liabilitas jangka pendek",
                                   "total liabilitas jangka pendek"],
    "liabilitas_jangka_panjang": ["jumlah liabilitas jangka panjang",
                                    "total liabilitas jangka panjang"],
    "ekuitas": ["jumlah ekuitas", "total ekuitas"],
}

KAS_BLACKLIST = ["penurunan", "kenaikan", "perubahan", "neto", "bersih dari",
                  "digunakan", "diperoleh", "dari aktivitas", "akhir periode",
                  "awal periode"]
BLACKLIST_LBL = ["lainnya", "lain-lain", "lain lain", "komprehensif lain",
                  "subjumlah", "total komprehensif"]

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
    return re.sub(r"([^:])//+", r"\1/", url)


# ============================================================
# CACHE DAFTAR LAPORAN
# ============================================================
def get_report_list(year, periode, verbose=False):
    cache_file = REPORT_LIST_CACHE_DIR / f"{year}_{periode}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

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
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(rl, f)
    except Exception:
        pass
    return rl


def _xlsx_cache_path(url):
    h = hashlib.md5(url.encode()).hexdigest()
    return XLSX_CACHE_DIR / f"{h}.xlsx"


def download_xlsx(url, verbose=False):
    if not url: return None
    url = _normalize_url(url)
    cp = _xlsx_cache_path(url)
    if cp.exists():
        try:
            content = cp.read_bytes()
            if content[:2] == b"PK" and zipfile.is_zipfile(io.BytesIO(content)):
                return content
        except Exception: pass

    cookies = _extract_cookies()
    if verbose: print(f"    [dl] {url[:80]}...")
    for attempt in range(3):
        try:
            r = curl_requests.get(url, headers=DL_HEADERS, cookies=cookies,
                                   impersonate="firefox", timeout=90)
            if r.status_code == 200 and r.content and r.content[:2] == b"PK":
                if zipfile.is_zipfile(io.BytesIO(r.content)):
                    try: cp.write_bytes(r.content)
                    except Exception: pass
                    if verbose: print(f"    [dl OK] {len(r.content)} bytes")
                    return r.content
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1)); continue
        except Exception as e:
            if "curl: (16)" in str(e) or "HTTP/2" in str(e):
                time.sleep(10 * (attempt + 1))
                continue
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
        except Exception: continue
        if df.empty: continue
        for _, row in df.iterrows():
            if len(row) < 2: continue
            label = row.iloc[0]
            if pd.isna(label): continue
            ll = str(label).lower().strip()
            if len(ll) < 4: continue
            if any(b in ll for b in BLACKLIST_LBL): continue

            for field, kws in FIELDS.items():
                if field in hasil:
                    if field == "pendapatan" and "bunga bersih" in ll and "bunga bersih" not in str(hasil.get("pendapatan", "")):
                        pass
                    else:
                        continue

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

                for col in range(1, min(len(row), 5)):
                    num = _to_num(row.iloc[col])
                    if num is not None and num != 0 and abs(num) >= min_abs:
                        hasil[field] = num
                        break

    if "laba_induk" in hasil and "laba_bersih" not in hasil:
        hasil["laba_bersih"] = hasil["laba_induk"]
    if "laba_bersih" in hasil and "laba_induk" not in hasil:
        hasil["laba_induk"] = hasil["laba_bersih"]

    return hasil


# ============================================================
# CACHE HASIL PARSING
# ============================================================
def fetch_one_period(kode, year, periode, verbose=False):
    cache_file = PARSED_CACHE_DIR / f"{kode}_{year}_{periode}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

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

    parsed = parse_xlsx(content)
    if parsed:
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(parsed, f)
        except Exception:
            pass
    return parsed


def compute_ratios(d, harga=None, shares=None, periode=None, ttm_ni=None, ttm_rev=None):
    def sd(a, b): return a / b if a and b and b != 0 else None

    laba = d.get("laba_induk") or d.get("laba_bersih")
    ek = d.get("ekuitas_induk") or d.get("ekuitas")
    pendapatan = d.get("pendapatan")

    def nz(v):
        if v is None: return None
        return v * 1_000_000 if abs(v) < 1_000_000_000 else v

    if ttm_ni is not None:
        laba_rp = ttm_ni
        factor = 1
    else:
        laba_rp = nz(laba)
        p_key = str(periode).split("-")[-1] if periode else "audit"
        factor = {"tw1": 4, "tw2": 2, "tw3": 4/3, "audit": 1}.get(p_key, 1)

    if ttm_rev is not None:
        pend_rp = ttm_rev
        factor_rev = 1
    else:
        pend_rp = nz(pendapatan)
        p_key = str(periode).split("-")[-1] if periode else "audit"
        factor_rev = {"tw1": 4, "tw2": 2, "tw3": 4/3, "audit": 1}.get(p_key, 1)

    ek_rp = nz(ek)

    eps_calc, pe_calc, pb_calc, ps_calc, bv_calc = None, None, None, None, None

    if shares and shares > 0 and harga:
        if ek_rp:
            bv_calc = ek_rp / shares
            if bv_calc > 0: pb_calc = harga / bv_calc
        if laba_rp:
            eps_calc = (laba_rp * factor) / shares
            if eps_calc > 0: pe_calc = harga / eps_calc
        if pend_rp:
            ps_calc = (harga * shares) / (pend_rp * factor_rev)

    # FIX: Sanity Check PER & PBV
    if pe_calc is not None and (pe_calc < 1 or pe_calc > 1000): pe_calc = None
    if pb_calc is not None and (pb_calc < 0.1 or pb_calc > 100): pb_calc = None

    return {
        "roe": sd(laba, ek), "roa": sd(laba, d.get("aset")),
        "der": sd(d.get("liabilitas"), d.get("ekuitas")),
        "dar": sd(d.get("liabilitas"), d.get("aset")),
        "current_ratio": sd(d.get("aset_lancar"), d.get("liabilitas_jangka_pendek")),
        "margin_laba_bersih": sd(laba, d.get("pendapatan")),
        "margin_laba_kotor": sd(d.get("laba_kotor"), d.get("pendapatan")),
        "margin_laba_operasi": sd(d.get("laba_operasi"), d.get("pendapatan")),
        "eps_calc": eps_calc, "pe_calc": pe_calc, "pb_calc": pb_calc,
        "ps_calc": ps_calc, "bv_calc": bv_calc,
    }


def fetch_yfinance(kode):
    if not HAS_YF: return {}
    try:
        t = yf.Ticker(f"{kode}.JK")
        info = t.info or {}
    except Exception:
        return {}
    if not info: return {}
    harga = (info.get("currentPrice") or info.get("regularMarketPrice")
              or info.get("previousClose"))
    return {
        "harga": harga,
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "free_float_pct": (info.get("floatShares") / info.get("sharesOutstanding") * 100
                            if info.get("floatShares") and info.get("sharesOutstanding") else None),
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
    except Exception: return {}
    if len(df) < 20: return {}

    d = df.tail(20)
    high = d["High"].astype(float); low = d["Low"].astype(float)
    close = d["Close"].astype(float); vol = d["Volume"].astype(float)
    hl = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / hl
    mfv = mfm.fillna(0) * vol
    cmf = float(mfv.sum() / vol.sum()) if vol.sum() else 0.0

    full = df.tail(40)
    vt = 1.0
    if len(full) >= 40:
        vr = full["Volume"].tail(20).mean()
        vp = full["Volume"].head(20).mean()
        if vp: vt = float(vr / vp)
    chg = 0.0
    if len(df) >= 21:
        pn = float(df["Close"].iloc[-1]); pt = float(df["Close"].iloc[-21])
        chg = (pn - pt) / pt * 100 if pt else 0.0

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


def _standalone(curr, prev, quarter_num):
    if curr is None: return None
    if quarter_num == 1: return curr
    if prev is None: return None
    result = curr - prev
    return result if result != 0 else None


def build_one(kode, verbose=False):
    kode = kode.strip().upper()

    snap = None; snap_periode = None
    for y, p in SNAPSHOT_CANDIDATES:
        d = fetch_one_period(kode, y, p, verbose=verbose)
        if d and d.get("aset"):
            snap = d; snap_periode = f"{y}-{p}"; break
    if not snap:
        return None

    all_periods = {}
    for y, p, lbl, qnum in QUARTERLY_PERIODS:
        if f"{y}-{p}" == snap_periode:
            d = snap
        else:
            d = fetch_one_period(kode, y, p, verbose=False)
        if d:
            all_periods[lbl] = {"data": d, "qnum": qnum, "year": y, "period": p}

    q_rev, q_eps, q_ni = {}, {}, {}
    standalone_data = []

    for year in sorted(set(v["year"] for v in all_periods.values())):
        year_data = {
            qnum: all_periods[lbl]
            for lbl, v in all_periods.items()
            if v["year"] == year
            for qnum in [v["qnum"]]
        }

        prev_rev, prev_eps, prev_ni = None, None, None

        for qnum in [1, 2, 3, 4]:
            if qnum not in year_data:
                prev_rev = prev_eps = prev_ni = None
                continue

            d = year_data[qnum]["data"]
            lbl = f"{year}-Q{qnum}"

            cum_rev = d.get("pendapatan")
            if cum_rev is not None:
                cum_rev = cum_rev * 1_000_000 if abs(cum_rev) < 1_000_000_000_000 else cum_rev

            cum_ni = d.get("laba_induk") or d.get("laba_bersih")
            if cum_ni is not None:
                cum_ni = cum_ni * 1_000_000 if abs(cum_ni) < 1_000_000_000_000 else cum_ni

            cum_eps = d.get("eps_basic")

            rev_std = _standalone(cum_rev, prev_rev, qnum)
            eps_std = _standalone(cum_eps, prev_eps, qnum)
            ni_std = _standalone(cum_ni, prev_ni, qnum)

            if rev_std is not None: q_rev[lbl] = round(rev_std, 2)
            if eps_std is not None: q_eps[lbl] = round(eps_std, 2)
            if ni_std is not None: q_ni[lbl] = round(ni_std, 2)

            if rev_std is not None and ni_std is not None:
                standalone_data.append({"lbl": lbl, "rev": rev_std, "ni": ni_std})

            prev_rev = cum_rev
            prev_eps = cum_eps
            prev_ni = cum_ni

    ttm_ni, ttm_rev = None, None
    standalone_data.sort(key=lambda x: (x["lbl"].split("-")[0], x["lbl"].split("-")[1]), reverse=True)

    if len(standalone_data) >= 4:
        recent_4 = standalone_data[:4]
        ttm_ni = sum(item["ni"] for item in recent_4)
        ttm_rev = sum(item["rev"] for item in recent_4)

    r_eps, r_rev = {}, {}
    for y in RIWAYAT_YEARS:
        if f"{y}-audit" == snap_periode:
            d = snap
        else:
            d = fetch_one_period(kode, y, "audit", verbose=False)
        if d:
            if d.get("eps_basic") is not None:
                r_eps[str(y)] = round(d["eps_basic"], 2)
            if d.get("pendapatan") is not None:
                raw_rev = d["pendapatan"]
                r_rev[str(y)] = raw_rev if abs(raw_rev) > 1_000_000_000_000 else raw_rev * 1_000_000

    yfd = fetch_yfinance(kode)
    harga = yfd.get("harga")
    shares = yfd.get("shares_outstanding")
    
    # FIX BUG SHARES
    if shares is not None and shares < 10_000_000:
        shares = shares * 1_000_000
        
    if not shares and yfd.get("market_cap") and harga:
        shares = yfd.get("market_cap") / harga

    ratios = compute_ratios(snap, harga=harga, shares=shares, periode=snap_periode, ttm_ni=ttm_ni, ttm_rev=ttm_rev)
    akum = compute_akumulasi(kode)

    warnings = []
    if not snap.get("pendapatan"):
        warnings.append("revenue_missing")
    if not snap.get("laba_induk") and not snap.get("laba_bersih"):
        warnings.append("income_missing")
    if ratios.get("pe_calc") and ratios["pe_calc"] < 0:
        warnings.append("pe_negative")
    if len(q_rev) < 4:
        warnings.append("quarterly_incomplete")
    if ttm_ni is None:
        warnings.append("ttm_fallback")

    data = {
        "kode": kode,
        "nama": yfd.get("nama"),
        "sektor": yfd.get("sektor"),
        "industri": yfd.get("industri"),
        "harga": harga,
        "update": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periode_terbaru": snap_periode,
        "warnings": warnings,
        "rasio_kunci": {
            "pe": ratios.get("pe_calc"), "pb": ratios.get("pb_calc"),
            "ps": ratios.get("ps_calc"), "roe": ratios.get("roe"),
            "eps": ratios.get("eps_calc"), "de": ratios.get("der"),
            "margin_net": ratios.get("margin_laba_bersih"),
            "current_ratio": ratios.get("current_ratio"),
            "roa": ratios.get("roa"), "bv": ratios.get("bv_calc"),
        },
        "quarterly": {
            "revenue": q_rev,     
            "eps": q_eps,          
            "net_income": q_ni,    
            "note": "nilai standalone (Q1/Q2/Q3/Q4 individual, bukan cumulative)"
        },
        "riwayat": {"eps": r_eps, "revenue_per_share": r_rev},
        "statistik": {
            "market_cap": yfd.get("market_cap"),
            "enterprise_value": yfd.get("enterprise_value"),
            "shares_outstanding": shares,
            "free_float_pct": yfd.get("free_float_pct"),
        },
        "akumulasi": akum,
        "neraca": {k: snap.get(k) for k in
                   ["aset", "aset_lancar", "kas", "piutang_usaha", "persediaan",
                    "aset_tetap", "liabilitas", "liabilitas_jangka_pendek",
                    "liabilitas_jangka_panjang", "utang_usaha", "utang_bank",
                    "ekuitas", "ekuitas_induk", "modal_saham", "saldo_laba"]},
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
    print(f"Fetch {len(tickers)} saham\n")

    periods = set(SNAPSHOT_CANDIDATES)
    for y, p, _, _ in QUARTERLY_PERIODS: periods.add((y, p))
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
                warns = ",".join(d.get("warnings", [])) or "OK"
                print(f"OK ({d['periode_terbaru']}) Q:{nq} [{warns}]")
            else:
                err += 1
                print("SKIP (no XLSX)")
        except Exception as e:
            err += 1
            print(f"ERR: {e}")
        time.sleep(random.uniform(0.3, 0.8))

    print(f"\nSelesai: OK={ok}, ERR={err} | {time.time()-t0:.0f}s")


def batch(tickers, workers=4, delay=1.0, skip_existing=False):
    if not tickers:
        print("Tidak ada ticker.")
        return

    print(f"Batch {len(tickers)} saham, {workers} workers\n")

    periods = set(SNAPSHOT_CANDIDATES)
    for y, p, _, _ in QUARTERLY_PERIODS: periods.add((y, p))
    for y in RIWAYAT_YEARS: periods.add((y, "audit"))

    print(f"Pre-fetch {len(periods)} report list...")
    for y, p in sorted(periods):
        rl = get_report_list(y, p)
        print(f"  {y} {p}: {len(rl)}", flush=True)
    print()

    ok, err, skip = 0, 0, 0
    lock = threading.Lock()
    counter = {"n": 0}
    t0 = time.time()

    def worker(kode):
        time.sleep(random.uniform(0, delay))
        try:
            d = build_one(kode, verbose=False)
            return kode, ("OK" if d else "SKIP"), None
        except Exception as e:
            return kode, "ERR", str(e)[:100]

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(worker, k): k for k in tickers}
        for fut in as_completed(futures):
            k, status, e = fut.result()
            with lock:
                counter["n"] += 1
                n = counter["n"]
                if status == "OK": ok += 1
                elif status == "SKIP": skip += 1
                else: err += 1
            if n % 10 == 0 or n == len(tickers):
                elapsed = time.time() - t0
                rate = n / elapsed if elapsed > 0 else 0
                eta = (len(tickers) - n) / rate if rate > 0 else 0
                err_rate = err / n * 100
                print(f"[{n}/{len(tickers)}] OK={ok} skip={skip} err={err} "
                      f"({err_rate:.0f}%) | {rate:.2f}/s | ETA {eta:.0f}s", flush=True)

    print(f"\nSelesai: OK={ok}, SKIP={skip}, ERR={err} | {time.time()-t0:.0f}s")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        q3_file = REPORT_LIST_CACHE_DIR / "2026_tw3.json"
        
        if q3_file.exists():
            with open(q3_file, 'r', encoding='utf-8') as f:
                q3_data = json.load(f)
            tickers = list(q3_data.keys())
            print(f"📌 MODE Q3 AKTIF: Memproses {len(tickers)} saham yang ada di laporan Q3 2026.")
        else:
            print("⚠️ File 2026_tw3.json tidak ditemukan. Menggunakan daftar_saham.csv.")
            with open("daftar_saham.csv", "r", encoding="utf-8-sig") as f:
                tickers = []
                for row in csv.DictReader(f):
                    for k in ["Kode", "kode"]:
                        if k in row and row[k]:
                            tickers.append(row[k].strip().upper()); break
        
        batch(tickers, workers=10, delay=1.5)
    else:
        tickers = sys.argv[1:] if len(sys.argv) > 1 else ["BBCA"]
        main([t.upper() for t in tickers])