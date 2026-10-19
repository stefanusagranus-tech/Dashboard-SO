"""
Proxy Router — Menyembunyikan API Key dari Frontend
=====================================================
Frontend nembak ke /api/proxy/..., backend yang nerusin ke API asli
dengan nempelin X-API-Key rahasia. Frontend gak pernah tau key-nya.
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, Response
import httpx
import os

router = APIRouter()

# URL Backend asli (internal)
INTERNAL_BACKEND_URL = os.getenv("INTERNAL_BACKEND_URL", "https://dashboard-so.fastapicloud.dev")
# API Key Rahasia (dari .env, TIDAK dikirim ke frontend)
INTERNAL_API_KEY = os.getenv("SO_API_KEY")

# Daftar endpoint yang BOLEH diakses lewat proxy (whitelist)
ALLOWED_PREFIXES = ("yui/", "hana/", "rei/", "kurumi/", "config/", "auth/me", "auth/logout")

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(path: str, request: Request):
    # 1. VALIDASI PATH (Cegah SSRF / sembarang nembak)
    if not any(path.startswith(p) for p in ALLOWED_PREFIXES):
        raise HTTPException(status_code=403, detail=f"Path /{path} tidak diizinkan lewat proxy")

    # 2. SUSUN URL TUJUAN
    url = f"{INTERNAL_BACKEND_URL}/api/{path}"
    
    # 3. AMBIL HEADER & BODY DARI FRONTEND
    body = await request.body()
    auth_header = request.headers.get("Authorization")
    
    # 4. SUSUN HEADER BARU (Inject API Key Rahasia)
    headers = {
        "X-API-Key": INTERNAL_API_KEY or "",
        "Content-Type": request.headers.get("content-type", "application/json"),
    }
    if auth_header:
        headers["Authorization"] = auth_header

    # 5. TERUSKAN REQUEST KE BACKEND ASLI
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
            
            # 6. KEMBALIKAN RESPONSE KE FRONTEND (tanpa bawa API Key)
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type=response.headers.get("content-type", "application/json")
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Backend timeout")
        except Exception as e:
            # Jangan bocorin error detail ke frontend
            print(f"[PROXY ERROR] {type(e).__name__}: {e}")
            raise HTTPException(status_code=502, detail="Gagal konek ke backend")