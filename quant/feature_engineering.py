"""
Feature engineering. SEMUA fitur hanya menggunakan data sampai dan termasuk
hari T. Signal untuk eksekusi di T+1 diambil dari baris T.
"""

import numpy as np
import pandas as pd


# ============================================================
# UTIL
# ============================================================
def _g(df, col, func, window, min_periods=None, name=None):
    """Helper: apply rolling per kode."""
    if min_periods is None:
        min_periods = max(2, window // 2)
    result = (df.groupby("kode")[col]
                .transform(lambda s: s.rolling(window, min_periods=min_periods)
                                     .apply(func, raw=True)
                                     if callable(func) else
                                     getattr(s.rolling(window, min_periods=min_periods), func)()))
    if name:
        df[name] = result
    return result


# ============================================================
# A. PRICE ACTION
# ============================================================
def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Multi-horizon returns. Semua backward-looking."""
    for n in [1, 2, 3, 5, 10, 20]:
        df[f"ret_{n}d"] = df.groupby("kode")["close"].pct_change(n)
    return df


def add_price_action(df: pd.DataFrame) -> pd.DataFrame:
    # Close Location Value: (close - low) / (high - low)
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    df["clv"] = (df["close"] - df["low"]) / rng

    # Wick ratios
    df["upper_wick"] = (df["high"] - df[["open", "close"]].max(axis=1)) / rng
    df["lower_wick"] = (df[["open", "close"]].min(axis=1) - df["low"]) / rng

    # Consecutive green/red
    green = (df["close"] > df["open"]).astype(int)
    red = (df["close"] < df["open"]).astype(int)

    def consecutive(s):
        return s.groupby((s != s.shift()).cumsum()).cumsum()

    df["consec_green"] = green.groupby(df["kode"]).transform(consecutive)
    df["consec_red"] = red.groupby(df["kode"]).transform(consecutive)

    # Distance from rolling high/low
    for n in [10, 20, 50]:
        roll_high = df.groupby("kode")["high"].transform(
            lambda s: s.rolling(n, min_periods=2).max())
        roll_low = df.groupby("kode")["low"].transform(
            lambda s: s.rolling(n, min_periods=2).min())
        df[f"dist_high_{n}"] = (df["close"] - roll_high) / roll_high
        df[f"dist_low_{n}"] = (df["close"] - roll_low) / roll_low

    # Higher low / lower high (3-bar pattern)
    df["higher_low_3"] = (
        (df["low"] > df.groupby("kode")["low"].shift(1)) &
        (df.groupby("kode")["low"].shift(1) > df.groupby("kode")["low"].shift(2))
    ).astype(int)

    df["lower_high_3"] = (
        (df["high"] < df.groupby("kode")["high"].shift(1)) &
        (df.groupby("kode")["high"].shift(1) < df.groupby("kode")["high"].shift(2))
    ).astype(int)

    return df


# ============================================================
# B. VOLUME
# ============================================================
def add_volume(df: pd.DataFrame) -> pd.DataFrame:
    for n in [5, 10, 20, 50]:
        ma = df.groupby("kode")["volume"].transform(
            lambda s: s.rolling(n, min_periods=max(2, n // 2)).mean())
        df[f"vol_ma{n}"] = ma
        df[f"vol_ratio_{n}"] = df["volume"] / ma.replace(0, np.nan)

    # Volume acceleration
    df["vol_accel_5"] = df["vol_ratio_5"] - df.groupby("kode")["vol_ratio_5"].shift(1)

    # Volume z-score (20-day)
    def zscore(s, w=20):
        return (s - s.rolling(w, min_periods=5).mean()) / s.rolling(w, min_periods=5).std()
    df["vol_z_20"] = df.groupby("kode")["volume"].transform(zscore)

    # Value acceleration
    val_ma20 = df.groupby("kode")["value"].transform(
        lambda s: s.rolling(20, min_periods=5).mean())
    df["value_ratio_20"] = df["value"] / val_ma20.replace(0, np.nan)

    # Frequency acceleration
    freq_ma20 = df.groupby("kode")["frequency"].transform(
        lambda s: s.rolling(20, min_periods=5).mean())
    df["freq_ratio_20"] = df["frequency"] / freq_ma20.replace(0, np.nan)

    # Volume-price divergence (volume naik, harga turun)
    df["vol_up_price_down"] = (
        (df["vol_ratio_20"] > 1.5) & (df["ret_1d"] < 0)
    ).astype(int)

    # High volume, flat price (potensi akumulasi)
    df["vol_high_price_flat"] = (
        (df["vol_ratio_20"] > 2.0) & (df["ret_1d"].abs() < 0.01)
    ).astype(int)

    # High volume, close near high
    df["vol_high_close_high"] = (
        (df["vol_ratio_20"] > 1.5) & (df["clv"] > 0.7)
    ).astype(int)

    return df


# ============================================================
# C. VOLATILITAS
# ============================================================
def add_volatility(df: pd.DataFrame) -> pd.DataFrame:
    # True Range
    prev_close = df.groupby("kode")["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["tr"] = tr

    # ATR
    for n in [5, 10, 14, 20]:
        atr = df.groupby("kode")["tr"].transform(
            lambda s: s.rolling(n, min_periods=2).mean())
        df[f"atr_{n}"] = atr
        df[f"atr_{n}_pct"] = atr / df["close"].replace(0, np.nan)

    # Historical volatility (std of log returns)
    log_ret = np.log(df["close"] / df.groupby("kode")["close"].shift(1))
    df["log_ret"] = log_ret
    for n in [10, 20]:
        hv = df.groupby("kode")["log_ret"].transform(
            lambda s: s.rolling(n, min_periods=5).std() * np.sqrt(252))
        df[f"hv_{n}"] = hv

    # Bollinger Band width
    ma20 = df.groupby("kode")["close"].transform(
        lambda s: s.rolling(20, min_periods=5).mean())
    std20 = df.groupby("kode")["close"].transform(
        lambda s: s.rolling(20, min_periods=5).std())
    df["bb_upper"] = ma20 + 2 * std20
    df["bb_lower"] = ma20 - 2 * std20
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / ma20.replace(0, np.nan)
    df["bb_pos"] = (df["close"] - df["bb_lower"]) / (
        df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)

    # Bollinger squeeze: BB width di percentile rendah 20 hari
    df["bb_width_pct_rank_60"] = df.groupby("kode")["bb_width"].transform(
        lambda s: s.rolling(60, min_periods=20).rank(pct=True))

    # Volatility percentile
    df["atr_pct_rank_60"] = df.groupby("kode")["atr_14_pct"].transform(
        lambda s: s.rolling(60, min_periods=20).rank(pct=True))

    # NR4 / NR7
    rng = df["high"] - df["low"]
    df["nr4"] = (rng == df.groupby("kode")["high"].transform(
        lambda s: s.rolling(4, min_periods=4).apply(
            lambda x: x.iloc[-1] == min(x), raw=False)).astype(bool)).astype(int)
    # Cara lebih sederhana:
    rng_rank_4 = df.groupby("kode").apply(
        lambda g: (g["high"] - g["low"]).rolling(4, min_periods=4).apply(
            lambda x: x.iloc[-1] == x.min(), raw=False)
    ).reset_index(level=0, drop=True)
    df["nr4"] = rng_rank_4.reindex(df.index).fillna(0).astype(int)

    rng_rank_7 = df.groupby("kode").apply(
        lambda g: (g["high"] - g["low"]).rolling(7, min_periods=7).apply(
            lambda x: x.iloc[-1] == x.min(), raw=False)
    ).reset_index(level=0, drop=True)
    df["nr7"] = rng_rank_7.reindex(df.index).fillna(0).astype(int)

    return df


# ============================================================
# D. INDIKATOR TEKNIKAL
# ============================================================
def _rsi(series, n):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(n, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).rolling(n, min_periods=n).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # SMA / EMA
    for n in [5, 10, 20, 50, 100, 200]:
        df[f"sma_{n}"] = df.groupby("kode")["close"].transform(
            lambda s: s.rolling(n, min_periods=max(2, n // 2)).mean())
        df[f"ema_{n}"] = df.groupby("kode")["close"].transform(
            lambda s: s.ewm(span=n, adjust=False, min_periods=max(2, n // 2)).mean())

    # Price vs MA
    for n in [20, 50, 200]:
        df[f"px_vs_sma{n}"] = (df["close"] - df[f"sma_{n}"]) / df[f"sma_{n}"]

    # MA cross state
    df["ma20_gt_ma50"] = (df["sma_20"] > df["sma_50"]).astype(int)
    df["ma50_gt_ma200"] = (df["sma_50"] > df["sma_200"]).astype(int)

    # RSI
    for n in [7, 14, 21]:
        df[f"rsi_{n}"] = df.groupby("kode")["close"].transform(lambda s: _rsi(s, n))

    # MACD (12, 26, 9)
    ema12 = df.groupby("kode")["close"].transform(
        lambda s: s.ewm(span=12, adjust=False).mean())
    ema26 = df.groupby("kode")["close"].transform(
        lambda s: s.ewm(span=26, adjust=False).mean())
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df.groupby("kode")["macd"].transform(
        lambda s: s.ewm(span=9, adjust=False).mean())
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["macd_hist_accel"] = df.groupby("kode")["macd_hist"].diff()

    # Stochastic
    low14 = df.groupby("kode")["low"].transform(
        lambda s: s.rolling(14, min_periods=5).min())
    high14 = df.groupby("kode")["high"].transform(
        lambda s: s.rolling(14, min_periods=5).max())
    df["stoch_k"] = 100 * (df["close"] - low14) / (high14 - low14).replace(0, np.nan)
    df["stoch_d"] = df.groupby("kode")["stoch_k"].transform(
        lambda s: s.rolling(3, min_periods=2).mean())

    # ADX (14)
    up_move = df.groupby("kode")["high"].diff()
    down_move = -df.groupby("kode")["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    df["_plus_dm"] = plus_dm
    df["_minus_dm"] = minus_dm

    atr14 = df.groupby("kode")["tr"].transform(
        lambda s: s.rolling(14, min_periods=5).mean())

    plus_di = 100 * df.groupby("kode")["_plus_dm"].transform(
        lambda s: s.rolling(14, min_periods=5).mean()) / atr14.replace(0, np.nan)
    minus_di = 100 * df.groupby("kode")["_minus_dm"].transform(
        lambda s: s.rolling(14, min_periods=5).mean()) / atr14.replace(0, np.nan)
    df["plus_di_14"] = plus_di
    df["minus_di_14"] = minus_di
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["adx_14"] = dx.groupby(df["kode"]).transform(
        lambda s: s.rolling(14, min_periods=5).mean())

    df = df.drop(columns=["_plus_dm", "_minus_dm"])

    # OBV
    direction = np.sign(df["ret_1d"]).fillna(0)
    df["obv"] = (direction * df["volume"]).groupby(df["kode"]).cumsum()

    # Chaikin Money Flow (20)
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (
        df["high"] - df["low"]).replace(0, np.nan)
    mfv = mfm * df["volume"]
    df["cmf_20"] = (mfv.groupby(df["kode"]).transform(
        lambda s: s.rolling(20, min_periods=10).sum()) /
        df.groupby("kode")["volume"].transform(
        lambda s: s.rolling(20, min_periods=10).sum()).replace(0, np.nan))

    # MFI (14)
    typical = (df["high"] + df["low"] + df["close"]) / 3
    raw_mf = typical * df["volume"]
    pos_mf = raw_mf.where(typical > typical.groupby(df["kode"]).shift(1), 0)
    neg_mf = raw_mf.where(typical < typical.groupby(df["kode"]).shift(1), 0)
    pos_sum = pos_mf.groupby(df["kode"]).transform(
        lambda s: s.rolling(14, min_periods=5).sum())
    neg_sum = neg_mf.groupby(df["kode"]).transform(
        lambda s: s.rolling(14, min_periods=5).sum())
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    df["mfi_14"] = 100 - (100 / (1 + mfr))

    # Rate of Change
    for n in [5, 10, 20]:
        df[f"roc_{n}"] = df.groupby("kode")["close"].pct_change(n)

    # Donchian Channel
    df["donchian_high_20"] = df.groupby("kode")["high"].transform(
        lambda s: s.rolling(20, min_periods=5).max())
    df["donchian_low_20"] = df.groupby("kode")["low"].transform(
        lambda s: s.rolling(20, min_periods=5).min())
    df["donchian_pos"] = (
        (df["close"] - df["donchian_low_20"]) /
        (df["donchian_high_20"] - df["donchian_low_20"]).replace(0, np.nan))

    # Supertrend (10, 3) — versi sederhana
    hl2 = (df["high"] + df["low"]) / 2
    atr10 = df.groupby("kode")["tr"].transform(
        lambda s: s.rolling(10, min_periods=3).mean())
    upper = hl2 + 3 * atr10
    lower = hl2 - 3 * atr10
    df["supertrend_upper"] = upper
    df["supertrend_lower"] = lower

    return df


# ============================================================
# E. AKUMULASI / DISTRIBUSI
# ============================================================
def add_accumulation(df: pd.DataFrame) -> pd.DataFrame:
    # OBV naik saat harga sideways
    obv_ma10 = df.groupby("kode")["obv"].transform(
        lambda s: s.rolling(10, min_periods=5).mean())
    df["obv_above_ma10"] = (df["obv"] > obv_ma10).astype(int)

    # A/D Line
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (
        df["high"] - df["low"]).replace(0, np.nan)
    df["ad_line"] = (mfm * df["volume"]).groupby(df["kode"]).cumsum()
    df["ad_slope_10"] = df.groupby("kode")["ad_line"].diff(10)

    # CMF positif ketika harga konsolidasi
    df["cmf_pos_while_flat"] = (
        (df["cmf_20"] > 0.05) & (df["ret_5d"].abs() < 0.03)
    ).astype(int)

    # Net foreign buy berulang
    if "foreign_net" in df.columns:
        fn_pos = (df["foreign_net"] > 0).astype(int)
        df["foreign_buy_streak_5"] = fn_pos.groupby(df["kode"]).transform(
            lambda s: s.rolling(5, min_periods=3).sum())

    return df


# ============================================================
# PIPELINE LENGKAP
# ============================================================
def build_features(df: pd.DataFrame) -> pd.DataFrame:
    print("Membangun fitur...")
    print("  → price action")
    df = add_returns(df)
    df = add_price_action(df)
    print("  → volume")
    df = add_volume(df)
    print("  → volatility")
    df = add_volatility(df)
    print("  → indicators")
    df = add_indicators(df)
    print("  → accumulation")
    df = add_accumulation(df)

    # Defragment: gabung semua blok memori jadi satu
    df = df.copy()

    print(f"  ✅ selesai. Total kolom: {df.shape[1]}")
    return df


if __name__ == "__main__":
    from .data_loader import load_panel_from_gabungan
    from .data_cleaner import clean_panel

    panel = load_panel_from_gabungan()
    panel = clean_panel(panel)
    feat = build_features(panel)
    print(f"\nHasil: {feat.shape}")
    print(f"Kolom: {list(feat.columns)}")