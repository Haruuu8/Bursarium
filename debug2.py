from quant.parquet_loader import load_parquet_safe
import pandas as pd

df_all = load_parquet_safe()
print("=" * 60)
print("PARQUET INFO")
print("=" * 60)
print(f"Total rows  : {len(df_all):,}")
print(f"Columns     : {list(df_all.columns)}")
print(f"Sample kodes: {sorted(df_all['Kode'].unique())[:10]}")

# Filter BBCA
df_all["Kode"] = df_all["Kode"].astype(str).str.strip().str.upper()
bbca = df_all[df_all["Kode"] == "BBCA"].copy()

print()
print("=" * 60)
print("BBCA FILTER")
print("=" * 60)
print(f"BBCA rows   : {len(bbca)}")
print(f"dtypes      :")
print(bbca.dtypes)
print()
print("Sample 3 baris pertama:")
print(bbca.head(3).to_string())
print()
print("Sample 3 baris terakhir:")
print(bbca.tail(3).to_string())
print()

# Cek masing-masing kolom setelah konversi
print("=" * 60)
print("SETELAH KONVERSI")
print("=" * 60)
bbca["Date"] = pd.to_datetime(bbca["Date"], errors="coerce")
print(f"Date NaN count: {bbca['Date'].isna().sum()} / {len(bbca)}")

for c in ["Open", "High", "Low", "Close"]:
    bbca[c] = pd.to_numeric(bbca[c], errors="coerce")
    print(f"{c} NaN count: {bbca[c].isna().sum()} / {len(bbca)}")

after_drop = bbca.dropna(subset=["Date", "Open", "High", "Low", "Close"])
print(f"\nSetelah dropna semua kolom: {len(after_drop)} baris tersisa")
