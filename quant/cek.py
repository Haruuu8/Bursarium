import os
import sys
import json
import pandas as pd
import numpy as np

# Pastikan path quant terbaca
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quant.fundamental import (
    fetch_one_period, fetch_yfinance, build_one, SNAPSHOT_CANDIDATES
)

# ====================================================
# GANTI KODE SAHAM DI SINI
# (Misal: saham yang tadi EPS-nya -829,867 atau ANTM)
KODE_SAHAM = "ANTM" 
# ====================================================

print(f"=== 🔍 DEBUG EPS UNTUK SAHAM: {KODE_SAHAM} ===\n")

# 1. Cek Data Mentah dari IDX
print("1. MENGAMBIL DATA DARI IDX (Excel)...")
snap = None
for y, p in SNAPSHOT_CANDIDATES:
    d = fetch_one_period(KODE_SAHAM, y, p)
    if d and d.get("aset"):
        snap = d
        print(f"   ✅ Data ditemukan di periode: {y}-{p}")
        break

if not snap:
    print("   ❌ Data IDX tidak ditemukan di cache!")
else:
    eps_idx = snap.get("eps_basic")
    laba_idx = snap.get("laba_induk") or snap.get("laba_bersih")
    print(f"   • EPS Basic dari IDX    : {eps_idx}")
    print(f"   • Laba Bersih dari IDX  : {laba_idx}")
    print(f"   • Ekuitas dari IDX      : {snap.get('ekuitas_induk') or snap.get('ekuitas')}")

# 2. Cek Data Yahoo Finance
print("\n2. MENGAMBIL DATA DARI YAHOO FINANCE...")
yfd = fetch_yfinance(KODE_SAHAM)
harga = yfd.get("harga")
mcap = yfd.get("market_cap")
shares_yf = yfd.get("shares_outstanding")
print(f"   • Harga       : {harga}")
print(f"   • Market Cap  : {mcap}")
print(f"   • Shares YF   : {shares_yf}")

# 3. Simulasi Perhitungan Shares (Logika Baru)
print("\n3. SIMULASI PERHITUNGAN SHARES (LOGIKA BARU)...")
shares_terpilih = None

if mcap and harga and harga > 0:
    shares_terpilih = mcap / harga
    print(f"   ✅ Shares dari Market Cap : {shares_terpilih:,.0f} (Paling Akurat)")
elif eps_idx and eps_idx > 0 and laba_idx:
    laba_rp = laba_idx * 1_000_000 if abs(laba_idx) < 1_000_000_000_000 else laba_idx
    shares_terpilih = laba_rp / eps_idx
    print(f"   ✅ Shares dari IDX EPS    : {shares_terpilih:,.0f}")
else:
    shares_terpilih = shares_yf
    print(f"   ⚠️ Shares fallback YF     : {shares_terpilih}")

# 4. Build Akhir (Menggunakan fungsi build_one)
print("\n4. HASIL AKHIR PERHITUNGAN (build_one)...")
data_akhir = build_one(KODE_SAHAM)

if data_akhir:
    rk = data_akhir.get("rasio_kunci", {})
    print(f"   • EPS Akhir (Save JSON) : {rk.get('eps')}")
    print(f"   • PER Akhir (Save JSON) : {rk.get('pe')}")
    print(f"   • PBV Akhir (Save JSON) : {rk.get('pb')}")
    print(f"   • ROE Akhir (Save JSON) : {rk.get('roe')}")
else:
    print("   ❌ build_one gagal mengembalikan data.")