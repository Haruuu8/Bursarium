"""
quant/supres.py — Support/Resistance HANYA dari metode backtest 90%+ WR.

Hasil backtest 30M+ touch di 900 saham IDX:
- SUPPORT (swing low W=5)   : 91.1% mantul  → BUY LIMIT
- RESISTANCE (swing high W=5): 87.3% breakout → STOP BUY

Semua metode lain (donchian_55, round_100, pivot_fib, pivot_classic, dll)
DIHAPUS karena WR-nya di bawah 90% dan tidak layak dipakai sebagai filter.

Kalau mau WR lebih tinggi (92.9%), ubah SWING_WINDOW = 7.
Kalau mau lebih sering muncul (tapi WR 87.8%), ubah SWING_WINDOW = 3.

Struktur kode:
- Konfigurasi
- Helper: safe division
- Load OHLCV (dengan normalisasi kolom openprice vs Open)
- ATR calculation
- Swing detection (high & low)
- Zone helper (band, make_zone)
- Build supports (swing low W=5)
- Build resistances (swing high W=5)
- Public API: get_support_resistance()
- Internal impl: _impl()
"""

import numpy as np
import pandas as pd
from quant.parquet_loader import load_parquet_safe


# ============================================================
# KONFIGURASI GLOBAL
# ============================================================
SWING_WINDOW = 5
# SWING_WINDOW = 5 → 91.1% WR support, 87.3% breakout resistance
# SWING_WINDOW = 7 → 92.9% WR support, 89.3% breakout resistance (lebih jarang)
# SWING_WINDOW = 3 → 87.8% WR support, 83.8% breakout resistance (lebih sering)

MIN_DISTANCE_PCT = 0.5
# Level support/resistance minimal 0.5% dari harga sekarang.
# Kalau lebih dekat dari ini, dianggap noise.

MAX_DISTANCE_PCT = 15.0
# Level support/resistance maksimal 15% dari harga sekarang.
# Kalau lebih jauh dari ini, tidak actionable untuk trade 1-2 minggu.

BAND_PCT = 0.005
# Lebar band zona: 0.5% di atas & di bawah level.
# Contoh: level 5,000 → zona lower 4,975, upper 5,025.

MIN_BARS = 60
# Minimal 60 baris data historis untuk perhitungan ATR & swing.
# Kalau kurang, return None.


# ============================================================
# HELPER — SAFE DIVISION
# ============================================================
def _safe_div(a, b, default=0.0):
    """
    Pembagian aman dengan handling untuk nilai 0, NaN, inf, None.
    
    Args:
        a: numerator
        b: denominator
        default: nilai return kalau b == 0 atau invalid
    
    Returns:
        a/b atau default kalau tidak bisa dihitung
    """
    try:
        if b is None or b == 0:
            return default
        r = a / b
        if isinstance(r, float) and (np.isnan(r) or np.isinf(r)):
            return default
        return r
    except (TypeError, ZeroDivisionError, ValueError):
        return default


# ============================================================
# LOAD DATA OHLCV DARI PARQUET
# ============================================================
def _load_ohlcv(kode):
    """
    Ambil OHLCV satu saham dari parquet global.
    
    Handle kasus-kasus khusus yang ditemukan di data IDX:
    1. Kolom 'Open' di parquet bisa NaN, sedangkan 'openprice' valid
       → normalisasi ke nama standar (Open, High, Low, Close, Date)
    2. Kolom bisa lowercase atau berbeda nama
    3. Beberapa baris mungkin punya harga 0 atau NaN
       → filter sebelum return
    4. Saham baru IPO atau suspensi lama bisa punya < 60 baris
       → return None, tidak bisa dihitung
    
    Args:
        kode: string kode saham (e.g., "BBCA")
    
    Returns:
        DataFrame dengan kolom Date, Open, High, Low, Close
        atau None kalau data tidak cukup / error
    """
    df_all = load_parquet_safe()
    if df_all is None:
        print("[supres] parquet is None")
        return None
    
    if "Kode" not in df_all.columns:
        print(f"[supres] no Kode column, columns: {list(df_all.columns)}")
        return None
    
    # Normalisasi kode saham
    df_all["Kode"] = df_all["Kode"].astype(str).str.strip().str.upper()
    kode_clean = str(kode).strip().upper()
    df = df_all[df_all["Kode"] == kode_clean].copy()
    
    if df.empty:
        print(f"[supres] {kode_clean} not found in parquet")
        return None
    
    # ============================================================
    # NORMALISASI NAMA KOLOM
    # ============================================================
    col_aliases = {
        "Open": [
            "Open", "open", "openprice", "open_price", "OpenPrice"
        ],
        "High": [
            "High", "high", "highprice", "high_price", "HighPrice"
        ],
        "Low": [
            "Low", "low", "lowprice", "low_price", "LowPrice"
        ],
        "Close": [
            "Close", "close", "closeprice", "close_price",
            "ClosePrice", "last"
        ],
        "Date": [
            "Date", "date", "tanggal", "Tanggal", "datetime"
        ],
    }
    
    for target, candidates in col_aliases.items():
        # Cek apakah kolom target sudah ada dan valid
        if target in df.columns:
            if target == "Date":
                test = pd.to_datetime(df[target], errors="coerce")
            else:
                test = pd.to_numeric(df[target], errors="coerce")
            if test.notna().sum() > 0:
                continue
        
        # Cari kolom alternatif
        found = False
        for alt in candidates:
            if alt == target:
                continue
            if alt not in df.columns:
                continue
            
            if target == "Date":
                test = pd.to_datetime(df[alt], errors="coerce")
                if test.notna().sum() > 0:
                    df["Date"] = test
                    found = True
                    break
            else:
                test = pd.to_numeric(df[alt], errors="coerce")
                if test.notna().sum() > 0 and (test.dropna() > 0).any():
                    df[target] = test
                    found = True
                    break
        
        # Fallback: Open = (High + Low) / 2
        if not found and target in ["Open", "High", "Low", "Close"]:
            if (target == "Open"
                    and "High" in df.columns
                    and "Low" in df.columns):
                df["Open"] = (df["High"] + df["Low"]) / 2
                continue
            print(f"[supres] {kode_clean}: no valid '{target}' column")
            return None
    
    # ============================================================
    # PARSING & FILTERING
    # ============================================================
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    if df.empty:
        print(f"[supres] {kode_clean}: all Date invalid")
        return None
    
    for c in ["Open", "High", "Low", "Close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[
        (df["Open"] > 0)
        & (df["High"] > 0)
        & (df["Low"] > 0)
        & (df["Close"] > 0)
    ]
    
    if df.empty:
        print(f"[supres] {kode_clean}: no valid rows after OHLC filter")
        return None
    
    df = df.sort_values("Date").reset_index(drop=True)
    
    if len(df) < MIN_BARS:
        print(f"[supres] {kode_clean}: only {len(df)} rows (need {MIN_BARS})")
        return None
    
    return df


# ============================================================
# ATR (Average True Range)
# ============================================================
def _atr(df, n=14):
    """
    Hitung ATR (Average True Range) untuk 14 periode terakhir.
    
    ATR dipakai untuk:
    - Menentukan tolerance di UI (band zona)
    - Menentukan range swing di beberapa fungsi (kalau perlu)
    
    Formula:
        TR = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
        ATR = rolling_mean(TR, n)
    """
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(n, min_periods=n).mean()
    
    if atr.empty or pd.isna(atr.iloc[-1]):
        return 0.0
    return float(atr.iloc[-1])


# ============================================================
# SWING DETECTION
# ============================================================
def _find_swings(df, window=5):
    """
    Cari semua swing high & swing low dalam data.
    
    Definisi swing:
    - Swing low  : low[i] < SEMUA low di [i-window, i) DAN
                          low[i] < SEMUA low di (i, i+window]
    - Swing high : high[i] > SEMUA high di [i-window, i) DAN
                          high[i] > SEMUA high di (i, i+window]
    
    Args:
        df: DataFrame dengan kolom High, Low
        window: jumlah bar di kiri & kanan untuk cek lokal ekstremum
    
    Returns:
        (swing_lows, swing_highs) — list of dict {idx, price}
    """
    highs = df["High"].values
    lows = df["Low"].values
    n = len(df)
    
    swing_lows = []
    swing_highs = []
    
    for i in range(window, n - window):
        left_h = highs[i - window:i]
        right_h = highs[i + 1:i + 1 + window]
        left_l = lows[i - window:i]
        right_l = lows[i + 1:i + 1 + window]
        
        if len(left_h) < window or len(right_h) < window:
            continue
        if len(left_l) < window or len(right_l) < window:
            continue
        
        # Swing low
        if lows[i] > 0 and lows[i] < left_l.min() and lows[i] < right_l.min():
            swing_lows.append({"idx": i, "price": float(lows[i])})
        
        # Swing high
        if highs[i] > 0 and highs[i] > left_h.max() and highs[i] > right_h.max():
            swing_highs.append({"idx": i, "price": float(highs[i])})
    
    return swing_lows, swing_highs


# ============================================================
# ZONE HELPER
# ============================================================
def _band(price, pct=BAND_PCT):
    """
    Buat band di sekitar level harga.
    Contoh: price=5000, pct=0.005 → lower=4975, upper=5025
    """
    b = price * pct
    return round(price - b, 2), round(price + b, 2)


def _make_zone(level, side, role, strategy, score, strength,
               source, backtest_wr, df, last_idx, note, distance_pct=0.0):
    """
    Buat dict zona standar dengan semua field yang dibutuhkan UI.
    
    Args:
        level        : harga level zona
        side         : "support" atau "resistance"
        role         : "buy_limit" atau "stop_buy"
        strategy     : "limit_buy" atau "stop_buy"
        score        : 0-10 (kekuatan zona)
        strength     : "WEAK" | "MODERATE" | "STRONG"
        source       : nama metode ("swing_w5")
        backtest_wr  : WR historis dari backtest
        df           : dataframe (untuk ambil last_touch date)
        last_idx     : index bar touch terakhir
        note         : keterangan untuk UI
        distance_pct : % jarak dari harga sekarang
    """
    lower, upper = _band(level)
    days_since = (df["Date"].iloc[-1] - df["Date"].iloc[last_idx]).days
    
    return {
        "level": round(level, 2),
        "lower": lower,
        "upper": upper,
        "type": side,
        "role": role,
        "strategy": strategy,
        "original_type": side,
        "flip": False,
        "is_elite": False,
        "width_pct": 1.0,
        "n_touches": 1,
        "last_touch": df["Date"].iloc[last_idx],
        "days_since_last": days_since,
        "score": round(score, 2),
        "strength": strength,
        "bounces": 0,
        "source": source,
        "backtest_wr": backtest_wr,
        "distance_pct": round(distance_pct, 2),
        "note": note,
    }


# ============================================================
# BUILD SUPPORT ZONES — Hanya Swing Low W=5
# ============================================================
def _build_supports(df, current, swing_lows):
    """
    Bangun list support dari swing low W=5.
    
    Backtest: swing low W=5 = 91.1% WR mantul (1.29M touch).
    
    Logic:
    1. Filter swing low di bawah current price
    2. Filter jarak: MIN_DISTANCE_PCT <= jarak <= MAX_DISTANCE_PCT
    3. Sort: terdekat dulu (harga paling tinggi di bawah current)
    4. Ambil maksimal 2 support terdekat
    5. Set role = "buy_limit" (pasang limit order di level ini)
    """
    supports = []
    
    # Filter kandidat
    candidates = []
    for s in swing_lows:
        if s["price"] <= 0:
            continue
        if s["price"] >= current:
            continue
        
        dist_pct = (current - s["price"]) / current * 100
        if dist_pct < MIN_DISTANCE_PCT:
            continue
        if dist_pct > MAX_DISTANCE_PCT:
            continue
        
        candidates.append(s)
    
    # Sort: terdekat dulu (harga paling tinggi = paling dekat dari current)
    candidates.sort(key=lambda s: -s["price"])
    candidates = candidates[:2]
    
    # Build zone untuk setiap kandidat
    for i, s in enumerate(candidates):
        level = s["price"]
        dist = (level / current - 1) * 100
        
        # Score: support terdekat dapat 8.5, berikutnya 8.0
        score = 8.5 - i * 0.5
        strength = "STRONG" if i == 0 else "MODERATE"
        
        zone = _make_zone(
            level=level,
            side="support",
            role="buy_limit",
            strategy="limit_buy",
            score=score,
            strength=strength,
            source=f"swing_w{SWING_WINDOW}",
            backtest_wr=91.1,
            df=df,
            last_idx=s["idx"],
            note=f"Swing low W={SWING_WINDOW} — 91.1% mantul (backtest)",
            distance_pct=dist,
        )
        supports.append(zone)
    
    # Sort final: level tertinggi dulu (terdekat dari harga)
    supports.sort(key=lambda z: -z["level"])
    
    return supports


# ============================================================
# BUILD RESISTANCE ZONES — Hanya Swing High W=5
# ============================================================
def _build_resistances(df, current, swing_highs):
    """
    Bangun list resistance dari swing high W=5.
    
    Backtest: swing high W=5 = 87.3% breakout (1.12M touch).
    
    PENTING: Untuk resistance, kita pakai strategi BREAKOUT (beli saat
    tembus), bukan REVERSAL (jual saat mantul). Karena dari backtest:
    - Resistance reversal WR hanya 12.7% (artinya 87.3% ditembus)
    - Jadi role = "breakout_trigger" (buy stop di atas level)
    
    Logic:
    1. Filter swing high di atas current price
    2. Filter jarak: MIN_DISTANCE_PCT <= jarak <= MAX_DISTANCE_PCT
    3. Sort: terdekat dulu (harga paling rendah di atas current)
    4. Ambil maksimal 2 resistance terdekat
    5. Set role = "breakout_trigger" (pasang stop buy di atas level)
    """
    resistances = []
    
    # Filter kandidat
    candidates = []
    for s in swing_highs:
        if s["price"] <= 0:
            continue
        if s["price"] <= current:
            continue
        
        dist_pct = (s["price"] - current) / current * 100
        if dist_pct < MIN_DISTANCE_PCT:
            continue
        if dist_pct > MAX_DISTANCE_PCT:
            continue
        
        candidates.append(s)
    
    # Sort: terdekat dulu (harga paling rendah = paling dekat dari current)
    candidates.sort(key=lambda s: s["price"])
    candidates = candidates[:2]
    
    # Build zone untuk setiap kandidat
    for i, s in enumerate(candidates):
        level = s["price"]
        dist = (level / current - 1) * 100
        
        # Score: resistance terdekat dapat 8.5, berikutnya 8.0
        score = 8.5 - i * 0.5
        strength = "STRONG" if i == 0 else "MODERATE"
        
        zone = _make_zone(
            level=level,
            side="resistance",
            role="breakout_trigger",
            strategy="stop_buy",
            score=score,
            strength=strength,
            source=f"swing_w{SWING_WINDOW}",
            backtest_wr=87.3,
            df=df,
            last_idx=s["idx"],
            note=f"Swing high W={SWING_WINDOW} — 87.3% breakout (beli saat tembus)",
            distance_pct=dist,
        )
        resistances.append(zone)
    
    # Sort final: level terendah dulu (terdekat dari harga)
    resistances.sort(key=lambda z: z["level"])
    
    return resistances


# ============================================================
# PUBLIC API
# ============================================================
def get_support_resistance(kode, timeframe="daily", **kwargs):
    """
    Hitung support & resistance untuk satu saham.
    
    Ini adalah fungsi yang dipanggil dari views/Watchlist.py.
    Semua kwargs tambahan (scales, max_per_side, dll) diabaikan
    karena implementasi baru hanya pakai swing_w5.
    
    Args:
        kode: string kode saham (e.g., "BBCA")
        timeframe: "daily" (hanya support daily untuk sekarang)
        **kwargs: kompatibilitas backward (diabaikan)
    
    Returns:
        dict dengan key:
        - kode          : string
        - timeframe     : string
        - current_price : float
        - atr           : float
        - tolerance     : float (band untuk UI)
        - n_bars        : int (jumlah baris data)
        - scales        : dict (info konfigurasi)
        - supports      : list of dict (max 2)
        - resistances   : list of dict (max 2)
        
        Atau None kalau data tidak cukup / error.
    """
    try:
        return _impl(kode, timeframe)
    except Exception as e:
        print(f"[supres] gagal hitung {kode}: {e}")
        return None


# ============================================================
# INTERNAL IMPLEMENTATION
# ============================================================
def _impl(kode, timeframe):
    """
    Implementasi utama get_support_resistance.
    
    Steps:
    1. Load OHLCV data (dengan normalisasi kolom)
    2. Cek minimal 60 baris
    3. Ambil current price (close bar terakhir)
    4. Hitung ATR (untuk tolerance)
    5. Deteksi semua swing low & swing high
    6. Build supports dari swing low W=5
    7. Build resistances dari swing high W=5
    8. Return dict lengkap
    """
    # Step 1: Load data
    df = _load_ohlcv(kode)
    if df is None:
        return None
    
    # Step 2: Cek minimal baris
    if len(df) < MIN_BARS:
        return None
    
    # Step 3: Current price
    current = float(df["Close"].iloc[-1])
    if current <= 0 or pd.isna(current):
        return None
    
    # Step 4: ATR
    atr = _atr(df, 14)
    
    # Step 5: Detect swings
    swing_lows, swing_highs = _find_swings(df, window=SWING_WINDOW)
    
    # Step 6: Build supports
    supports = _build_supports(df, current, swing_lows)
    
    # Step 7: Build resistances
    resistances = _build_resistances(df, current, swing_highs)
    
    # Step 8: Return
    return {
        "kode": kode,
        "timeframe": timeframe,
        "current_price": current,
        "atr": atr,
        "tolerance": round(max(atr * 0.5, current * 0.005), 2),
        "n_bars": len(df),
        "scales": {"swing": SWING_WINDOW},
        "supports": supports,
        "resistances": resistances,
    }