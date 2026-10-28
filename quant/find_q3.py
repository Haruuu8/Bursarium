import os
import glob
import json
import pandas as pd
import numpy as np

def extract_all_q3():
    print("Memulai pencarian laporan keuangan Q3...")
    folder_path = "data_fundamental"
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    
    if not json_files:
        print(f"❌ Tidak ada file JSON di folder '{folder_path}'.")
        return

    data_list = []
    skipped = 0
    
    for file in json_files:
        with open(file, 'r', encoding='utf-8') as f:
            try:
                d = json.load(f)
            except Exception:
                continue
                
        kode = d.get("kode")
        q_rev = d.get("quarterly", {}).get("revenue", {})
        q_ni = d.get("quarterly", {}).get("net_income", {})
        
        q3_key = "2026-Q3"
        if q3_key not in q_rev and q3_key not in q_ni:
            skipped += 1
            continue 
            
        def get_q(data, key): return data.get(key, 0)
        
        # Hitung YTD (Q1+Q2+Q3) tahun 2026 & 2025
        rev_ytd = sum([get_q(q_rev, f"2026-Q{q}") for q in [1, 2, 3]])
        ni_ytd = sum([get_q(q_ni, f"2026-Q{q}") for q in [1, 2, 3]])
        rev_ytd_ly = sum([get_q(q_rev, f"2025-Q{q}") for q in [1, 2, 3]])
        ni_ytd_ly = sum([get_q(q_ni, f"2025-Q{q}") for q in [1, 2, 3]])
        
        # ===== FILTER BARU: BUANG DATA SAMPAH =====
        # 1. Laba harus positif (bukan rugi)
        if ni_ytd <= 0:
            skipped += 1
            continue
            
        # 2. Pendapatan harus positif
        if rev_ytd <= 0:
            skipped += 1
            continue
            
        # 3. Harus ada data tahun lalu (untuk YoY)
        if ni_ytd_ly == 0 or rev_ytd_ly == 0:
            skipped += 1
            continue
        
        # 4. Filter outlier (angka tidak masuk akal)
        if rev_ytd > 1e15 or rev_ytd_ly > 1e15:
            skipped += 1
            continue
            
        # 5. Laba tidak boleh lebih besar 5x dari pendapatan (kemungkinan one-off besar)
        if ni_ytd > rev_ytd * 5:
            skipped += 1
            continue
            
        # Ambil Rasio
        rasio = d.get("rasio_kunci", {})
        roe_raw = rasio.get("roe")
        roe = (roe_raw * 100) if roe_raw is not None and abs(roe_raw) < 1 else roe_raw
        
        cfo = d.get("arus_kas", {}).get("arus_kas_operasi")
        
        sektor = d.get("sektor") or "Unknown"
        industri = str(d.get("industri", "")).lower()
        is_bank = "bank" in sektor.lower() or "bank" in industri
        
        data_list.append({
            'Kode': kode,
            'Sektor': sektor,
            'Tipe': 'Bank' if is_bank else 'Non-Bank',
            'NI_YTD': ni_ytd,
            'NI_YTD_LY': ni_ytd_ly,
            'Rev_YTD': rev_ytd,
            'Rev_YTD_LY': rev_ytd_ly,
            'CFO_YTD': cfo if cfo else 0,
            'ROE': roe if roe else 0,
            'DER': rasio.get("de", 0),
            'PER': rasio.get("pe", 0),
            'PBV': rasio.get("pb", 0)
        })
        
    if data_list:
        df = pd.DataFrame(data_list)
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
        output_file = "data_q3_clean.csv"
        df.to_csv(output_file, index=False)
        print(f"✅ Selesai! Ditemukan {len(df)} saham yang VALID & SEHAT rilis Q3 2026.")
        print(f"❌ Dilewati (rugi/data kosong/outlier): {skipped} saham.")
    else:
        print("⚠️ Tidak ada satu pun saham yang valid.")

if __name__ == "__main__":
    extract_all_q3()