"""
Auth Middleware — API Key verification (FINAL FIX)
"""
import os
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

# Header CORS WAJIB ADA di setiap balasan error
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
}

PUBLIC_PATHS = {
    "/", "/health", "/docs", "/redoc", "/openapi.json",
    "/api/bots", "/api/config", "/api/config/",
    # AUTH
    "/api/auth/setup", "/api/auth/login", "/api/auth/verify-pin",
    "/api/auth/forgot-pin", "/api/auth/logout",
    # HEALTH SETIAP BOT
    "/api/yui/health", "/api/hana/health", "/api/rei/health", "/api/kurumi/health",
}

PUBLIC_PREFIXES = ("/docs", "/redoc", "/static", "/favicon", "/api/proxy")

def get_valid_api_key() -> Optional[str]:
    _key = os.getenv("SO_API_KEY", "").strip()
    return _key if _key else None

def verify_api_key(api_key: Optional[str]) -> bool:
    _valid = get_valid_api_key()
    if not _valid or not api_key:
        return False
    return api_key.strip() == _valid

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        _path = request.url.path
        
        # 1. Selalu izinkan OPTIONS (preflight CORS)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # 2. Cek path publik
        if _path in PUBLIC_PATHS:
            return await call_next(request)
        
        # 3. Cek prefix publik (termasuk /api/proxy)
        if any(_path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # 4. Cek dari URL query (buat WebView)
        _query_token = request.query_params.get("auth_token")
        _query_apikey = request.query_params.get("api_key")
        
        if _query_token and _query_apikey:
            if verify_api_key(_query_apikey):
                request.state.auth_token = _query_token
                return await call_next(request)
            else:
                return JSONResponse(
                    status_code=401,
                    content={"error": "API key URL invalid"},
                    headers=CORS_HEADERS  # ✅ TAMBAH CORS
                )

        # 5. Cek dari header
        _api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if not _api_key:
            _auth = request.headers.get("Authorization") or request.headers.get("authorization")
            if _auth and _auth.lower().startswith("bearer "):
                _api_key = _auth[7:].strip()
        
        if not verify_api_key(_api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "API key invalid"},
                headers=CORS_HEADERS  # ✅ TAMBAH CORS
            )
        
        return await call_next(request)