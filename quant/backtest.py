"""
Test suite untuk views/smart_money.py

Jalankan:
    python test_smart_money.py

Atau dengan pytest:
    pytest test_smart_money.py -v

Test ini TIDAK butuh parquet asli — semua pakai data sintetis.
"""
import sys
import os
import unittest
import numpy as np
import pandas as pd


# ============================================================
# COPY FUNGSI DARI smart_money.py (untuk testable tanpa streamlit)
# ============================================================
def classify_verdict(close_pct, cmf, close_gt_open):
    """Copy dari smart_money.py — logika klasifikasi kualitas bar."""
    if pd.isna(close_pct) or pd.isna(cmf):
        return "—"
    if not close_gt_open:
        if close_pct < 0.3 and cmf < 0:
            return "🔴 DISTRIBUSI"
        return "🟠 BEARISH"
    if close_pct >= 0.7 and cmf >= 0.1:
        return "🟢🟢 AKUMULASI KUAT"
    elif close_pct >= 0.6 and cmf > 0:
        return "🟢 AKUMULASI"
    elif close_pct >= 0.5:
        return "🟡 CAMPURAN"
    elif close_pct >= 0.3:
        return "🟠 BUYER LEMAH"
    else:
        return "🔴 DISTRIBUSI TERSAMAR"


def calc_close_pct(high, low, close):
    """CLV = (close - low) / (high - low)."""
    rng = high - low
    if rng == 0:
        return np.nan
    return (close - low) / rng


def calc_cmf(df, period=20):
    """Chaikin Money Flow."""
    rng = (df["High"] - df["Low"]).replace(0, np.nan)
    mfm = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / rng
    mfv = mfm * df["Volume"]
    cmf = mfv.rolling(period).sum() / df["Volume"].rolling(period).sum()
    return cmf


def calc_mfi(df, period=14):
    """Money Flow Index."""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    mf = tp * df["Volume"]
    pos_mf = mf.where(tp > tp.shift(1), 0)
    neg_mf = mf.where(tp < tp.shift(1), 0)
    mfr = pos_mf.rolling(period).sum() / neg_mf.rolling(period).sum()
    return 100 - (100 / (1 + mfr))


def filter_accumulation(df_today, vol_min=2.0, vol_max=50.0,
                        close_pct_min=0.6, cmf_min=0.0):
    """Filter akumulasi — sama dengan di smart_money.py."""
    return df_today[
        (df_today["Vol_Ratio"] > vol_min) &
        (df_today["Vol_Ratio"] < vol_max) &
        (df_today["Close"] > df_today["Open"]) &
        (df_today["Close_Pct"] > close_pct_min) &
        (df_today["CMF_20"] > cmf_min) &
        (df_today["Close"] > 0) &
        (df_today["Volume"] > 0)
    ].copy()


def filter_distribution(df_today, vol_min=2.0, vol_max=50.0,
                        close_pct_max=0.3):
    """Filter distribusi tersamar — sama dengan di smart_money.py."""
    return df_today[
        (df_today["Vol_Ratio"] > vol_min) &
        (df_today["Vol_Ratio"] < vol_max) &
        (df_today["Close_Pct"] < close_pct_max) &
        (df_today["Close"] > 0) &
        (df_today["Volume"] > 0)
    ].copy()


# ============================================================
# TEST 1: CLV CALCULATION
# ============================================================
class TestCLV(unittest.TestCase):
    """Test Close Location Value."""

    def test_close_at_high(self):
        """Close = high → CLV = 1.0 (buyer dominan penuh)."""
        self.assertAlmostEqual(calc_close_pct(120, 100, 120), 1.0)

    def test_close_at_low(self):
        """Close = low → CLV = 0.0 (seller dominan penuh)."""
        self.assertAlmostEqual(calc_close_pct(120, 100, 100), 0.0)

    def test_close_at_mid(self):
        """Close = midpoint → CLV = 0.5."""
        self.assertAlmostEqual(calc_close_pct(120, 100, 110), 0.5)

    def test_close_at_70pct(self):
        """Close di 70% range → CLV = 0.7 (batas akumulasi kuat)."""
        self.assertAlmostEqual(calc_close_pct(120, 100, 114), 0.7)

    def test_close_at_30pct(self):
        """Close di 30% range → CLV = 0.3 (batas buyer lemah)."""
        self.assertAlmostEqual(calc_close_pct(120, 100, 106), 0.3)

    def test_zero_range(self):
        """High = low (doji sempurna) → NaN (hindari div by zero)."""
        self.assertTrue(pd.isna(calc_close_pct(100, 100, 100)))


# ============================================================
# TEST 2: VERDICT CLASSIFICATION
# ============================================================
class TestClassifyVerdict(unittest.TestCase):
    """Test klasifikasi verdict berdasarkan CLV + CMF + candle."""

    # --- Kasus BULLISH (close > open) ---
    def test_strong_accumulation(self):
        """CLV 80% + CMF 0.15 + bullish → AKUMULASI KUAT."""
        self.assertEqual(
            classify_verdict(0.80, 0.15, True),
            "🟢🟢 AKUMULASI KUAT"
        )

    def test_accumulation(self):
        """CLV 65% + CMF 0.05 + bullish → AKUMULASI."""
        self.assertEqual(
            classify_verdict(0.65, 0.05, True),
            "🟢 AKUMULASI"
        )

    def test_mixed(self):
        """CLV 55% + CMF 0.02 + bullish → CAMPURAN."""
        self.assertEqual(
            classify_verdict(0.55, 0.02, True),
            "🟡 CAMPURAN"
        )

    def test_weak_buyer(self):
        """CLV 40% + CMF 0.01 + bullish → BUYER LEMAH."""
        self.assertEqual(
            classify_verdict(0.40, 0.01, True),
            "🟠 BUYER LEMAH"
        )

    def test_hidden_distribution(self):
        """Candle hijau tapi CLV 20% + CMF -0.05 → DISTRIBUSI TERSAMAR."""
        self.assertEqual(
            classify_verdict(0.20, -0.05, True),
            "🔴 DISTRIBUSI TERSAMAR"
        )

    # --- Kasus BEARISH (close < open) ---
    def test_distribution_bearish(self):
        """Candle merah + CLV 20% + CMF -0.05 → DISTRIBUSI."""
        self.assertEqual(
            classify_verdict(0.20, -0.05, False),
            "🔴 DISTRIBUSI"
        )

    def test_bearish_but_not_distribution(self):
        """Candle merah tapi CLV 40% + CMF positif → BEARISH (bukan distribusi)."""
        self.assertEqual(
            classify_verdict(0.40, 0.02, False),
            "🟠 BEARISH"
        )

    # --- Edge case ---
    def test_nan_input(self):
        """NaN input → '—'."""
        self.assertEqual(classify_verdict(np.nan, 0.1, True), "—")
        self.assertEqual(classify_verdict(0.8, np.nan, True), "—")

    def test_boundary_70_0_1(self):
        """CLV = 0.7 tepat + CMF = 0.1 tepat → AKUMULASI KUAT (batas inklusif)."""
        self.assertEqual(
            classify_verdict(0.7, 0.1, True),
            "🟢🟢 AKUMULASI KUAT"
        )


# ============================================================
# TEST 3: CMF CALCULATION
# ============================================================
class TestCMF(unittest.TestCase):
    """Test Chaikin Money Flow."""

    def test_cmf_all_buying(self):
        """Semua hari close di HIGH → CMF = 1.0 (buying penuh)."""
        df = pd.DataFrame({
            "High": [110] * 25,
            "Low": [100] * 25,
            "Close": [110] * 25,  # close = high
            "Volume": [1000] * 25,
        })
        cmf = calc_cmf(df, 20)
        self.assertAlmostEqual(cmf.iloc[-1], 1.0, places=4)

    def test_cmf_all_selling(self):
        """Semua hari close di LOW → CMF = -1.0 (selling penuh)."""
        df = pd.DataFrame({
            "High": [110] * 25,
            "Low": [100] * 25,
            "Close": [100] * 25,  # close = low
            "Volume": [1000] * 25,
        })
        cmf = calc_cmf(df, 20)
        self.assertAlmostEqual(cmf.iloc[-1], -1.0, places=4)

    def test_cmf_neutral(self):
        """Close di midpoint → CMF = 0 (neutral)."""
        df = pd.DataFrame({
            "High": [110] * 25,
            "Low": [100] * 25,
            "Close": [105] * 25,  # midpoint
            "Volume": [1000] * 25,
        })
        cmf = calc_cmf(df, 20)
        self.assertAlmostEqual(cmf.iloc[-1], 0.0, places=4)

    def test_cmf_zero_range_handled(self):
        """High = low (doji) → NaN tidak crash, CMF tetap bisa dihitung."""
        df = pd.DataFrame({
            "High": [110, 110, 100, 110] * 10,
            "Low": [100, 100, 100, 100] * 10,  # baris 3 doji
            "Close": [110, 105, 100, 110] * 10,
            "Volume": [1000] * 40,
        })
        cmf = calc_cmf(df, 20)
        self.assertFalse(cmf.iloc[-1] is None)


# ============================================================
# TEST 4: MFI CALCULATION
# ============================================================
class TestMFI(unittest.TestCase):
    """Test Money Flow Index."""

    def test_mfi_all_up(self):
        """Harga terus naik → MFI = 100 (overbought ekstrem)."""
        n = 20
        df = pd.DataFrame({
            "High": np.arange(100, 100 + n),
            "Low": np.arange(99, 99 + n),
            "Close": np.arange(100, 100 + n),
            "Volume": [1000] * n,
        })
        mfi = calc_mfi(df, 14)
        self.assertAlmostEqual(mfi.iloc[-1], 100.0, places=2)

    def test_mfi_all_down(self):
        """Harga terus turun → MFI = 0 (oversold ekstrem)."""
        n = 20
        df = pd.DataFrame({
            "High": np.arange(120, 120 - n, -1),
            "Low": np.arange(119, 119 - n, -1),
            "Close": np.arange(119, 119 - n, -1),
            "Volume": [1000] * n,
        })
        mfi = calc_mfi(df, 14)
        self.assertAlmostEqual(mfi.iloc[-1], 0.0, places=2)


# ============================================================
# TEST 5: FILTER AKUMULASI (INTEGRASI)
# ============================================================
class TestAccumulationFilter(unittest.TestCase):
    """Test filter akumulasi pada df_today sintetis."""

    def _make_today(self, rows):
        """Helper: bikin df_today dari list of dict."""
        return pd.DataFrame(rows)

    def test_strong_accumulation_passes(self):
        """Saham dengan semua syarat akumulasi → lolos filter."""
        df = self._make_today([{
            "Kode": "BBCA",
            "Open": 9000, "High": 9200, "Low": 9000, "Close": 9150,
            "Volume": 5_000_000,
            "Vol_Ratio": 2.5,
            "Close_Pct": 0.75,  # close 75% range
            "CMF_20": 0.15,
        }])
        result = filter_accumulation(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Kode"], "BBCA")

    def test_hidden_distribution_rejected(self):
        """Volume spike + candle hijau TAPI close di low → ditolak."""
        df = self._make_today([{
            "Kode": "TRAP",
            "Open": 100, "High": 130, "Low": 99, "Close": 105,  # hijau tapi dekat low
            "Volume": 10_000_000,
            "Vol_Ratio": 5.0,
            "Close_Pct": 0.19,  # close 19% range
            "CMF_20": -0.10,
        }])
        result = filter_accumulation(df)
        self.assertEqual(len(result), 0, "Distribusi tersamar harus ditolak")

    def test_low_volume_rejected(self):
        """Close bagus tapi volume normal → ditolak."""
        df = self._make_today([{
            "Kode": "QUIET",
            "Open": 100, "High": 105, "Low": 99, "Close": 104,
            "Volume": 1_000_000,
            "Vol_Ratio": 1.2,  # di bawah 2x
            "Close_Pct": 0.83,
            "CMF_20": 0.10,
        }])
        result = filter_accumulation(df)
        self.assertEqual(len(result), 0)

    def test_negative_cmf_rejected(self):
        """Close bagus tapi CMF negatif (20 hari distribusi) → ditolak."""
        df = self._make_today([{
            "Kode": "WEAK",
            "Open": 100, "High": 110, "Low": 100, "Close": 108,
            "Volume": 5_000_000,
            "Vol_Ratio": 3.0,
            "Close_Pct": 0.80,
            "CMF_20": -0.05,  # negatif!
        }])
        result = filter_accumulation(df)
        self.assertEqual(len(result), 0)

    def test_red_candle_rejected(self):
        """Volume besar tapi close < open → ditolak."""
        df = self._make_today([{
            "Kode": "RED",
            "Open": 110, "High": 115, "Low": 100, "Close": 105,  # merah
            "Volume": 5_000_000,
            "Vol_Ratio": 3.0,
            "Close_Pct": 0.33,  # di bawah 60%
            "CMF_20": 0.05,
        }])
        result = filter_accumulation(df)
        self.assertEqual(len(result), 0)

    def test_outlier_volume_rejected(self):
        """Volume ratio >50x (mungkin data error) → ditolak."""
        df = self._make_today([{
            "Kode": "OUTLIER",
            "Open": 100, "High": 110, "Low": 100, "Close": 109,
            "Volume": 100_000_000,
            "Vol_Ratio": 80.0,  # di atas 50x → outlier
            "Close_Pct": 0.90,
            "CMF_20": 0.15,
        }])
        result = filter_accumulation(df)
        self.assertEqual(len(result), 0)

    def test_mixed_batch(self):
        """Batch dengan 3 saham: 1 akumulasi asli + 1 distribusi + 1 normal."""
        df = self._make_today([
            {  # akumulasi asli
                "Kode": "GOOD", "Open": 100, "High": 110, "Low": 100,
                "Close": 108, "Volume": 5_000_000, "Vol_Ratio": 3.0,
                "Close_Pct": 0.80, "CMF_20": 0.15,
            },
            {  # distribusi tersamar
                "Kode": "TRAP", "Open": 100, "High": 130, "Low": 99,
                "Close": 105, "Volume": 8_000_000, "Vol_Ratio": 4.5,
                "Close_Pct": 0.20, "CMF_20": -0.10,
            },
            {  # normal (volume rata)
                "Kode": "NORMAL", "Open": 100, "High": 102, "Low": 99,
                "Close": 101, "Volume": 1_000_000, "Vol_Ratio": 1.0,
                "Close_Pct": 0.67, "CMF_20": 0.02,
            },
        ])
        result = filter_accumulation(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Kode"], "GOOD")


# ============================================================
# TEST 6: FILTER DISTRIBUSI (INTEGRASI)
# ============================================================
class TestDistributionFilter(unittest.TestCase):
    """Test filter distribusi tersamar."""

    def test_hidden_distribution_caught(self):
        """Candle hijau + volume besar + close rendah → tertangkap."""
        df = pd.DataFrame([{
            "Kode": "TRAP",
            "Open": 100, "High": 130, "Low": 99, "Close": 105,
            "Volume": 10_000_000,
            "Vol_Ratio": 5.0,
            "Close_Pct": 0.19,
            "CMF_20": -0.10,
        }])
        result = filter_distribution(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Kode"], "TRAP")

    def test_strong_close_not_distribution(self):
        """Close di 80% range bukan distribusi."""
        df = pd.DataFrame([{
            "Kode": "GOOD",
            "Open": 100, "High": 110, "Low": 100, "Close": 108,
            "Volume": 5_000_000,
            "Vol_Ratio": 3.0,
            "Close_Pct": 0.80,
            "CMF_20": 0.10,
        }])
        result = filter_distribution(df)
        self.assertEqual(len(result), 0)

    def test_no_volume_spike_not_caught(self):
        """Close rendah tapi volume normal → bukan distribusi (cuma red day biasa)."""
        df = pd.DataFrame([{
            "Kode": "WEAK",
            "Open": 100, "High": 102, "Low": 95, "Close": 96,
            "Volume": 500_000,
            "Vol_Ratio": 0.8,  # bukan spike
            "Close_Pct": 0.14,
            "CMF_20": -0.02,
        }])
        result = filter_distribution(df)
        self.assertEqual(len(result), 0)


# ============================================================
# TEST 7: INTEGRASI — END-TO-END SAMPLE
# ============================================================
class TestEndToEnd(unittest.TestCase):
    """Simulasi satu hari penuh: hitung CMF/CLV lalu filter."""

    def test_full_pipeline(self):
        """Bangun 30 bar OHLCV untuk 2 saham, hitung, filter, cek hasil."""
        np.random.seed(42)

        # Saham A: akumulasi asli (uptrend + close di atas)
        n = 30
        a_prices = np.cumsum(np.random.randn(n) * 0.5) + 100
        a_df = pd.DataFrame({
            "High": a_prices + 2,
            "Low": a_prices - 2,
            "Close": a_prices + 1.5,  # close dekat high
            "Open": a_prices - 1,
            "Volume": [1_000_000] * (n - 1) + [5_000_000],
        })

        # Saham B: distribusi (uptrend tapi hari terakhir close di low)
        b_prices = np.cumsum(np.random.randn(n) * 0.5) + 100
        b_df = pd.DataFrame({
            "High": b_prices + 2,
            "Low": b_prices - 2,
            "Close": b_prices - 1.5,  # close dekat low
            "Open": b_prices + 1,
            "Volume": [1_000_000] * (n - 1) + [8_000_000],
        })

        for name, df in [("A", a_df), ("B", b_df)]:
            df["CMF_20"] = calc_cmf(df, 20)
            df["Close_Pct"] = (df["Close"] - df["Low"]) / (df["High"] - df["Low"])
            df["Vol_Ratio"] = df["Volume"] / df["Volume"].rolling(20).mean()

        # Hari terakhir saja
        today = pd.DataFrame([
            {
                "Kode": "ACCUM",
                **a_df.iloc[-1][["Open", "High", "Low", "Close", "Volume",
                                 "Vol_Ratio", "Close_Pct", "CMF_20"]].to_dict(),
            },
            {
                "Kode": "DIST",
                **b_df.iloc[-1][["Open", "High", "Low", "Close", "Volume",
                                 "Vol_Ratio", "Close_Pct", "CMF_20"]].to_dict(),
            },
        ])

        # Filter
        accum = filter_accumulation(today)
        dist = filter_distribution(today)

        # Saham A harus muncul di akumulasi
        self.assertIn("ACCUM", accum["Kode"].values,
                      f"ACCUM tidak lolos filter akumulasi. "
                      f"CLV={a_df.iloc[-1]['Close_Pct']:.2f}, "
                      f"CMF={a_df.iloc[-1]['CMF_20']:.3f}")

        # Saham B harus muncul di distribusi
        self.assertIn("DIST", dist["Kode"].values,
                      f"DIST tidak muncul di filter distribusi. "
                      f"CLV={b_df.iloc[-1]['Close_Pct']:.2f}")


# ============================================================
# RUNNER
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("TEST SUITE: views/smart_money.py")
    print("=" * 70)
    print()

    # Jalankan semua test
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print()
    print("=" * 70)
    if result.wasSuccessful():
        print(f"✅ SEMUA TEST LULUS ({result.testsRun} test)")
    else:
        print(f"❌ ADA {len(result.failures) + len(result.errors)} TEST GAGAL")
        print(f"   Lulus: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)