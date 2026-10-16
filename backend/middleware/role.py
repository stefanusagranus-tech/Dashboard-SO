"""
Role Middleware — Bearer Token + Role-Based Access
====================================================
Dependency FastAPI buat:
1. Verify Bearer token (dari /api/auth/login + /verify-pin)
2. Cek role user (admin/operator/viewer)

Cara pakai:
    from middleware.role import require_token, require_role, require_admin

    @router.post("/chat")
    async def chat(req: ChatRequest, user: dict = Depends(require_token)):
        # user = {"id": 2, "username": "ADMIN", "role": "admin", ...}
        ...

    @router.post("/admin-only")
    async def admin_endpoint(user: dict = Depends(require_admin)):
        ...

Catatan:
- Middleware `AuthMiddleware` (API Key) tetap jalan duluan.
- Dependency ini jalan SETELAH middleware, di level route handler.
"""

from fastapi import Header, HTTPException, Depends
from typing import Optional


# =========================================================
# ROLE HIERARCHY
# =========================================================
# Role dengan akses tertinggi = admin, lalu operator, lalu viewer
_ROLE_LEVELS = {
    "viewer": 1,
    "operator": 2,
    "admin": 3,
}


def _role_level(role: str) -> int:
    """Convert role ke level angka. Default 0 (nggak valid)."""
    return _ROLE_LEVELS.get((role or "").lower(), 0)


# =========================================================
# REQUIRE TOKEN — Cek Bearer token valid, return user info
# =========================================================
async def require_token(
    authorization: Optional[str] = Header(None),
) -> dict:
    """
    Dependency: Verify Bearer token + return user info.

    Raise 401 kalau:
    - Header Authorization nggak ada
    - Format bukan 'Bearer <token>'
    - Token nggak valid / expired / revoked

    Return: dict user {"id", "username", "nama_lengkap", "role", "aktif"}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header tidak valid. Format: 'Bearer <token>'",
        )

    _token = authorization.replace("Bearer ", "").strip()
    if not _token:
        raise HTTPException(401, "Token kosong")

    # Import di dalam fungsi biar nggak circular
    from services.auth import verify_session

    _verify = verify_session(_token)
    if not _verify.get("valid"):
        raise HTTPException(401, _verify.get("error", "Token invalid"))

    return _verify["user"]


# =========================================================
# REQUIRE ROLE — Factory: cek role user punya akses minimal
# =========================================================
def require_role(*allowed_roles: str):
    """
    Factory: bikin dependency yang cek role user.

    Contoh:
        require_role("admin")              # cuma admin
        require_role("admin", "operator")  # admin atau operator
        require_role("admin", "operator", "viewer")  # semua role

    Role hierarchy: viewer < operator < admin.
    Kalau user role-nya lebih tinggi dari minimal yang dibutuhin, lolos.

    Return: dict user (kalau lolos)
    Raise: 403 kalau role nggak cukup
    """
    _min_level = min(_role_level(r) for r in allowed_roles) if allowed_roles else 0
    _allowed_set = {r.lower() for r in allowed_roles}

    async def _checker(user: dict = Depends(require_token)) -> dict:
        _user_role = (user.get("role") or "").lower()
        _user_level = _role_level(_user_role)

        # Cek: role user ada di daftar? ATAU level user >= level minimum?
        if _user_role in _allowed_set or _user_level >= _min_level:
            return user

        raise HTTPException(
            status_code=403,
            detail=f"Akses ditolak. Role '{_user_role}' nggak cukup. "
                   f"Butuh salah satu: {', '.join(allowed_roles)}",
        )

    return _checker


# =========================================================
# SHORTCUT — Ready-to-use dependencies
# =========================================================
require_admin = require_role("admin")
require_operator = require_role("admin", "operator")
require_viewer = require_role("admin", "operator", "viewer")


# =========================================================
# REQUIRE SELF OR ADMIN — Buat endpoint yang user bisa akses dirinya sendiri
# =========================================================
async def require_self_or_admin(
    user_id: int,
    user: dict = Depends(require_token),
) -> dict:
    """
    Dependency: Cek user yang login == user_id di path, ATAU role admin.

    Contoh:
        @router.get("/users/{user_id}/profile")
        async def get_profile(user_id: int, user: dict = Depends(require_self_or_admin)):
            ...
    """
    _user_role = (user.get("role") or "").lower()
    _user_id = user.get("id")

    if _user_role == "admin" or _user_id == user_id:
        return user

    raise HTTPException(
        status_code=403,
        detail="Cuma bisa akses data diri sendiri, atau login sebagai admin.",
    )