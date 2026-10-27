import pandas as pd
from datetime import datetime
import time
import random
from curl_cffi import requests as curl_requests

# ============================================================
# DAFTAR TICKER
# ============================================================
INDEKS_GLOBAL = {
    "Dow Jones": "^DJI",
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Shanghai": "000001.SS",
    "STI Singapore": "^STI",
    "DAX Jerman": "^GDAXI",
}

MATA_UANG = {
    "USD/IDR": "IDR=X",
    "DXY Index": "DX-Y.NYB",
    "USD/CNY": "CNY=X",
    "USD/JPY": "JPY=X",
}

KOMODITAS = {
    "Minyak Brent": "BZ=F",
    "Minyak WTI": "CL=F",
    "Emas": "GC=F",
    "Perak": "SI=F",
    "Batu Bara": "MTF=F",
    "CPO (Malaysia)": "FCPO.KL",
    "Tembaga": "HG=F",
}

# ============================================================
# FUNGSI AMBIL DATA LANGSUNG DARI API YAHOO (BYPASS BLOCK)
# ============================================================
def fetch_yahoo_chart_direct(ticker, range_period="5d", interval="1d", max_retries=3):
    """
    Mengambil data historis langsung dari query1.finance.yahoo.com
    menggunakan curl_cffi untuk menyamar sebagai browser.
    """
    ticker = ticker.strip()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_period}&interval={interval}"
    
    # Header lengkap untuk menipu Yahoo
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    session = curl_requests.Session(impersonate="chrome120")
    
    for attempt in range(max_retries):
        try:
            response = session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 429:
                # Rate limit, tunggu dan coba lagi
                time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))
                continue
                
            response.raise_for_status()
            data = response.json()
            
            result = data.get("chart", {}).get("result")
            if not result:
                return None
                
            timestamps = result[0].get("timestamp", [])
            closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
            
            # Filter nilai None
            valid_data = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
            if not valid_data:
                return None
                
            df = pd.DataFrame(valid_data, columns=["Date", "Close"])
            df["Date"] = pd.to_datetime(df["Date"], unit="s")
            df.set_index("Date", inplace=True)
            return df
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Gagal mengambil {ticker}: {e}")
                return None
            time.sleep((2 ** attempt) + random.uniform(0.5, 1.5))

    return None


def fetch_ticker(ticker, days=5):
    """Ambil harga terakhir + perubahan %."""
    df = fetch_yahoo_chart_direct(ticker, range_period=f"{days}d")
    
    if df is None or len(df) < 2:
        return None

    close_now = df["Close"].iloc[-1]
    close_prev = df["Close"].iloc[-2]
    change_pct = (close_now / close_prev - 1) * 100

    return {
        "harga": float(close_now),
        "prev": float(close_prev),
        "change_pct": float(change_pct),
        "tanggal": df.index[-1].strftime("%d %b %Y"),
    }

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
        time.sleep(0.5)

    # Mata uang
    for nama, ticker in MATA_UANG.items():
        result = fetch_ticker(ticker)
        if result and "error" not in result:
            data["mata_uang"][nama] = result
        time.sleep(0.5)

    # Komoditas
    for nama, ticker in KOMODITAS.items():
        result = fetch_ticker(ticker)
        if result and "error" not in result:
            data["komoditas"][nama] = result
        time.sleep(0.5)

    return data

# ... (Bagian hitung_sentimen dan get_dampak_ihsg biarkan sama persis) ...