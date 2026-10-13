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

# Load env
load_dotenv()

# Import routers
from routers import kurumi, hana, yui, rei

# Import auth middleware
from middleware.auth import AuthMiddleware


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
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# 1. CORS dulu
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Auth middleware setelah CORS
app.add_middleware(AuthMiddleware)


# =========================================================
# ROUTERS
# =========================================================
app.include_router(kurumi.router)
app.include_router(hana.router)
app.include_router(yui.router)
app.include_router(rei.router)


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