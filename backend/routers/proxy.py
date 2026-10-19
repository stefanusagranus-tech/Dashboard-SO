"""
Proxy Router — Versi Final (FIX CORS + 401)
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, Response
import httpx
import os

router = APIRouter()

INTERNAL_BACKEND_URL = os.getenv("INTERNAL_BACKEND_URL", "https://dashboard-so.fastapicloud.dev")
INTERNAL_API_KEY = os.getenv("SO_API_KEY")
ALLOWED_PREFIXES = ("yui/", "hana/", "rei/", "kurumi/", "config/", "auth/me", "auth/logout")

# Header CORS yang WAJIB ada di semua balasan
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Credentials": "true",
}

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_request(path: str, request: Request):
    # 1. Handle Preflight (Browser nanya dulu)
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=CORS_HEADERS)

    # 2. Validasi Path
    if not any(path.startswith(p) for p in ALLOWED_PREFIXES):
        return JSONResponse(
            status_code=403,
            content={"error": f"Path /{path} tidak diizinkan"},
            headers=CORS_HEADERS
        )

    # 3. Cek API Key Internal
    if not INTERNAL_API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "API Key internal kosong di server"},
            headers=CORS_HEADERS
        )

    # 4. Susun URL & Headers
    url = f"{INTERNAL_BACKEND_URL}/api/{path}"
    body = await request.body()
    auth_header = request.headers.get("Authorization")
    
    headers = {
        "X-API-Key": INTERNAL_API_KEY,
        "Content-Type": request.headers.get("content-type", "application/json"),
    }
    if auth_header:
        headers["Authorization"] = auth_header

    # 5. Teruskan Request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                timeout=60.0,
                follow_redirects=True
            )
            
            # 6. Balikin Response + Pastiin Header CORS Ada
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type=response.headers.get("content-type", "application/json"),
                headers=CORS_HEADERS
            )
        except httpx.TimeoutException:
            return JSONResponse(status_code=504, content={"error": "Backend timeout"}, headers=CORS_HEADERS)
        except Exception as e:
            print(f"[PROXY ERROR] {type(e).__name__}: {e}")
            return JSONResponse(status_code=502, content={"error": "Gagal konek ke backend"}, headers=CORS_HEADERS)