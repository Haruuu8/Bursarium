import json
import os

file_path = "data_fundamental/TLKM.json"
if not os.path.exists(file_path):
    print("❌ File TLKM.json tidak ditemukan! Jalankan scrape dulu.")
else:
    with open(file_path, 'r', encoding='utf-8') as f:
        d = json.load(f)
        
    print("=== ISI DATA MENTAH TLKM ===")
    print("Harga           :", d.get("harga"))
    print("Ekuitas Induk   :", d.get("neraca", {}).get("ekuitas_induk"))
    print("Ekuitas Total   :", d.get("neraca", {}).get("ekuitas"))
    print("Laba Induk      :", d.get("laba_rugi", {}).get("laba_induk"))
    print("EPS Basic       :", d.get("laba_rugi", {}).get("eps_basic"))
    print("--------------------------")
    print("Rasio ROE       :", d.get("rasio_kunci", {}).get("roe"))
    print("Rasio PE        :", d.get("rasio_kunci", {}).get("pe"))
    print("Rasio PB        :", d.get("rasio_kunci", {}).get("pb"))