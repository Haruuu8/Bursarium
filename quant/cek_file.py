import os
import pandas as pd

OUTPUT_DIR = "quant/output"

print("=" * 80)
print("  CEK FILE KANDIDAT DI FOLDER OUTPUT")
print("=" * 80)

if not os.path.exists(OUTPUT_DIR):
    print(f"❌ Folder '{OUTPUT_DIR}' tidak ditemukan.")
    exit()

files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("kandidat_") and f.endswith(".csv")]

if not files:
    print("✅ Tidak ada file kandidat di folder output.")
    exit()

# Urutkan dari yang terbaru
files.sort(reverse=True)

data_summary = []

for f in files:
    path = os.path.join(OUTPUT_DIR, f)
    size_kb = os.path.getsize(path) / 1024
    
    try:
        df = pd.read_csv(path)
        n_rows = len(df)
        saham = ", ".join(df["kode"].astype(str).str.upper().tolist()) if "kode" in df.columns else "-"
    except Exception as e:
        n_rows = 0
        saham = f"Error: {e}"

    data_summary.append({
        "Nama File": f,
        "Ukuran (KB)": round(size_kb, 1),
        "Jumlah Baris": n_rows,
        "Saham (Kode)": saham
    })

# Print Tabel
df_summary = pd.DataFrame(data_summary)
print("\nDaftar File Kandidat:")
print(df_summary.to_string(index=False))

# Cek Duplikasi Isi
print("\n" + "=" * 80)
print("  ANALISA DUPLIKASI")
print("=" * 80)

if len(files) > 1:
    # Cek apakah ada file yang isinya persis sama
    all_codes = {}
    for f in files:
        try:
            df = pd.read_csv(os.path.join(OUTPUT_DIR, f))
            if "kode" in df.columns:
                codes = tuple(sorted(df["kode"].astype(str).str.upper().tolist()))
                if codes not in all_codes:
                    all_codes[codes] = []
                all_codes[codes].append(f)
        except:
            pass
    
    double_found = False
    for codes, flist in all_codes.items():
        if len(flist) > 1:
            double_found = True
            print(f"⚠️ DITEMUKAN FILE DOUBLE (Isi saham sama persis):")
            for f in flist:
                print(f"   - {f}")
            print(f"   Saham: {', '.join(codes)}\n")
            
    if not double_found:
        print("✅ Tidak ada file yang isinya 100% sama (double).")
        print("   Kemungkinan perbedaannya hanya di tanggal/stempel waktu.")
else:
    print("Hanya ada 1 file, tidak ada duplikasi.")