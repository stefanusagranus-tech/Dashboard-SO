# backend/routers/proxy.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import os

router = APIRouter()

# Ambil API Key dari .env (RAHASIA, gak dikirim ke frontend)
BACKEND_URL = os.getenv("BACKEND_URL", "https://dashboard-so.fastapicloud.dev")
INTERNAL_API_KEY = os.getenv("SO_API_KEY") # Ini key rahasia lu

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(path: str, request: Request):
    """
    Endpoint Proxy: Frontend nembak ke sini, Backend yang nerusin ke API asli.
    """
    url = f"{BACKEND_URL}/api/{path}"
    
    # Ambil token user dari header (kalo ada)
    auth_header = request.headers.get("Authorization")
    
    # Ambil body (kalo POST)
    body = await request.body()
    headers = {
        "X-API-Key": INTERNAL_API_KEY, # Inject API Key rahasia di sini!
        "Content-Type": "application/json",
    }
    if auth_header:
        headers["Authorization"] = auth_header
    
    # Terusin request ke API asli
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                timeout=30.0
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})