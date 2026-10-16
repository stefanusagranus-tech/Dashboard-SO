"""
Auth Service — Backend Version
================================
Password hashing, token generation, verification.

Dependencies:
- passlib[bcrypt] untuk hashing
- secrets untuk token generation
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

try:
    from passlib.context import CryptContext
    PASSLIB_OK = True
except ImportError:
    PASSLIB_OK = False


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _get_supabase():
    from services.supabase_client import get_supabase
    return get_supabase()


# =========================================================
# PASSWORD HASHING
# =========================================================
if PASSLIB_OK:
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    _pwd_context = None


def hash_password(password: str) -> str:
    """Hash password pakai bcrypt."""
    if not PASSLIB_OK or not _pwd_context:
        # Fallback: SHA256 (kurang aman, tapi works)
        return hashlib.sha256(password.encode()).hexdigest()
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password."""
    if not plain or not hashed:
        return False
    if not PASSLIB_OK or not _pwd_context:
        return hashlib.sha256(plain.encode()).hexdigest() == hashed
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


# =========================================================
# PIN HASHING (same as password)
# =========================================================
def hash_pin(pin: str) -> str:
    return hash_password(pin)


def verify_pin(plain: str, hashed: str) -> bool:
    return verify_password(plain, hashed)


# =========================================================
# TOKEN GENERATION
# =========================================================
def generate_token() -> str:
    """Generate random 64-char token."""
    return secrets.token_urlsafe(48)


def get_token_expiry(days: int = 7) -> str:
    """Token expired 7 hari dari sekarang."""
    return (_now_jkt() + timedelta(days=days)).isoformat()


# =========================================================
# SESSION MANAGEMENT
# =========================================================
def create_session(user_id: int, device_info: str = "", ip: str = "") -> dict:
    """Bikin session baru di DB."""
    try:
        _sb = _get_supabase()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        _token = generate_token()
        _expires = get_token_expiry(days=7)

        _data = {
            "token": _token,
            "user_id": user_id,
            "device_info": device_info[:200] if device_info else "",
            "ip_address": ip[:50] if ip else "",
            "expires_at": _expires,
            "revoked": False,
        }

        _res = _sb.table("sessions").insert(_data).execute()

        if _res.data:
            return {
                "success": True,
                "token": _token,
                "expires_at": _expires,
                "user_id": user_id,
            }
        return {"success": False, "error": "Gagal bikin session"}

    except Exception as e:
        print(f"[CREATE_SESSION ERROR] {e}")
        return {"success": False, "error": str(e)[:200]}


def verify_session(token: str) -> dict:
    """Verify session token. Return user data kalau valid."""
    if not token:
        return {"valid": False, "error": "Token kosong"}

    try:
        _sb = _get_supabase()
        if _sb is None:
            return {"valid": False, "error": "Supabase gak konek"}

        _res = (
            _sb.table("sessions")
            .select("*")
            .eq("token", token)
            .eq("revoked", False)
            .execute()
        )

        if not _res.data or len(_res.data) == 0:
            return {"valid": False, "error": "Token nggak ditemukan"}

        _session = _res.data[0]

        # Cek expired
        try:
            _exp = _session.get("expires_at", "")
            if _exp:
                _exp_dt = datetime.fromisoformat(_exp.replace("Z", "+00:00"))
                if _exp_dt < _now_jkt():
                    return {"valid": False, "error": "Token expired"}
        except Exception:
            pass

        # Ambil user
        _uid = _session.get("user_id")
        _res_user = _sb.table("users").select("*").eq("id", _uid).execute()

        if not _res_user.data:
            return {"valid": False, "error": "User nggak ditemukan"}

        _user = _res_user.data[0]

        if not _user.get("aktif", True):
            return {"valid": False, "error": "User nonaktif"}

        return {
            "valid": True,
            "user": {
                "id": _user.get("id"),
                "username": _user.get("username"),
                "nama_lengkap": _user.get("nama_lengkap"),
                "role": _user.get("role", "operator"),
                "aktif": _user.get("aktif", True),
            },
            "session_id": _session.get("id"),
        }

    except Exception as e:
        print(f"[VERIFY_SESSION ERROR] {e}")
        return {"valid": False, "error": str(e)[:200]}


def revoke_session(token: str) -> bool:
    """Revoke token (logout)."""
    try:
        _sb = _get_supabase()
        if _sb is None:
            return False
        _sb.table("sessions").update({"revoked": True}).eq("token", token).execute()
        return True
    except Exception as e:
        print(f"[REVOKE_SESSION ERROR] {e}")
        return False


def revoke_all_sessions(user_id: int) -> int:
    """Revoke semua session user (force logout)."""
    try:
        _sb = _get_supabase()
        if _sb is None:
            return 0
        _res = (
            _sb.table("sessions")
            .update({"revoked": True})
            .eq("user_id", user_id)
            .eq("revoked", False)
            .execute()
        )
        return len(_res.data) if _res.data else 0
    except Exception as e:
        print(f"[REVOKE_ALL ERROR] {e}")
        return 0


# =========================================================
# USER MANAGEMENT
# =========================================================
def get_user_by_username(username: str) -> dict:
    """Ambil user by username."""
    try:
        _sb = _get_supabase()
        if _sb is None:
            return None
        _res = _sb.table("users").select("*").eq("username", username.upper()).execute()
        if _res.data and len(_res.data) > 0:
            return _res.data[0]
        return None
    except Exception as e:
        print(f"[GET_USER ERROR] {e}")
        return None


def get_user_by_id(user_id: int) -> dict:
    try:
        _sb = _get_supabase()
        if _sb is None:
            return None
        _res = _sb.table("users").select("*").eq("id", user_id).execute()
        if _res.data and len(_res.data) > 0:
            return _res.data[0]
        return None
    except Exception as e:
        print(f"[GET_USER_ID ERROR] {e}")
        return None


def list_users() -> list:
    """List semua user (admin only)."""
    try:
        _sb = _get_supabase()
        if _sb is None:
            return []
        _res = _sb.table("users").select(
            "id, username, nama_lengkap, role, aktif, last_login, created_at"
        ).order("username").execute()
        return _res.data if _res.data else []
    except Exception as e:
        print(f"[LIST_USERS ERROR] {e}")
        return []


def create_user(
    username: str,
    password: str,
    nama_lengkap: str,
    role: str = "operator",
    pin: str = "123456",
) -> dict:
    """Bikin user baru."""
    try:
        _sb = _get_supabase()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        _username = username.strip().upper()
        if len(_username) < 3:
            return {"success": False, "error": "Username minimal 3 karakter"}
        if len(password) < 6:
            return {"success": False, "error": "Password minimal 6 karakter"}
        if len(pin) != 6 or not pin.isdigit():
            return {"success": False, "error": "PIN harus 6 digit angka"}

        # Cek username udah ada
        _existing = get_user_by_username(_username)
        if _existing:
            return {"success": False, "error": f"Username {_username} sudah ada"}

        _data = {
            "username": _username,
            "password_hash": hash_password(password),
            "nama_lengkap": nama_lengkap.strip(),
            "role": role if role in ("admin", "operator", "viewer") else "operator",
            "pin_hash": hash_pin(pin),
            "aktif": True,
        }

        _res = _sb.table("users").insert(_data).execute()

        if _res.data:
            return {
                "success": True,
                "user": {
                    "id": _res.data[0].get("id"),
                    "username": _username,
                    "nama_lengkap": nama_lengkap,
                    "role": role,
                },
            }
        return {"success": False, "error": "Gagal bikin user"}

    except Exception as e:
        print(f"[CREATE_USER ERROR] {e}")
        return {"success": False, "error": str(e)[:200]}


def update_password(user_id: int, new_password: str) -> dict:
    try:
        _sb = _get_supabase()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}
        if len(new_password) < 6:
            return {"success": False, "error": "Password minimal 6 karakter"}
        _sb.table("users").update(
            {"password_hash": hash_password(new_password)}
        ).eq("id", user_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def update_pin(user_id: int, new_pin: str) -> dict:
    try:
        _sb = _get_supabase()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}
        if len(new_pin) != 6 or not new_pin.isdigit():
            return {"success": False, "error": "PIN harus 6 digit angka"}
        _sb.table("users").update(
            {"pin_hash": hash_pin(new_pin)}
        ).eq("id", user_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def update_last_login(user_id: int) -> bool:
    try:
        _sb = _get_supabase()
        if _sb is None:
            return False
        _sb.table("users").update(
            {"last_login": _now_jkt().isoformat()}
        ).eq("id", user_id).execute()
        return True
    except Exception as e:
        return False