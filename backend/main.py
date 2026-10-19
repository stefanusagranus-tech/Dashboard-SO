"""
Dashboard SO C383 — FastAPI Backend (FINAL FIX)
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from routers import kurumi, hana, yui, rei, config, auth, proxy
from middleware.auth import AuthMiddleware
from middleware.rate_limit import setup_rate_limit

app = FastAPI(title="Dashboard SO C383 API", version="1.0.0", docs_url="/docs")

# =========================================================
# MIDDLEWARE — URUTAN PALING PENTING!
# =========================================================
# 1. CORS harus di paling atas kode (dieksekusi paling akhir)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Auth middleware
app.add_middleware(AuthMiddleware)

# 3. Rate limit
setup_rate_limit(app)

# =========================================================
# ROUTERS
# =========================================================
app.include_router(auth.router)
app.include_router(kurumi.router)
app.include_router(hana.router)
app.include_router(yui.router)
app.include_router(rei.router)
app.include_router(config.router)
app.include_router(proxy.router, prefix="/api/proxy")

# =========================================================
# HEALTH
# =========================================================
@app.get("/")
async def root():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# =========================================================
# GLOBAL ERROR HANDLER (WAJIB ADA CORS)
# =========================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[ERROR] {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": "Terjadi kesalahan internal."},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )