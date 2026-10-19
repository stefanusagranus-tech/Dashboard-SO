"""
Dashboard SO C383 — FastAPI Backend
=====================================
Backend API untuk 4 bot: Kurumi, Hana, Yui, Rei.

Arsitektur:
- Android frontend (Kotlin) → HTTP → FastAPI → Groq/Gemini/Supabase
- API Keys disimpan di environment variables, TIDAK di-expose ke client
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from routers import proxy

# Load env
load_dotenv()

# Import routers
from routers import kurumi, hana, yui, rei, config, auth

# Import auth middleware
from middleware.auth import AuthMiddleware
from middleware.rate_limit import setup_rate_limit      # ← BARU

# =========================================================
# APP INIT
# =========================================================
app = FastAPI(
    title="Dashboard SO C383 API",
    description="Backend API untuk 4 AI assistant Toko C383",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# =========================================================
# MIDDLEWARE
# =========================================================
# 1. CORS HARUS PALING BAWAH (Paling Akhir Dipasang = Paling Awal Dieksekusi)
# Ini biar semua response, termasuk error 401/500, tetep dapet header CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Pake ini aja buat development
    allow_credentials=False,      # HARUS False kalau pake allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 2. Auth middleware
app.add_middleware(AuthMiddleware)

# 3. Rate limiting
setup_rate_limit(app)                   # ← BARU


# =========================================================
# ROUTERS
# =========================================================
app.include_router(auth.router)      # ← TAMBAH INI
app.include_router(kurumi.router)
app.include_router(hana.router)
app.include_router(yui.router)
app.include_router(rei.router)
app.include_router(config.router)
app.include_router(proxy.router, prefix="/api/proxy")

# =========================================================
# HEALTH & INFO
# =========================================================
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Dashboard SO C383 API",
        "version": "1.0.0",
        "bots": ["kurumi", "hana", "yui", "rei"],
    }


@app.get("/health")
async def health():
    """Health check endpoint buat Render."""
    return {"status": "healthy"}


@app.get("/api/bots")
async def list_bots():
    """List semua bot yang tersedia."""
    return {
        "bots": [
            {
                "id": "kurumi",
                "name": "Kurumi",
                "role": "Chief of Staff",
                "endpoint": "/api/kurumi/chat",
            },
            {
                "id": "hana",
                "name": "Hana",
                "role": "Master Shift",
                "endpoint": "/api/hana/chat",
            },
            {
                "id": "yui",
                "name": "Yui",
                "role": "Data Entry",
                "endpoint": "/api/yui/chat",
            },
            {
                "id": "rei",
                "name": "Rei",
                "role": "Analis SO",
                "endpoint": "/api/rei/chat",
            },
        ]
    }


# =========================================================
# ERROR HANDLER
# =========================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[ERROR] {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)[:200], "type": type(exc).__name__},
    )


# =========================================================
# RUN (untuk dev lokal)
# =========================================================
if __name__ == "__main__":
    import uvicorn
    _port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=_port, reload=True)