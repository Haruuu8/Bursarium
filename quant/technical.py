"""
Modul perhitungan indikator teknikal & sinyal trading.
Semua dari data lokal OHLCV (data_ohlcv_idx/{kode}.csv).
"""

import os
import numpy as np
import pandas as pd


def load_ohlcv(kode, min_rows=60):
    path = os.path.join("data_ohlcv_idx", f"{kode}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        # Ambil 250 hari terakhir untuk cukup data
        df = df.tail(250).reset_index(drop=True)
        if len(df) < min_rows:
            return None
        return df
    except Exception:
        return None


def _rsi(series, n=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(n, min_periods=n).mean()
    loss = -delta.clip(upper=0).rolling(n, min_periods=n).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _ema(series, n):
    return series.ewm(span=n, adjust=False, min_periods=n).mean()


def _atr(df, n=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def _macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _bollinger(series, n=20, k=2):
    ma = series.rolling(n, min_periods=n).mean()
    std = series.rolling(n, min_periods=n).std()
    upper = ma + k * std
    lower = ma - k * std
    width = (upper - lower) / ma.replace(0, np.nan)
    pct_b = (series - lower) / (upper - lower).replace(0, np.nan)
    return upper, ma, lower, width, pct_b


def _find_swing_levels(df, lookback=5, num_levels=3):
    """Cari support & resistance dari swing high/low."""
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values
    current_price = closes[-1]

    # Swing high: high lebih tinggi dari lookback kiri dan kanan
    swing_highs = []
    swing_lows = []
    for i in range(lookback, len(df) - lookback):
        window_high = highs[i - lookback:i + lookback + 1]
        window_low = lows[i - lookback:i + lookback + 1]
        if highs[i] == window_high.max():
            swing_highs.append(highs[i])
        if lows[i] == window_low.min():
            swing_lows.append(lows[i])

    # Ambil resistance = swing high > current price, terdekat dulu
    resistances = sorted(set([round(x) for x in swing_highs if x > current_price * 1.005]))
    resistances = resistances[:num_levels]

    # Support = swing low < current price, terdekat dulu
    supports = sorted(set([round(x) for x in swing_lows if x < current_price * 0.995]),
                      reverse=True)
    supports = supports[:num_levels]

    # Klasifikasi strength berdasarkan jarak
    def _strength(level, price):
        dist = abs(level / price - 1)
        if dist < 0.02: return "WEAK"
        if dist < 0.05: return "MODERATE"
        return "STRONG"

    supports_out = [(s, _strength(s, current_price)) for s in supports]
    resistances_out = [(r, _strength(r, current_price)) for r in resistances]

    return supports_out, resistances_out


def hitung_indikator_teknikal(kode):
    df = load_ohlcv(kode)
    if df is None or len(df) < 30:
        return None

    close = df["Close"]
    last = close.iloc[-1]

    rsi14 = _rsi(close, 14).iloc[-1]
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd_line, signal_line, hist = _macd(close)
    macd_hist = hist.iloc[-1]

    upper, ma20, lower, bb_width, pct_b = _bollinger(close, 20, 2)
    bb_pct_b = pct_b.iloc[-1]
    sma20 = ma20.iloc[-1]
    ema20 = _ema(close, 20).iloc[-1]

    atr14 = _atr(df, 14).iloc[-1]
    atr_pct = atr14 / last * 100 if last else 0

    # Klasifikasi RSI
    if rsi14 >= 70: rsi_label = "OVERBOUGHT"
    elif rsi14 <= 30: rsi_label = "OVERSOLD"
    else: rsi_label = "NEUTRAL"

    # MACD
    if macd_hist > 0.5: macd_label = "BULLISH"
    elif macd_hist < -0.5: macd_label = "BEARISH"
    else: macd_label = "NEUTRAL"

    # Bollinger
    if bb_pct_b >= 0.8: bb_label = "OVERBOUGHT"
    elif bb_pct_b <= 0.2: bb_label = "OVERSOLD"
    else: bb_label = "NEUTRAL"

    # ATR
    if atr_pct < 1: atr_label = "LOW"
    elif atr_pct < 3: atr_label = "MEDIUM"
    else: atr_label = "HIGH"

    supports, resistances = _find_swing_levels(df)

    return {
        "rsi14": float(rsi14) if pd.notna(rsi14) else None,
        "rsi_label": rsi_label,
        "macd_hist": float(macd_hist) if pd.notna(macd_hist) else None,
        "macd_label": macd_label,
        "bb_pct_b": float(bb_pct_b) if pd.notna(bb_pct_b) else None,
        "bb_label": bb_label,
        "atr": float(atr14) if pd.notna(atr14) else None,
        "atr_pct": float(atr_pct),
        "atr_label": atr_label,
        "sma20": float(sma20) if pd.notna(sma20) else None,
        "ema20": float(ema20) if pd.notna(ema20) else None,
        "supports": supports,
        "resistances": resistances,
        "harga": float(last),
    }


# ============================================================
# RISK / REWARD
# ============================================================
def hitung_risk_reward(kode, indikator=None):
    if indikator is None:
        indikator = hitung_indikator_teknikal(kode)
    if not indikator:
        return None

    entry = indikator["harga"]
    atr = indikator["atr"] or (entry * 0.02)
    supports = indikator.get("supports", [])
    resistances = indikator.get("resistances", [])

    # Stop loss: di bawah support terdekat, atau 2x ATR
    if supports:
        sl = supports[0][0] * 0.99
    else:
        sl = entry - 2 * atr

    risk_per_share = entry - sl
    if risk_per_share <= 0:
        risk_per_share = 2 * atr
        sl = entry - risk_per_share

    # Target: pakai resistance, atau 1:2 R:R
    targets = []
    for r, strength in resistances[:3]:
        if r > entry:
            gain_pct = (r / entry - 1) * 100
            # Probabilitas sederhana berdasarkan jarak
            if gain_pct < 3: prob = 75
            elif gain_pct < 8: prob = 55
            else: prob = 35
            targets.append({
                "harga": r,
                "prob": prob,
                "gain_pct": gain_pct,
                "strength": strength,
            })

    # Kalau tidak ada resistance, pakai R:R
    if not targets:
        for rr, prob in [(1.5, 70), (2.0, 55), (3.0, 40)]:
            t = entry + risk_per_share * rr
            targets.append({
                "harga": round(t),
                "prob": prob,
                "gain_pct": (t / entry - 1) * 100,
                "strength": "MODERATE",
            })

    # Risk/Reward ratio berdasarkan target pertama
    reward = targets[0]["harga"] - entry if targets else risk_per_share
    rr_ratio = reward / risk_per_share if risk_per_share > 0 else 0

    # Verdict
    if rr_ratio >= 2: setup = "GOOD SETUP"
    elif rr_ratio >= 1.5: setup = "FAIR SETUP"
    elif rr_ratio >= 1: setup = "POOR SETUP"
    else: setup = "BAD SETUP"

    # Lot disarankan (asumsi modal 10 juta, risiko 1% per trade = 100k)
    modal = 10_000_000
    risk_per_trade = modal * 0.01
    lot = int(risk_per_trade / (risk_per_share * 100)) if risk_per_share > 0 else 0
    if lot < 1: lot = 1

    return {
        "entry": entry,
        "stop_loss": round(sl),
        "risk_per_share": risk_per_share,
        "rr_ratio": rr_ratio,
        "setup": setup,
        "targets": targets,
        "lot_disarankan": lot,
        "investasi": lot * 100 * entry,
    }


# ============================================================
# SINYAL TRADING
# ============================================================
def hitung_sinyal_trading(kode):
    df = load_ohlcv(kode)
    if df is None or len(df) < 60:
        return None

    close = df["Close"]
    last = close.iloc[-1]

    # --- Hitung indikator ---
    rsi14 = _rsi(close, 14).iloc[-1]
    macd_line, signal_line, macd_hist = _macd(close)
    macd_h = macd_hist.iloc[-1]
    macd_h_prev = macd_hist.iloc[-2] if len(macd_hist) > 1 else 0

    sma20 = close.rolling(20).mean().iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1]

    # Volume
    vol = df["Volume"]
    vol_ma20 = vol.rolling(20).mean().iloc[-1]
    vol_ratio = vol.iloc[-1] / vol_ma20 if vol_ma20 > 0 else 1

    # OBV
    direction = np.sign(close.diff()).fillna(0)
    obv = (direction * vol).cumsum()
    obv_ma = obv.rolling(20).mean()
    obv_above = obv.iloc[-1] > obv_ma.iloc[-1]

    # VWAP (approx 20 hari)
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vwap = (typical * vol).rolling(20).sum() / vol.rolling(20).sum()
    vwap_last = vwap.iloc[-1]
    above_vwap = last > vwap_last if pd.notna(vwap_last) else False

    # --- Skor per sinyal ---
    score = 0
    max_score = 0
    factors = []

    # 1. RSI (weight 20)
    max_score += 20
    if pd.notna(rsi14):
        if rsi14 < 30:
            score += 20
            factors.append(("RSI oversold", "BULLISH"))
        elif rsi14 < 45:
            score += 12
            factors.append(("RSI rendah", "BULLISH"))
        elif rsi14 > 70:
            score -= 20
            factors.append(("RSI overbought", "BEARISH"))
        elif rsi14 > 55:
            score -= 5
            factors.append(("RSI tinggi", "NEUTRAL"))

    # 2. MACD (weight 25)
    max_score += 25
    if pd.notna(macd_h):
        if macd_h > 0 and macd_h > macd_h_prev:
            score += 25
            factors.append(("MACD bullish naik", "BULLISH"))
        elif macd_h > 0:
            score += 10
            factors.append(("MACD bullish", "BULLISH"))
        elif macd_h < 0 and macd_h < macd_h_prev:
            score -= 25
            factors.append(("MACD bearish turun", "BEARISH"))
        elif macd_h < 0:
            score -= 10
            factors.append(("MACD bearish", "BEARISH"))

    # 3. Trend MA (weight 20)
    max_score += 20
    if pd.notna(sma20) and pd.notna(sma50):
        if last > sma20 > sma50:
            score += 20
            factors.append(("Uptrend (Px>SMA20>SMA50)", "BULLISH"))
        elif last < sma20 < sma50:
            score -= 20
            factors.append(("Downtrend (Px<SMA20<SMA50)", "BEARISH"))
        elif last > sma20:
            score += 8
            factors.append(("Px di atas SMA20", "BULLISH"))
        elif last < sma20:
            score -= 8
            factors.append(("Px di bawah SMA20", "BEARISH"))

    # 4. OBV (weight 15)
    max_score += 15
    if obv_above:
        score += 15
        factors.append(("OBV bullish", "BULLISH"))
    else:
        score -= 15
        factors.append(("OBV bearish", "BEARISH"))

    # 5. VWAP (weight 10)
    max_score += 10
    if above_vwap:
        score += 10
        factors.append(("Above VWAP", "BULLISH"))
    else:
        score -= 10
        factors.append(("Below VWAP", "BEARISH"))

    # 6. Volume (weight 10)
    max_score += 10
    if vol_ratio > 1.5:
        factors.append(("Volume tinggi", "NEUTRAL"))
    elif vol_ratio < 0.7:
        factors.append(("Volume rendah", "NEUTRAL"))

    # --- Konversi ke sinyal ---
    normalized = score / max_score * 100 if max_score > 0 else 0

    if normalized >= 30:
        sinyal = "BUY"
        confidence = min(50 + normalized / 2, 95)
    elif normalized <= -30:
        sinyal = "SELL"
        confidence = min(50 + abs(normalized) / 2, 95)
    else:
        sinyal = "HOLD"
        confidence = 50 + abs(normalized) / 3

    confidence = round(confidence)

    # --- Multi-timeframe ---
    def _trend(series, n_short=5, n_long=20):
        if len(series) < n_long + 5: return "SIDEWAYS"
        s = series.rolling(n_short).mean().iloc[-1]
        l = series.rolling(n_long).mean().iloc[-1]
        diff = (s / l - 1) * 100
        if diff > 1: return "BULLISH"
        if diff < -1: return "BEARISH"
        return "SIDEWAYS"

    trend_short = _trend(close.tail(10))
    trend_mid = _trend(close.tail(30))
    trend_long = _trend(close.tail(100))

    # Description
    desc = f"{sinyal} dengan confidence {confidence}%."
    if sinyal == "BUY":
        desc += " Sinyal bullish dari beberapa indikator."
    elif sinyal == "SELL":
        desc += " Tekanan jual terdeteksi."
    else:
        desc += " Pasar belum menunjukkan arah jelas."

    return {
        "sinyal": sinyal,
        "confidence": confidence,
        "deskripsi": desc,
        "factors": factors,
        "trend_short": trend_short,
        "trend_mid": trend_mid,
        "trend_long": trend_long,
        "harga": float(last),
    }


if __name__ == "__main__":
    # Test
    for kode in ["BBCA", "BBRI", "TLKM"]:
        print(f"\n=== {kode} ===")
        ind = hitung_indikator_teknikal(kode)
        rr = hitung_risk_reward(kode)
        sig = hitung_sinyal_trading(kode)
        if ind:
            print(f"  RSI: {ind['rsi14']:.1f} ({ind['rsi_label']})")
            print(f"  MACD: {ind['macd_hist']:.2f} ({ind['macd_label']})")
            print(f"  ATR: {ind['atr_pct']:.2f}% ({ind['atr_label']})")
            print(f"  Supports: {ind['supports']}")
            print(f"  Resistances: {ind['resistances']}")
        if rr:
            print(f"  R:R: 1:{rr['rr_ratio']:.2f} ({rr['setup']})")
        if sig:
            print(f"  Sinyal: {sig['sinyal']} ({sig['confidence']}%)")