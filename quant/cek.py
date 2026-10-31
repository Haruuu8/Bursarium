import os
import json
import pandas as pd

FUND_DIR = "data_fundamental"
SAHAM_SAMPEL = ["BBCA", "ANTM", "PADI", "GOTO", "TLKM", "ELSA"]

# Field penting yang wajib ada (Neraca, Laba Rugi, Arus Kas, Rasio)
FIELDS_TO_CHECK = {
    "Neraca": ["aset", "liabilitas", "ekuitas"],
    "Laba Rugi": ["pendapatan", "laba_kotor", "laba_operasi", "laba_induk"],
    "Arus Kas": ["arus_kas_operasi"],
    "Rasio": ["pe", "pb", "roe", "eps", "bv"]
}

def cek_kelengkapan(kode):
    file_path = os.path.join(FUND_DIR, f"{kode}.json")
    if not os.path.exists(file_path):
        return {"Kode": kode, "Status": "File JSON tidak ada"}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    hasil = {"Kode": kode}
    
    # Cek tiap kategori
    for kategori, fields in FIELDS_TO_CHECK.items():
        for field in fields:
            # Ambil dari nested dictionary yang sesuai
            if field in ["aset", "liabilitas", "ekuitas"]:
                val = data.get("neraca", {}).get(field)
            elif field in ["pendapatan", "laba_kotor", "laba_operasi", "laba_induk"]:
                val = data.get("laba_rugi", {}).get(field)
            elif field == "arus_kas_operasi":
                val = data.get("arus_kas", {}).get(field)
            else:
                val = data.get("rasio_kunci", {}).get(field)
                
            # Beri tanda centang jika ada isinya (bukan None atau 0)
            if val is not None and val != 0:
                hasil[f"{field}"] = "✅"
            else:
                hasil[f"{field}"] = "❌"
                
    return hasil

# Jalankan pengecekan
hasil_cek = [cek_kelengkapan(kode) for kode in SAHAM_SAMPEL]
df_cek = pd.DataFrame(hasil_cek)

# Rapikan urutan kolom
cols = ["Kode", "aset", "liabilitas", "ekuitas", "pendapatan", "laba_kotor", "laba_operasi", "laba_induk", "arus_kas_operasi", "pe", "pb", "roe", "eps", "bv"]
df_cek = df_cek[cols]

print("\n=== 📊 CEK KELENGKAPAN DATA FUNDAMENTAL ===\n")
print(df_cek.to_string(index=False))
print("\nKeterangan:")
print("✅ = Data tersedia")
print("❌ = Data kosong / tidak ada di laporan")
print("\nCatatan: Bank (seperti BBCA) wajar jika 'laba_kotor' ❌ karena tidak melaporkan COGS.")