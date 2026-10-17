"""
Ambil data global dari Yahoo Finance untuk Ringkasan Pagi.
- Indeks global (Wall Street, Asia, Eropa)
- Mata uang (USD/IDR, DXY)
- Komoditas (Brent, Gold, Coal, CPO)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


# ============================================================
# DAFTAR TICKER
# ============================================================
INDEKS_GLOBAL = {
    "Dow Jones": "    ^DJI",
    "S&P 500": "      ^GSPC",
    "Nasdaq": "       ^IXIC",
    "Nikkei 225": "   ^N225",
    "Hang Seng": "    ^HSI",
    "Shanghai": "    000001.SS",
    "STI Singapore": "^STI",
    "DAX Jerman": "  ^GDAXI",
}

MATA_UANG = {
    "USD/IDR": "IDR=X",
    "DXY Index": "DX-Y.NYB",
    "USD/CNY": "CNY=X",
    "USD/JPY": "JPY=X",
}

KOMODITAS = {
    "Minyak Brent": "BZ=F",
    "Minyak WTI": "  CL=F",
    "Emas": "        GC=F",
    "Perak": "       SI=F",
    "Batu Bara": "   MTF=F",
    "CPO (Malaysia)": "FCPO.KL",
    "Tembaga": "     HG=F",
}


# ============================================================
# FETCH DATA
# ============================================================
def fetch_ticker(ticker, days=5):
    """Ambil harga terakhir + perubahan % dari yfinance."""
    try:
        t = yf.Ticker(ticker.strip())
        hist = t.history(period=f"{days}d")

        if hist.empty or len(hist) < 2:
            return None

        close_now = hist["Close"].iloc[-1]
        close_prev = hist["Close"].iloc[-2]
        change_pct = (close_now / close_prev - 1) * 100

        return {
            "harga": float(close_now),
            "prev": float(close_prev),
            "change_pct": float(change_pct),
            "tanggal": hist.index[-1].strftime("%d %b %Y"),
        }
    except Exception as e:
        return {"error": str(e)}


def get_all_global_data():
    """Ambil semua data global sekaligus."""
    data = {
        "indeks": {},
        "mata_uang": {},
        "komoditas": {},
        "waktu": datetime.now().strftime("%d %B %Y, %H:%M"),
    }

    # Indeks
    for nama, ticker in INDEKS_GLOBAL.items():
        result = fetch_ticker(ticker)
        if result and "error" not in result:
            data["indeks"][nama] = result

    # Mata uang
    for nama, ticker in MATA_UANG.items():
        result = fetch_ticker(ticker)
        if result and "error" not in result:
            data["mata_uang"][nama] = result

    # Komoditas
    for nama, ticker in KOMODITAS.items():
        result = fetch_ticker(ticker)
        if result and "error" not in result:
            data["komoditas"][nama] = result

    return data


# ============================================================
# ANALISIS SENTIMEN
# ============================================================
def hitung_sentimen(data):
    """Hitung sentimen global dari data."""
    positif = 0
    negatif = 0
    netral = 0
    detail = []

    # Indeks global (bobot 1)
    for nama, d in data.get("indeks", {}).items():
        chg = d["change_pct"]
        if chg > 0.3:
            positif += 1
            detail.append(f"✅ {nama}: {chg:+.2f}%")
        elif chg < -0.3:
            negatif += 1
            detail.append(f"❌ {nama}: {chg:+.2f}%")
        else:
            netral += 1
            detail.append(f"➖ {nama}: {chg:+.2f}%")

    # Komoditas (bobot 1)
    for nama, d in data.get("komoditas", {}).items():
        chg = d["change_pct"]
        if chg > 0.5:
            positif += 1
        elif chg < -0.5:
            negatif += 1
        else:
            netral += 1

    # USD/IDR (khusus: naik = negatif untuk IDX)
    usd_idr = data.get("mata_uang", {}).get("USD/IDR", {})
    if usd_idr:
        chg = usd_idr["change_pct"]
        if chg > 0.2:
            negatif += 2  # rupiah melemah = negatif untuk IHSG
        elif chg < -0.2:
            positif += 2  # rupiah menguat = positif
        else:
            netral += 1

    total = positif + negatif + netral
    if total == 0:
        return "NETRAL", "Data tidak cukup", detail

    skor_positif = positif / total

    if skor_positif >= 0.65:
        status = "BULLISH KUAT"
        emoji = "🟢🟢"
    elif skor_positif >= 0.55:
        status = "BULLISH"
        emoji = "🟢"
    elif skor_positif <= 0.30:
        status = "BEARISH KUAT"
        emoji = "🔴🔴"
    elif skor_positif <= 0.45:
        status = "BEARISH"
        emoji = "🔴"
    else:
        status = "NETRAL"
        emoji = "🟡"

    return f"{emoji} {status}", f"Positif: {positif}, Negatif: {negatif}, Netral: {netral}", detail


def get_dampak_ihsg(data):
    """Analisis dampak spesifik ke IHSG."""
    dampak = []

    # Wall Street
    dj = data["indeks"].get("Dow Jones", {}).get("change_pct", 0)
    sp = data["indeks"].get("S&P 500", {}).get("change_pct", 0)
    ns = data["indeks"].get("Nasdaq", {}).get("change_pct", 0)
    ws_avg = (dj + sp + ns) / 3 if any([dj, sp, ns]) else 0

    if ws_avg > 0.5:
        dampak.append(("Wall Street", f"{ws_avg:+.2f}%", "POSITIF", "Bursa AS naik, sentimen global positif"))
    elif ws_avg < -0.5:
        dampak.append(("Wall Street", f"{ws_avg:+.2f}%", "NEGATIF", "Bursa AS turun, waspada"))
    else:
        dampak.append(("Wall Street", f"{ws_avg:+.2f}%", "NETRAL", "Bursa AS mixed"))

    # USD/IDR
    usd_idr = data["mata_uang"].get("USD/IDR", {})
    if usd_idr:
        chg = usd_idr["change_pct"]
        harga = usd_idr["harga"]
        if chg > 0.2:
            dampak.append(("USD/IDR", f"{harga:,.0f} ({chg:+.2f}%)", "NEGATIF", "Rupiah melemah, tekanan jual asing"))
        elif chg < -0.2:
            dampak.append(("USD/IDR", f"{harga:,.0f} ({chg:+.2f}%)", "POSITIF", "Rupiah menguat, asing masuk"))
        else:
            dampak.append(("USD/IDR", f"{harga:,.0f} ({chg:+.2f}%)", "NETRAL", "Rupiah stabil"))

    # Minyak
    brent = data["komoditas"].get("Minyak Brent", {}).get("change_pct", 0)
    if brent > 1:
        dampak.append(("Minyak Brent", f"{brent:+.2f}%", "POSITIF", "Minyak naik, positif untuk energi"))
    elif brent < -1:
        dampak.append(("Minyak Brent", f"{brent:+.2f}%", "NEGATIF", "Minyak turun, tekanan ke energi"))

    return dampak