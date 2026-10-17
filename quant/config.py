"""
Konfigurasi global untuk sistem riset kuantitatif IDX.
Semua path relatif terhadap folder quant/.
"""

from pathlib import Path

# ============================================================
# PATH
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Sumber data mentah (dari scraper)
RAW_CSV_GABUNGAN = PROJECT_ROOT / "ohlcv_idx_2026_all.csv"
RAW_CSV_PER_SAHAM = PROJECT_ROOT / "data_ohlcv_idx"
DAFTAR_SAHAM_CSV = PROJECT_ROOT / "daftar_saham.csv"

# Data yang sudah diproses
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
PANEL_PARQUET = DATA_DIR / "panel.parquet"
FEATURES_PARQUET = DATA_DIR / "features.parquet"
EVENTS_PARQUET = DATA_DIR / "events.parquet"
IHSG_CSV = DATA_DIR / "ihsg.csv"

# Output analisis
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================
# UNIVERSE & PERIODE
# ============================================================
TAHUN = 2026
START_DATE = f"{TAHUN}-01-01"
END_DATE = None   # None = sampai data terakhir

# Filter universe minimum
MIN_HARI_TRADING = 60          # minimal 60 hari data per saham
MIN_HARGA = 50                 # rupiah, hindari saham gocap
MIN_RATA_VOLUME = 100_000      # lembar/hari, filter saham tidak likuid

# ============================================================
# DEFINISI TOP GAINER (bagian 2 ROLE.txt)
# ============================================================

# A. Daily rank-based
DAILY_RANK_TOP_PCT = [0.01, 0.03, 0.05, 0.10]

# B. Extreme return threshold (CLOSE-based)
# Yaitu: close / prev_close - 1 >= threshold
EXTREME_RETURN_THRESHOLDS = [0.05, 0.10, 0.15, 0.20]

# B2. Intraday HIGH-based (menyentuh level, bukan close)
# Yaitu: high / prev_close - 1 >= threshold
# Termasuk saham yang menyentuh +10% lalu closing merah.
# Ini definisi UTAMA untuk riset, karena lebih realistis untuk trading.
INTRADAY_HIGH_THRESHOLDS = [0.05, 0.10, 0.15, 0.20]

# C. Multi-day return
MULTIDAY_HORIZONS = [1, 3, 5, 10, 20]
MULTIDAY_THRESHOLDS = [0.10, 0.20, 0.30]

# D. Maximum Favorable Excursion
MFE_HORIZONS = [3, 5, 10, 20]
MFE_THRESHOLD = 0.10

# ============================================================
# HORIZON EVENT STUDY (bagian 3 ROLE.txt)
# ============================================================
LOOKBACK_DAYS = [1, 2, 3, 5, 10, 20]
FORWARD_DAYS = [1, 2, 3, 5, 10]

# ============================================================
# LABEL PREDIKSI (bagian 6 ROLE.txt)
# ============================================================
TARGETS = {
    "A_top5pct_besok": {"horizon": 1, "type": "rank", "threshold": 0.05},
    "B_up5pct_3d":     {"horizon": 3, "type": "return", "threshold": 0.05},
    "C_up10pct_5d":    {"horizon": 5, "type": "return", "threshold": 0.10},
    "D_up15pct_10d":   {"horizon": 10, "type": "return", "threshold": 0.15},
    "E_mfe10_sebelum_dd5": {"horizon": 10, "type": "mfe_mae",
                             "mfe": 0.10, "mae": -0.05},
}

# ============================================================
# ANTI-LEAKAGE (bagian 8 ROLE.txt)
# ============================================================
# Fitur pada baris tanggal T hanya boleh memakai data <= T-1.
# Signal di-generate pada akhir hari T untuk eksekusi di T+1.
# Konvensi: setiap fitur punya suffix _at_T artinya "dihitung dari data
# sampai dan termasuk hari T, untuk diambil keputusan di akhir T".
FEATURE_LAG = 1   # sinyal untuk eksekusi T+1 memakai fitur sampai T