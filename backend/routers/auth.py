"""
Router Auth — Multi-User Authentication
=========================================
Endpoint:
- POST /api/auth/register       ← Admin bikin user
- POST /api/auth/login          ← Username + Password → temp token
- POST /api/auth/verify-pin     ← PIN → full access
- POST /api/auth/logout         ← Revoke token
- GET  /api/auth/me             ← Info user
- POST /api/auth/forgot-pin     ← Reset PIN (self-service)
- POST /api/auth/change-pin     ← Ganti PIN
- POST /api/auth/change-password ← Ganti password
- GET  /api/auth/users          ← List users (admin)
- POST /api/auth/users/{id}/reset-password
- POST /api/auth/users/{id}/reset-pin
- POST /api/auth/users/{id}/force-logout
- POST /api/auth/users/{id}/delete
"""

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, Field
from typing import Optional

from middleware.rate_limit import limiter
from services.auth import (
    hash_password, verify_password, hash_pin, verify_pin,
    create_session, verify_session, revoke_session, revoke_all_sessions,
    get_user_by_username, get_user_by_id, list_users, create_user,
    update_password, update_pin, update_last_login,
)


router = APIRouter(prefix="/api/auth", tags=["Auth"])


# =========================================================
# SCHEMA
# =========================================================
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    nama_lengkap: str = Field(..., min_length=2)
    role: str = Field("operator")
    pin: str = Field("123456", min_length=6, max_length=6)


class LoginRequest(BaseModel):
    username: str
    password: str
    device_info: Optional[str] = ""


class VerifyPinRequest(BaseModel):
    temp_token: str
    pin: str


class ForgotPinRequest(BaseModel):
    username: str
    password: str
    new_pin: str = Field(..., min_length=6, max_length=6)


class ChangePinRequest(BaseModel):
    old_pin: str
    new_pin: str = Field(..., min_length=6, max_length=6)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class ResetUserPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6)


class ResetUserPinRequest(BaseModel):
    new_pin: str = Field(..., min_length=6, max_length=6)


# =========================================================
# HELPER — Get current user from token
# =========================================================
def _get_current_user(authorization: str = Header(None)):
    """Ambil user dari Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header tidak valid")
    _token = authorization.replace("Bearer ", "").strip()
    _verify = verify_session(_token)
    if not _verify.get("valid"):
        raise HTTPException(401, _verify.get("error", "Token invalid"))
    return _verify["user"], _token


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(403, "Cuma admin yang bisa akses ini")


# =========================================================
# REGISTER (admin only)
# =========================================================
@router.post("/register")
@limiter.limit("10/minute")
async def register_endpoint(request: Request, req: RegisterRequest, authorization: str = Header(None)):
    """Bikin user baru (admin only)."""
    _user, _ = _get_current_user(authorization)
    _require_admin(_user)

    _result = create_user(
        username=req.username,
        password=req.password,
        nama_lengkap=req.nama_lengkap,
        role=req.role,
        pin=req.pin,
    )

    if not _result.get("success"):
        raise HTTPException(400, _result.get("error", "Gagal bikin user"))

    return _result


# =========================================================
# LOGIN
# =========================================================
@router.post("/login")
@limiter.limit("10/minute")
async def login_endpoint(request: Request, req: LoginRequest):
    """Login pakai username + password → kasih temp token."""
    _username = req.username.strip().upper()
    _user = get_user_by_username(_username)

    if not _user:
        raise HTTPException(401, "Username atau password salah")

    if not _user.get("aktif", True):
        raise HTTPException(403, "User nonaktif. Hubungi admin.")

    if not verify_password(req.password, _user.get("password_hash", "")):
        raise HTTPException(401, "Username atau password salah")

    # Cek user punya PIN
    if not _user.get("pin_hash"):
        raise HTTPException(400, "User belum set PIN. Hubungi admin.")

    # Bikin temp token (belum full access — cuma buat verify PIN)
    _ip = request.client.host if request.client else ""
    _session = create_session(
        user_id=_user.get("id"),
        device_info=req.device_info or "",
        ip=_ip,
    )

    if not _session.get("success"):
        raise HTTPException(500, _session.get("error", "Gagal bikin session"))

    return {
        "success": True,
        "step": "verify_pin",
        "temp_token": _session.get("token"),
        "expires_at": _session.get("expires_at"),
        "user": {
            "username": _user.get("username"),
            "nama_lengkap": _user.get("nama_lengkap"),
        },
    }


# =========================================================
# VERIFY PIN (2FA)
# =========================================================
@router.post("/verify-pin")
@limiter.limit("10/minute")
async def verify_pin_endpoint(request: Request, req: VerifyPinRequest):
    """Verify PIN → kasih full access."""
    _verify = verify_session(req.temp_token)
    if not _verify.get("valid"):
        raise HTTPException(401, _verify.get("error", "Token invalid"))

    _uid = _verify["user"]["id"]
    _user = get_user_by_id(_uid)

    if not _user:
        raise HTTPException(404, "User nggak ditemukan")

    if not verify_pin(req.pin, _user.get("pin_hash", "")):
        raise HTTPException(401, "PIN salah")

    # Update last login
    update_last_login(_uid)

    return {
        "success": True,
        "token": req.temp_token,
        "user": {
            "id": _user.get("id"),
            "username": _user.get("username"),
            "nama_lengkap": _user.get("nama_lengkap"),
            "role": _user.get("role", "operator"),
        },
    }


# =========================================================
# LOGOUT
# =========================================================
@router.post("/logout")
@limiter.limit("30/minute")
async def logout_endpoint(request: Request, authorization: str = Header(None)):
    _user, _token = _get_current_user(authorization)
    revoke_session(_token)
    return {"success": True, "message": "Logout berhasil"}


# =========================================================
# ME — Info user
# =========================================================
@router.get("/me")
@limiter.limit("60/minute")
async def me_endpoint(request: Request, authorization: str = Header(None)):
    _user, _ = _get_current_user(authorization)
    return {"success": True, "user": _user}


# =========================================================
# FORGOT PIN (self-service)
# =========================================================
@router.post("/forgot-pin")
@limiter.limit("5/minute")
async def forgot_pin_endpoint(request: Request, req: ForgotPinRequest):
    """Reset PIN pake username + password."""
    _user = get_user_by_username(req.username.strip().upper())
    if not _user:
        raise HTTPException(401, "Username atau password salah")

    if not verify_password(req.password, _user.get("password_hash", "")):
        raise HTTPException(401, "Username atau password salah")

    _result = update_pin(_user.get("id"), req.new_pin)
    if not _result.get("success"):
        raise HTTPException(500, _result.get("error", "Gagal reset PIN"))

    return {"success": True, "message": "PIN berhasil direset"}


# =========================================================
# CHANGE PIN (logged in user)
# =========================================================
@router.post("/change-pin")
@limiter.limit("10/minute")
async def change_pin_endpoint(request: Request, req: ChangePinRequest, authorization: str = Header(None)):
    _user, _ = _get_current_user(authorization)
    _full_user = get_user_by_id(_user["id"])

    if not verify_pin(req.old_pin, _full_user.get("pin_hash", "")):
        raise HTTPException(401, "PIN lama salah")

    _result = update_pin(_user["id"], req.new_pin)
    if not _result.get("success"):
        raise HTTPException(500, _result.get("error", "Gagal ganti PIN"))

    return {"success": True, "message": "PIN berhasil diganti"}


# =========================================================
# CHANGE PASSWORD (logged in user)
# =========================================================
@router.post("/change-password")
@limiter.limit("10/minute")
async def change_password_endpoint(request: Request, req: ChangePasswordRequest, authorization: str = Header(None)):
    _user, _ = _get_current_user(authorization)
    _full_user = get_user_by_id(_user["id"])

    if not verify_password(req.old_password, _full_user.get("password_hash", "")):
        raise HTTPException(401, "Password lama salah")

    _result = update_password(_user["id"], req.new_password)
    if not _result.get("success"):
        raise HTTPException(500, _result.get("error", "Gagal ganti password"))

    return {"success": True, "message": "Password berhasil diganti"}


# =========================================================
# ADMIN — List users
# =========================================================
@router.get("/users")
@limiter.limit("30/minute")
async def list_users_endpoint(request: Request, authorization: str = Header(None)):
    _user, _ = _get_current_user(authorization)
    _require_admin(_user)
    _users = list_users()
    return {"success": True, "users": _users}


# =========================================================
# ADMIN — Reset password user lain
# =========================================================
@router.post("/users/{user_id}/reset-password")
@limiter.limit("10/minute")
async def admin_reset_password_endpoint(
    request: Request,
    user_id: int,
    req: ResetUserPasswordRequest,
    authorization: str = Header(None),
):
    _user, _ = _get_current_user(authorization)
    _require_admin(_user)

    _target = get_user_by_id(user_id)
    if not _target:
        raise HTTPException(404, "User nggak ditemukan")

    _result = update_password(user_id, req.new_password)
    if not _result.get("success"):
        raise HTTPException(500, _result.get("error", "Gagal reset"))

    return {"success": True, "message": f"Password {_target.get('username')} berhasil direset"}


# =========================================================
# ADMIN — Reset PIN user lain
# =========================================================
@router.post("/users/{user_id}/reset-pin")
@limiter.limit("10/minute")
async def admin_reset_pin_endpoint(
    request: Request,
    user_id: int,
    req: ResetUserPinRequest,
    authorization: str = Header(None),
):
    _user, _ = _get_current_user(authorization)
    _require_admin(_user)

    _target = get_user_by_id(user_id)
    if not _target:
        raise HTTPException(404, "User nggak ditemukan")

    _result = update_pin(user_id, req.new_pin)
    if not _result.get("success"):
        raise HTTPException(500, _result.get("error", "Gagal reset"))

    return {"success": True, "message": f"PIN {_target.get('username')} berhasil direset"}


# =========================================================
# ADMIN — Force logout user (revoke all sessions)
# =========================================================
@router.post("/users/{user_id}/force-logout")
@limiter.limit("10/minute")
async def admin_force_logout_endpoint(request: Request, user_id: int, authorization: str = Header(None)):
    _user, _ = _get_current_user(authorization)
    _require_admin(_user)

    _target = get_user_by_id(user_id)
    if not _target:
        raise HTTPException(404, "User nggak ditemukan")

    _count = revoke_all_sessions(user_id)
    return {"success": True, "message": f"{_count} session di-revoke"}


# =========================================================
# ADMIN — Delete user (soft delete / nonaktifkan)
# =========================================================
@router.post("/users/{user_id}/delete")
@limiter.limit("10/minute")
async def admin_delete_user_endpoint(request: Request, user_id: int, authorization: str = Header(None)):
    _user, _ = _get_current_user(authorization)
    _require_admin(_user)

    if user_id == _user["id"]:
        raise HTTPException(400, "Nggak bisa hapus diri sendiri")

    _target = get_user_by_id(user_id)
    if not _target:
        raise HTTPException(404, "User nggak ditemukan")

    # Soft delete: nonaktifkan + revoke session
    from services.supabase_client import get_supabase
    _sb = get_supabase()
    _sb.table("users").update({"aktif": False}).eq("id", user_id).execute()
    revoke_all_sessions(user_id)

    return {"success": True, "message": f"User {_target.get('username')} dinonaktifkan"}