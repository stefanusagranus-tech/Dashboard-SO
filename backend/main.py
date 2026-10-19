"""
Dashboard SO C383 — FastAPI Backend (HARDENED v2)
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

app = FastAPI(
    title="Dashboard SO C383 API",
    description="Backend API untuk 4 AI assistant Toko C383",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =========================================================
# MIDDLEWARE (URUTAN PENTING!)
# =========================================================
# 1. CORS — Hanya izinkan domain frontend lu
_allowed = os.getenv("ALLOWED_ORIGINS", "https://stefanusagranus-tech.github.io").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Auth Middleware
app.add_middleware(AuthMiddleware)

# 3. Rate Limiting
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
# HEALTH & INFO
# =========================================================
@app.get("/")
async def root():
    return {"status": "ok", "service": "Dashboard SO C383 API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/bots")
async def list_bots():
    return {"bots": [
        {"id": "kurumi", "name": "Kurumi", "role": "Chief of Staff", "endpoint": "/api/kurumi/chat"},
        {"id": "hana", "name": "Hana", "role": "Master Shift", "endpoint": "/api/hana/chat"},
        {"id": "yui", "name": "Yui", "role": "Data Entry", "endpoint": "/api/yui/chat"},
        {"id": "rei", "name": "Rei", "role": "Analis SO", "endpoint": "/api/rei/chat"},
    ]}

# =========================================================
# GLOBAL ERROR HANDLER (ANTI-BOCOR)
# =========================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[ERROR] {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": "Terjadi kesalahan internal. Hubungi admin."},
    )

if __name__ == "__main__":
    import uvicorn
    _port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=_port, reload=True)