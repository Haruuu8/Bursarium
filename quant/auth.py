"""Sistem registrasi terintegrasi dengan Supabase Database."""

import os
import secrets
import string
from datetime import datetime
from pathlib import Path

import bcrypt
import streamlit as st
from supabase import create_client, Client


# Setup Supabase (bisa dari Secrets Streamlit atau Env Lokal)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))

if not SUPABASE_URL or not SUPABASE_KEY:
    supabase = None
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

UPLOAD_DIR = Path("data_registrations/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def generate_username(telegram: str) -> str:
    base = "".join(c.lower() for c in telegram if c.isalnum())[:12]
    if not base: base = "user"
    suffix = "".join(secrets.choice(string.digits) for _ in range(3))
    return f"{base}{suffix}"


def generate_password(length=10) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def submit_registration(telegram, bukti_bytes, bukti_filename):
    if not supabase: return "ERROR_DB"
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    reg_id = f"REG_{ts}_{secrets.token_hex(3)}"

    ext = Path(bukti_filename).suffix.lower() or ".jpg"
    bukti_path = UPLOAD_DIR / f"{reg_id}{ext}"
    bukti_path.write_bytes(bukti_bytes)

    data = {
        "reg_id": reg_id,
        "telegram": telegram,
        "bukti_file": str(bukti_path),
        "status": "pending"
    }
    supabase.table("users").insert(data).execute()
    return reg_id


def list_pending():
    if not supabase: return []
    res = supabase.table("users").select("*").eq("status", "pending").order("created_at", desc=True).execute()
    
    items = []
    for row in res.data:
        row["submitted_at"] = row.get("created_at", "")
        items.append(row)
    return items


def list_approved():
    if not supabase: return []
    res = supabase.table("users").select("*").eq("status", "approved").order("approved_at", desc=True).execute()
    
    items = []
    for row in res.data:
        row["password"] = row.get("password_hash", "-") 
        items.append(row)
    return items


def approve_registration(reg_id):
    if not supabase: return {"error": "DB Error"}
    
    res = supabase.table("users").select("*").eq("reg_id", reg_id).execute()
    if not res.data: return {"error": "Data tidak ditemukan"}
    
    data = res.data[0]
    tele = data.get("telegram", "")
    username = generate_username(tele)
    password = generate_password()
    pw_hash = hash_password(password)

    update_data = {
        "username": username,
        "password_hash": pw_hash,
        "status": "approved",
        "approved_at": datetime.now().isoformat()
    }
    supabase.table("users").update(update_data).eq("reg_id", reg_id).execute()

    return {
        "success": True,
        "username": username,
        "password": password,
        "telegram": tele,
    }


def reject_registration(reg_id, alasan=""):
    if not supabase: return False
    supabase.table("users").update({"status": "rejected"}).eq("reg_id", reg_id).execute()
    return True


def get_all_approved_users_for_auth():
    if not supabase: return {}
    res = supabase.table("users").select("username, telegram, password_hash").eq("status", "approved").execute()
    
    users = {}
    for u in res.data:
        if u.get("username"):
            users[u["username"]] = {
                "email": "",
                "name": u["telegram"],
                "password": u["password_hash"],
                "paket": "premium"
            }
    return users


def reset_user_password(reg_id):
    """Generate password baru untuk user yang sudah approved."""
    if not supabase: return {"error": "DB Error"}
    
    res = supabase.table("users").select("*").eq("reg_id", reg_id).execute()
    if not res.data: return {"error": "Data tidak ditemukan"}
    
    data = res.data[0]
    username = data.get("username")
    tele = data.get("telegram", "")
    
    new_password = generate_password()
    new_hash = hash_password(new_password)
    
    supabase.table("users").update({"password_hash": new_hash}).eq("reg_id", reg_id).execute()
    
    return {
        "success": True,
        "username": username,
        "password": new_password,
        "telegram": tele,
    }


def update_username(reg_id, new_username):
    """Ubah username user di database dengan validasi keunikan."""
    if not supabase: return {"error": "DB Error"}
    
    # Validasi format (hanya huruf, angka, underscore)
    if not new_username.isalnum() and "_" not in new_username:
        return {"error": "Username hanya boleh huruf, angka, dan underscore."}
        
    # Cek apakah username sudah dipakai user lain
    check = supabase.table("users").select("reg_id").eq("username", new_username).execute()
    if check.data and check.data[0]["reg_id"] != reg_id:
        return {"error": "Username sudah dipakai oleh user lain."}
        
    try:
        supabase.table("users").update({"username": new_username}).eq("reg_id", reg_id).execute()
        return {"success": True, "new_username": new_username}
    except Exception as e:
        return {"error": str(e)}


def delete_user(reg_id):
    """Hapus user dari database secara permanen."""
    if not supabase: return False
    try:
        supabase.table("users").delete().eq("reg_id", reg_id).execute()
        return True
    except Exception as e:
        print(f"Error delete: {e}")
        return False


def list_all_users():
    if not supabase: return {}
    res = supabase.table("users").select("username, telegram").eq("status", "approved").execute()
    users = {}
    for u in res.data:
        if u.get("username"):
            users[u["username"]] = u
    return users