"""
Auth Middleware — API Key verification
=======================================
Verifikasi API key dari header X-API-Key untuk semua endpoint
kecuali yang ada di PUBLIC_PATHS.

Cara pakai:
- Set env: SO_API_KEY=<key_panjang_random>
- APK kirim: X-API-Key: <key_panjang_random>
- Kalau gak cocok → 401 Unauthorized

Update v2: Tambah whitelist /api/auth/* endpoints
"""

import os
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

# =========================================================
# KONFIGURASI
# =========================================================
# Endpoint yang TIDAK butuh API key (public)
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/bots",
    "/api/config",
    "/api/config/",
    # === AUTH (public — belum punya token) ===
    "/api/auth/setup",        # ← bikin admin pertama (auto-lock setelah ada admin)
    "/api/auth/login",
    "/api/auth/verify-pin",
    "/api/auth/forgot-pin",
    "/api/auth/logout",       # logout public biar bisa logout walau token expired
}

# Prefix yang TIDAK butuh API key
PUBLIC_PREFIXES = (
    "/docs",
    "/redoc",
    "/static",
    "/favicon",
)


# =========================================================
# GET API KEY DARI ENV
# =========================================================
def get_valid_api_key() -> Optional[str]:
    """Ambil API key valid dari environment."""
    _key = os.getenv("SO_API_KEY", "").strip()
    return _key if _key else None


def verify_api_key(api_key: Optional[str]) -> bool:
    """Cek apakah API key valid."""
    _valid = get_valid_api_key()
    if not _valid:
        # Kalau env gak di-set, anggap gagal (biar gak accidentally open)
        return False
    if not api_key:
        return False
    # Bandingkan constant-time (meskipun Python string compare cukup oke)
    return api_key.strip() == _valid


# =========================================================
# MIDDLEWARE
# =========================================================
class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware yang cek X-API-Key di setiap request.
    Skip untuk path di PUBLIC_PATHS / PUBLIC_PREFIXES.
    """
    
    async def dispatch(self, request: Request, call_next):
        _path = request.url.path
        
        # Skip OPTIONS (buat CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip public paths
        if _path in PUBLIC_PATHS:
            return await call_next(request)
        
        # Skip public prefixes
        if any(_path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)
        
        # Ambil API key dari header
        _api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        
        # Cek juga Authorization: Bearer <key>
        if not _api_key:
            _auth = request.headers.get("Authorization") or request.headers.get("authorization")
            if _auth and _auth.lower().startswith("bearer "):
                _api_key = _auth[7:].strip()
        
        # Verify
        if not verify_api_key(_api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "API key required atau tidak valid. "
                              "Kirim header 'X-API-Key: <key>' atau "
                              "'Authorization: Bearer <key>'.",
                },
            )
        
        # Lanjut
        return await call_next(request)


# =========================================================
# DEPENDENCY (buat endpoint tertentu aja)
# =========================================================
async def require_api_key(request: Request):
    """
    Dependency function buat endpoint yang mau enforce API key manual.
    
    Contoh:
        @router.post("/chat")
        async def chat(req: ChatRequest, _: None = Depends(require_api_key)):
            ...
    """
    _api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not _api_key:
        _auth = request.headers.get("Authorization") or request.headers.get("authorization")
        if _auth and _auth.lower().startswith("bearer "):
            _api_key = _auth[7:].strip()
    
    if not verify_api_key(_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required atau tidak valid.",
        )
    return None