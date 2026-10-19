"""
Proxy Router — Menyembunyikan API Key dari Frontend (FIXED CORS)
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, Response
import httpx
import os

router = APIRouter()

INTERNAL_BACKEND_URL = os.getenv("INTERNAL_BACKEND_URL", "https://dashboard-so.fastapicloud.dev")
INTERNAL_API_KEY = os.getenv("SO_API_KEY")
ALLOWED_PREFIXES = ("yui/", "hana/", "rei/", "kurumi/", "config/", "auth/me", "auth/logout")

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_request(path: str, request: Request):
    # 1. Handle Preflight OPTIONS (Browser nanya dulu sebelum nembak)
    if request.method == "OPTIONS":
        return JSONResponse(
            status_code=200,
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )

    # 2. Validasi Path
    if not any(path.startswith(p) for p in ALLOWED_PREFIXES):
        raise HTTPException(status_code=403, detail=f"Path /{path} tidak diizinkan lewat proxy")

    # 3. Susun URL Tujuan
    url = f"{INTERNAL_BACKEND_URL}/api/{path}"
    
    # 4. Ambil Header & Body
    body = await request.body()
    auth_header = request.headers.get("Authorization")
    
    headers = {
        "X-API-Key": INTERNAL_API_KEY or "",
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
            
            # 6. ✅ FIX CORS: Tambahin header CORS manual ke response
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type=response.headers.get("content-type", "application/json"),
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Backend timeout")
        except Exception as e:
            print(f"[PROXY ERROR] {type(e).__name__}: {e}")
            raise HTTPException(status_code=502, detail="Gagal konek ke backend")