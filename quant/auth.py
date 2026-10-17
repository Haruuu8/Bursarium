"""Sistem registrasi manual dengan approval admin — bcrypt edition."""

import os
import json
import secrets
import string
from datetime import datetime
from pathlib import Path

import bcrypt
import yaml


PENDING_DIR = Path("data_registrations/pending")
APPROVED_DIR = Path("data_registrations/approved")
UPLOAD_DIR = Path("data_registrations/uploads")
REJECTED_DIR = Path("data_registrations/rejected")
CONFIG_FILE = "config.yaml"

for d in [PENDING_DIR, APPROVED_DIR, UPLOAD_DIR, REJECTED_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def generate_username(nama: str) -> str:
    base = "".join(c.lower() for c in nama if c.isalnum())[:12]
    if not base:
        base = "user"
    suffix = "".join(secrets.choice(string.digits) for _ in range(3))
    return f"{base}{suffix}"


def generate_password(length=10) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def submit_registration(nama, email, whatsapp, bukti_bytes, bukti_filename, paket="basic"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    reg_id = f"REG_{ts}_{secrets.token_hex(3)}"

    ext = Path(bukti_filename).suffix.lower() or ".jpg"
    bukti_path = UPLOAD_DIR / f"{reg_id}{ext}"
    bukti_path.write_bytes(bukti_bytes)

    data = {
        "reg_id": reg_id, "nama": nama, "email": email,
        "whatsapp": whatsapp, "paket": paket,
        "bukti_file": str(bukti_path),
        "submitted_at": datetime.now().isoformat(),
        "status": "pending",
    }
    with open(PENDING_DIR / f"{reg_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return reg_id


def list_pending():
    items = []
    for f in sorted(PENDING_DIR.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            d["_path"] = str(f)
            items.append(d)
        except Exception:
            pass
    return sorted(items, key=lambda x: x.get("submitted_at", ""), reverse=True)


def list_approved():
    items = []
    for f in sorted(APPROVED_DIR.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                items.append(json.load(fh))
        except Exception:
            pass
    return sorted(items, key=lambda x: x.get("approved_at", ""), reverse=True)


def approve_registration(reg_id):
    pending_path = PENDING_DIR / f"{reg_id}.json"
    if not pending_path.exists():
        return {"error": f"Registration {reg_id} tidak ditemukan"}

    with open(pending_path, encoding="utf-8") as f:
        data = json.load(f)

    username = generate_username(data.get("nama", ""))
    password = generate_password()

    existing = _load_config()
    while username in existing.get("credentials", {}).get("usernames", {}):
        username = generate_username(data.get("nama", ""))

    data["username"] = username
    data["password"] = password
    data["status"] = "approved"
    data["approved_at"] = datetime.now().isoformat()

    with open(APPROVED_DIR / f"{reg_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    _add_user_to_config(username, data.get("email", ""), data.get("nama", ""),
                        password, data.get("paket", "basic"))
    pending_path.unlink()

    return {
        "success": True, "username": username, "password": password,
        "email": data.get("email"), "whatsapp": data.get("whatsapp"),
        "nama": data.get("nama"),
    }


def reject_registration(reg_id, alasan=""):
    pending_path = PENDING_DIR / f"{reg_id}.json"
    if not pending_path.exists():
        return False
    with open(pending_path, encoding="utf-8") as f:
        data = json.load(f)
    data["status"] = "rejected"
    data["rejected_at"] = datetime.now().isoformat()
    data["alasan"] = alasan
    with open(REJECTED_DIR / f"{reg_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    pending_path.unlink()
    return True


def _load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"credentials": {"usernames": {}}}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or {"credentials": {"usernames": {}}}
    except Exception:
        return {"credentials": {"usernames": {}}}


def _save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def _add_user_to_config(username, email, nama, password, paket="basic"):
    config = _load_config()
    config.setdefault("credentials", {}).setdefault("usernames", {})
    config["credentials"]["usernames"][username] = {
        "email": email, "name": nama,
        "password": hash_password(password),
        "paket": paket,
        "registered_at": datetime.now().isoformat(),
    }
    _save_config(config)


def list_all_users():
    config = _load_config()
    return config.get("credentials", {}).get("usernames", {})
