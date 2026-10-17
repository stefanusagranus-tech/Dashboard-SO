"""
Role Middleware — Bearer Token + Role-Based Access
====================================================
"""

from fastapi import Header, HTTPException, Depends, Request
from typing import Optional

_ROLE_LEVELS = {"viewer": 1, "operator": 2, "admin": 3}

def _role_level(role: str) -> int:
    return _ROLE_LEVELS.get((role or "").lower(), 0)


async def require_token(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    """
    Dependency: Verify Bearer token (dari Header ATAU URL)
    """
    _token = ""

    # 1. Cek dari Header dulu (Browser)
    if authorization and authorization.startswith("Bearer "):
        _token = authorization.replace("Bearer ", "").strip()
    
    # 2. Kalau Header kosong, cek dari URL (APK WebView)
    if not _token:
        _token = getattr(request.state, "auth_token", None)

    if not _token:
        raise HTTPException(401, "Authorization token tidak ditemukan (Header/URL).")

    from services.auth import verify_session
    _verify = verify_session(_token)
    if not _verify.get("valid"):
        raise HTTPException(401, _verify.get("error", "Token invalid"))

    return _verify["user"]


def require_role(*allowed_roles: str):
    _min_level = min(_role_level(r) for r in allowed_roles) if allowed_roles else 0
    _allowed_set = {r.lower() for r in allowed_roles}

    async def _checker(user: dict = Depends(require_token)) -> dict:
        _user_role = (user.get("role") or "").lower()
        _user_level = _role_level(_user_role)

        if _user_role in _allowed_set or _user_level >= _min_level:
            return user

        raise HTTPException(
            status_code=403,
            detail=f"Akses ditolak. Role '{_user_role}' nggak cukup.",
        )

    return _checker

require_admin = require_role("admin")
require_operator = require_role("admin", "operator")
require_viewer = require_role("admin", "operator", "viewer")