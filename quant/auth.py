"""Sistem registrasi terintegrasi dengan Supabase Database."""

import os
import secrets
import string
from datetime import datetime
from pathlib import Path

import bcrypt
import streamlit as st
from supabase import create_client, Client


# ============================================================
# SETUP SUPABASE
# ============================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))


# ============================================================
# SAFE CLIENT — handle API key format lama (JWT) & baru (sb_...)
# ============================================================
def _make_supabase_client(url: str, key: str):
    """
    Buat client Supabase, kompatibel dengan:
    - Key LAMA (JWT anon/service): "eyJhbGciOi..."
    - Key BARU: "sb_publishable_..." atau "sb_secret_..."

    Library `supabase` versi lama (<2.15.0) memvalidasi key sebagai JWT
    secara lokal. Kalau key format baru, validasi ini gagal sebelum
    request ke server. Fungsi ini mem-bypass validasi JWT secara aman
    agar tetap bisa dipakai tanpa upgrade library.
    """
    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        msg = str(e)
        is_new_format = str(key).startswith(("sb_publishable_", "sb_secret_"))

        if "Invalid API key" not in msg or not is_new_format:
            # Error lain (URL salah, network, dll.) → biarkan naik
            raise

        # ─── FALLBACK: bypass validasi JWT saat init ───
        try:
            import jwt as _jwt
            import supabase._sync.client as _sc

            _orig_decode = _jwt.decode
            _orig_init = _sc.SyncClient.__init__

            def _safe_decode(*args, **kwargs):
                try:
                    return _orig_decode(*args, **kwargs)
                except Exception:
                    # Payload dummy → validasi JWT lolos, server tetap
                    # yang akan memvalidasi key sebenarnya.
                    return {"role": "anon", "iss": "supabase"}

            def _patched_init(self, supabase_url, supabase_key, options):
                _jwt.decode = _safe_decode
                try:
                    _orig_init(self, supabase_url, supabase_key, options)
                finally:
                    _jwt.decode = _orig_decode

            _sc.SyncClient.__init__ = _patched_init
            try:
                return create_client(url, key)
            finally:
                _sc.SyncClient.__init__ = _orig_init
        except Exception:
            raise RuntimeError(
                "Supabase API key baru (`sb_publishable_` / `sb_secret_`) "
                "tidak bisa dipakai karena library `supabase` di environment "
                "masih versi lama.\n\n"
                "SOLUSI (pilih salah satu):\n"
                "1. Tambah `supabase>=2.15.0` di requirements.txt, "
                "lalu Reboot app.\n"
                "2. Atau pakai key legacy `anon` (format JWT, diawali `eyJ`) "
                "dari Supabase Dashboard → Project Settings → API → "
                "Legacy API Keys."
            ) from e


supabase = _make_supabase_client(SUPABASE_URL, SUPABASE_KEY)

UPLOAD_DIR = Path("data_registrations/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPER
# ============================================================
def generate_username(telegram: str) -> str:
    base = "".join(c.lower() for c in telegram if c.isalnum())[:12]
    if not base:
        base = "user"
    suffix = "".join(secrets.choice(string.digits) for _ in range(3))
    return f"{base}{suffix}"


def generate_password(length=10) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ============================================================
# SUBMIT REGISTRASI
# ============================================================
def submit_registration(telegram, bukti_bytes, bukti_filename):
    if not supabase:
        return "ERROR_DB"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    reg_id = f"REG_{ts}_{secrets.token_hex(3)}"

    ext = Path(bukti_filename).suffix.lower() or ".jpg"
    bukti_path = UPLOAD_DIR / f"{reg_id}{ext}"
    try:
        bukti_path.write_bytes(bukti_bytes)
    except Exception as e:
        print(f"[auth] gagal simpan file bukti lokal: {e}")

    data = {
        "reg_id": reg_id,
        "telegram": telegram,
        "bukti_file": str(bukti_path),
        "status": "pending",
    }
    supabase.table("users").insert(data).execute()
    return reg_id


# ============================================================
# LIST
# ============================================================
def list_pending():
    if not supabase:
        return []
    res = (
        supabase.table("users")
        .select("*")
        .eq("status", "pending")
        .order("created_at", desc=True)
        .execute()
    )

    items = []
    for row in res.data:
        row["submitted_at"] = row.get("created_at", "")
        items.append(row)
    return items


def list_approved():
    if not supabase:
        return []
    res = (
        supabase.table("users")
        .select("*")
        .eq("status", "approved")
        .order("approved_at", desc=True)
        .execute()
    )

    items = []
    for row in res.data:
        row["password"] = row.get("password_hash", "-")
        items.append(row)
    return items


# ============================================================
# APPROVE / REJECT
# ============================================================
def approve_registration(reg_id, custom_username=None, custom_password=None):
    if not supabase:
        return {"error": "DB Error"}

    res = supabase.table("users").select("*").eq("reg_id", reg_id).execute()
    if not res.data:
        return {"error": "Data tidak ditemukan"}

    data = res.data[0]
    tele = data.get("telegram", "")

    if custom_username and custom_username.strip():
        username = custom_username.strip().lower().replace(" ", "")
    else:
        username = generate_username(tele)

    if custom_password and custom_password.strip():
        password = custom_password.strip()
    else:
        password = generate_password()

    pw_hash = hash_password(password)

    check = supabase.table("users").select("reg_id").eq("username", username).execute()
    if check.data:
        return {"error": f"Username '{username}' sudah dipakai user lain."}

    update_data = {
        "username": username,
        "password_hash": pw_hash,
        "status": "approved",
        "approved_at": datetime.now().isoformat(),
    }
    supabase.table("users").update(update_data).eq("reg_id", reg_id).execute()

    return {
        "success": True,
        "username": username,
        "password": password,
        "telegram": tele,
    }


def reject_registration(reg_id, alasan=""):
    if not supabase:
        return False
    supabase.table("users").update({"status": "rejected"}).eq("reg_id", reg_id).execute()
    return True


# ============================================================
# UNTUK STREAMLIT-AUTHENTICATOR
# ============================================================
def get_all_approved_users_for_auth():
    if not supabase:
        return {}
    res = (
        supabase.table("users")
        .select("username, telegram, password_hash")
        .eq("status", "approved")
        .execute()
    )

    users = {}
    for u in res.data:
        if u.get("username"):
            users[u["username"]] = {
                "email": "",
                "name": u["telegram"] or "",
                "password": u["password_hash"],
                "paket": "premium",
            }
    return users


# ============================================================
# RESET / UPDATE / DELETE
# ============================================================
def reset_user_password(reg_id):
    """Generate password baru untuk user yang sudah approved."""
    if not supabase:
        return {"error": "DB Error"}

    res = supabase.table("users").select("*").eq("reg_id", reg_id).execute()
    if not res.data:
        return {"error": "Data tidak ditemukan"}

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
    if not supabase:
        return {"error": "DB Error"}

    if not new_username.isalnum() and "_" not in new_username:
        return {"error": "Username hanya boleh huruf, angka, dan underscore."}

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
    if not supabase:
        return False
    try:
        supabase.table("users").delete().eq("reg_id", reg_id).execute()
        return True
    except Exception as e:
        print(f"Error delete: {e}")
        return False


def list_all_users():
    if not supabase:
        return {}
    res = supabase.table("users").select("username, telegram").eq("status", "approved").execute()
    users = {}
    for u in res.data:
        if u.get("username"):
            users[u["username"]] = u
    return users


# ============================================================
# GABUNGAN UPDATE USERNAME & PASSWORD
# ============================================================
def update_user_credentials(reg_id, new_username=None, new_password=None):
    """Ubah username dan/atau password user di database dengan validasi."""
    if not supabase:
        return {"error": "DB Error"}

    res = supabase.table("users").select("*").eq("reg_id", reg_id).execute()
    if not res.data:
        return {"error": "Data tidak ditemukan"}

    current_data = res.data[0]
    update_data = {}

    result = {
        "success": True,
        "username": current_data.get("username"),
        "password": "*** (Tidak diubah)",
    }

    # 1. Cek & Siapkan Update Username
    if new_username and new_username.strip():
        clean_username = new_username.strip().lower().replace(" ", "")
        if clean_username != current_data.get("username"):
            check = supabase.table("users").select("reg_id").eq("username", clean_username).execute()
            if check.data and check.data[0]["reg_id"] != reg_id:
                return {"error": f"Username '{clean_username}' sudah dipakai user lain."}
            update_data["username"] = clean_username
            result["username"] = clean_username

    # 2. Cek & Siapkan Update Password
    if new_password and new_password.strip():
        pw_hash = hash_password(new_password.strip())
        update_data["password_hash"] = pw_hash
        result["password"] = new_password.strip()

    # 3. Eksekusi ke Database
    if update_data:
        try:
            supabase.table("users").update(update_data).eq("reg_id", reg_id).execute()
        except Exception as e:
            return {"error": str(e)}

    return result